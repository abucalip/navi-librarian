import DiscairAudio
import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import Foundation
import Testing
@testable import DiscairAudio
@testable import DiscairUI

@MainActor
private final class FakeOutput: AudioOutput {
    var onFinished: (() -> Void)?
    var isPlaying = false
    var position: Double = 0
    var duration: Double = 200
    var opened: [URL] = []
    var seeks: [Double] = []
    var failNextOpen = false
    func open(file: URL) throws {
        if failNextOpen { failNextOpen = false; throw AudioError("This file could not be opened for playback.") }
        opened.append(file); position = 0
    }
    func play() { isPlaying = true }
    func pause() { isPlaying = false }
    func stop() { isPlaying = false }
    func seek(to seconds: Double) { seeks.append(seconds); position = seconds }
    var onAdvanced: (() -> Void)?
    var preloads: [Transition] = []
    var cancels = 0
    func preload(file: URL, transition: Transition) throws { preloads.append(transition) }
    func cancelPreload() { cancels += 1 }
    var volume: Float = 1
    var eqApplied: [(gains: [Double], preGain: Double)] = []
    func applyEQ(gains: [Double], preGain: Double) { eqApplied.append((gains, preGain)) }
    var rateMatching: [Bool] = []
    var restores = 0
    func setMatchOutputRate(_ on: Bool) { rateMatching.append(on) }
    func restoreOutputRate() { restores += 1 }
    var growingOpened = 0
    var isGrowing = false
    func openGrowing(_ download: GrowingDownload, expectedDuration: Double) throws { growingOpened += 1; isGrowing = true; position = 0 }
    func advance() { position = 0; onAdvanced?() }
    func finish() { isPlaying = false; onFinished?() }
}

private final class FakeFetcher: AudioFetcher, @unchecked Sendable {
    private let lock = NSLock()
    private var urls: [URL] = []
    var requested: [URL] { lock.withLock { urls } }
    func fetch(_ url: URL, suffix: String?) async throws -> URL {
        lock.withLock { urls.append(url) }
        let f = FileManager.default.temporaryDirectory.appending(path: "fake-\(UUID().uuidString).\(suffix ?? "bin")")
        try Data([0]).write(to: f)
        return f
    }
}

/// Hands out one growing download that the test controls.
private final class GrowingFetcher: AudioFetcher, @unchecked Sendable {
    let download = GrowingDownload(file: FileManager.default.temporaryDirectory.appending(path: "grow-\(UUID().uuidString).mp3"))
    func fetch(_ url: URL, suffix: String?) async throws -> URL { throw AudioError("whole-file path not expected") }
    func beginGrowing(_ url: URL, suffix: String?) -> GrowingDownload? { download }
}

private func streamBuilder() throws -> StreamURLBuilder {
    try StreamURLBuilder(baseURL: URL(string: "https://navi.example.ts.net")!, auth: SubsonicAuth(credential: Credential(username: "o", password: "pw")))
}

private func songs(_ n: Int, suffix: String? = "flac", album: String? = nil) -> [QueueItem] {
    (0..<n).map { QueueItem(songID: "s\($0)", title: "T\($0)", artist: "A", album: "Al", albumID: album, duration: 200, suffix: suffix, track: $0 + 1, disc: 1) }
}

@MainActor
private func make() throws -> (PlayerModel, FakeOutput, FakeFetcher) {
    let out = FakeOutput(), fetch = FakeFetcher()
    let p = PlayerModel(output: out, fetcher: fetch, defaults: UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!)
    p.configure(urls: try streamBuilder())
    return (p, out, fetch)
}

@MainActor
private func until(_ condition: () -> Bool) async {
    for _ in 0..<500 where !condition() { try? await Task.sleep(for: .milliseconds(10)) }
}

