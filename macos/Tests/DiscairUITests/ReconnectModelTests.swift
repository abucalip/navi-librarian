import DiscairAudio
import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import Foundation
import Testing
@testable import DiscairAudio
@testable import DiscairUI

/// Holds every wait the model asks for until the test lets it go, and remembers its length.
@MainActor
private final class Gate {
    var delays: [TimeInterval] = []
    private var waiting: [(TimeInterval, CheckedContinuation<Void, Never>)] = []
    func wait(_ d: TimeInterval) async {
        delays.append(d)
        await withCheckedContinuation { waiting.append((d, $0)) }
    }
    /// Lets the waits of this length go (the watchdog waits 20 s, a try waits its backoff).
    func release(_ d: TimeInterval) async {
        for _ in 0..<20 { await Task.yield() }              // let the model's task reach its wait
        let ready = waiting.filter { $0.0 == d }
        waiting.removeAll { $0.0 == d }
        for (_, c) in ready { c.resume() }
        for _ in 0..<20 { await Task.yield() }
    }
}

@MainActor
private final class QuietOutput: AudioOutput {
    var onFinished: (() -> Void)?
    var onAdvanced: (() -> Void)?
    var isPlaying = false
    var position: Double = 0
    var duration: Double = 200
    var volume: Float = 1
    func open(file: URL) throws {}
    func play() { isPlaying = true }
    func pause() { isPlaying = false }
    func stop() { isPlaying = false }
    func seek(to seconds: Double) {}
    func preload(file: URL, transition: Transition) throws {}
    func cancelPreload() {}
    func applyEQ(gains: [Double], preGain: Double) {}
    func restoreOutputRate() {}
}

private final class QuietFetcher: AudioFetcher, @unchecked Sendable {
    func fetch(_ url: URL, suffix: String?) async throws -> URL {
        let f = FileManager.default.temporaryDirectory.appending(path: "rc-\(UUID().uuidString).\(suffix ?? "bin")")
        try Data([0]).write(to: f)
        return f
    }
}

private let fip = RadioStation(id: "1", name: "FIP", proxied: true, playableURL: "/radio/stream/tok1", favourite: true)

@MainActor
private func make() throws -> (PlayerModel, FakeLiveOutput, Gate, QuietOutput) {
    let live = FakeLiveOutput(), out = QuietOutput(), gate = Gate()
    let defaults = UserDefaults(suiteName: "discair-reconnect-\(UUID().uuidString)")!
    let p = PlayerModel(output: out, fetcher: QuietFetcher(), defaults: defaults, liveOutput: live)
    p.configure(urls: try StreamURLBuilder(baseURL: URL(string: "https://navi.example.ts.net")!, auth: SubsonicAuth(credential: Credential(username: "o", password: "pw"))))
    p.liveBase = URL(string: "http://librarian.example.invalid:8689")
    p.reconnectPause = { await gate.wait($0) }
    return (p, live, gate, out)
}

@MainActor
struct ReconnectModelTests {
    @Test func aDropWaitsTwoSecondsThenStartsTheStreamAgain() async throws {
        let (p, live, gate, _) = try make()
        p.playStation(fip)
        live.report(.playing)
        live.report(.failed)
        #expect(p.live?.phase == .reconnecting && p.live?.reconnect?.attempt == 1 && p.live?.reconnect?.of == 5)
        #expect(live.started.count == 1)
        await gate.release(2)
        #expect(live.started.count == 2 && live.started[1] == live.started[0])
        #expect(p.live?.phase == .reconnecting)          // still "Reconnecting…" until sound arrives
        live.report(.connecting); #expect(p.live?.phase == .reconnecting)
        live.report(.playing)
        #expect(p.live?.phase == .playing && p.live?.reconnect == nil)
    }

    @Test func eachFailureWaitsLongerAndTheSixthIsUnreachable() async throws {
        let (p, live, gate, _) = try make()
        p.playStation(fip)
        live.report(.playing)
        for (i, delay) in [2.0, 5, 10, 20, 30].enumerated() {
            live.report(.failed)
            #expect(p.live?.reconnect?.attempt == i + 1)
            await gate.release(delay)
            #expect(live.started.count == i + 2)
        }
        live.report(.failed)
        #expect(p.live?.phase == .unreachable && p.live?.reconnect == nil && p.live?.phaseSentence == "Station unreachable")
        let started = live.started.count
        await gate.release(30); await gate.release(20)
        #expect(live.started.count == started)            // nothing more is tried
    }

    @Test func retryStartsAFreshRoundAfterUnreachable() async throws {
        let (p, live, gate, _) = try make()
        p.playStation(fip)
        for delay in [2.0, 5, 10, 20, 30] { live.report(.failed); await gate.release(delay) }
        live.report(.failed)
        #expect(p.live?.phase == .unreachable)
        let started = live.started.count
        p.retryStation()
        #expect(live.started.count == started + 1 && p.live?.phase == .connecting)
        live.report(.failed)
        #expect(p.live?.reconnect?.attempt == 1)          // the count began again
    }

    @Test func retryDoesNothingWhileAStationIsNotUnreachable() async throws {
        let (p, live, _, _) = try make()
        p.playStation(fip); live.report(.playing)
        p.retryStation()
        #expect(live.started.count == 1)
    }

