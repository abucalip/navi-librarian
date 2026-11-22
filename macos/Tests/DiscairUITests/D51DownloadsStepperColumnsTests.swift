import AppKit
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

/// D5.1 regression tests (`docs/plans/MACOS_DESIGN_DETAILS.md`):
/// Downloads stepper has a fixed width and fixed column widths, and the trailing action stack has a fixed width,
/// so the four stage dots align vertically across rows regardless of which action buttons a row shows.
@MainActor
struct D51DownloadsStepperColumnsTests {
    @Test
    func fixedStepperAndActionDimensionsFitMinimumCard() {
        #expect(CupertinoDownloads.stepperColumnWidth == 70)
        #expect(CupertinoDownloads.stepperWidth == CupertinoDownloads.stepperColumnWidth * CGFloat(CUChartMath.stageNames.count))
        #expect(CupertinoDownloads.actionWidth == 128)

        // Panel horizontal padding (16 * 2) + 48 pt cover + 2 * 16 pt HStack spacing = 112 pt overhead.
        let minCardWidth: CGFloat = 520
        let fixedOverhead: CGFloat = CU.Space.m * 2 + 48 + CU.Space.m * 2
        #expect(fixedOverhead + CupertinoDownloads.stepperWidth + CupertinoDownloads.actionWidth <= minCardWidth)
    }

    @Test(arguments: [0, 1, 2, 3, 4])
    func stageTrackerKeepsExactFixedWidthAcrossSteps(_ step: Int) {
        let tracker = CUStageTracker(
            step: step,
            progress: step == 1 ? 0.5 : nil,
            failed: step == 1,
            failureReason: nil,
            showsNames: true,
            width: CupertinoDownloads.stepperWidth,
            columnWidth: CupertinoDownloads.stepperColumnWidth
        )
        let host = NSHostingView(rootView: tracker)
        let fitting = host.fittingSize
        #expect(abs(fitting.width - CupertinoDownloads.stepperWidth) < 0.5)
    }

    @Test
    func downloadsRendersWithFixedColumnsAcrossMixedActionRows() throws {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = .day
        defer { CUPalette.current = saved }

        let state = AppState(themeID: .cupertino, screen: .downloads)
        state.acquisition.showJobs(AcquisitionModelTests.sampleJobs)

        let size = NSSize(width: 1100, height: 640)
        let host = NSHostingView(
            rootView: CupertinoDownloads(state: state)
                .frame(width: size.width, height: size.height)
                .background(CU.content)
                .environment(\.colorScheme, .light)
        )
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.5))

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        var colours = Set<Int>()
        for ix in 0..<48 {
            for iy in 0..<48 {
                guard let c = rep.colorAt(x: (rep.pixelsWide - 1) * ix / 47, y: (rep.pixelsHigh - 1) * iy / 47)?.usingColorSpace(.sRGB) else { continue }
                colours.insert(Int(c.redComponent * 15) << 8 | Int(c.greenComponent * 15) << 4 | Int(c.blueComponent * 15))
            }
        }
        #expect(colours.count >= 4, "Downloads render looks blank (\(colours.count) distinct colours)")
    }
}