@MainActor
struct GrowingFailureTests {
    @Test func aBrokenDownloadSaysSoWhenItsSongEnds() async throws {
        let out = FakeOutput(), fetch = GrowingFetcher()
        let p = PlayerModel(output: out, fetcher: fetch, defaults: UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!)
        p.configure(urls: try streamBuilder())
        fetch.download.setState(bytes: 300_000, complete: false)        // enough to start an MP3
        p.play(songs(2, suffix: "mp3"))
        await until { p.phase == .playing }
        #expect(out.growingOpened == 1 && p.notice == nil)

        fetch.download.setState(bytes: 300_000, complete: false, failure: "The song could not be streamed.")
        await until { p.notice != nil }
        #expect(p.notice == "“T0” stopped downloading, so it ended early.")

        out.finish()                                                   // the engine plays out what arrived, then ends the song
        #expect(p.current?.title == "T1")
        #expect(p.notice == "“T0” stopped downloading, so it ended early.")   // kept across the start of the next song
    }

    @Test func aSongThatEndsWellBeforeItsLengthSaysSo() async throws {
        let (p, out, _) = try make()
        p.play(songs(2))
        await until { p.phase == .playing }
        out.position = 60
        await until { p.position == 60 }
        out.finish()
        #expect(p.current?.title == "T1" && p.notice == "“T0” ended at 1:00 of 3:20.")
    }

    @Test func theClockCarriesOnBetweenTicksAndNeverRunsBack() async throws {
        let (p, out, _) = try make()
        p.play(songs(1))
        await until { p.phase == .playing }
        out.position = 30
        await until { p.position == 30 }
        let now = Date()
        #expect(p.displayPosition(at: now.addingTimeInterval(0.5)) >= 30.4)
        #expect(p.displayPosition(at: now.addingTimeInterval(60)) <= 32.1)      // a stalled tick is carried at most 2 s
        #expect(p.displayPosition(at: now.addingTimeInterval(-5)) >= 30)
    }

    @Test func aCompleteDownloadSaysNothing() async throws {
        let out = FakeOutput(), fetch = GrowingFetcher()
        let p = PlayerModel(output: out, fetcher: fetch, defaults: UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!)
        p.configure(urls: try streamBuilder())
        fetch.download.setState(bytes: 300_000, complete: true)
        p.play(songs(2, suffix: "mp3"))
        await until { p.phase == .playing }
        out.finish()
        #expect(p.current?.title == "T1" && p.notice == nil)
    }
}

@MainActor
struct PlayerModelTests {
    @Test func playLoadsTheSongThenPlaysIt() async throws {
        let (p, out, fetch) = try make()
        p.play(songs(3), startAt: 1)
        #expect(p.phase == .loading && p.current?.title == "T1")
        await until { p.phase == .playing }
        #expect(p.isPlaying && out.isPlaying && out.opened.count == 1 && p.duration == 200)
        #expect(fetch.requested.first?.path.hasSuffix("rest/stream") == true)
        #expect(URLComponents(url: fetch.requested[0], resolvingAgainstBaseURL: false)?.queryItems?.contains { $0.name == "id" && $0.value == "s1" } == true)
    }

    @Test func pauseAndResume() async throws {
        let (p, out, _) = try make()
        p.play(songs(2))
        await until { p.isPlaying }
        p.togglePlayPause()
        #expect(p.phase == .paused && !out.isPlaying)
        p.togglePlayPause()
        #expect(p.phase == .playing && out.isPlaying)
    }

    @Test func aFinishedSongStartsTheNextAndTheLastOneStops() async throws {
        let (p, out, _) = try make()
        p.play(songs(2))
        await until { p.isPlaying }
        out.finish()
        #expect(p.current?.title == "T1")
        await until { p.isPlaying }
        out.finish()
        #expect(p.phase == .idle)
    }

    @Test func repeatOneReplaysTheSameSong() async throws {
        let (p, out, _) = try make()
        p.play(songs(2))
        p.cycleRepeat(); p.cycleRepeat()
        #expect(p.repeatMode == .one)
        await until { p.isPlaying }
        out.finish()
        #expect(p.current?.title == "T0")
        await until { out.opened.count == 2 }
        #expect(out.opened.count == 2)
    }

    @Test func previousRestartsAfterThreeSecondsOtherwiseGoesBack() async throws {
        let (p, out, _) = try make()
        p.play(songs(3), startAt: 2)
        await until { p.isPlaying }
        out.position = 10; p.previous()
        #expect(out.seeks == [0] && p.current?.title == "T2")
        out.position = 1
        p.previous()
        #expect(p.current?.title == "T1")
    }

