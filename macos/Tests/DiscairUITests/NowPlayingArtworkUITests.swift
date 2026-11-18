import AppKit
import DiscairAudio
import DiscairCore
import DiscairLibrarian
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

/// Now Playing artwork (docs/archive/completed/artwork.md, ideas 3 to 5): the slideshow switch and the cover the system is given.
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

/// The Core Animation slideshow's keyframes against the SwiftUI rule it replaced (`slideshowFrame`): at every moment of the cycle
/// the layers, stacked in order, show the same photos in the same mix and at the same zoom-and-pan progress.
@Suite("Slideshow keyframes")
struct SlideshowKeyframesTests {
    @Test(arguments: [2, 3, 5, 12])
    func layersMatchTheSlideshowRule(count: Int) {
        let hold = 14.0, fade = 3.0, cycle = Double(count) * hold
        let frames = (0..<count).map { SlideshowKeyframes(index: $0, count: count, hold: hold, fade: fade) }
        var t = 0.05
        while t < cycle * 2 {
            let local = t.truncatingRemainder(dividingBy: cycle)
            let edge = (0...count).map { Double($0) * hold }.contains { abs(local - $0) < 0.01 }
            if !edge {
                // Stack the layers bottom to top: each one covers what is under it by its opacity.
                var weight = Array(repeating: 0.0, count: count)
                for (i, f) in frames.enumerated() {
                    let o = f.value(at: local).opacity
                    weight = weight.map { $0 * (1 - o) }
                    weight[i] += o
                }
                let rule = slideshowFrame(elapsed: t, count: count, hold: hold, fade: fade)!
                var expected = Array(repeating: 0.0, count: count)
                expected[rule.index] += 1 - rule.mix
                expected[rule.next] += rule.mix
                for i in 0..<count { #expect(abs(weight[i] - expected[i]) < 0.01, "t \(t) photo \(i)") }
                #expect(abs(frames[rule.index].value(at: local).progress - rule.progress) < 0.01, "t \(t) progress")
                if rule.mix > 0.01 { #expect(frames[rule.next].value(at: local).progress < 0.01, "t \(t) next still") }
            }
            t += 0.25
        }
    }
}
