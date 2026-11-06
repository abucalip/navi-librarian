import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

private let clockNow = Date(timeIntervalSince1970: 1_800_000_000)

@MainActor
private final class SkipLog {
    var events: [FeedbackEvent] = []
}

/// Plays `seconds` of counted time, a quarter second per reading (the tracker counts forward steps only).
@MainActor
private func play(_ c: ScrobbleCoordinator, seconds: Int, length: Double = 200) {
    c.update(position: 0, playerDuration: length, isPlaying: true)
    var p = 0.0
    for _ in 0..<(seconds * 4) { p += 0.25; c.update(position: p, playerDuration: length, isPlaying: true) }
}

@MainActor
struct ScrobbleSkipFeedbackTests {
    private func make(_ log: SkipLog) -> ScrobbleCoordinator {
        let c = ScrobbleCoordinator(enabled: true, now: { clockNow }, sleep: { _ in })
        c.onSkip = { log.events.append($0) }
        return c
    }

    @Test func leavingEarlyByOwnerIsReportedAsASkip() {
        let log = SkipLog(), c = make(log)
        c.begin(songID: "navidrome-song-1", duration: 200, mbid: "3F2504E0-4F89-41D3-9A0C-0305E82C3301")
        play(c, seconds: 12)
        c.end(leftByOwner: true, wasLastInQueue: false)

        #expect(log.events.count == 1)
        let e = log.events.first
        #expect(e?.kind == .skip && e?.subjectKind == .track && e?.subjectID == "navidrome-song-1")
        #expect(e?.client == "macos")
        #expect(e?.mbid == "3f2504e0-4f89-41d3-9a0c-0305e82c3301")
        #expect(e?.occurredAt == clockNow.timeIntervalSince1970)
        #expect(abs((e?.playedSeconds ?? -1) - 12) < 0.01)
        #expect(e?.durationSeconds == 200)
    }

    @Test func mbidIsOmittedUnlessItIsAKnownUUID() {
        let log = SkipLog(), c = make(log)
        c.begin(songID: "a", duration: 200)
        play(c, seconds: 5)
        c.end(leftByOwner: true)
        c.begin(songID: "b", duration: 200, mbid: "not-a-uuid")
        play(c, seconds: 5)
        c.end(leftByOwner: true)

        #expect(log.events.map(\.mbid) == [nil, nil])
    }

    @Test func naturalEndIsNotASkip() {
        let log = SkipLog(), c = make(log)
        c.begin(songID: "s", duration: 200)
        play(c, seconds: 5)
        c.end()

        #expect(log.events.isEmpty)
    }

    @Test func leavingTheLastSongInTheQueueIsNotASkip() {
        let log = SkipLog(), c = make(log)
        c.begin(songID: "s", duration: 200)
        play(c, seconds: 5)
        c.end(leftByOwner: true, wasLastInQueue: true)

        #expect(log.events.isEmpty)
    }

    @Test func aLongEnoughPlayIsNotASkip() {
        let log = SkipLog(), c = make(log)
        c.begin(songID: "s", duration: 200)
        play(c, seconds: 40)
        c.end(leftByOwner: true, wasLastInQueue: false)

        #expect(log.events.isEmpty)
    }

    @Test func noSkipIsRecordedWhenNothingWasPlaying() {
        let log = SkipLog(), c = make(log)
        c.end(leftByOwner: true, wasLastInQueue: false)

        #expect(log.events.isEmpty)
    }
}