    @Test func seekingUsesAFractionOfTheDuration() async throws {
        let (p, out, _) = try make()
        p.play(songs(1))
        await until { p.isPlaying }
        p.seek(toFraction: 0.25)
        #expect(out.seeks == [50] && p.position == 50 && p.fraction == 0.25)
    }

    @Test func vorbisAndWmaAskTheServerForOpusAt192OthersPlayTheOriginal() async throws {
        let (p, _, fetch) = try make()
        p.play(songs(1, suffix: "ogg"))
        await until { !fetch.requested.isEmpty }
        let q = URLComponents(url: fetch.requested[0], resolvingAgainstBaseURL: false)!.queryItems!
        #expect(q.contains { $0.name == "format" && $0.value == "opus" } && q.contains { $0.name == "maxBitRate" && $0.value == "192" })
        #expect(PlayerModel.streamOptions(suffix: "flac").format == nil && PlayerModel.streamOptions(suffix: "MP3").bitRate == nil)
    }

    @Test func withoutAConnectionItSaysSoInsteadOfPlaying() {
        let p = PlayerModel(output: FakeOutput(), fetcher: FakeFetcher())
        p.play(songs(1))
        #expect(p.phase == .failed("Not connected to Navidrome. Check Settings."))
    }

    @Test func playNextOnAnIdlePlayerStartsIt() async throws {
        let (p, _, _) = try make()
        p.playNext(songs(1)[0])
        await until { p.isPlaying }
        #expect(p.current?.title == "T0")
    }

    // MARK: Gapless and crossfade

    @Test func theNextSongIsPreloadedGaplessByDefaultAndTheEngineAdvancesTheQueue() async throws {
        let (p, out, _) = try make()
        p.play(songs(3))
        await until { !out.preloads.isEmpty }
        #expect(out.preloads == [.gapless])
        out.advance()
        #expect(p.current?.title == "T1" && p.isPlaying && p.history.first?.title == "T0")
        await until { out.preloads.count == 2 }
        #expect(out.preloads.count == 2)          // T2 is handed over next
        #expect(out.opened.count == 1)            // the join needed no new open
    }

    @Test func crossfadeAppliesToUnrelatedSongsButNotToAContinuousAlbum() async throws {
        let (p, out, _) = try make()
        p.crossfadeSeconds = 6
        p.play(songs(2))                                          // no album ids: unrelated songs
        await until { !out.preloads.isEmpty }
        #expect(out.preloads == [.crossfade(6)])
        let (p2, out2, _) = try make()
        p2.crossfadeSeconds = 6
        p2.play(songs(2, album: "al1"))                           // tracks 1 and 2 of one album
        await until { !out2.preloads.isEmpty }
        #expect(out2.preloads == [.gapless])
    }

    @Test func rateMatchingIsOffByDefaultAndTellsTheOutput() throws {
        let (p, out, _) = try make()
        #expect(!p.matchOutputRate)
        #expect(out.rateMatching == [false])
        p.matchOutputRate = true
        #expect(out.rateMatching == [false, true])
        p.restoreOutputRate()
        #expect(out.restores == 1)
    }

    @Test func changingWhatIsNextReplacesThePreload() async throws {
        let (p, out, _) = try make()
        p.play(songs(3))
        await until { out.preloads.count == 1 }
        p.playNext(QueueItem(songID: "x", title: "X", artist: "A", duration: 100, suffix: "mp3"))
        await until { out.preloads.count == 2 }
        #expect(out.cancels >= 1 && out.preloads.count == 2)
        out.advance()
        #expect(p.current?.title == "X")
    }

    @Test func skippingDropsThePreloadAndClearUpNextRemovesIt() async throws {
        let (p, out, _) = try make()
        p.play(songs(4))
        await until { out.preloads.count == 1 }
        p.clearUpNext()
        #expect(out.cancels >= 1 && p.queue.upNext.isEmpty)
    }

    @Test func jumpPlaysTheChosenSongAndRemembersTheOne() async throws {
        let (p, _, _) = try make()
        p.play(songs(4))
        await until { p.isPlaying }
        p.jump(toUpNext: 1)
        #expect(p.current?.title == "T2" && p.history.first?.title == "T0")
    }

