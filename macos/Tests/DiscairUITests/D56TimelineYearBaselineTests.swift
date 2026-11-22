import AppKit
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

/// D5.6 (`docs/plans/MACOS_DESIGN_DETAILS.md`): Timeline year labels align with the card title's first baseline
/// (`.firstTextBaseline`) instead of sitting ~9 pt above the title at the card's unpadded top edge.
@MainActor
struct D56TimelineYearBaselineTests {
    @Test func timelineRowUsesFirstTextBaselineAlignment() {
        #expect(TimelineView.rowAlignment == .firstTextBaseline)
    }

    @Test(arguments: AppearanceMode.allCases)
    func yearLabelAlignsToCardTitleFirstBaseline(_ mode: AppearanceMode) throws {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer { CUPalette.current = saved }

        let size = NSSize(width: 960, height: 480)
        let state = AppState(themeID: .cupertino, screen: .timeline)
        // Uppercase title has no descenders, matching "1961" so each glyph box's bottom edge is its baseline.
        let item = TimelinePreview.make("g1", "album", "MY FAVORITE THINGS", "1961", owned: false)
        state.timeline.preview(person: TimelinePreview.person, items: [item], undated: 0)

        let view = TimelineView(state: state, style: .cupertino)
            .frame(width: size.width, height: size.height)
            .background(CU.content)
            .environment(\.colorScheme, mode == .night ? .dark : .light)
        let host = NSHostingView(rootView: view)
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

        // Year column sits at x = 32..96 pt (horizontalPadding 32 + 64 pt trailing-aligned frame).
        let pageBg = rgb(2, 2)
        let yearXs = Int(32 * scale)..<Int(96 * scale)
        let searchYs = Int(60 * scale)..<Int(200 * scale)
        let yearYs = searchYs.filter { y in yearXs.contains { x in dist(rgb(x, y), pageBg) > 0.12 } }
        let yearTop = try #require(yearYs.first)
        let yearBottom = try #require(yearYs.last)
        let yearBaseline = CGFloat(yearBottom) / scale

        // Card starts at x = 110 pt (32 + 64 + 14) with 10 pt padding; sample card background in the left padding strip.
        let cardBg = rgb(Int(115 * scale), yearTop)
        let titleXs = Int(120 * scale)..<Int(320 * scale)
        let titleBand = max(0, yearTop - Int(4 * scale))...min(rep.pixelsHigh - 1, yearBottom + Int(4 * scale))
        let titleYs = titleBand.filter { y in titleXs.contains { x in dist(rgb(x, y), cardBg) > 0.12 } }
        let titleTop = try #require(titleYs.first)
        let titleBottom = try #require(titleYs.last)
        let titleBaseline = CGFloat(titleBottom) / scale

        // Before D5.6 (.top alignment), "1961" sat ~9 pt above the card title.
        #expect(abs(yearBaseline - titleBaseline) <= 1.5,
                "Year baseline \(yearBaseline) pt vs title baseline \(titleBaseline) pt (top \(CGFloat(yearTop) / scale) vs \(CGFloat(titleTop) / scale)) (\(mode))")
    }
}
