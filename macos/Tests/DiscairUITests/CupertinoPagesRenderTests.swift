import AppKit
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

/// Renders the redesigned Cupertino Insights, History, Downloads and Gap Radar pages to PNG, to be put beside the mockups in
/// `docs/design/redesign/macos/cupertino/`. Output goes to `DISCAIR_SCREENSHOT_DIR` (or a temp folder) as `cupertino-<page>.png`.
@MainActor
struct CupertinoPagesRenderTests {
    /// The server's own taste body with a saved listening context, from the contract fixture (the morning-vs-night contrast is stated).
    static func tasteResponse() throws -> TasteResponse {
        let url = URL(fileURLWithPath: #filePath).deletingLastPathComponent().appending(path: "../../../intelligence/contract-fixtures/taste_context_contrast.json").standardized
        let object = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
        return try JSONDecoder().decode(TasteResponse.self, from: JSONSerialization.data(withJSONObject: object["response"]!))
    }

    static func jobs() throws -> [Acquisition] {
        let now = Date().timeIntervalSince1970
        let raw: [[String: Any]] = [
            ["artist": "Slowdive", "album": "Pygmalion", "status": "downloading", "updated_at": now - 300, "created_at": now - 900,
             "details": ["album_name": "Pygmalion", "live_progress": ["available": true, "percent": 64.0, "completed_tracks": 7, "total_tracks": 9]]],
            ["artist": "Broadcast", "album": "Tender Buttons", "status": "searching", "updated_at": now - 180, "created_at": now - 180],
            ["artist": ".O.rang", "album": "Herd of Instinct", "status": "slskd_error", "updated_at": now - 1200, "created_at": now - 3600,
             "details": ["message": "Stopped: the source went offline at 41%."]],
            ["artist": "The Blue Nile", "album": "Hats", "status": "imported", "updated_at": now - 3600, "created_at": now - 7200],
        ]
        return try raw.map { try JSONDecoder().decode(Acquisition.self, from: JSONSerialization.data(withJSONObject: ["title": $0["album"]!, "id": $0["album"]!].merging($0) { a, _ in a })) }
    }

    func render(_ name: String, width: CGFloat, height: CGFloat, _ view: some View, setup: (AppState) -> Void) throws {
        RenderMode.offscreenScreenshot = true
        let host = NSHostingView(rootView: view.frame(width: width, height: height).background(Color.white).environment(\.colorScheme, .light))
        host.frame = NSRect(origin: .zero, size: NSSize(width: width, height: height))
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(1.2))
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let png = try #require(rep.representation(using: .png, properties: [:]))
        let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try png.write(to: dir.appendingPathComponent("cupertino-\(name).png"))
    }

    @Test func rendersInsights() throws {
        let state = AppState(themeID: .cupertino, screen: .insights)
        state.taste.showForPreview(try Self.tasteResponse())
        try render("insights", width: 1100, height: 1900, CupertinoInsights(state: state)) { _ in }
    }

    /// The Home radio card on its own (E7), to put beside the mockup's `.hcard`.
    @Test func rendersHomeRadioCards() throws {
        let state = AppState(themeID: .cupertino, screen: .home)
        let fip = RadioStation(id: "1", name: "FIP", proxied: true, playableURL: "https://example.invalid/1", favourite: true, tags: ["Eclectic"],
                               lastPlayedAt: Date().timeIntervalSince1970 - 3600)
        state.stations.showForPreview(stations: [fip])
        state.player.live = LiveSession(stationID: "1", name: "FIP", logoPath: "", startedAt: Date().addingTimeInterval(-600), phase: .playing)
        state.player.liveNow = RadioNow(state: .ok, rawTitle: "Talk Talk - Life's What You Make It", artist: "Talk Talk", title: "Life's What You Make It", playID: 4)
        try render("home-radio-card-playing", width: 720, height: 90, HomeRadioCardView(state: state, card: HomeRadioCard.of(
            live: state.player.live, line: state.player.liveLine, lastStationID: nil, stations: [fip], at: Date())!).padding(12)) { _ in }
        try render("home-radio-card-resume", width: 720, height: 90, HomeRadioCardView(state: state, card: .resume(station: fip, lastPlayed: "Last played today, 21:17")).padding(12)) { _ in }
    }

