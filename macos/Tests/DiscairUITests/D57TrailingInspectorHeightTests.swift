import AppKit
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

/// D5.7 (`docs/plans/MACOS_DESIGN_DETAILS.md`): Timeline and Atlas trailing inspectors run the full window height
/// beside the toolbar (which stops at the panel edge), use the queue's glass chrome, and align their title on
/// the toolbar's centre line.
@MainActor
struct D57TrailingInspectorHeightTests {
    @Test func trailingPanelWidthMatchesActiveInspector() {
        let timelineState = AppState(themeID: .cupertino, screen: .timeline)
        #expect(CupertinoWindow.trailingPanelWidth(for: timelineState) == TimelineView.inspectorWidth)

        let atlasState = AppState(themeID: .cupertino, screen: .atlas)
        #expect(CupertinoWindow.trailingPanelWidth(for: atlasState) == AtlasView.inspectorWidth)

        let homeState = AppState(themeID: .cupertino, screen: .home)
        #expect(CupertinoWindow.trailingPanelWidth(for: homeState) == 0)

        timelineState.queueOpen = true
        #expect(CupertinoWindow.trailingPanelWidth(for: timelineState) == CupertinoQueueInspector.width)
    }

    @Test func inspectorTopPaddingAlignsTitleWithToolbarCentreLine() {
        #expect(CupertinoToolbar.centreY == CU.Shell.toolbarTop + CupertinoToolbar.height / 2)
        #expect(TimelineInspector.topPadding == CupertinoToolbar.centreY - 11)
        #expect(AtlasInspector.topPadding == CupertinoToolbar.centreY - 11)
    }

    @Test(arguments: AppearanceMode.allCases)
    func timelineAndAtlasInspectorsRunFullHeightWithTitleOnToolbarCentre(_ mode: AppearanceMode) throws {
        let timelineState = AppState(themeID: .cupertino, screen: .timeline)
        timelineState.timeline.preview(person: TimelinePreview.person, items: TimelinePreview.items, undated: 1)
        try assertFullHeightTrailingInspector(state: timelineState, width: TimelineView.inspectorWidth, mode: mode, label: "Timeline")

        let atlasState = AppState(themeID: .cupertino, screen: .atlas)
        atlasState.atlas.showsList = true
        atlasState.atlas.preview(places: [AtlasPreview.paris, AtlasPreview.addis])
        try assertFullHeightTrailingInspector(state: atlasState, width: AtlasView.inspectorWidth, mode: mode, label: "Atlas")
    }

    private func assertFullHeightTrailingInspector(state: AppState, width inspectorWidth: CGFloat, mode: AppearanceMode, label: String) throws {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer { CUPalette.current = saved }

        let size = NSSize(width: 1200, height: 640)
        let host = NSHostingView(
            rootView: CupertinoWindow(state: state)
                .frame(width: size.width, height: size.height)
                .environment(\.colorScheme, mode == .night ? .dark : .light)
        )
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

        // Inspector's leading 1 pt divider sits at x = size.width - inspectorWidth, running from y = 0 down to the player bar.
        let dividerRange = Int((size.width - inspectorWidth - 2) * scale)..<Int((size.width - inspectorWidth + 3) * scale)
        let topBandY = Int(6 * scale)
        let midBandY = Int(240 * scale)
        let topRef = rgb(Int((size.width - inspectorWidth - 12) * scale), topBandY)
        let midRef = rgb(Int((size.width - inspectorWidth - 12) * scale), midBandY)

        let hasTopDivider = dividerRange.contains { x in dist(rgb(x, topBandY), topRef) > 0.03 }
        let hasMidDivider = dividerRange.contains { x in dist(rgb(x, midBandY), midRef) > 0.03 }
        #expect(hasTopDivider, "\(label) inspector divider missing in top band (y=6 pt) in \(mode) mode")
        #expect(hasMidDivider, "\(label) inspector divider missing in mid band (y=240 pt) in \(mode) mode")

        // Inspector title sits inside the inspector (x >= panelLeft + 16) on the toolbar's centre line (~34 pt),
        // not pushed down under the toolbar (~85 pt).
        let panelLeft = size.width - inspectorWidth
        let panelGround = rgb(Int((panelLeft + 6) * scale), Int(8 * scale))
        let titleXRange = Int((panelLeft + 14) * scale)..<Int((panelLeft + 120) * scale)
        let titleYRange = Int(16 * scale)..<Int(52 * scale)
        let titleRows = titleYRange.filter { y in
            titleXRange.contains { x in dist(rgb(x, y), panelGround) > 0.12 }
        }
        let firstTitleY = try #require(titleRows.first, "\(label) inspector title not found in toolbar band in \(mode) mode")
        let lastTitleY = try #require(titleRows.last)
        let measuredCentreY = CGFloat(firstTitleY + lastTitleY) / (2 * scale)
        #expect(
            abs(measuredCentreY - CupertinoToolbar.centreY) <= 6.0,
            "\(label) title centre y=\(measuredCentreY) expected near toolbar centre \(CupertinoToolbar.centreY) (\(mode))"
        )
    }
}
