import AppKit
import SwiftUI
import Testing
@testable import DiscairUI

@MainActor
struct CommandPaletteTests {
    private func album(_ id: Int, _ title: String, _ artist: String, owned: Bool = true) -> AlbumItem {
        AlbumItem(id: id, title: title, artist: artist, year: 1986, genre: "", format: "", owned: owned, hue: 10)
    }
    private func titles(_ q: String, albums: [AlbumItem] = [], artists: [ArtistItem] = []) -> [String] {
        PaletteCatalog.results(query: q, playing: false, albums: albums, artists: artists).map(\.title)
    }

    @Test func emptyQueryListsScreensAndPlayback() {
        let t = titles("")
        #expect(t.first == "Go to Home")
        #expect(t.count == 9)
    }

    @Test func screenWordFindsItsScreen() {
        #expect(titles("down").first == "Go to Downloads")
        #expect(titles("eq").first == "Go to Equalizer")
    }

    @Test func playbackLabelFollowsPlayState() {
        let playing = PaletteCatalog.fixed(playing: true).first { $0.id == "playpause" }
        #expect(playing?.title == "Pause")
        #expect(PaletteCatalog.fixed(playing: false).first { $0.id == "playpause" }?.title == "Play")
    }

    @Test func ownedAlbumOffersPlayAndMissingOffersGet() {
        let owned = album(1, "Spirit of Eden", "Talk Talk")
        let missing = album(2, "Dummy", "Portishead", owned: false)
        let t = titles("o", albums: [owned, missing])
        #expect(titles("eden", albums: [owned, missing]).contains("Play Spirit of Eden · Talk Talk"))
        #expect(!titles("eden", albums: [owned, missing]).contains("Get Spirit of Eden · Talk Talk"))
        #expect(titles("dummy", albums: [owned, missing]).contains("Get Dummy · Portishead"))
        #expect(!t.isEmpty)
    }

    @Test func matchingIgnoresCaseAndAccents() {
        let a = album(3, "Mélodie", "Étienne")
        #expect(titles("melodie", albums: [a]).contains("Open Mélodie · Étienne"))
    }

    @Test func everyWordOfTheQueryMustMatch() {
        let a = album(4, "Dummy", "Portishead")
        #expect(titles("dummy portis", albums: [a]).contains("Open Dummy · Portishead"))
        #expect(!titles("dummy zzz", albums: [a]).contains("Open Dummy · Portishead"))
    }

    @Test func noMatchGivesNothing() { #expect(titles("qqqqqq").isEmpty) }

    @Test func duplicateAlbumsAppearOnce() {
        let a = album(5, "Dummy", "Portishead"), b = album(6, "Dummy", "Portishead")
        #expect(titles("dummy", albums: [a, b]).filter { $0.hasPrefix("Open Dummy") }.count == 1)
    }

    @Test func performGoesToScreenAndCloses() {
        let state = AppState(themeID: .cupertino, screen: .home)
        state.palette.open()
        state.palette.query = "settings"
        let first = try! #require(state.paletteResults().first)
        state.perform(first)
        #expect(state.screen == .settings)
        #expect(!state.palette.isOpen)
    }

    @Test func highlightWrapsAndResetsOnTyping() {
        let p = PaletteModel()
        p.open()
        p.move(-1, count: 3)
        #expect(p.highlight == 2)
        p.move(1, count: 3)
        #expect(p.highlight == 0)
        p.highlight = 2
        p.query = "x"
        #expect(p.highlight == 0)
    }

    @Test(arguments: [ThemeID.cupertino, ThemeID.zine])
    func rendersOpenPalette(theme: ThemeID) throws {
        RenderMode.offscreenScreenshot = true
        let state = AppState(themeID: theme, screen: .home)
        state.palette.open()
        state.palette.query = "a"
        let size = CGSize(width: 1100, height: 700)
        let host = NSHostingView(rootView: RootView(state: state))
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.4))
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let png = try #require(rep.representation(using: .png, properties: [:]))
        let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
        try png.write(to: dir.appendingPathComponent("palette-\(theme.rawValue).png"))
    }
}
