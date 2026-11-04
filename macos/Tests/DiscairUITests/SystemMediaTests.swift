import AppKit
import DiscairAudio
import MediaPlayer
import Testing
@testable import DiscairUI

@Suite @MainActor struct SystemMediaTests {
    private let song = QueueItem(songID: "s1", title: "Title", artist: "Artist", album: "Album", coverArt: "al-1", duration: 200)

    @Test func infoWithoutCoverHasTextAndTimingOnly() {
        let info = SystemMedia.info(for: song, duration: 200, position: 12, playing: true, cover: nil)
        #expect(info[MPMediaItemPropertyTitle] as? String == "Title")
        #expect(info[MPMediaItemPropertyArtist] as? String == "Artist")
        #expect(info[MPMediaItemPropertyAlbumTitle] as? String == "Album")
        #expect(info[MPNowPlayingInfoPropertyElapsedPlaybackTime] as? Double == 12)
        #expect(info[MPNowPlayingInfoPropertyPlaybackRate] as? Double == 1)
        #expect(info[MPMediaItemPropertyArtwork] == nil)
    }

    @Test func infoWithCoverCarriesTheArtworkAtItsSize() throws {
        let cover = NSImage(size: NSSize(width: 600, height: 600))
        let info = SystemMedia.info(for: song, duration: 200, position: 0, playing: false, cover: cover)
        #expect(info[MPNowPlayingInfoPropertyPlaybackRate] as? Double == 0)
        let art = try #require(info[MPMediaItemPropertyArtwork] as? MPMediaItemArtwork)
        #expect(art.bounds.size == CGSize(width: 600, height: 600))
        #expect(art.image(at: CGSize(width: 100, height: 100)) === cover)
    }

    private func picture(width: Int, height: Int) -> NSImage {
        let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height, bitsPerSample: 8, samplesPerPixel: 4,
                                   hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        let image = NSImage(size: NSSize(width: width, height: height))
        image.addRepresentation(rep)
        return image
    }

    @Test func aWideCoverIsCutToACentredSquare() throws {
        let square = try #require(SystemMedia.squareCover(picture(width: 600, height: 450)))
        #expect(square.size == NSSize(width: 450, height: 450))
    }

    @Test func aTallCoverIsCutToACentredSquare() throws {
        let square = try #require(SystemMedia.squareCover(picture(width: 400, height: 600)))
        #expect(square.size == NSSize(width: 400, height: 400))
    }

    @Test func aSquareCoverIsLeftAlone() throws {
        let original = picture(width: 600, height: 600)
        #expect(SystemMedia.squareCover(original) === original)
    }
}
