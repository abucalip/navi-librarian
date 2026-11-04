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
}
