import DiscairAudio
import DiscairCore
import DiscairNavidrome
import Foundation
import Testing
@testable import DiscairUI

@MainActor
private final class FakeOutput: AudioOutput {
    var onFinished: (() -> Void)?
    var isPlaying = false
    var position: Double = 0
    var duration: Double = 200
    var opened: [URL] = []
    var seeks: [Double] = []
    func open(file: URL) throws { opened.append(file); position = 0 }
    func play() { isPlaying = true }
    func pause() { isPlaying = false }
    func stop() { isPlaying = false }
    func seek(to seconds: Double) { seeks.append(seconds); position = seconds }
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

private func streamBuilder() throws -> StreamURLBuilder {
    try StreamURLBuilder(baseURL: URL(string: "https://navi.example.ts.net")!, auth: SubsonicAuth(credential: Credential(username: "o", password: "pw")))
}

private func songs(_ n: Int, suffix: String? = "flac") -> [QueueItem] {
    (0..<n).map { QueueItem(songID: "s\($0)", title: "T\($0)", artist: "A", album: "Al", duration: 200, suffix: suffix) }
}

@MainActor
private func make() throws -> (PlayerModel, FakeOutput, FakeFetcher) {
    let out = FakeOutput(), fetch = FakeFetcher()
    let p = PlayerModel(output: out, fetcher: fetch)
    p.configure(urls: try streamBuilder())
    return (p, out, fetch)
}

@MainActor
private func until(_ condition: () -> Bool) async {
    for _ in 0..<500 where !condition() { try? await Task.sleep(for: .milliseconds(10)) }
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
}
