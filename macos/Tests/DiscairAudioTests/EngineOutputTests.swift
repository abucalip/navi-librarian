import AVFoundation
import Foundation
import Testing
@testable import DiscairAudio

/// Plays one second of digital silence through the real engine, so nothing is heard. A machine with no audio output
/// (a CI runner) cannot start the engine; the test then ends without checking, since that is the machine's limit.
@MainActor
@Suite("Engine output") struct EngineOutputTests {
    private func silentFile(seconds: Double) throws -> URL {
        let url = FileManager.default.temporaryDirectory.appending(path: "silence-\(UUID().uuidString).caf")
        let format = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: 44_100, channels: 2, interleaved: false)!
        let file = try AVAudioFile(forWriting: url, settings: format.settings)
        let buf = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(seconds * 44_100))!
        buf.frameLength = buf.frameCapacity
        try file.write(from: buf)
        return url
    }

    @Test func opensSeeksAndReportsTheEnd() async throws {
        let url = try silentFile(seconds: 1)
        defer { try? FileManager.default.removeItem(at: url) }
        let out = EngineOutput()
        do { try out.open(file: url) } catch let e as AudioError where e.description.contains("could not start") { return }
        #expect(abs(out.duration - 1) < 0.01 && out.position == 0)
        out.seek(to: 0.5)
        #expect(abs(out.position - 0.5) < 0.01 && !out.isPlaying)
        var finished = 0
        out.onFinished = { finished += 1 }
        out.play()
        for _ in 0..<300 where finished == 0 { try await Task.sleep(for: .milliseconds(10)) }
        #expect(finished == 1)
        out.stop()
        #expect(out.duration == 0)
    }

    @Test func aStoppedFileNeverReportsFinished() async throws {
        let url = try silentFile(seconds: 1)
        defer { try? FileManager.default.removeItem(at: url) }
        let out = EngineOutput()
        do { try out.open(file: url) } catch let e as AudioError where e.description.contains("could not start") { return }
        var finished = 0
        out.onFinished = { finished += 1 }
        out.play(); out.stop()
        try await Task.sleep(for: .milliseconds(300))
        #expect(finished == 0)
    }

    @Test func aBrokenFileIsRefusedWithWords() throws {
        let url = FileManager.default.temporaryDirectory.appending(path: "broken-\(UUID().uuidString).flac")
        try Data("not audio".utf8).write(to: url)
        defer { try? FileManager.default.removeItem(at: url) }
        #expect(throws: AudioError.self) { try EngineOutput().open(file: url) }
    }

    @Test func aPreloadedSongJoinsGaplesslyAndFinishesOnce() async throws {
        let a = try silentFile(seconds: 0.6), b = try silentFile(seconds: 0.6)
        defer { try? FileManager.default.removeItem(at: a); try? FileManager.default.removeItem(at: b) }
        let out = EngineOutput()
        do { try out.open(file: a) } catch let e as AudioError where e.description.contains("could not start") { return }
        var advanced = 0, finished = 0
        out.onAdvanced = { advanced += 1 }
        out.onFinished = { finished += 1 }
        try out.preload(file: b, transition: .gapless)
        out.play()
        for _ in 0..<400 where finished == 0 { try await Task.sleep(for: .milliseconds(10)) }
        #expect(advanced == 1 && finished == 1)
    }

    @Test func aCrossfadeAdvancesAtTheStartOfTheFadeAndFinishesOnce() async throws {
        let a = try silentFile(seconds: 0.8), b = try silentFile(seconds: 0.8)
        defer { try? FileManager.default.removeItem(at: a); try? FileManager.default.removeItem(at: b) }
        let out = EngineOutput()
        do { try out.open(file: a) } catch let e as AudioError where e.description.contains("could not start") { return }
        var advanced = 0, finished = 0
        var positionAtAdvance = -1.0
        out.onAdvanced = { advanced += 1; positionAtAdvance = out.position }
        out.onFinished = { finished += 1 }
        try out.preload(file: b, transition: .crossfade(0.3))
        out.play()
        for _ in 0..<500 where finished == 0 { try await Task.sleep(for: .milliseconds(10)) }
        #expect(advanced == 1 && finished == 1)
        #expect(positionAtAdvance < 0.3)           // the position now belongs to the new song
    }

    @Test func cancellingAPreloadLeavesTheCurrentSongPlayingToItsEnd() async throws {
        let a = try silentFile(seconds: 0.5), b = try silentFile(seconds: 0.5)
        defer { try? FileManager.default.removeItem(at: a); try? FileManager.default.removeItem(at: b) }
        let out = EngineOutput()
        do { try out.open(file: a) } catch let e as AudioError where e.description.contains("could not start") { return }
        var advanced = 0, finished = 0
        out.onAdvanced = { advanced += 1 }
        out.onFinished = { finished += 1 }
        try out.preload(file: b, transition: .gapless)
        out.cancelPreload()
        out.play()
        for _ in 0..<300 where finished == 0 { try await Task.sleep(for: .milliseconds(10)) }
        #expect(advanced == 0 && finished == 1)
    }
}