    @Test func rendersHistory() throws {
        let state = AppState(themeID: .cupertino, screen: .history)
        state.library.showSongs(Fixtures.songs)
        try render("history", width: 1100, height: 1300, CupertinoHistory(state: state)) { _ in }
    }

    @Test func rendersDownloads() throws {
        let state = AppState(themeID: .cupertino, screen: .downloads)
        state.acquisition.showJobs(try Self.jobs())
        try render("downloads", width: 1100, height: 760, CupertinoDownloads(state: state)) { _ in }
    }

    @Test func rendersGapRadar() throws {
        let state = AppState(themeID: .cupertino, screen: .gapRadar)
        try render("gap-radar", width: 1100, height: 900, CupertinoGapRadar(state: state)) { _ in }
    }

    /// The Radio page (S2-1 item 7, mockup A2) with the mockup's sample stations. Logos are not fetched here, so they show as plain squares.
    @Test func rendersStations() throws {
        let state = AppState(themeID: .cupertino, screen: .stations)
        let day = Date().timeIntervalSince1970 - 3600
        func st(_ id: String, _ name: String, _ tags: [String], fav: Bool = false, proxied: Bool = true, played: Double? = nil) -> RadioStation {
            RadioStation(id: id, name: name, proxied: proxied, playableURL: "https://example.invalid/\(id)", favourite: fav, tags: tags, lastPlayedAt: played)
        }
        state.stations.showForPreview(stations: [
            st("1", "FIP", ["Eclectic"], fav: true, played: day),
            st("2", "Radio Paradise", ["Eclectic"], fav: true, played: day - 86_400 * 0.1),
            st("3", "KEXP", ["Indie"], fav: true, played: day - 86_400),
            st("4", "BBC Radio 6 Music", ["Indie", "Talk"], fav: true, proxied: false),
            st("5", "SomaFM Groove Salad", ["Electronic"], fav: true, played: day - 86_400 * 3),
            st("6", "Radio Swiss Jazz", ["Jazz"], fav: true),
            st("7", "NTS 1", ["Electronic", "Talk"]),
            st("8", "Worldwide FM", ["Jazz", "Eclectic"]),
        ], now: [
            "1": RadioNow(state: .ok, rawTitle: "Talk Talk - Life's What You Make It", artist: "Talk Talk", title: "Life's What You Make It"),
            "6": RadioNow(state: .noMetadata),
            "8": RadioNow(state: .unavailable),
        ])
        try render("stations", width: 1180, height: 640, CupertinoStations(state: state, selected: "1")) { _ in }
    }

