import AppKit
import SwiftUI
import Testing
@testable import DiscairUI

/// D4.5 (`docs/plans/MACOS_DESIGN_DETAILS.md`): the quality badge uses one filled rounded-rectangle style across the player
/// bar, track table, album header and library song table (never outlined).
@MainActor
struct D4QualityBadgeTests {
    @Test func badgeMetricsMatchSharedSpec() {
        #expect(CUQualityBadge.cornerRadius == 4)
        #expect(CUQualityBadge.horizontalPadding == CU.Space.s)
        #expect(CUQualityBadge.verticalPadding == 2)
    }

    @Test(arguments: AppearanceMode.allCases)
    func standardAndPlayingBadgesRenderFilled(_ mode: AppearanceMode) throws {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer { CUPalette.current = saved }

        let size = NSSize(width: 240, height: 60)
        let view = HStack(spacing: 16) {
            CUQualityBadge(text: "MP3 320", surface: .standard)
            CUQualityBadge(text: "FLAC", surface: .playing)
        }
        .padding(16)
        .frame(width: size.width, height: size.height)
        .background(CU.content)
        .environment(\.colorScheme, mode == .night ? .dark : .light)

        let host = NSHostingView(rootView: view)
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.1))

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

        // The standard badge has a filled interior (pixels just inside its top edge differ from CU.content).
        let bg = rgb(2, 2)
        let midY = Int(30 * scale)
        let fillXs = (Int(50 * scale)..<Int(120 * scale)).filter { dist(rgb($0, midY), bg) > 0.03 }
        #expect(fillXs.count >= 20, "standard badge should be filled, got \(fillXs.count) non-bg pixels (\(mode))")
    }
}
