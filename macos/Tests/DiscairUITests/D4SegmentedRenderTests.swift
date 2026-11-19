import AppKit
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

/// D4.1 acceptance renders (`docs/plans/MACOS_DESIGN_DETAILS.md`): the five pages that carried four different segmented-control
/// looks, in Day and Night. Output goes to `DISCAIR_SCREENSHOT_DIR` (or a temp folder) as `d4-<page>-<mode>.png`.
@MainActor
struct D4SegmentedRenderTests {
    private func render<V: View>(_ name: String, _ mode: AppearanceMode, page: () -> V) throws {
        RenderMode.offscreenScreenshot = true
        // `CU` reads the palette global, not the colour scheme; put Day or Night back after the render.
        let saved = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer { CUPalette.current = saved }
        let size = NSSize(width: 1100, height: 640)
        let host = NSHostingView(rootView: page().frame(width: size.width, height: size.height).background(CU.content)
            .environment(\.colorScheme, mode == .night ? .dark : .light))
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(1.0))
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let png = try #require(rep.representation(using: .png, properties: [:]))
        var colours = Set<Int>()
        for ix in 0..<48 { for iy in 0..<48 {
            guard let c = rep.colorAt(x: (rep.pixelsWide - 1) * ix / 47, y: (rep.pixelsHigh - 1) * iy / 47)?.usingColorSpace(.sRGB) else { continue }
            colours.insert(Int(c.redComponent * 15) << 8 | Int(c.greenComponent * 15) << 4 | Int(c.blueComponent * 15))
        } }
        #expect(colours.count >= 4, "render looks blank (\(colours.count) distinct colours)")
        let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try png.write(to: dir.appendingPathComponent("d4-\(name)-\(mode.rawValue.lowercased()).png"))
    }

    @Test(arguments: AppearanceMode.allCases)
    func rendersTimeline(_ mode: AppearanceMode) throws {
        let state = AppState(themeID: .cupertino, screen: .timeline)
        state.timeline.preview(person: TimelinePreview.person, items: TimelinePreview.items, undated: 1)
        state.timeline.selectedID = "album:g2"
        try render("timeline", mode) { TimelineView(state: state, style: .cupertino) }
    }

    @Test(arguments: AppearanceMode.allCases)
    func rendersAtlas(_ mode: AppearanceMode) throws {
        let state = AppState(themeID: .cupertino, screen: .atlas)
        state.atlas.preview(places: [AtlasPreview.paris, AtlasPreview.addis])
        state.atlas.selectedID = "p1"
        try render("atlas", mode) { AtlasView(state: state, style: .cupertino) }
    }

    @Test(arguments: AppearanceMode.allCases)
    func rendersConnections(_ mode: AppearanceMode) throws {
        let state = AppState(themeID: .cupertino, screen: .connections)
        state.graph.preview(centre: GraphPreview.centre, nodes: GraphPreview.nodes)
        state.graph.selectedID = "b1"
        try render("connections", mode) { CupertinoConnections(state: state) }
    }

    @Test(arguments: AppearanceMode.allCases)
    func rendersRadio(_ mode: AppearanceMode) throws {
        let state = AppState(themeID: .cupertino, screen: .stations)
        func station(_ id: String, _ name: String, _ tag: String) -> RadioStation {
            RadioStation(id: id, name: name, proxied: true, playableURL: "https://example.invalid/\(id)", tags: [tag])
        }
        state.stations.showForPreview(stations: [station("1", "FIP", "Eclectic"), station("2", "KEXP", "Indie"),
                                                 station("3", "NTS 1", "Electronic")])
        try render("radio", mode) { CupertinoStations(state: state, selected: "1") }
    }

    @Test(arguments: AppearanceMode.allCases)
    func rendersDownloads(_ mode: AppearanceMode) throws {
        let state = AppState(themeID: .cupertino, screen: .downloads)
        state.acquisition.showJobs(AcquisitionModelTests.sampleJobs)
        try render("downloads", mode) { CupertinoDownloads(state: state) }
    }
}
