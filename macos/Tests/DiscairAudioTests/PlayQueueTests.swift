import Foundation
import Testing
@testable import DiscairAudio

/// Same shuffle every run.
struct Seeded: RandomNumberGenerator {
    var state: UInt64
    mutating func next() -> UInt64 { state = state &* 6364136223846793005 &+ 1442695040888963407; return state >> 11 }
}

private func songs(_ n: Int) -> [QueueItem] { (0..<n).map { QueueItem(songID: "s\($0)", title: "T\($0)", artist: "A") } }
private func titles(_ q: PlayQueue) -> [String] { ([q.current].compactMap { $0 } + q.upNext).map(\.title) }

@Suite("Play queue") struct PlayQueueTests {
    @Test func startsAtTheChosenSongAndWalksForwardThenStops() {
        var q = PlayQueue(); q.set(songs(4), startAt: 1)
        #expect(q.current?.title == "T1" && q.upNext.map(\.title) == ["T2", "T3"])
        #expect(q.advance(natural: true)?.title == "T2")
        #expect(q.advance(natural: true)?.title == "T3")
        #expect(q.advance(natural: true) == nil && q.current?.title == "T3")   // finished; stays on the last song
    }

    @Test func repeatAllWrapsAndRepeatOneReplaysOnlyWhenTheSongEnds() {
        var q = PlayQueue(); q.set(songs(2), startAt: 1); q.repeatMode = .all
        #expect(q.advance(natural: true)?.title == "T0")
        q.repeatMode = .one
        #expect(q.advance(natural: true)?.title == "T0")      // ended by itself: same song
        #expect(q.advance(natural: false)?.title == "T1")     // owner pressed next: moves on
    }

    @Test func backStepsAndWrapsOnlyWithRepeatAll() {
        var q = PlayQueue(); q.set(songs(3), startAt: 1)
        #expect(q.back()?.title == "T0" && q.back()?.title == "T0")
        q.repeatMode = .all
        #expect(q.back()?.title == "T2")
    }

    @Test func playNextGoesRightAfterTheCurrentSongAndAppendGoesLast() {
        var q = PlayQueue(); q.set(songs(3), startAt: 0)
        q.playNext(QueueItem(songID: "n", title: "Next", artist: "A"))
        q.append(QueueItem(songID: "e", title: "End", artist: "A"))
        #expect(titles(q) == ["T0", "Next", "T1", "T2", "End"])
        #expect(q.items.map(\.title) == ["T0", "Next", "T1", "T2", "End"])
    }

    @Test func playNextOnAnEmptyQueueSelectsIt() {
        var q = PlayQueue(); q.playNext(QueueItem(songID: "n", title: "Only", artist: "A"))
        #expect(q.current?.title == "Only")
    }

    @Test func reorderAndRemoveWorkInUpNext() {
        var q = PlayQueue(); q.set(songs(5), startAt: 0)
        q.moveUpNext(from: 0, to: 2)
        #expect(q.upNext.map(\.title) == ["T2", "T3", "T1", "T4"])
        q.removeUpNext(at: 1)
        #expect(q.upNext.map(\.title) == ["T2", "T1", "T4"] && q.current?.title == "T0")
        #expect(q.advance(natural: true)?.title == "T2")
    }

    @Test func shuffleKeepsTheCurrentSongFirstAndPlaysEverythingOnce() {
        var rng = Seeded(state: 7)
        var q = PlayQueue(); q.set(songs(8), startAt: 3, using: &rng)
        q.setShuffle(true, using: &rng)
        #expect(q.current?.title == "T3" && q.upNext.count == 7)
        #expect(Set(titles(q)).count == 8)
        q.setShuffle(false, using: &rng)
        #expect(q.current?.title == "T3" && q.upNext.map(\.title) == ["T4", "T5", "T6", "T7"])   // back to list order from here
    }

    @Test func selectJumpsToASongInTheList() {
        var q = PlayQueue(); q.set(songs(4), startAt: 0)
        q.select(index: 2)
        #expect(q.current?.title == "T2" && q.upNext.map(\.title) == ["T3"])
    }
}
