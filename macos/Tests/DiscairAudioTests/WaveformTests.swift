import AVFoundation
import Foundation
import Testing
@testable import DiscairAudio

struct WaveformTests {
    /// A mono 16-bit WAV: quiet for the first half, loud for the second.
    private func wav(seconds: Double = 2, rate: Double = 8_000) throws -> URL {
        let url = FileManager.default.temporaryDirectory.appending(path: "wf-\(UUID().uuidString).wav")
        let format = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: rate, channels: 1, interleaved: true)!
        let file = try AVAudioFile(forWriting: url, settings: format.settings, commonFormat: .pcmFormatInt16, interleaved: true)
        let frames = AVAudioFrameCount(seconds * rate)
        let buf = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames)!
        buf.frameLength = frames
        for i in 0..<Int(frames) { buf.int16ChannelData![0][i] = i < Int(frames) / 2 ? 3_000 : 24_000 }
        try file.write(from: buf)
        return url
    }

    @Test func peaksFollowTheLoudness() throws {
        let p = try #require(WaveformReader.peaks(of: try wav()))
        #expect(p.count == 1000)
        #expect(p[100] < 0.15 && p[900] > 0.7)
        #expect(p.allSatisfy { $0 >= 0 && $0 <= 1 })
    }

    @Test func aFileThatIsNotAudioGivesNothing() throws {
        let url = FileManager.default.temporaryDirectory.appending(path: "wf-\(UUID().uuidString).flac")
        try Data("not audio".utf8).write(to: url)
        #expect(WaveformReader.peaks(of: url) == nil)
        #expect(WaveformReader.peaks(of: URL(fileURLWithPath: "/nonexistent/file.flac")) == nil)
    }

    @Test func aCancelledReadGivesNothing() throws {
        #expect(WaveformReader.peaks(of: try wav(), shouldCancel: { true }) == nil)
    }

    @Test func silenceIsNotAWaveform() {
        #expect(WaveformReader.normalised([Float](repeating: 0, count: 10)) == nil)
        #expect(WaveformReader.normalised([0.5, 2, .nan]) == [0.5, 1, 0])
    }

    @Test func cacheRoundTripsAndStaysSmall() throws {
        let root = FileManager.default.temporaryDirectory.appending(path: "wfc-\(UUID().uuidString)")
        let c = WaveformCache(root: root)
        let peaks = (0..<1000).map { Float($0) / 999 }
        #expect(c.peaks(songID: "a") == nil)            // no scope yet
        c.setScope("u")
        #expect(c.peaks(songID: "a") == nil)
        c.put(peaks, songID: "a")
        let back = try #require(c.peaks(songID: "a"))
        #expect(back.count == 1000 && abs(back[500] - peaks[500]) < 0.0001)
        let files = try FileManager.default.subpathsOfDirectory(atPath: root.path).filter { $0.hasSuffix(".wave") }
        #expect(files.count == 1)
        #expect(try Data(contentsOf: root.appending(path: files[0])).count == 2000)
        c.setScope("other"); #expect(c.peaks(songID: "a") == nil)   // per server user
        c.clear(); c.setScope("u"); #expect(c.peaks(songID: "a") == nil)
    }

    @Test func aSongIDCannotNameAPath() {
        let root = FileManager.default.temporaryDirectory.appending(path: "wfc-\(UUID().uuidString)")
        let c = WaveformCache(root: root); c.setScope("u")
        c.put([0.5, 0.5], songID: "../../escape")
        #expect(!FileManager.default.fileExists(atPath: root.deletingLastPathComponent().appending(path: "escape").path))
    }
}
