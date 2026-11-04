import AVFoundation
import Foundation
import Testing
@testable import DiscairAudio

/// Serves a fixed body for any request, so a `GrowingDownload` can be tested without the network.
private final class StubStream: URLProtocol, @unchecked Sendable {
    nonisolated(unsafe) static var body = Data()
    nonisolated(unsafe) static var status = 200

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        let response = HTTPURLResponse(url: request.url!, statusCode: Self.status, httpVersion: "HTTP/1.1", headerFields: nil)!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        var offset = 0
        let body = Self.body
        while offset < body.count {
            let end = min(offset + 64 * 1024, body.count)
            client?.urlProtocol(self, didLoad: body.subdata(in: offset..<end))
            offset = end
        }
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}
}

private func stubConfiguration() -> URLSessionConfiguration {
    let c = URLSessionConfiguration.ephemeral
    c.protocolClasses = [StubStream.self]
    return c
}

@Suite("Growing download", .serialized) struct GrowingDownloadTests {
    @Test func streamsTheBodyToDiskAndCompletes() async throws {
        StubStream.status = 200
        StubStream.body = Data(repeating: 7, count: 300_000)
        let file = FileManager.default.temporaryDirectory.appending(path: "stream-\(UUID().uuidString).mp3")
        defer { try? FileManager.default.removeItem(at: file) }
        let download = GrowingDownload(file: file, configuration: stubConfiguration())
        var completed: URL?
        download.onComplete = { completed = $0 }
        try download.start(URL(string: "https://stub.invalid/stream")!)
        for _ in 0..<300 where !download.isComplete { try await Task.sleep(for: .milliseconds(10)) }
        #expect(download.isComplete)
        #expect(download.bytesOnDisk == 300_000)
        #expect(download.failure == nil)
        #expect(completed == file)
        let size = try FileManager.default.attributesOfItem(atPath: file.path)[.size] as? Int
        #expect(size == 300_000)
    }

    @Test func aServerErrorFailsWithoutCompleting() async throws {
        StubStream.status = 500
        StubStream.body = Data("oops".utf8)
        let file = FileManager.default.temporaryDirectory.appending(path: "stream-\(UUID().uuidString).mp3")
        defer { try? FileManager.default.removeItem(at: file) }
        let download = GrowingDownload(file: file, configuration: stubConfiguration())
        try download.start(URL(string: "https://stub.invalid/stream")!)
        for _ in 0..<300 where download.failure == nil { try await Task.sleep(for: .milliseconds(10)) }
        #expect(download.failure == "The server did not send the song.")
        #expect(!download.isComplete)
    }
}

/// Growing playback through the real engine. Like `EngineOutputTests`, a machine with no audio output ends the test early.
@MainActor
@Suite("Growing playback", .serialized) struct GrowingPlaybackTests {
    private func silentFile(seconds: Double) throws -> URL {
        let url = FileManager.default.temporaryDirectory.appending(path: "grow-\(UUID().uuidString).caf")
        let format = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: 44_100, channels: 2, interleaved: false)!
        let file = try AVAudioFile(forWriting: url, settings: format.settings)
        let buf = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(seconds * 44_100))!
        buf.frameLength = buf.frameCapacity
        try file.write(from: buf)
        return url
    }

    /// Replaces the file the engine reads with a longer copy, as a download does.
    private func grow(_ path: URL, to source: URL) throws {
        try FileManager.default.removeItem(at: path)
        try FileManager.default.copyItem(at: source, to: path)
    }

    @Test func aGrowingSongPlaysThroughWhenTheRestArrives() async throws {
        let full = try silentFile(seconds: 2)
        let partial = try silentFile(seconds: 1)
        let growing = FileManager.default.temporaryDirectory.appending(path: "grow-\(UUID().uuidString).caf")
        try FileManager.default.copyItem(at: partial, to: growing)
        defer { for u in [full, partial, growing] { try? FileManager.default.removeItem(at: u) } }

        let download = GrowingDownload(file: growing)
        download.setState(bytes: 1, complete: false)
        let out = EngineOutput()
        do { try out.openGrowing(download, expectedDuration: 2) } catch let e as AudioError where e.description.contains("could not start") { return }
        #expect(out.isGrowing)
        #expect(out.duration == 2)
        #expect(throws: AudioError.self) { try out.preload(file: full, transition: .gapless) }   // no follower while growing

        try grow(growing, to: full)
        download.setState(bytes: 2, complete: true)
        var finished = 0
        out.onFinished = { finished += 1 }
        out.play()
        for _ in 0..<400 where finished == 0 { try await Task.sleep(for: .milliseconds(10)) }
        #expect(finished == 1)
        #expect(!out.isGrowing)
        out.stop()
    }

    @Test func aStarvedSongWaitsInsteadOfEndingEarly() async throws {
        let full = try silentFile(seconds: 2)
        let partial = try silentFile(seconds: 1)
        let growing = FileManager.default.temporaryDirectory.appending(path: "grow-\(UUID().uuidString).caf")
        try FileManager.default.copyItem(at: partial, to: growing)
        defer { for u in [full, partial, growing] { try? FileManager.default.removeItem(at: u) } }

        let download = GrowingDownload(file: growing)
        download.setState(bytes: 1, complete: false)
        let out = EngineOutput()
        do { try out.openGrowing(download, expectedDuration: 2) } catch let e as AudioError where e.description.contains("could not start") { return }
        var finished = 0
        out.onFinished = { finished += 1 }
        out.play()
        // The first second runs out with the rest still downloading: the song must wait, not report its end.
        try await Task.sleep(for: .milliseconds(1_600))
        #expect(finished == 0)
        #expect(!out.isPlaying)

        try grow(growing, to: full)
        download.setState(bytes: 2, complete: true)
        for _ in 0..<400 where finished == 0 { try await Task.sleep(for: .milliseconds(10)) }
        #expect(finished == 1)
        out.stop()
    }
}