    /// A station playing (S2-2 items 4 and 5): the page with the tinted row and the On Air hero, and the bar's live branch (mockup B1).
    @Test func rendersStationPlaying() throws {
        let state = AppState(themeID: .cupertino, screen: .stations)
        func st(_ id: String, _ name: String, _ tags: [String], fav: Bool = false) -> RadioStation {
            RadioStation(id: id, name: name, proxied: true, playableURL: "https://example.invalid/\(id)", favourite: fav, tags: tags)
        }
        state.stations.showForPreview(stations: [st("1", "FIP", ["Eclectic"], fav: true), st("2", "KEXP", ["Indie"], fav: true), st("3", "NTS 1", ["Electronic"])])
        state.player.live = LiveSession(stationID: "1", name: "FIP", logoPath: "", startedAt: Date().addingTimeInterval(-(19 * 60 + 12)), phase: .playing)
        try render("stations-playing", width: 1180, height: 420, CupertinoStations(state: state)) { _ in }
        try render("player-bar-live", width: 1180, height: CupertinoPlayerBar.height, CupertinoPlayerBar(state: state)) { _ in }
        // The live song (S2-3 items 1 and 2): the song over the artist, and Download, on the page and in the bar.
        state.player.liveNow = RadioNow(state: .ok, rawTitle: "Air - Playground Love", artist: "Air", title: "Playground Love", playID: 4)
        state.player.liveSongSince = Date().addingTimeInterval(-40)
        try render("stations-playing-song", width: 1180, height: 420, CupertinoStations(state: state)) { _ in }
        try render("player-bar-live-song", width: 1180, height: CupertinoPlayerBar.height, CupertinoPlayerBar(state: state)) { _ in }
        state.player.liveNow = RadioNow(state: .ok, rawTitle: "Air - Playground Love", artist: "Air", title: "Playground Love")
        try render("player-bar-live-listening", width: 1180, height: CupertinoPlayerBar.height, CupertinoPlayerBar(state: state)) { _ in }
        state.player.liveNow = RadioNow(state: .noMetadata)
        try render("stations-playing-nometa", width: 1180, height: 420, CupertinoStations(state: state)) { _ in }
        state.player.live?.phase = .reconnecting
        try render("stations-reconnecting", width: 1180, height: 420, CupertinoStations(state: state)) { _ in }
        // S2-4: the countdown line, "Station unreachable" with Retry, and the moon with minutes left.
        state.player.live?.reconnect = .init(attempt: 2, of: 5, retryAt: Date().addingTimeInterval(5))
        try render("player-bar-live-countdown", width: 1180, height: CupertinoPlayerBar.height, CupertinoPlayerBar(state: state)) { _ in }
        state.player.live?.reconnect = nil
        state.player.live?.phase = .unreachable
        try render("player-bar-live-unreachable", width: 1180, height: CupertinoPlayerBar.height, CupertinoPlayerBar(state: state)) { _ in }
        try render("stations-unreachable", width: 1180, height: 420, CupertinoStations(state: state)) { _ in }
        state.player.live?.phase = .playing
        state.player.sleepTimer.start(minutes: 45)
        try render("player-bar-live-sleep", width: 1180, height: CupertinoPlayerBar.height, CupertinoPlayerBar(state: state)) { _ in }
        state.player.sleepTimer.cancel()
    }

    /// Heard (S2-3 item 4): the On Air panel's Heard box, then the Heard tab with every state of the button, and the empty tab.
    @Test func rendersHeard() throws {
        let state = AppState(themeID: .cupertino, screen: .stations)
        state.stations.showForPreview(stations: [RadioStation(id: "1", name: "FIP", proxied: true, playableURL: "https://example.invalid/1", favourite: true, tags: ["Eclectic"]),
                                                  RadioStation(id: "2", name: "KEXP", proxied: true, playableURL: "https://example.invalid/2", tags: ["Indie"])])
        let t = Date().timeIntervalSince1970
        state.showHomeFeeds(radio: [
            RadioPlay(id: 1, stationName: "FIP", artist: "Elis Regina & Tom Jobim", title: "Águas de Março", heardAt: t - 900),
            RadioPlay(id: 2, stationName: "FIP", artist: "Radiohead", title: "Pyramid Song", heardAt: t - 1500, inLibrary: true),
            RadioPlay(id: 3, stationName: "FIP", artist: "Minnie Riperton", title: "Les Fleurs", heardAt: t - 1800, grabbed: true),
            RadioPlay(id: 4, stationName: "KEXP", artist: "Television", title: "Marquee Moon", heardAt: t - 86_400 * 1.2),
        ])
        state.player.live = LiveSession(stationID: "1", name: "FIP", logoPath: "", startedAt: Date().addingTimeInterval(-600), phase: .playing)
        state.player.liveNow = RadioNow(state: .ok, rawTitle: "Talk Talk - Life's What You Make It", artist: "Talk Talk", title: "Life's What You Make It")
        try render("stations-onair-heard", width: 1180, height: 760, CupertinoStations(state: state)) { _ in }
        state.stations.pane = .heard
        try render("stations-heard-tab", width: 1180, height: 640, CupertinoStations(state: state)) { _ in }
        let empty = AppState(themeID: .cupertino, screen: .stations)
        empty.stations.showForPreview(stations: [])
        empty.stations.pane = .heard
        try render("stations-heard-empty", width: 900, height: 300, CupertinoStations(state: empty)) { _ in }
    }