    @Test func soundResetsTheCount() async throws {
        let (p, live, gate, _) = try make()
        p.playStation(fip)
        live.report(.failed); await gate.release(2)
        live.report(.failed); await gate.release(5)
        live.report(.playing)
        live.report(.failed)
        #expect(p.live?.reconnect?.attempt == 1)
        _ = gate
    }

    @Test func nothingIsTriedAfterTheOwnerPressedStop() async throws {
        let (p, live, gate, _) = try make()
        p.playStation(fip); live.report(.playing)
        live.report(.failed)
        p.stopStation()
        let started = live.started.count
        await gate.release(2)
        #expect(live.started.count == started && p.live == nil)
        live.report(.failed)
        #expect(p.live == nil && live.started.count == started)
    }

    @Test func twentySecondsWithoutSoundCountsAsADrop() async throws {
        let (p, live, gate, _) = try make()
        p.playStation(fip)                                // connecting, no sound ever
        await gate.release(20)
        #expect(p.live?.reconnect?.attempt == 1 && p.live?.phase == .reconnecting)
        _ = live
    }

    @Test func soundCancelsTheWatchdog() async throws {
        let (p, live, gate, _) = try make()
        p.playStation(fip); live.report(.playing)
        await gate.release(20)
        #expect(p.live?.phase == .playing && p.live?.reconnect == nil)
    }

    @Test func aStallThatLastsTwentySecondsIsADrop() async throws {
        let (p, live, gate, _) = try make()
        p.playStation(fip); live.report(.playing)
        live.report(.stalled)
        #expect(p.live?.phase == .reconnecting && p.live?.reconnect == nil && p.live?.phaseSentence == "Reconnecting…")
        await gate.release(20)
        #expect(p.live?.reconnect?.attempt == 1)
    }

    @Test func nothingIsTriedWhileTheMacSleepsAndOneFreshRoundHappensOnWake() async throws {
        let (p, live, gate, _) = try make()
        p.playStation(fip); live.report(.playing)
        live.report(.failed); live.report(.failed)        // a second report while waiting is a drop too
        p.systemWillSleep()
        let started = live.started.count
        await gate.release(2); await gate.release(5)
        #expect(live.started.count == started)
        live.report(.failed)
        #expect(p.live?.phase != .unreachable)
        p.systemDidWake()
        #expect(live.started.count == started + 1 && p.live?.phase == .connecting)
        live.report(.failed)
        #expect(p.live?.reconnect?.attempt == 1)          // a fresh round
    }

    @Test func wakeStartsNothingWhenNoStationWasPlaying() async throws {
        let (p, live, _, _) = try make()
        p.systemWillSleep(); p.systemDidWake()
        #expect(live.started.isEmpty)
        p.playStation(fip); p.stopStation()
        let started = live.started.count
        p.systemWillSleep(); p.systemDidWake()
        #expect(live.started.count == started)
    }

    @Test func theSentencesCountDownAndNameTheAttempt() {
        var s = LiveSession(stationID: "1", name: "FIP", logoPath: "", startedAt: Date(), phase: .reconnecting)
        let at = Date(timeIntervalSince1970: 5_000)
        s.reconnect = .init(attempt: 2, of: 5, retryAt: at.addingTimeInterval(5))
        #expect(s.phaseSentence(at: at) == "Connection lost · trying again in 5 s (attempt 2 of 5)")
        #expect(s.phaseSentence(at: at.addingTimeInterval(2.4)) == "Connection lost · trying again in 3 s (attempt 2 of 5)")
        #expect(s.phaseSentence(at: at.addingTimeInterval(5)) == "Reconnecting… (attempt 2 of 5)")
        s.reconnect = nil
        #expect(s.phaseSentence(at: at) == "Reconnecting…")
        s.phase = .unreachable
        #expect(s.phaseSentence(at: at) == "Station unreachable")
    }

    // MARK: Sleep timer expiry

    @Test func theTimerStopsAStationAndPlayStartsItAgain() async throws {
        let (p, live, _, _) = try make()
        p.playStation(fip); live.report(.playing)
        p.sleepTimer.start(minutes: 15)
        p.sleepTimerExpired()
        #expect(p.live == nil && live.stops >= 1)
        #expect(p.sleepTimer.isRunning == false)
        p.togglePlayPause()
        #expect(p.live?.stationID == "1")
    }

    @Test func theTimerPausesALibrarySong() async throws {
        let (p, _, _, out) = try make()
        p.play((0..<2).map { QueueItem(songID: "s\($0)", title: "T", artist: "A", album: "Al", duration: 200, suffix: "mp3", track: $0 + 1, disc: 1) })
        for _ in 0..<200 where p.phase != .playing { try? await Task.sleep(for: .milliseconds(10)) }
        #expect(p.phase == .playing)
        p.sleepTimer.start(minutes: 30)
        p.sleepTimerExpired()
        #expect(p.phase == .paused && !out.isPlaying)
    }

    @Test func stoppingAStationOrTheQueueCancelsTheTimer() async throws {
        let (p, live, _, _) = try make()
        p.playStation(fip); live.report(.playing)
        p.sleepTimer.start(minutes: 45)
        #expect(p.sleepTimer.isRunning)
        p.stopStation()
        #expect(!p.sleepTimer.isRunning)
        p.sleepTimer.start(minutes: 45)
        p.stop()
        #expect(!p.sleepTimer.isRunning)
    }
}
