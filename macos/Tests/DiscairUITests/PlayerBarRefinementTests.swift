import AppKit
import DiscairCore
import DiscairLibrarian
@testable import DiscairNavidrome
import SwiftUI
import Testing
@testable import DiscairUI

private func song(_ json: String) throws -> NavidromeSong { try JSONDecoder().decode(NavidromeSong.self, from: Data(json.utf8)) }

@MainActor
@Suite("Player bar refinements", .serialized)
struct PlayerBarRefinementTests {
    let now = ISO8601DateFormatter().date(from: "2026-11-09T12:00:00Z")!

    @Test func libraryFactsAreWrittenOnlyFromWhatTheLibraryHolds() throws {
        let s = try song(#"{"id":"s1","title":"Song","album":"Spirit","albumId":"a1","track":4,"year":1986,"genre":"Art Rock","playCount":18,"played":"2026-10-01T10:00:00Z","created":"2024-11-09T12:00:00Z","suffix":"flac","bitDepth":24,"samplingRate":96000,"userRating":4}"#)
        let other = try song(#"{"id":"s2","title":"Other"}"#)
        let album = NavidromeAlbumDetail(album: NavidromeAlbum(id: "a1", name: "Spirit", artist: "Talk Talk", artistId: "ar1", coverArt: nil, songCount: 8, duration: 2520, year: 1988, genre: nil, created: nil, musicBrainzId: nil),
                                         songs: [s] + Array(repeating: other, count: 7))
        let texts = LocalFacts.make(song: s, album: album, artistName: "Talk Talk", artistAlbumCount: 3, now: now).map(\.text)
        #expect(texts.contains("Track 4 of 8 on Spirit"))
        #expect(texts.contains("Spirit came out in 1988, 38 years ago"))
        #expect(texts.contains("Spirit runs 42 minutes over 8 songs"))
        #expect(texts.contains("You have played this 18 times"))
        #expect(texts.contains("You last played this 1 month ago"))
        #expect(texts.contains("Added to your library 2 years ago"))
        #expect(texts.contains("This file is FLAC, 24-bit / 96 kHz"))
        #expect(texts.contains("You rated this 4 of 5"))
        #expect(texts.contains("3 albums by Talk Talk in your library"))
        #expect(LocalFacts.make(song: nil, album: nil, artistName: nil, artistAlbumCount: nil, now: now).isEmpty)
    }

    @Test func aSongWithoutPlaysSaysSoAndSkipsTheLastPlayedLine() throws {
        let s = try song(#"{"id":"s1","title":"Song","suffix":"mp3","bitRate":320}"#)
        let texts = LocalFacts.make(song: s, album: nil, artistName: nil, artistAlbumCount: nil, now: now).map(\.text)
        #expect(texts.contains("No plays of this song are recorded yet") && !texts.contains { $0.hasPrefix("You last played") })
        #expect(texts.contains("This file is MP3 at 320 kbps"))
    }

    @Test func linesAlternateBetweenTheServerAndTheLibraryWithoutRepeats() {
        func f(_ t: String, _ o: PlayerFact.Origin) -> PlayerFact { PlayerFact(kind: t, text: t, source: "s", origin: o) }
        let mixed = FactsModel.mix(knowledge: [f("k1", .knowledge), f("k2", .knowledge), f("k1", .knowledge)], library: [f("l1", .library), f("l2", .library), f("l3", .library)])
        #expect(mixed.map(\.text) == ["k1", "l1", "k2", "l2", "l3"])
        #expect(FactsModel.mix(knowledge: [], library: []).isEmpty)
    }

    @Test func onlyMusicBrainzHttpsPagesBecomeLinks() {
        #expect(FactsModel.safeURL("https://musicbrainz.org/recording/x") != nil)
        #expect(FactsModel.safeURL("http://musicbrainz.org/recording/x") == nil)
        #expect(FactsModel.safeURL("https://evil.example/musicbrainz.org") == nil)
    }

    @Test func theTwoSwitchesAreOnByDefaultAndRemembered() throws {
        let defaults = try #require(UserDefaults(suiteName: "player-bar-\(UUID().uuidString)"))
        let a = PlayerBarOptions(defaults: defaults)
        #expect(a.showLyrics && a.showFacts)
        a.showLyrics = false
        let b = PlayerBarOptions(defaults: defaults)
        #expect(!b.showLyrics && b.showFacts)
    }

    @Test func theQuoteMarkSitsInsideItsBox() {
        let r = QuoteMark().path(in: CGRect(x: 0, y: 0, width: 24, height: 24)).boundingRect
        #expect(r.minX == 5 && r.maxX == 19 && r.minY == 7 && r.maxY == 17)
    }

    /// The restart bug: the queue comes back before the connection exists, so the first ask for a cover gets nothing. The
    /// view has to ask again when the connection arrives.
    @Test func aCoverAskedForBeforeTheConnectionStillArrivesAfterIt() async throws {
        RenderMode.offscreenScreenshot = true
        defer { RenderMode.offscreenScreenshot = false }
        let store = ArtworkStore(transport: PlainTransport())
        let album = AlbumItem(id: -1, title: "t", artist: "a", year: 0, genre: "", format: "", owned: true, hue: 200, coverArt: "al-1")
        let host = NSHostingView(rootView: ArtworkImage(album: album).environment(\.artwork, store).frame(width: 100, height: 100))
        host.frame = NSRect(x: 0, y: 0, width: 100, height: 100)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.makeKeyAndOrderFront(nil)
        try await Task.sleep(for: .milliseconds(200))
        #expect(host.isRed == false, "no connection yet: nothing is drawn")
        store.configure(try StreamURLBuilder(baseURL: URL(string: "http://192.168.1.87:4533")!, auth: SubsonicAuth(credential: Credential(username: "o", password: "pw"))))
        var drawn = false
        for _ in 0..<30 where !drawn {
            try await Task.sleep(for: .milliseconds(100))
            drawn = host.isRed
        }
        window.orderOut(nil)
        #expect(drawn, "the cover should load once the connection is configured")
    }
}

private struct PlainTransport: HTTPTransport {
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let img = NSImage(size: NSSize(width: 20, height: 20))
        img.lockFocus(); NSColor.red.setFill(); NSRect(x: 0, y: 0, width: 20, height: 20).fill(); img.unlockFocus()
        let png = NSBitmapImageRep(data: img.tiffRepresentation!)!.representation(using: .png, properties: [:])!
        return (png, HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
    }
}

private extension NSView {
    /// True when the middle of the view is clearly red.
    @MainActor var isRed: Bool {
        guard let rep = bitmapImageRepForCachingDisplay(in: bounds) else { return false }
        cacheDisplay(in: bounds, to: rep)
        guard let c = rep.colorAt(x: rep.pixelsWide / 2, y: rep.pixelsHigh / 2)?.usingColorSpace(.sRGB) else { return false }
        return c.redComponent > 0.8 && c.greenComponent < 0.3
    }
}