    @Test func theCrossfadeChoiceIsRemembered() {
        let suite = UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!
        let a = PlayerModel(output: FakeOutput(), fetcher: FakeFetcher(), defaults: suite)
        #expect(a.crossfadeSeconds == 0)
        a.crossfadeSeconds = 4
        #expect(PlayerModel(output: FakeOutput(), fetcher: FakeFetcher(), defaults: suite).crossfadeSeconds == 4)
    }

    @Test func continuousMeansTheNextTrackOfTheSameAlbum() {
        func item(_ album: String?, _ track: Int?, _ disc: Int? = 1) -> QueueItem { QueueItem(songID: "x", title: "t", artist: "a", albumID: album, track: track, disc: disc) }
        #expect(PlayerModel.isContinuous(item("a", 3), item("a", 4)))
        #expect(PlayerModel.isContinuous(item("a", 12), item("a", 1, 2)))     // next disc
        #expect(!PlayerModel.isContinuous(item("a", 3), item("a", 5)))
        #expect(!PlayerModel.isContinuous(item("a", 3), item("b", 4)))
        #expect(!PlayerModel.isContinuous(item(nil, 3), item(nil, 4)))
    }

    // MARK: Volume, equalizer, saved queue

    @Test func volumeIsAppliedAndRemembered() {
        let suite = UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!
        let out = FakeOutput()
        let p = PlayerModel(output: out, fetcher: FakeFetcher(), defaults: suite)
        #expect(p.volume == 1)
        p.volume = 0.4
        #expect(out.volume == 0.4)
        let out2 = FakeOutput()
        let again = PlayerModel(output: out2, fetcher: FakeFetcher(), defaults: suite)
        #expect(again.volume == 0.4 && out2.volume == 0.4)
    }

    @Test func theEqualizerReachesTheEngineAndIsRemembered() {
        let suite = UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!
        let out = FakeOutput()
        let p = PlayerModel(output: out, fetcher: FakeFetcher(), defaults: suite)
        p.updateEQ { $0.enabled = true; $0.choose(preset: "bass_boost") }
        #expect(out.eqApplied.last?.gains.first == 6 && out.eqApplied.last?.preGain == -6)
        p.updateEQ { $0.enabled = false }
        #expect(out.eqApplied.last?.gains.allSatisfy { $0 == 0 } == true && out.eqApplied.last?.preGain == 0)
        let out2 = FakeOutput()
        let again = PlayerModel(output: out2, fetcher: FakeFetcher(), defaults: suite)
        #expect(again.eq.presetID == "bass_boost" && !again.eq.enabled && out2.eqApplied.count == 1)
    }

    @Test func theQueueAndPositionComeBackAfterARestartAndPlayFromThere() async throws {
        let suite = UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!
        let out = FakeOutput(), fetch = FakeFetcher()
        let p = PlayerModel(output: out, fetcher: fetch, defaults: suite)
        p.configure(urls: try streamBuilder())
        p.play(songs(4), startAt: 1)
        await until { p.isPlaying }
        out.position = 42
        p.togglePlayPause()                               // pausing saves the position
        let out2 = FakeOutput()
        let again = PlayerModel(output: out2, fetcher: fetch, defaults: suite)
        #expect(again.current?.title == "T1" && again.queue.upNext.count == 2 && again.phase == .idle && again.position == 42)
        again.configure(urls: try streamBuilder())
        again.togglePlayPause()
        await until { again.isPlaying }
        #expect(out2.seeks == [42] && again.current?.title == "T1")
    }

    // MARK: Streaming quality

    @Test func aCapIsAskedForAndVorbisUsesTheLowerOfTheCapAnd192() async throws {
        #expect(PlayerModel.streamOptions(suffix: "flac", cap: 128).bitRate == 128 && PlayerModel.streamOptions(suffix: "flac", cap: 128).format == nil)
        #expect(PlayerModel.streamOptions(suffix: "ogg", cap: 320).bitRate == 192 && PlayerModel.streamOptions(suffix: "ogg", cap: 96).bitRate == 96)
        #expect(PlayerModel.streamOptions(suffix: "flac", cap: nil).bitRate == nil)
        let (p, _, fetch) = try make()
        p.qualityCap = 192
        p.play(songs(1))
        await until { !fetch.requested.isEmpty }
        let q = URLComponents(url: fetch.requested[0], resolvingAgainstBaseURL: false)!.queryItems!
        #expect(q.contains { $0.name == "maxBitRate" && $0.value == "192" } && !q.contains { $0.name == "format" })
    }

