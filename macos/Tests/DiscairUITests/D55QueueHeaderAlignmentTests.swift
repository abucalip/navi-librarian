import AppKit
import SwiftUI
import Testing
@testable import DiscairUI

/// D5.5 (`docs/plans/MACOS_DESIGN_DETAILS.md`):
/// The queue inspector's header (Queue / Saved segmented control and count) sits on the toolbar's
/// centre line instead of leaving an empty ~70 pt band above it.
@MainActor
@Suite(.serialized)
struct D55QueueHeaderAlignmentTests {
    @Test func queueHeaderTopMatchesToolbarTop() {
        #expect(CupertinoQueueInspector.headerTop == CU.Shell.toolbarTop)
        #expect(CupertinoToolbar.height == 44)
    }

    @Test(arguments: AppearanceMode.allCases)
    func queueSegmentedControlAlignsWithToolbarCentreLine(_ mode: AppearanceMode) throws {
        let savedScreenshotMode = RenderMode.offscreenScreenshot
        RenderMode.offscreenScreenshot = true
        let savedPalette = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer {
            RenderMode.offscreenScreenshot = savedScreenshotMode
            CUPalette.current = savedPalette
        }

        let state = AppState(themeID: .cupertino, screen: .home)
        state.queueOpen = true

        let size = NSSize(width: 1180, height: 640)
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
        RunLoop.current.run(until: Date().addingTimeInterval(0.2))

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let scale = CGFloat(rep.pixelsWide) / size.width

        // Probe the Queue circle button in the toolbar (left of the queue inspector) to find the toolbar's centre line.
        // Toolbar trailing padding when queue is open = CupertinoQueueInspector.width + CU.Space.m; circle is 40 pt wide.
        let queueButtonCenterX = Int((size.width - CupertinoQueueInspector.width - CU.Space.m - 20) * scale)
        let queueButtonXRange = (queueButtonCenterX - Int(14 * scale))...(queueButtonCenterX + Int(14 * scale))
        let topBand = Int(6 * scale)..<Int(62 * scale)
        let toolbarBg = rgb(rep, x: queueButtonCenterX, y: Int(4 * scale))
        let toolbarYs = topBand.filter { y in
            queueButtonXRange.contains { x in
                dist(rgb(rep, x: x, y: y), toolbarBg) > 0.05
            }
        }
        let toolbarIconTopPt = CGFloat(try #require(toolbarYs.first)) / scale
        let toolbarIconBottomPt = CGFloat(try #require(toolbarYs.last)) / scale
        let toolbarCentrePt = (toolbarIconTopPt + toolbarIconBottomPt) / 2

        // Probe the "Queue" segmented control inside the panel header (panel starts at width - 380, plus 16 pt horizontal padding).
        let panelLeadingPt = size.width - CupertinoQueueInspector.width
        let segmentXRange = Int((panelLeadingPt + CU.Space.m + 4) * scale)...Int((panelLeadingPt + CU.Space.m + 64) * scale)
        let panelBg = rgb(rep, x: Int((panelLeadingPt + 8) * scale), y: Int(4 * scale))
        let segmentBand = Int(10 * scale)..<Int(58 * scale)
        let segmentYs = segmentBand.filter { y in
            segmentXRange.contains { x in
                dist(rgb(rep, x: x, y: y), panelBg) > 0.06
            }
        }
        let segmentTopPt = CGFloat(try #require(segmentYs.first)) / scale
        let segmentBottomPt = CGFloat(try #require(segmentYs.last)) / scale
        let segmentCentrePt = (segmentTopPt + segmentBottomPt) / 2

        let expectedCentrePt = CU.Shell.toolbarTop + CupertinoToolbar.height / 2
        #expect(
            abs(toolbarCentrePt - expectedCentrePt) <= 2.5,
            "toolbar icon centre=\(toolbarCentrePt) (\(toolbarIconTopPt)...\(toolbarIconBottomPt)) expected ~\(expectedCentrePt) (\(mode))"
        )
        #expect(
            abs(segmentCentrePt - toolbarCentrePt) <= 2.5,
            "queue segmented centre=\(segmentCentrePt) (\(segmentTopPt)...\(segmentBottomPt)) vs toolbar centre=\(toolbarCentrePt) (\(toolbarIconTopPt)...\(toolbarIconBottomPt)) (\(mode))"
        )
        #expect(
            segmentTopPt < 30,
            "queue segmented top=\(segmentTopPt) should sit in the toolbar band, not ~70 pt down (\(mode))"
        )
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
}
