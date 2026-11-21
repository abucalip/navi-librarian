import AppKit
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

/// D4.4 (`docs/plans/MACOS_DESIGN_DETAILS.md`): Timeline and Atlas share `CU.Space.xl` (32 pt) horizontal page padding with
/// Home, Radio, Connections and Downloads so their page titles, search field and map/rail align on the same leading edge.
@MainActor
struct D4PageTitleEdgeTests {
    @Test func timelineAndAtlasUseSharedHorizontalPadding() {
        #expect(TimelineView.horizontalPadding == CU.Space.xl)
        #expect(AtlasView.horizontalPadding == CU.Space.xl)
    }

    @Test(arguments: AppearanceMode.allCases)
    func pageTitlesShareLeadingEdge(_ mode: AppearanceMode) throws {
        let timelineX = try measureTitleLeadingX(mode) {
            let state = AppState(themeID: .cupertino, screen: .timeline)
            state.timeline.preview(person: TimelinePreview.person, items: TimelinePreview.items, undated: 1)
            return TimelineView(state: state, style: .cupertino)
        }
        let atlasX = try measureTitleLeadingX(mode) {
            let state = AppState(themeID: .cupertino, screen: .atlas)
            state.atlas.preview(places: [AtlasPreview.paris, AtlasPreview.addis])
            return AtlasView(state: state, style: .cupertino)
        }
        let connectionsX = try measureTitleLeadingX(mode) {
            let state = AppState(themeID: .cupertino, screen: .connections)
            return CupertinoConnections(state: state)
        }
        let downloadsX = try measureTitleLeadingX(mode) {
            let state = AppState(themeID: .cupertino, screen: .downloads)
            return CupertinoDownloads(state: state)
        }

        // All pages use `CU.Space.xl` (32 pt) horizontal inset; glyph side-bearings differ by < 2 pt across letters.
        let reference = connectionsX
        #expect(abs(timelineX - reference) <= 2.0, "Timeline title x=\(timelineX) vs Connections x=\(reference) (\(mode))")
        #expect(abs(atlasX - reference) <= 2.0, "Atlas title x=\(atlasX) vs Connections x=\(reference) (\(mode))")
        #expect(abs(downloadsX - reference) <= 2.0, "Downloads title x=\(downloadsX) vs Connections x=\(reference) (\(mode))")
        #expect(timelineX >= CU.Space.xl - 1.0 && timelineX <= CU.Space.xl + 4.0, "Timeline title x=\(timelineX) expected near 32 pt")
        #expect(atlasX >= CU.Space.xl - 1.0 && atlasX <= CU.Space.xl + 4.0, "Atlas title x=\(atlasX) expected near 32 pt")
    }

    private func measureTitleLeadingX<V: View>(_ mode: AppearanceMode, page: () -> V) throws -> CGFloat {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer { CUPalette.current = saved }

        let size = NSSize(width: 960, height: 480)
        let host = NSHostingView(rootView: page().frame(width: size.width, height: size.height).background(CU.content)
            .environment(\.colorScheme, mode == .night ? .dark : .light))
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.3))

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let scale = CGFloat(rep.pixelsWide) / size.width

        func rgb(_ x: Int, _ y: Int) -> (CGFloat, CGFloat, CGFloat) {
            let c = rep.colorAt(x: x, y: y)?.usingColorSpace(.sRGB) ?? .black
            return (c.redComponent, c.greenComponent, c.blueComponent)
        }
        func dist(_ a: (CGFloat, CGFloat, CGFloat), _ b: (CGFloat, CGFloat, CGFloat)) -> CGFloat {
            abs(a.0 - b.0) + abs(a.1 - b.1) + abs(a.2 - b.2)
        }

        let bg = rgb(2, 2)
        // Page title sits in the top band (y = 4..44 pt) on the leading side (x = 0..120 pt).
        let yRange = Int(4 * scale)..<Int(44 * scale)
        let xRange = 0..<Int(120 * scale)
        let firstX = try #require(xRange.first { x in yRange.contains { y in dist(rgb(x, y), bg) > 0.12 } })
        return CGFloat(firstX) / scale
    }
}