    @Test func theCapIsRememberedAndOnlyAllowedValuesAreKept() {
        let suite = UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!
        PlayerModel(output: FakeOutput(), fetcher: FakeFetcher(), defaults: suite).qualityCap = 96
        #expect(PlayerModel(output: FakeOutput(), fetcher: FakeFetcher(), defaults: suite).qualityCap == 96)
        suite.set(77, forKey: "discair.qualityCap")
        #expect(PlayerModel(output: FakeOutput(), fetcher: FakeFetcher(), defaults: suite).qualityCap == nil)
    }

    @Test func aFileTheMacCannotDecodeIsRetriedOnceAsAnMP3AndTheOwnerIsTold() async throws {
        let (p, out, fetch) = try make()
        out.failNextOpen = true
        p.play(songs(1))
        await until { p.isPlaying }
        #expect(p.isPlaying && fetch.requested.count >= 2 && p.notice?.contains("MP3") == true)
        let q = URLComponents(url: fetch.requested[1], resolvingAgainstBaseURL: false)!.queryItems!
        #expect(q.contains { $0.name == "format" && $0.value == "mp3" } && q.contains { $0.name == "maxBitRate" && $0.value == "320" })
        #expect(p.qualityCap == nil)                                         // the saved quality is not changed
    }
}


@MainActor
struct WaveformPlaybackTests {
    private func cache() -> WaveformCache {
        let c = WaveformCache(root: FileManager.default.temporaryDirectory.appending(path: "wf-\(UUID().uuidString)"))
        c.setScope("navidrome|o")
        return c
    }

    private func make(cache: WaveformCache, fetch: @escaping @Sendable (String) async -> SongPeaks) throws -> PlayerModel {
        let p = PlayerModel(output: FakeOutput(), fetcher: FakeFetcher(), defaults: UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!, waveformCache: cache)
        p.configure(urls: try streamBuilder())
        p.waveformFetch = fetch
        p.waveformRetry = .milliseconds(50)
        return p
    }

    private let peaks = [Float](repeating: 0.5, count: 1000)

    @Test func serverPeaksGiveAWaveformAndItIsCached() async throws {
        let c = cache()
        let p = try make(cache: c) { [peaks] _ in .ready(peaks) }
        p.play(songs(1))
        await until { p.waveform != nil }
        #expect(p.waveform?.count == 1000)
        #expect(c.peaks(songID: "s0")?.count == 1000)
    }

    @Test func noPeaksOnTheServerMeansNoWaveform() async throws {
        let p = try make(cache: cache()) { _ in .unavailable }
        p.play(songs(1))
        await until { p.phase == .playing }
        try await Task.sleep(for: .milliseconds(300))
        #expect(p.waveform == nil)
    }

    @Test func aCachedWaveformShowsAtOnceWithoutAsking() async throws {
        let c = cache()
        c.put(peaks, songID: "s0")
        let p = try make(cache: c) { _ in .unavailable }
        p.play(songs(1))
        await until { p.waveform != nil }
        #expect(p.waveform?.count == 1000)
    }

    @Test func aPendingAnswerIsAskedAgainUntilReady() async throws {
        let calls = PeakCallCounter()
        let p = try make(cache: cache()) { [peaks] _ in await calls.next() < 3 ? .pending : .ready(peaks) }
        p.play(songs(1))
        await until { p.waveform != nil }
        #expect(p.waveform?.count == 1000)
    }

    @Test func theWaveformIsDroppedWhenTheSongChanges() async throws {
        let p = try make(cache: cache()) { [peaks] id in id == "s0" ? .ready(peaks) : .unavailable }
        p.play(songs(2))
        await until { p.waveform != nil }
        p.next()
        await until { p.current?.title == "T1" && p.waveform == nil }
        #expect(p.waveform == nil)
    }
}

private actor PeakCallCounter {
    private var n = 0
    func next() -> Int { n += 1; return n }
}
