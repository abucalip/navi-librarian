import AppKit
import DiscairAudio
import DiscairCore
import Testing
@testable import DiscairUI

@Suite @MainActor struct WidgetPublisherTests {
    private let song = QueueItem(songID: "s1", title: "Title", artist: "Artist", album: "Album", coverArt: "al-1", duration: 200)
    private func setup() -> (WidgetPublisher, URL, Counter) {
        let dir = FileManager.default.temporaryDirectory.appending(path: "wp-\(UUID().uuidString)")
        let counter = Counter()
        return (WidgetPublisher(folder: dir, reload: { counter.n += 1 }), dir, counter)
    }
    private final class Counter { var n = 0 }
    private func cover() -> NSImage {
        let img = NSImage(size: NSSize(width: 640, height: 640))
        img.lockFocus(); NSColor.red.setFill(); NSRect(x: 0, y: 0, width: 640, height: 640).fill(); img.unlockFocus()
        return img
    }

    @Test func publishesTheSongAndReloadsOnce() throws {
        let (p, dir, count) = setup(); defer { try? FileManager.default.removeItem(at: dir) }
        p.publish(item: song, duration: 200, position: 10, playing: true, cover: nil)
        p.publish(item: song, duration: 200, position: 10, playing: true, cover: nil)   // same state: nothing new
        let snap = try #require(NowPlayingShare.read(in: dir))
        #expect(snap.title == "Title" && snap.isPlaying && snap.coverFile == nil)
        #expect(count.n == 1)
    }

    @Test func aCoverArrivingLaterIsWrittenSmallAsJPEG() throws {
        let (p, dir, count) = setup(); defer { try? FileManager.default.removeItem(at: dir) }
        p.publish(item: song, duration: 200, position: 0, playing: true, cover: nil)
        p.publish(item: song, duration: 200, position: 0, playing: true, cover: cover())
        let snap = try #require(NowPlayingShare.read(in: dir))
        let data = try #require(NowPlayingShare.coverData(for: snap, in: dir))
        let image = try #require(NSBitmapImageRep(data: data))
        #expect(image.pixelsWide == WidgetPublisher.coverPixels)
        #expect(count.n == 2)
    }

    @Test func pauseAndSeekAreWrittenButPlainTickingIsNot() {
        let (p, dir, count) = setup(); defer { try? FileManager.default.removeItem(at: dir) }
        p.publish(item: song, duration: 200, position: 10, playing: true, cover: nil)
        p.publish(item: song, duration: 200, position: 10.5, playing: true, cover: nil)   // within tolerance
        #expect(count.n == 1)
        p.publish(item: song, duration: 200, position: 10.5, playing: false, cover: nil)
        #expect(count.n == 2)
        p.publish(item: song, duration: 200, position: 150, playing: false, cover: nil)
        #expect(count.n == 3)
    }

    @Test func stoppingClearsTheFilesOnce() {
        let (p, dir, count) = setup(); defer { try? FileManager.default.removeItem(at: dir) }
        p.publish(item: song, duration: 200, position: 0, playing: true, cover: nil)
        p.publish(item: nil, duration: 0, position: 0, playing: false, cover: nil)
        p.publish(item: nil, duration: 0, position: 0, playing: false, cover: nil)
        #expect(NowPlayingShare.read(in: dir) == nil)
        #expect(count.n == 2)
    }

    @Test func aStationIsWrittenLiveWithItsLogoAndReloadsOnce() throws {
        let (p, dir, count) = setup(); defer { try? FileManager.default.removeItem(at: dir) }
        p.publishLive(stationName: "FIP", stationID: "fip", logo: nil)
        p.publishLive(stationName: "FIP", stationID: "fip", logo: nil)   // same state: nothing new
        #expect(count.n == 1)
        let snap = try #require(NowPlayingShare.read(in: dir))
        #expect(snap.live && snap.title == "FIP" && snap.duration == 0 && snap.coverFile == nil)
        p.publishLive(stationName: "FIP", stationID: "fip", logo: cover())   // the logo arrives
        #expect(count.n == 2)
        let withLogo = try #require(NowPlayingShare.read(in: dir))
        #expect(NowPlayingShare.coverData(for: withLogo, in: dir) != nil)
    }

    @Test func anotherStationWritesAgainAndStoppingClears() {
        let (p, dir, count) = setup(); defer { try? FileManager.default.removeItem(at: dir) }
        p.publishLive(stationName: "FIP", stationID: "fip", logo: nil)
        p.publishLive(stationName: "KEXP", stationID: "kexp", logo: nil)
        #expect(count.n == 2)
        p.publish(item: nil, duration: 0, position: 0, playing: false, cover: nil)
        #expect(NowPlayingShare.read(in: dir) == nil)
        #expect(count.n == 3)
    }

    @Test func aSongAfterAStationReplacesTheLiveSnapshot() throws {
        let (p, dir, _) = setup(); defer { try? FileManager.default.removeItem(at: dir) }
        p.publishLive(stationName: "FIP", stationID: "fip", logo: nil)
        p.publish(item: song, duration: 200, position: 0, playing: true, cover: nil)
        #expect(try #require(NowPlayingShare.read(in: dir)).live == false)
    }
}
