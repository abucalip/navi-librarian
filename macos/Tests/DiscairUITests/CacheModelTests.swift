import AppKit
import DiscairAudio
import DiscairCore
import DiscairNavidrome
import Foundation
import Testing
@testable import DiscairUI

private func temp() -> URL { FileManager.default.temporaryDirectory.appending(path: "discair-cm-\(UUID().uuidString)") }
private func defaults() -> UserDefaults { UserDefaults(suiteName: "discair-cm-\(UUID().uuidString)")! }

private final class PngTransport: HTTPTransport, @unchecked Sendable {
    private let lock = NSLock(); private var n = 0
    var requests: Int { lock.withLock { n } }
    var online = true
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        guard online else { throw URLError(.cannotConnectToHost) }
        lock.withLock { n += 1 }
        let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 4, pixelsHigh: 4, bitsPerSample: 8, samplesPerPixel: 4,
                                   hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        return (rep.representation(using: .png, properties: [:])!, HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
    }
}

@MainActor
struct CacheModelTests {
    @Test func offByDefaultAndTheSwitchIsRemembered() {
        let d = defaults(), media = MediaCache(root: temp())
        let m = CacheModel(media: media, defaults: d)
        #expect(!m.isEnabled && !media.isEnabled)
        m.isEnabled = true
        #expect(media.isEnabled)
        #expect(CacheModel(media: MediaCache(root: temp()), defaults: d).isEnabled)
    }

    @Test func readoutAndClear() async {
        let media = MediaCache(root: temp()); media.setScope("u")
        let m = CacheModel(media: media, defaults: defaults()); m.isEnabled = true
        media.store(data: Data(repeating: 1, count: 5_000_000), key: "k", ext: "bin")
        await m.refresh()
        #expect(m.usedBytes == 5_000_000 && m.readout.contains("5") && m.readout.contains("2 GB"))
        await m.clear()
        #expect(m.usedBytes == 0)
    }

    @Test func coversComeFromDiskWhenTheServerIsGone() async throws {
        let media = MediaCache(root: temp()); media.setScope("u"); media.isEnabled = true
        let t = PngTransport()
        let builder = try StreamURLBuilder(baseURL: URL(string: "https://navi.example.ts.net")!, auth: SubsonicAuth(credential: Credential(username: "o", password: "pw")))
        let first = ArtworkStore(transport: t, media: media); first.configure(builder)
        #expect(await first.image(coverArt: "al-1", px: 300) != nil && t.requests == 1)
        t.online = false
        let relaunched = ArtworkStore(transport: t, media: media); relaunched.configure(builder)   // memory is empty again
        #expect(await relaunched.image(coverArt: "al-1", px: 300) != nil && t.requests == 1)
        #expect(await relaunched.image(coverArt: "al-2", px: 300) == nil)                          // never saved
    }

    @Test func withTheCacheOffNothingIsKept() async throws {
        let media = MediaCache(root: temp()); media.setScope("u")
        let t = PngTransport()
        let builder = try StreamURLBuilder(baseURL: URL(string: "https://navi.example.ts.net")!, auth: SubsonicAuth(credential: Credential(username: "o", password: "pw")))
        let s = ArtworkStore(transport: t, media: media); s.configure(builder)
        _ = await s.image(coverArt: "al-1", px: 300)
        #expect(media.usedBytes() == 0)
    }

    @Test func aFailedCoverIsAskedForAgainAfterFiveMinutes() async throws {
        let t = PngTransport(); t.online = false
        let builder = try StreamURLBuilder(baseURL: URL(string: "https://navi.example.ts.net")!, auth: SubsonicAuth(credential: Credential(username: "o", password: "pw")))
        let s = ArtworkStore(transport: t, media: nil); s.configure(builder)
        var clock = Date(timeIntervalSince1970: 1_000)
        s.now = { clock }
        #expect(await s.image(coverArt: "al-1", px: 300) == nil)
        t.online = true
        #expect(await s.image(coverArt: "al-1", px: 300) == nil)          // still remembered as failed
        clock = clock.addingTimeInterval(301)
        #expect(await s.image(coverArt: "al-1", px: 300) != nil)          // the server was fixed in the meantime
    }

    @Test func resetAllForgetsFailuresAtOnce() async throws {
        let t = PngTransport(); t.online = false
        let builder = try StreamURLBuilder(baseURL: URL(string: "https://navi.example.ts.net")!, auth: SubsonicAuth(credential: Credential(username: "o", password: "pw")))
        let s = ArtworkStore(transport: t, media: nil); s.configure(builder)
        _ = await s.image(coverArt: "al-1", px: 300)
        t.online = true
        let before = s.generation
        s.resetAll()
        #expect(s.generation == before + 1)
        #expect(await s.image(coverArt: "al-1", px: 300) != nil)
    }
}
