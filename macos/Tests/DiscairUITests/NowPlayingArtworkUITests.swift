import AppKit
import DiscairAudio
import DiscairCore
import DiscairNavidrome
import Foundation
import Testing
@testable import DiscairUI

private struct PNGTransport: HTTPTransport {
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 400, pixelsHigh: 400, bitsPerSample: 8, samplesPerPixel: 4,
                                   hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        let data = rep.representation(using: .png, properties: [:])!
        return (data, HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
    }
}

/// Now Playing artwork (docs/artwork.md, ideas 3 to 5): the slideshow switch and the cover the system is given.
@MainActor
@Suite("Now Playing artwork", .serialized)
struct NowPlayingArtworkUITests {
    @Test func theSlideshowSwitchIsOnByDefaultAndRemembered() throws {
        let defaults = try #require(UserDefaults(suiteName: "discair.test.slideshow.\(UUID().uuidString)"))
        let first = PlayerBarOptions(defaults: defaults)
        #expect(first.showSlideshow)
        first.showSlideshow = false
        #expect(PlayerBarOptions(defaults: defaults).showSlideshow == false)
        first.showSlideshow = true
        #expect(PlayerBarOptions(defaults: defaults).showSlideshow)
    }

    @Test func theSystemCoverKeyChangesWithThePick() {
        let song = QueueItem(songID: "s", title: "t", artist: "a", album: "b", albumID: "42", coverArt: "al-42", duration: 1)
        #expect(SystemMedia.coverKey(song, pick: nil) != SystemMedia.coverKey(song, pick: 7))
        #expect(SystemMedia.coverKey(song, pick: 7) == SystemMedia.coverKey(song, pick: 7))
    }

    @Test func aLibraryCoverIsLoadedByItsCoverId() async throws {
        let store = ArtworkStore(transport: PNGTransport())
        store.configure(try StreamURLBuilder(baseURL: URL(string: "http://192.168.1.87:4533")!, auth: SubsonicAuth(credential: Credential(username: "o", password: "pw"))))
        let image = await store.libraryCover(albumID: "42", coverArt: "al-42", px: 600)
        #expect(image != nil)
        #expect(await store.libraryCover(albumID: nil, coverArt: nil, px: 600) == nil)
    }

    @Test func noLibrarianMeansNoAlbumIndex() async {
        let store = ArtworkStore(transport: PNGTransport())
        #expect(await store.nowPlayingIndex(artist: "a", album: "b") == nil)
        #expect(await store.nowPlayingIndex(artist: "a", album: "") == nil)
    }
}
