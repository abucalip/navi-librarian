import DiscairAudio
import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import Foundation
import Testing
@testable import DiscairUI

/// The minimum an engine must do for these tests: the position stays where the test leaves it and `finish()` ends the song.
@MainActor
private final class SkipOutput: AudioOutput {
    var onFinished: (() -> Void)?
    var onAdvanced: (() -> Void)?
    var isPlaying = false
    var position: Double = 0
    var duration: Double = 200
    func open(file: URL) throws { position = 0 }
    func play() { isPlaying = true }
    func pause() { isPlaying = false }
    func stop() { isPlaying = false }
    func seek(to seconds: Double) { position = seconds }
    func preload(file: URL, transition: Transition) throws {}
    func cancelPreload() {}
    var volume: Float = 1
    func applyEQ(gains: [Double], preGain: Double) {}
    func setMatchOutputRate(_ on: Bool) {}
    func restoreOutputRate() {}
    var isGrowing = false
    func openGrowing(_ download: GrowingDownload, expectedDuration: Double) throws { isGrowing = true }
    func finish() { isPlaying = false; onFinished?() }
}

private final class SkipFetcher: AudioFetcher, @unchecked Sendable {
    func fetch(_ url: URL, suffix: String?) async throws -> URL {
        let f = FileManager.default.temporaryDirectory.appending(path: "skip-\(UUID().uuidString).\(suffix ?? "bin")")
        try Data([0]).write(to: f)
        return f
    }
}

/// Never accepts anything, so the outbox keeps what it is given and the test can read it back.
private struct Refused: Error {}

private func streamBuilder() throws -> StreamURLBuilder {
    try StreamURLBuilder(baseURL: URL(string: "https://navi.example.ts.net")!, auth: SubsonicAuth(credential: Credential(username: "o", password: "pw")))
}

private func songs(_ n: Int) -> [QueueItem] {
    (0..<n).map { QueueItem(songID: "s\($0)", title: "T\($0)", artist: "A", album: "Al", albumID: "al", duration: 200, suffix: "flac", track: $0 + 1, disc: 1, mbid: "3f2504e0-4f89-41d3-9a0c-0305e82c3301") }
}

@MainActor
private func settle(_ condition: () async -> Bool) async {
    for _ in 0..<400 where !(await condition()) { try? await Task.sleep(for: .milliseconds(5)) }
}

@MainActor
struct PlaybackSkipFeedbackTests {
    /// A player on a fake engine, with skips going to a fresh outbox in a temporary folder.
    private func make() throws -> (PlayerModel, SkipOutput, FeedbackOutbox) {
        let out = SkipOutput()
        let p = PlayerModel(output: out, fetcher: SkipFetcher(), defaults: UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!)
        p.configure(urls: try streamBuilder())
        let file = FileManager.default.temporaryDirectory.appending(path: "skip-outbox-\(UUID().uuidString)/feedback-outbox.json")
        let outbox = FeedbackOutbox(fileURL: file, send: { _ in throw Refused() })
        p.configureFeedback(outbox)
        return (p, out, outbox)
    }

    private func started(_ p: PlayerModel) async -> Bool {
        await settle { p.phase == .playing }
        return p.phase == .playing
    }

    @Test func nextPressedEarlyIsRecordedAsASkip() async throws {
        let (p, _, outbox) = try make()
        p.play(songs(3))
        #expect(await started(p))

        p.next()
        await settle { await outbox.pending.count == 1 }
        let pending = await outbox.pending
        #expect(pending.map(\.subjectID) == ["s0"])
        #expect(pending.first?.mbid == "3f2504e0-4f89-41d3-9a0c-0305e82c3301")
    }

    @Test func aSongThatEndsOnItsOwnIsNotASkip() async throws {
        let (p, out, outbox) = try make()
        p.play(songs(3))
        #expect(await started(p))

        out.finish()
        #expect(await started(p))
        try? await Task.sleep(for: .milliseconds(50))
        #expect(await outbox.pending.isEmpty)
    }

    @Test func leavingTheLastSongIsNotASkip() async throws {
        let (p, _, outbox) = try make()
        p.play(songs(1))
        #expect(await started(p))

        p.next()
        try? await Task.sleep(for: .milliseconds(50))
        #expect(await outbox.pending.isEmpty)
    }

    @Test func previousOnTheFirstSongRestartsItAndRecordsNothing() async throws {
        let (p, _, outbox) = try make()
        p.play(songs(3))
        #expect(await started(p))

        p.previous()
        try? await Task.sleep(for: .milliseconds(50))
        #expect(await outbox.pending.isEmpty)
        #expect(p.current?.songID == "s0")
    }
}
