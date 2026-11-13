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
}
