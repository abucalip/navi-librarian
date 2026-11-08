import AVFoundation
import Foundation
import Testing
@testable import DiscairAudio

/// Serves a fixed body for any request, so a `GrowingDownload` can be tested without the network.
private final class StubStream: URLProtocol, @unchecked Sendable {
    nonisolated(unsafe) static var body = Data()
    nonisolated(unsafe) static var status = 200
    /// When set, the connection drops after this many bytes, as a lost network does mid-song.
    nonisolated(unsafe) static var dropAfter: Int?

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        let response = HTTPURLResponse(url: request.url!, statusCode: Self.status, httpVersion: "HTTP/1.1", headerFields: nil)!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        var offset = 0
        let body = Self.body
        while offset < body.count {
            let end = min(offset + 64 * 1024, Self.dropAfter ?? body.count, body.count)
            client?.urlProtocol(self, didLoad: body.subdata(in: offset..<end))
            offset = end
            if let drop = Self.dropAfter, offset >= drop {
                client?.urlProtocol(self, didFailWithError: URLError(.networkConnectionLost))
                return
            }
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

    /// The connection is lost half way through the body: what arrived stays on disk, and the download reports a failure
    /// instead of completing (the player turns that into the "stopped downloading" notice).
    @Test func aLostConnectionMidBodyFailsAndKeepsWhatArrived() async throws {
        StubStream.status = 200
        StubStream.body = Data(repeating: 7, count: 400_000)
        StubStream.dropAfter = 192 * 1024
        defer { StubStream.dropAfter = nil }
        let file = FileManager.default.temporaryDirectory.appending(path: "stream-\(UUID().uuidString).mp3")
        defer { try? FileManager.default.removeItem(at: file) }
        let download = GrowingDownload(file: file, configuration: stubConfiguration())
        var completed: URL?
        download.onComplete = { completed = $0 }
        try download.start(URL(string: "https://stub.invalid/stream")!)
        for _ in 0..<300 where download.failure == nil { try await Task.sleep(for: .milliseconds(10)) }
        #expect(download.failure != nil)
        #expect(!download.isComplete)
        #expect(completed == nil)
        #expect(download.failure == "The song could not be streamed.")
        // URLSession may drop the chunk still queued when the error arrives, so only a partial, non-empty file is certain;
        // what matters is that the byte counter matches the file the player reads.
        #expect(download.bytesOnDisk > 0 && download.bytesOnDisk <= 192 * 1024)
        let size = try FileManager.default.attributesOfItem(atPath: file.path)[.size] as? Int
        #expect(Int64(size ?? -1) == download.bytesOnDisk)
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

    @Test func onceTheDownloadIsCompleteTheNextSongCanBePreloaded() async throws {
        let full = try silentFile(seconds: 3)
        let partial = try silentFile(seconds: 1)
        let growing = FileManager.default.temporaryDirectory.appending(path: "grow-\(UUID().uuidString).caf")
        try FileManager.default.copyItem(at: partial, to: growing)
        defer { for u in [full, partial, growing] { try? FileManager.default.removeItem(at: u) } }
        let download = GrowingDownload(file: growing)
        download.setState(bytes: 1, complete: false)
        let out = EngineOutput()
        do { try out.openGrowing(download, expectedDuration: 3) } catch let e as AudioError where e.description.contains("could not start") { return }
        try grow(growing, to: full)
        download.setState(bytes: 2, complete: true)
        out.play()
        for _ in 0..<100 where out.isGrowing { try await Task.sleep(for: .milliseconds(10)) }
        #expect(!out.isGrowing)                       // long before the last seconds of the song
        #expect(out.position < 2)
        #expect(abs(out.duration - 3) < 0.01)
        try out.preload(file: full, transition: .gapless)
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

    @Test func pausingDuringAStallKeepsTheSongPausedWhenTheRestArrives() async throws {
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
        try await Task.sleep(for: .milliseconds(1_600))      // the first second has played: the node is stalled
        #expect(!out.isPlaying)

        out.pause()                                          // used to do nothing during a stall
        let held = out.position
        try grow(growing, to: full)
        download.setState(bytes: 2, complete: true)
        try await Task.sleep(for: .milliseconds(1_500))      // the rest has arrived, but the song was paused
        #expect(finished == 0)
        #expect(!out.isPlaying)
        #expect(out.position == held)

        out.play()
        for _ in 0..<400 where finished == 0 { try await Task.sleep(for: .milliseconds(10)) }
        #expect(finished == 1)
        out.stop()
    }

    /// A FLAC of random noise (so it does not compress to nothing), made with the system encoder. Nil when it cannot be made.
    private func noiseFLAC(seconds: Double) throws -> URL? {
        let caf = FileManager.default.temporaryDirectory.appending(path: "noise-\(UUID().uuidString).caf")
        let format = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 44_100, channels: 2, interleaved: true)!
        let file = try AVAudioFile(forWriting: caf, settings: format.settings, commonFormat: .pcmFormatInt16, interleaved: true)
        let buf = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(seconds * 44_100))!
        buf.frameLength = buf.frameCapacity
        let p = buf.int16ChannelData![0]
        for i in 0..<Int(buf.frameLength) * 2 { p[i] = Int16.random(in: -8_000...8_000) }
        try file.write(from: buf)
        let flac = FileManager.default.temporaryDirectory.appending(path: "noise-\(UUID().uuidString).flac")
        let tool = Process()
        tool.executableURL = URL(fileURLWithPath: "/usr/bin/afconvert")
        tool.arguments = ["-f", "flac", "-d", "flac", caf.path, flac.path]
        try tool.run(); tool.waitUntilExit()
        try? FileManager.default.removeItem(at: caf)
        return tool.terminationStatus == 0 ? flac : nil
    }

    /// A partial FLAC reports the whole song's length in its header. Scheduling that many frames made the node read past the
    /// data and raise an exception (seen with a partial MP3); the engine must find the real end by test reads.
    @Test func aPartialFLACIsPlayedOnlyAsFarAsItDecodes() async throws {
        guard let full = try noiseFLAC(seconds: 6) else { return }
        let data = try Data(contentsOf: full)
        let growing = FileManager.default.temporaryDirectory.appending(path: "grow-\(UUID().uuidString).flac")
        try data.prefix(data.count * 4 / 10).write(to: growing)
        defer { for u in [full, growing] { try? FileManager.default.removeItem(at: u) } }

        let download = GrowingDownload(file: growing)
        download.setState(bytes: Int64(data.count * 4 / 10), complete: false)
        let partial = try AVAudioFile(forReading: growing)
        let claimed = partial.length
        let readable = EngineOutput.readableFrames(partial, download: download, known: 0)
        #expect(claimed == 6 * 44_100)                       // the header claims all of it
        #expect(readable > 0 && readable < claimed * 6 / 10) // roughly 40% decodes
        download.setState(bytes: Int64(data.count), complete: true)
        #expect(EngineOutput.readableFrames(partial, download: download, known: 0) == claimed)

        // Through the engine: it must wait at the end of the data, not crash or finish, then play on once the rest arrives.
        try data.prefix(data.count * 4 / 10).write(to: growing)
        download.setState(bytes: Int64(data.count * 4 / 10), complete: false)
        let out = EngineOutput()
        do { try out.openGrowing(download, expectedDuration: 6) } catch let e as AudioError where e.description.contains("could not start") { return }
        var finished = 0
        out.onFinished = { finished += 1 }
        out.play()
        try await Task.sleep(for: .milliseconds(3_500))        // 40% of 6 s is 2.4 s: the node is dry by now
        #expect(finished == 0)
        #expect(!out.isPlaying)

        try data.write(to: growing)
        download.setState(bytes: Int64(data.count), complete: true)
        for _ in 0..<800 where finished == 0 { try await Task.sleep(for: .milliseconds(10)) }
        #expect(finished == 1)
        out.stop()
    }

    /// A VBR MP3 with a Xing header (what many library songs are): byte share is not time share, and the header claims the whole
    /// song for any cut. Made with lame through ffmpeg; the test ends early when ffmpeg is not installed.
    private func vbrMP3(seconds: Int) throws -> URL? {
        let ffmpeg = "/opt/homebrew/bin/ffmpeg"
        guard FileManager.default.isExecutableFile(atPath: ffmpeg) else { return nil }
        let url = FileManager.default.temporaryDirectory.appending(path: "vbr-\(UUID().uuidString).mp3")
        let tool = Process()
        tool.executableURL = URL(fileURLWithPath: ffmpeg)
        tool.arguments = ["-loglevel", "error", "-y",
                          "-f", "lavfi", "-i", "aevalsrc=sin(2*PI*(200+300*t)*t)*0.5*(0.5+0.5*sin(2*PI*0.7*t)):s=44100:d=\(seconds)",
                          "-f", "lavfi", "-i", "anoisesrc=d=\(seconds):c=pink:a=0.15",
                          "-filter_complex", "amix=inputs=2:duration=first,pan=stereo|c0=c0|c1=c0",
                          "-c:a", "libmp3lame", "-q:a", "2", url.path]
        try tool.run(); tool.waitUntilExit()
        return tool.terminationStatus == 0 ? url : nil
    }

    @Test func aPartialVBRMP3IsPlayedOnlyAsFarAsItDecodes() async throws {
        guard let full = try vbrMP3(seconds: 8) else { return }
        let data = try Data(contentsOf: full)
        let growing = FileManager.default.temporaryDirectory.appending(path: "grow-\(UUID().uuidString).mp3")
        defer { for u in [full, growing] { try? FileManager.default.removeItem(at: u) } }
        let cut = data.count * 4 / 10
        try data.prefix(cut).write(to: growing)

        let download = GrowingDownload(file: growing)
        download.setState(bytes: Int64(cut), complete: false)
        let partial = try AVAudioFile(forReading: growing)
        let claimed = partial.length
        let readable = EngineOutput.readableFrames(partial, download: download, known: 0)
        let rate = partial.processingFormat.sampleRate
        #expect(abs(Double(claimed) / rate - 8) < 0.2)         // the Xing header claims the whole song
        #expect(readable > 0 && readable < claimed)            // but only part of it decodes
        #expect(Double(readable) / rate < 8 * 0.7)             // and not more than the bytes can hold (loose: VBR)
        download.setState(bytes: Int64(data.count), complete: true)
        try data.write(to: growing)
        #expect(EngineOutput.readableFrames(partial, download: download, known: 0) == claimed)

        try data.prefix(cut).write(to: growing)
        download.setState(bytes: Int64(cut), complete: false)
        let out = EngineOutput()
        do { try out.openGrowing(download, expectedDuration: 8) } catch let e as AudioError where e.description.contains("could not start") { return }
        var finished = 0
        out.onFinished = { finished += 1 }
        out.play()
        try await Task.sleep(for: .milliseconds(4_500))
        #expect(finished == 0)                                  // dry, waiting, not finished and no crash
        #expect(!out.isPlaying)

        try data.write(to: growing)
        download.setState(bytes: Int64(data.count), complete: true)
        for _ in 0..<1_000 where finished == 0 { try await Task.sleep(for: .milliseconds(10)) }
        #expect(finished == 1)
        out.stop()
    }
}
