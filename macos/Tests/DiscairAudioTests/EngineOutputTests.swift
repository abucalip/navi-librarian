import AVFoundation
import Foundation
import Testing
@testable import DiscairAudio

/// Plays one second of digital silence through the real engine, so nothing is heard. A machine with no audio output
/// (a CI runner) cannot start the engine; the test then ends without checking, since that is the machine's limit.
/// The levels are sampled in real time, which a CI runner's virtual audio device does not keep; these run on a real Mac.
let onCI = ProcessInfo.processInfo.environment["CI"] != nil

private func blockMainThread(_ seconds: Double) { Thread.sleep(forTimeInterval: seconds) }

@MainActor
@Suite("Engine output", .serialized) struct EngineOutputTests {
    private func silentFile(seconds: Double, rate: Double = 44_100, channels: AVAudioChannelCount = 2) throws -> URL {
        let url = FileManager.default.temporaryDirectory.appending(path: "silence-\(UUID().uuidString).caf")
        let format = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: rate, channels: channels, interleaved: false)!
        let file = try AVAudioFile(forWriting: url, settings: format.settings)
        let buf = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(seconds * rate))!
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

    @Test func aCrossfadeRampsBothLevelsAndEndsAtFullOnTheNewSong() async throws {
        if onCI { return }
        let a = try silentFile(seconds: 2), b = try silentFile(seconds: 2)
        defer { try? FileManager.default.removeItem(at: a); try? FileManager.default.removeItem(at: b) }
        let out = EngineOutput()
        do { try out.open(file: a) } catch let e as AudioError where e.description.contains("could not start") { return }
        var advanced = 0
        out.onAdvanced = { advanced += 1 }
        try out.preload(file: b, transition: .crossfade(1))
        out.play()
        var mid: (current: Float, other: Float)?
        for _ in 0..<400 {
            try await Task.sleep(for: .milliseconds(10))
            if advanced == 1, mid == nil, out.levelsForTests.current > 0.45, out.levelsForTests.current < 0.9 { mid = out.levelsForTests }
        }
        #expect(advanced == 1)
        #expect(mid != nil, "the new song's level should pass through the middle of the fade")
        if let m = mid { #expect(m.other > 0.3 && m.other < 0.95) }
    }

    /// Three songs of different formats: two fades in a row, the second reusing the first node.
    @Test func twoCrossfadesInARowAcrossFormatsEachRampTheLevels() async throws {
        if onCI { return }
        let a = try silentFile(seconds: 2, rate: 44_100), b = try silentFile(seconds: 2, rate: 48_000), c = try silentFile(seconds: 2, rate: 96_000, channels: 1)
        defer { for u in [a, b, c] { try? FileManager.default.removeItem(at: u) } }
        let out = EngineOutput()
        do { try out.open(file: a) } catch let e as AudioError where e.description.contains("could not start") { return }
        var advanced = 0
        out.onAdvanced = { advanced += 1 }
        try out.preload(file: b, transition: .crossfade(1))
        out.play()
        var mids: [(Float, Float)] = []
        var preloadedC = false
        for _ in 0..<1000 {
            try await Task.sleep(for: .milliseconds(10))
            if advanced == 1, !preloadedC { try out.preload(file: c, transition: .crossfade(1)); preloadedC = true }
            let l = out.levelsForTests
            if advanced > 0, l.current > 0.45, l.current < 0.9, mids.count < advanced, l.other > 0.3, l.other < 0.95 { mids.append((l.current, l.other)) }
        }
        #expect(advanced == 2)
        #expect(mids.count == 2, "each fade should pass through its middle with both levels between 0.3 and 0.95: \(mids)")
    }

    /// A main thread stalled for a second must not leave the fade behind the audio: by the time the new song has played
    /// as long as the fade, it is at full level.
    @Test func aStalledMainThreadDoesNotLagTheFade() async throws {
        if onCI { return }
        let a = try silentFile(seconds: 4), b = try silentFile(seconds: 4)
        defer { try? FileManager.default.removeItem(at: a); try? FileManager.default.removeItem(at: b) }
        let out = EngineOutput()
        do { try out.open(file: a) } catch let e as AudioError where e.description.contains("could not start") { return }
        var advanced = 0
        out.onAdvanced = { advanced += 1 }
        try out.preload(file: b, transition: .crossfade(2))
        out.play()
        for _ in 0..<600 where advanced == 0 { try await Task.sleep(for: .milliseconds(10)) }
        #expect(advanced == 1)
        try await Task.sleep(for: .milliseconds(300))
        blockMainThread(1.0)                                 // the main thread is busy
        try await Task.sleep(for: .milliseconds(1000))      // the new song has now played about 2.3 s of a 2 s fade
        #expect(out.levelsForTests.current > 0.99, "level \(out.levelsForTests.current)")
    }
}
