import DiscairAudio
import AppKit
import SwiftUI
import Testing
@testable import DiscairUI

@MainActor
struct MiniPlayerTests {
    private func item(_ t: String, _ a: String = "Artist") -> QueueItem { QueueItem(songID: t, title: t, artist: a) }

    @Test func emptyQueueShowsNothingPlayingAndNothingNext() {
        let c = MiniPlayerContent(current: nil, upNext: [])
        #expect(c.title == "Nothing playing")
        #expect(!c.hasSong)
        #expect(c.next == nil)
    }

    @Test func peeksAtTheFirstSongInUpNextOnly() {
        let c = MiniPlayerContent(current: item("One"), upNext: [item("Two", "B"), item("Three")])
        #expect(c.hasSong)
        #expect(c.title == "One")
        #expect(c.next == "Two · B")
    }

    @Test func lastSongHasNoNext() {
        #expect(MiniPlayerContent(current: item("One"), upNext: []).next == nil)
    }

    @Test func nextWithoutArtistShowsTitleAlone() {
        #expect(MiniPlayerContent(current: item("One"), upNext: [item("Two", "")]).next == "Two")
    }

    @Test(arguments: [ThemeID.cupertino, ThemeID.zine])
    func rendersMiniWindow(theme: ThemeID) throws {
        RenderMode.offscreenScreenshot = true
        let state = AppState(themeID: theme, screen: .home)
        state.player.play([QueueItem(songID: "a", title: "After the Flood", artist: "Talk Talk", duration: 300),
                           QueueItem(songID: "b", title: "Glory Box", artist: "Portishead", duration: 200)])
        let size = MiniPlayerView.size
        let host = NSHostingView(rootView: MiniPlayerView(state: state))
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.3))
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let png = try #require(rep.representation(using: .png, properties: [:]))
        let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
        try png.write(to: dir.appendingPathComponent("mini-\(theme.rawValue).png"))
    }
}
