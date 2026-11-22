import AppKit
import SwiftUI
import Testing
@testable import DiscairUI

/// D4.7 & D4.8 (`docs/plans/MACOS_DESIGN_DETAILS.md`):
/// - D4.7: Discover sub-item highlights share the top-level leading edge; only the icon and label indent.
/// - D4.8: The toolbar Search button places "⌘K" at its trailing edge in `CU.textTertiary`, separate from "Search".
@MainActor
struct D4SidebarHighlightSearchHintTests {
    @Test func subItemIndentMatchesSpaceM() {
        #expect(CupertinoSidebar.subItemIndent == CU.Space.m)
    }

    @Test(arguments: AppearanceMode.allCases)
    func sidebarSubItemHighlightSharesLeadingEdgeWithTopLevel(_ mode: AppearanceMode) throws {
        let homeRep = try renderSidebar(mode: mode, screen: .home)
        let connectionsRep = try renderSidebar(mode: mode, screen: .connections)

        let homeHighlight = try measureHighlight(in: homeRep, width: 240, mode: mode)
        let subHighlight = try measureHighlight(in: connectionsRep, width: 240, mode: mode)

        #expect(
            abs(homeHighlight.pillLeadingX - subHighlight.pillLeadingX) <= 1.0,
            "sub-item pill leading x=\(subHighlight.pillLeadingX) vs top-level x=\(homeHighlight.pillLeadingX) (\(mode))"
        )
        let iconIndent = subHighlight.iconLeadingX - homeHighlight.iconLeadingX
        #expect(
            abs(iconIndent - CupertinoSidebar.subItemIndent) <= 2.0,
            "sub-item icon indent=\(iconIndent) expected ~\(CupertinoSidebar.subItemIndent) (\(mode))"
        )
    }

    @Test(arguments: AppearanceMode.allCases)
    func searchFieldPlacesShortcutHintAtTrailingEdgeInTertiaryColour(_ mode: AppearanceMode) throws {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer { CUPalette.current = saved }

        let state = AppState(themeID: .cupertino, screen: .home)
        let size = NSSize(width: 420, height: 64)
        let host = NSHostingView(
            rootView: CupertinoToolbar(state: state)
                .padding(.horizontal, 12)
                .frame(width: size.width, height: size.height)
                .background(CU.content)
                .environment(\.colorScheme, mode == .night ? .dark : .light)
        )
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.15))

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let scale = CGFloat(rep.pixelsWide) / size.width

        // Search pill is 210 pt wide, 48 pt left of trailing edge (40 px Queue circle + 8 pt spacing + 12 pt padding = 60 pt).
        let pillTrailingPt: CGFloat = size.width - 12 - 40 - CU.Space.s
        let pillLeadingPt: CGFloat = pillTrailingPt - 210
        let yTop = Int(20 * scale)
        let yBottom = Int(44 * scale)

        let bg = rgb(rep, x: Int((pillLeadingPt + 6) * scale), y: Int(32 * scale))
        let secondaryTarget = rgb(CURGB: CU.textSecondaryRGB)
        let tertiaryTarget = rgb(CURGB: CU.textTertiaryRGB)

        // Scan x across the interior of the search pill (after 16 pt leading padding to before 16 pt trailing padding).
        let scanStart = Int((pillLeadingPt + 12) * scale)
        let scanEnd = Int((pillTrailingPt - 12) * scale)
        var activeColumns: [Int] = []
        for x in scanStart...scanEnd {
            let hasInk = (yTop...yBottom).contains { y in dist(rgb(rep, x: x, y: y), bg) > 0.04 }
            if hasInk { activeColumns.append(x) }
        }

        // Expect a clear gap between "Search" on the left and "⌘K" on the right.
        var maxGapPx = 0
        var gapStart = 0
        var gapEnd = 0
        for i in 1..<activeColumns.count {
            let gap = activeColumns[i] - activeColumns[i - 1]
            if gap > maxGapPx {
                maxGapPx = gap
                gapStart = activeColumns[i - 1]
                gapEnd = activeColumns[i]
            }
        }
        let maxGapPt = CGFloat(maxGapPx) / scale
        #expect(maxGapPt >= 60.0, "expected trailing gap between Search and ⌘K, got \(maxGapPt) pt (\(mode))")

        // Verify "Search" (left of gap) is closer to textSecondary and "⌘K" (right of gap) is closer to textTertiary.
        let searchColour = darkestInk(in: rep, xRange: scanStart...gapStart, yRange: yTop...yBottom, bg: bg)
        let hintColour = darkestInk(in: rep, xRange: gapEnd...scanEnd, yRange: yTop...yBottom, bg: bg)
        #expect(
            dist(hintColour, tertiaryTarget) < dist(hintColour, secondaryTarget),
            "⌘K hint colour should match textTertiary rather than textSecondary (\(mode))"
        )
        #expect(
            dist(searchColour, secondaryTarget) < dist(searchColour, tertiaryTarget),
            "Search text colour should match textSecondary rather than textTertiary (\(mode))"
        )
    }

    private func renderSidebar(mode: AppearanceMode, screen: Screen) throws -> NSBitmapImageRep {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer { CUPalette.current = saved }

        let state = AppState(themeID: .cupertino, screen: screen)
        state.discoverOpen = true

        let size = NSSize(width: 240, height: 640)
        let host = NSHostingView(
            rootView: CupertinoSidebar(state: state)
                .frame(width: size.width, height: size.height)
                .background(CU.content)
                .environment(\.colorScheme, mode == .night ? .dark : .light)
        )
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.15))

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        return rep
    }

    private func measureHighlight(in rep: NSBitmapImageRep, width: CGFloat, mode: AppearanceMode) throws -> (pillLeadingX: CGFloat, iconLeadingX: CGFloat) {
        let scale = CGFloat(rep.pixelsWide) / width
        let saved = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer { CUPalette.current = saved }

        let targetTint = rgb(CURGB: CU.accentTintRGB)
        let targetAccent = rgb(CURGB: CU.accentRGB)
        let bg = rgb(rep, x: Int(30 * scale), y: Int(580 * scale))

        // Find the y-band of the selected row by looking for the accent-tinted pill around x = 180 pt.
        let probeX = Int(180 * scale)
        let pillYs = (0..<rep.pixelsHigh).filter { y in
            let c = rgb(rep, x: probeX, y: y)
            return dist(c, targetTint) < dist(c, bg) && dist(c, bg) > 0.02
        }
        let pillTop = try #require(pillYs.first)
        let pillBottom = try #require(pillYs.last)
        let midY = (pillTop + pillBottom) / 2

        // Scan horizontally from x = 12 pt (inside sidebar inset) to 120 pt to find the pill's leading edge.
        let xStart = Int(12 * scale)
        let xEnd = Int(120 * scale)
        let pillLeadingPx = try #require((xStart...xEnd).first { x in
            dist(rgb(rep, x: x, y: midY), bg) > 0.02
        })

        // Inside the pill, find the first column containing the accent-coloured icon.
        let iconYRange = (pillTop + Int(4 * scale))...(pillBottom - Int(4 * scale))
        let iconLeadingPx = try #require((pillLeadingPx...xEnd).first { x in
            iconYRange.contains { y in dist(rgb(rep, x: x, y: y), targetAccent) < 0.25 }
        })

        return (CGFloat(pillLeadingPx) / scale, CGFloat(iconLeadingPx) / scale)
    }

    private func rgb(_ rep: NSBitmapImageRep, x: Int, y: Int) -> (CGFloat, CGFloat, CGFloat) {
        let c = rep.colorAt(x: x, y: y)?.usingColorSpace(.sRGB) ?? .black
        return (c.redComponent, c.greenComponent, c.blueComponent)
    }

    private func rgb(CURGB: CURGB) -> (CGFloat, CGFloat, CGFloat) {
        let c = NSColor(CURGB.color).usingColorSpace(.sRGB) ?? .black
        return (c.redComponent, c.greenComponent, c.blueComponent)
    }

    private func dist(_ a: (CGFloat, CGFloat, CGFloat), _ b: (CGFloat, CGFloat, CGFloat)) -> CGFloat {
        abs(a.0 - b.0) + abs(a.1 - b.1) + abs(a.2 - b.2)
    }

    private func darkestInk(in rep: NSBitmapImageRep, xRange: ClosedRange<Int>, yRange: ClosedRange<Int>, bg: (CGFloat, CGFloat, CGFloat)) -> (CGFloat, CGFloat, CGFloat) {
        var best = bg
        var bestDist: CGFloat = 0
        for x in xRange {
            for y in yRange {
                let c = rgb(rep, x: x, y: y)
                let d = dist(c, bg)
                if d > bestDist {
                    bestDist = d
                    best = c
                }
            }
        }
        return best
    }
}
