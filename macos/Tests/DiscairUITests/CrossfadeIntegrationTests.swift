import AVFoundation
@testable import DiscairAudio
import DiscairCore
import DiscairNavidrome
import Foundation
import Testing
@testable import DiscairUI

private final class SilenceFetcher: AudioFetcher, @unchecked Sendable {
    func fetch(_ url: URL, suffix: String?) async throws -> URL {
        let f = FileManager.default.temporaryDirectory.appending(path: "xf-\(UUID().uuidString).caf")
        let format = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: 44_100, channels: 2, interleaved: false)!
        let file = try AVAudioFile(forWriting: f, settings: format.settings)
        let buf = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: 44_100 * 5)!
        buf.frameLength = buf.frameCapacity
        try file.write(from: buf)
        return f
    }
}

let onCI = ProcessInfo.processInfo.environment["CI"] != nil

/// The model driving the real engine (digital silence): with a crossfade set, unrelated songs must fade, not cut.
@MainActor
struct CrossfadeIntegrationTests {
    @Test func unrelatedSongsFadeWhenACrossfadeIsSet() async throws {
        if onCI { return }
        let out = EngineOutput()
        let p = PlayerModel(output: out, fetcher: SilenceFetcher(), defaults: UserDefaults(suiteName: "xf-\(UUID().uuidString)")!)
        p.configure(urls: try StreamURLBuilder(baseURL: URL(string: "https://navi.example.ts.net")!, auth: SubsonicAuth(credential: Credential(username: "o", password: "pw"))))
        p.crossfadeSeconds = 2
        let items = (0..<2).map { QueueItem(songID: "s\($0)", title: "T\($0)", artist: "A\($0)", album: "Al\($0)", albumID: "al\($0)", duration: 5, suffix: "flac", track: 1, disc: 1) }
        p.play(items)
        for _ in 0..<300 where !p.isPlaying { try await Task.sleep(for: .milliseconds(10)) }
        guard p.isPlaying else { return }                      // no audio output on this machine
        var sawMiddle = false, titleStayedDuringFade = false
        for _ in 0..<900 {
            try await Task.sleep(for: .milliseconds(10))
            let l = out.levelsForTests
            if l.current > 0.45, l.current < 0.9, l.other > 0.3, l.other < 0.95 {
                sawMiddle = true
                if p.current?.title == "T0" { titleStayedDuringFade = true }     // the screen still shows the old song mid-fade
            }
        }
        #expect(p.current?.title == "T1")
        #expect(titleStayedDuringFade, "the title must not switch to the next song before the fade ends")
        #expect(sawMiddle, "the model should hand the engine a crossfade, so both levels pass through the middle")
    }
}
