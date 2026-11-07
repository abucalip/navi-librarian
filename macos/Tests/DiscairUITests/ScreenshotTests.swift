import AppKit
import DiscairAudio
import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import SwiftUI
import Testing
@testable import DiscairUI

/// Renders each theme screen to PNG. Output goes to `DISCAIR_SCREENSHOT_DIR` (CI uploads it) or a temp folder.
/// Baseline comparison is added once the owner approves the look on the Mac (contract M4 gate).
@MainActor
struct ScreenshotTests {
    @Test(arguments: ThemeID.allCases, [Screen.home, Screen.album, Screen.nowPlaying, Screen.queue, Screen.library, Screen.albums, Screen.artist, Screen.settings, Screen.downloads, Screen.discover, Screen.equalizer, Screen.gapRadar, Screen.atlas, Screen.smartPlaylists, Screen.history, Screen.insights, Screen.connections])
    func rendersWindow(theme: ThemeID, screen: Screen) throws {
        RenderMode.offscreenScreenshot = true
        // Settings needs a session; a throwaway one with a sample profile and an in-memory keychain.
        let session = SessionModel(store: ProfileStore(fileURL: FileManager.default.temporaryDirectory.appending(path: "discair-shot-\(UUID().uuidString)/profiles.json")), secrets: InMemorySecretStore())
        try session.addProfile(name: "Home", librarianURL: "http://192.168.1.87:8686", navidromeURL: "http://192.168.1.87:4533")
        try session.saveLogin(.navidrome, username: "owner", password: "not-shown")
        let state = AppState(themeID: theme, screen: screen, session: screen == .settings ? session : nil)
        let size = NSSize(width: 1280, height: 800)
        let host = NSHostingView(rootView: RootView(state: state).frame(width: size.width, height: size.height))
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        if screen == .downloads { state.acquisition.showJobs(AcquisitionModelTests.sampleJobs) }
        if screen == .discover { state.discovery.show(.personal, Fixtures.albums([7, 8, 9])) }
        if screen == .library && theme == .cupertino { state.library.apply(newest: [], first: [], artists: [], picks: []); state.library.showSongs(Fixtures.songs, more: true) }
        if screen == .connections { state.graph.preview(centre: GraphPreview.centre, nodes: GraphPreview.nodes); state.graph.selectedID = "b1" }
        if screen == .atlas { state.atlas.preview(places: [AtlasPreview.paris, AtlasPreview.addis]); state.atlas.selectedID = "p1" }
        if screen == .equalizer { state.player.updateEQ { $0.enabled = true; $0.choose(preset: "rock") } }
        if screen == .nowPlaying {
            state.lyrics.preview(Lyrics(timed: true, lines: ["A slow tide under the floorboards", "the lamp keeps counting what we left", "one long note, then the room agrees", "nobody here is in a hurry", "the water finds its level"].enumerated().map { LyricLine(startMs: $0.offset * 4000, text: $0.element) }))
        }
        if screen == .queue || screen == .nowPlaying {
            let q = (0..<6).map { QueueItem(songID: "s\($0)", title: ["After the Flood", "Glory Box", "Cloudbusting", "Maria También", "So What", "Such a Shame"][$0], artist: ["Talk Talk", "Portishead", "Kate Bush", "Khruangbin", "Miles Davis", "Talk Talk"][$0], album: "Album", duration: Double(180 + $0 * 37)) }
            state.player.play(q)
        }
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.5))
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let png = try #require(rep.representation(using: .png, properties: [:]))
        // A blank render is one flat colour; real UI has many. Sample a grid and count distinct quantised colours, which
        // does not depend on the render scale (CI and a Retina Mac produce different image sizes).
        var colours = Set<Int>()
        for ix in 0..<48 {
            for iy in 0..<30 {
                let x = (rep.pixelsWide - 1) * ix / 47, y = (rep.pixelsHigh - 1) * iy / 29
                guard let c = rep.colorAt(x: x, y: y)?.usingColorSpace(.sRGB) else { continue }
                colours.insert(Int(c.redComponent * 15) << 8 | Int(c.greenComponent * 15) << 4 | Int(c.blueComponent * 15))
            }
        }
        #expect(colours.count >= 8, "render looks blank (\(colours.count) distinct colours)")
        let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try png.write(to: dir.appendingPathComponent("\(theme.rawValue)-\(screen.rawValue).png"))
    }

    @Test func everyThemeIDResolves() {
        for id in ThemeID.allCases { #expect(ThemeRegistry.theme(id).id == id) }
    }
}

/// A small made-up walk for the explorer screenshot: owned and unowned artists and albums, credits and plain links.
enum GraphPreview {
    private static func entity(_ id: String, _ name: String, _ type: String, owned: Bool) -> KnowledgeEntity {
        try! JSONDecoder().decode(KnowledgeEntity.self, from: Data(#"{"mbid":"\#(id)","canonical_name":"\#(name)","type":"\#(type)","owned":\#(owned)}"#.utf8))
    }
    static let centre = entity("c", "Talk Talk", "artist", owned: true)
    static let nodes: [GraphNode] = [
        ("a1", "Spirit of Eden", "release", true, 1, "c", true), ("a2", "Laughing Stock", "release", true, 1, "c", true),
        ("a3", "Mark Hollis", "artist", false, 1, "c", true), ("b1", "Tim Friese-Greene", "artist", true, 1, "c", true),
        ("a4", "It's My Life", "release", false, 1, "c", true), ("a5", "EMI", "label", false, 1, "c", false),
        ("d1", "Phil Brown", "artist", false, 2, "b1", true), ("d2", "Colour of Spring", "release", false, 2, "b1", false),
    ].map { GraphNode(entity: entity($0.0, $0.1, $0.2, owned: $0.3), depth: $0.4, via: $0.5, credit: $0.6, evidence: []) }
}

/// Two sample places for the atlas screenshot.
@MainActor enum AtlasPreview {
    static func make(_ id: String, _ name: String, _ lat: Double, _ lon: Double, _ owned: Int) -> AtlasPlace {
        try! JSONDecoder().decode(AtlasPlace.self, from: Data(#"{"entity":{"mbid":"\#(id)","canonical_name":"\#(name)","type":"place"},"kind":"studio","latitude":\#(lat),"longitude":\#(lon),"recordings":9,"owned_recordings":\#(owned)}"#.utf8))
    }
    static let paris = make("p1", "Example Studio, Paris", 48.85, 2.41, 7)
    static let addis = make("p2", "Addis Hall", 9.03, 38.74, 0)
}
