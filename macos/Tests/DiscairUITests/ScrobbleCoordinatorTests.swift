import DiscairNavidrome
import Foundation
import Testing
@testable import DiscairUI

private final class FakeScrobbler: Scrobbling, @unchecked Sendable {
    struct Call: Equatable { let song: String; let time: Date; let submission: Bool }
    private let lock = NSLock()
    private var log: [Call] = []
    private var outcomes: [ScrobbleOutcome]
    init(outcomes: [ScrobbleOutcome] = []) { self.outcomes = outcomes }
    var calls: [Call] { lock.withLock { log } }
    func scrobble(songID: String, time: Date, submission: Bool) async -> ScrobbleOutcome {
        lock.withLock {
            log.append(Call(song: songID, time: time, submission: submission))
            return submission && !outcomes.isEmpty ? outcomes.removeFirst() : .sent
        }
    }
}

@MainActor
private func settle(_ condition: () -> Bool) async {
    for _ in 0..<300 where !condition() { try? await Task.sleep(for: .milliseconds(5)) }
}

@MainActor
private func playSeconds(_ c: ScrobbleCoordinator, _ seconds: Int, from: Double = 0, length: Double = 200) {
    var p = from
    c.update(position: p, playerDuration: length, isPlaying: true)
    for _ in 0..<(seconds * 4) { p += 0.25; c.update(position: p, playerDuration: length, isPlaying: true) }
}

@MainActor
struct ScrobbleCoordinatorTests {
    private func make(_ f: FakeScrobbler, enabled: Bool = true) -> ScrobbleCoordinator {
        let c = ScrobbleCoordinator(enabled: enabled, sleep: { _ in })
        c.configure(client: f)
        return c
    }

    @Test func nowPlayingThenOneScrobbleWithTheStartTime() async {
        let f = FakeScrobbler(), c = make(f)
        c.begin(songID: "s1", duration: 200)
        playSeconds(c, 120)
        await settle { f.calls.count == 2 }
        #expect(f.calls.map(\.submission) == [false, true] && f.calls.allSatisfy { $0.song == "s1" })
        #expect(f.calls[0].time == f.calls[1].time)
        playSeconds(c, 30, from: 120)
        try? await Task.sleep(for: .milliseconds(30))
        #expect(f.calls.count == 2)
    }

    @Test func aTrackThatNeverPlaysSendsNothing() async {
        let f = FakeScrobbler(), c = make(f)
        c.begin(songID: "s1", duration: 200)
        c.update(position: 0, playerDuration: 200, isPlaying: false)
        try? await Task.sleep(for: .milliseconds(30))
        #expect(f.calls.isEmpty)
    }

    @Test func aNeverSentRequestIsRetriedUpToThreeTimes() async {
        let f = FakeScrobbler(outcomes: [.notSent, .notSent, .notSent, .notSent, .notSent]), c = make(f)
        c.begin(songID: "s1", duration: 60)
        playSeconds(c, 30, length: 60)
        await settle { f.calls.filter(\.submission).count == 4 }
        try? await Task.sleep(for: .milliseconds(30))
        let finals = f.calls.filter(\.submission)
        #expect(finals.count == 4)                                   // one send and three retries
        #expect(Set(finals.map(\.time)).count == 1)                  // the original start time each time
    }

    @Test func anUncertainOutcomeIsNeverRetried() async {
        let f = FakeScrobbler(outcomes: [.unknown]), c = make(f)
        c.begin(songID: "s1", duration: 60)
        playSeconds(c, 30, length: 60)
        await settle { f.calls.filter(\.submission).count == 1 }
        try? await Task.sleep(for: .milliseconds(30))
        #expect(f.calls.filter(\.submission).count == 1)
    }

    @Test func offSendsNothingAndOnMidSongCountsFromThen() async {
        let f = FakeScrobbler(), c = make(f, enabled: false)
        c.begin(songID: "s1", duration: 60)
        playSeconds(c, 40, length: 60)
        try? await Task.sleep(for: .milliseconds(30))
        #expect(f.calls.isEmpty)
        c.isEnabled = true                                           // no backfill: 40 s already played do not count
        playSeconds(c, 10, from: 40, length: 60)
        await settle { f.calls.count == 1 }
        #expect(f.calls.map(\.submission) == [false])
        playSeconds(c, 25, from: 50, length: 60)
        await settle { f.calls.count == 2 }
        #expect(f.calls.map(\.submission) == [false, true])
    }

    @Test func turningItOffCancelsAPendingRetry() async {
        let gate = AsyncGate()
        let f = FakeScrobbler(outcomes: [.notSent, .notSent, .notSent, .notSent])
        let c = ScrobbleCoordinator(sleep: { _ in await gate.wait() })
        c.configure(client: f)
        c.begin(songID: "s1", duration: 60)
        playSeconds(c, 30, length: 60)
        await settle { f.calls.filter(\.submission).count == 1 }
        c.isEnabled = false
        await gate.open()
        try? await Task.sleep(for: .milliseconds(30))
        #expect(f.calls.filter(\.submission).count == 1)
    }

    @Test func aNewPlayOfTheSameSongScrobblesAgain() async {
        let f = FakeScrobbler(), c = make(f)
        for _ in 0..<2 { c.begin(songID: "s1", duration: 60); playSeconds(c, 30, length: 60) }
        await settle { f.calls.filter(\.submission).count == 2 }
        #expect(f.calls.filter(\.submission).count == 2)
    }
}

private actor AsyncGate {
    private var opened = false
    private var waiters: [CheckedContinuation<Void, Never>] = []
    func wait() async { if opened { return }; await withCheckedContinuation { waiters.append($0) } }
    func open() { opened = true; waiters.forEach { $0.resume() }; waiters = [] }
}