    /// Now Playing while a station plays (S2-3 item 3, mockup C1): the song, Download and Favourite on the left, what the station
    /// played tonight on the right.
    @Test func rendersNowPlayingLive() throws {
        let state = AppState(themeID: .cupertino, screen: .nowPlaying)
        state.stations.showForPreview(stations: [RadioStation(id: "1", name: "FIP", proxied: true, playableURL: "https://example.invalid/1", favourite: true, tags: ["Eclectic"]),
                                                  RadioStation(id: "2", name: "KEXP", proxied: true, playableURL: "https://example.invalid/2", favourite: true)])
        let t = Date().timeIntervalSince1970
        state.showHomeFeeds(radio: [
            RadioPlay(id: 1, stationName: "FIP", artist: "Elis Regina & Tom Jobim", title: "Águas de Março", heardAt: t - 600),
            RadioPlay(id: 2, stationName: "FIP", artist: "Radiohead", title: "Pyramid Song", heardAt: t - 1100, inLibrary: true),
            RadioPlay(id: 3, stationName: "FIP", artist: "Minnie Riperton", title: "Les Fleurs", heardAt: t - 1500, grabbed: true),
            RadioPlay(id: 4, stationName: "FIP", artist: "Miles Davis", title: "Blue in Green", heardAt: t - 2400, inLibrary: true),
        ])
        state.player.live = LiveSession(stationID: "1", name: "FIP", logoPath: "", startedAt: Date().addingTimeInterval(-(19 * 60 + 12)), phase: .playing)
        state.player.liveNow = RadioNow(state: .ok, rawTitle: "Talk Talk - Life's What You Make It", artist: "Talk Talk", title: "Life's What You Make It")
        state.player.liveSongSince = Date().addingTimeInterval(-18)
        try render("now-playing-live-listening", width: 1180, height: 720, CupertinoNowPlaying(state: state)) { _ in }
        state.player.liveNow = RadioNow(state: .ok, rawTitle: "Talk Talk - Life's What You Make It", artist: "Talk Talk", title: "Life's What You Make It", playID: 9)
        try render("now-playing-live-ready", width: 1180, height: 720, CupertinoNowPlaying(state: state)) { _ in }
        state.player.liveNow = RadioNow(state: .noMetadata)
        try render("now-playing-live-nometa", width: 1180, height: 720, CupertinoNowPlaying(state: state)) { _ in }
        state.player.liveNow = nil
        state.player.live?.phase = .reconnecting
        try render("now-playing-live-reconnecting", width: 1180, height: 720, CupertinoNowPlaying(state: state)) { _ in }
    }

    /// The Radio page's sentences when there is nothing to list (S2-1 item 9), and the Edit Tags sheet (item 8).
    @Test func rendersStationsStatesAndTagSheet() throws {
        let empty = AppState(themeID: .cupertino, screen: .stations)
        empty.stations.showForPreview(stations: [])
        try render("stations-empty", width: 900, height: 300, CupertinoStations(state: empty)) { _ in }
        let sheetStation = RadioStation(id: "1", name: "Radio Swiss Jazz", proxied: true, playableURL: "https://example.invalid/1", favourite: true, tags: ["Jazz", "Late night", "Swiss"])
        try render("stations-tags-sheet", width: 400, height: 260, StationTagsSheet(station: sheetStation) { _ in }) { _ in }
    }
}
