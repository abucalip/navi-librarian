import AppKit
import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import SwiftUI
import Testing
@testable import DiscairUI

/// Renders the screens that read the library with live-shaped data (no artwork, since nothing is fetched), to check
/// the layout with real-looking names, empty years and genres, and the "Nothing playing" state.
private struct OkTransport: HTTPTransport {
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let body = request.url!.path == "/api/acquisitions"
            ? #"{"ok":true,"acquisitions":[{"artist":"Stereolab","album":"Dots and Loops","status":"downloading","details":{"live_progress":{"available":true,"percent":64}}},{"artist":"Fela Kuti","album":"Zombie","status":"queued"}]}"#
            : #"{"ok":true,"status":"queued","message":"Queued for download."}"#
        return (Data(body.utf8), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
    }
}

@MainActor
struct LiveScreenshotTests {
    /// Album pages with two-digit track numbers (the Cupertino table used to wrap each digit onto its own line).
    @Test(arguments: ThemeID.allCases)
    func rendersTwoDigitTrackNumbers(theme: ThemeID) throws {
        RenderMode.offscreenScreenshot = true
        let state = try liveState(theme: theme, screen: .album)
        state.library.showTracks((0..<14).map {
            TrackItem(id: $0, title: "Track number \($0 + 1)", duration: "\($0 + 3):0\($0 % 10)", format: "FLAC", owned: $0 != 11, playing: false)
        })
        try render(state, theme, .album, suffix: "tracks")
    }

    /// Home when the Librarian has nothing to recommend (no sample lead story may appear).
    @Test(arguments: ThemeID.allCases)
    func rendersHomeWithoutRecommendations(theme: ThemeID) throws {
        RenderMode.offscreenScreenshot = true
        let state = try liveState(theme: theme, screen: .home)
        let albums = try JSONDecoder().decode([NavidromeAlbum].self, from: Data(#"[{"id":"1","name":"Laughing Stock","artist":"Talk Talk"},{"id":"2","name":"Dummy","artist":"Portishead"}]"#.utf8))
        state.library.apply(newest: albums, first: albums, artists: [], picks: [], picksNote: "Add your Librarian login in Settings to see recommendations.")
        try render(state, theme, .home, suffix: "nopicks")
    }

    /// Home with a job list (ticker, Requested button) and a Not for me waiting for its Undo.
    @Test(arguments: ThemeID.allCases)
    func rendersAcquisitionStates(theme: ThemeID) async throws {
        RenderMode.offscreenScreenshot = true
        let state = try liveState(theme: theme, screen: .home)
        state.acquisition.configure(librarian: try LibrarianClient(baseURL: URL(string: "https://lib.example.ts.net")!,
                                                                    credential: Credential(username: "o", password: "p"), transport: OkTransport()))
        await state.acquisition.refresh()
        await state.acquisition.get(state.library.missing[0])
        state.acquisition.notForMe(state.library.missing[2])
        try render(state, theme, .home, suffix: "acq")
        state.acquisition.configure(librarian: nil)
    }

    private func liveState(theme: ThemeID, screen: Screen) throws -> AppState {
        let state = AppState(themeID: theme, screen: screen)
        let dec = JSONDecoder()
        let albums = try dec.decode([NavidromeAlbum].self, from: Data(#"""
        [{"id":"1","name":"Laughing Stock","artist":"Talk Talk","artistId":"a1","coverArt":"1","songCount":6,"duration":2460,"year":1991,"genre":"Post-rock"},
         {"id":"2","name":"Dummy","artist":"Portishead","artistId":"a2","year":1994},
         {"id":"3","name":"A Very Long Album Title That Keeps Going And Going","artist":"An Artist With A Long Name","artistId":"a3"},
         {"id":"4","name":"Spirit of Eden","artist":"Talk Talk","artistId":"a1","year":1988,"genre":"Art rock"}]
        """#.utf8))
        let artists = try dec.decode([NavidromeArtist].self, from: Data(#"[{"id":"a1","name":"Talk Talk","albumCount":2},{"id":"a2","name":"Portishead","albumCount":1},{"id":"a3","name":"An Artist With A Long Name","albumCount":1},{"id":"a4","name":"Tortoise","albumCount":3},{"id":"a5","name":"Tom Waits","albumCount":9}]"#.utf8))
        let picks = try dec.decode(DashboardPicks.self, from: Data(#"""
        {"items":[{"artist":"Can","album":"Tago Mago","reason":"A double album that sits behind the Talk Talk records you play every week.","genres":["krautrock"],"suggested_tracks":["Halleluhwah","Paperhouse","Oh Yeah"]},
                  {"artist":"Stereolab","album":"Dots and Loops"},{"artist":"Cocteau Twins","album":"Heaven or Las Vegas"},
                  {"artist":"Fela Kuti","album":"Zombie"},{"artist":"Talk Talk","album":"The Colour of Spring"},{"artist":"Talk Talk","album":"Laughing Stock"}]}
        """#.utf8)).items
        state.library.apply(newest: albums, first: albums, artists: artists, picks: picks)
        state.selectedAlbum = state.library.recent[0]
        state.selectedArtist = state.library.artists[0]
        state.selectedLetter = "T"
        return state
    }

    @Test(arguments: ThemeID.allCases, [Screen.home, Screen.album, Screen.artist, Screen.library, Screen.albums])
    func rendersLive(theme: ThemeID, screen: Screen) async throws {
        RenderMode.offscreenScreenshot = true
        let state = try liveState(theme: theme, screen: screen)
        await state.library.loadArtist(state.selectedArtist, navidrome: nil)
        await state.library.loadTracks(for: state.library.missing[0], navidrome: nil)   // a pick: suggested tracks
        if screen == .album { state.selectedAlbum = state.library.missing[0] }
        try render(state, theme, screen)
        #expect(state.library.isLive)
    }

    private func render(_ state: AppState, _ theme: ThemeID, _ screen: Screen, suffix: String = "live") throws {
        let size = NSSize(width: 1280, height: 800)
        let host = NSHostingView(rootView: RootView(state: state).frame(width: size.width, height: size.height))
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.5))
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let png = try #require(rep.representation(using: .png, properties: [:]))
        let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try png.write(to: dir.appendingPathComponent("\(theme.rawValue)-\(screen.rawValue)-\(suffix).png"))
    }
}
