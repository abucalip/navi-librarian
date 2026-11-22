import AppKit
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

/// D5.3 (`docs/plans/MACOS_DESIGN_DETAILS.md`): the Downloads list card fills the content width up to a sensible max width,
/// and the "Clear … imported" button aligns with the card's trailing edge rather than floating over empty space.
@MainActor
@Suite(.serialized)
struct D53DownloadsCardWidthTests {
    @Test func maxListWidthIsSensible() {
        #expect(CupertinoDownloads.maxListWidth >= 900)
        #expect(CupertinoDownloads.maxListWidth <= 1200)
    }

    @Test(arguments: AppearanceMode.allCases)
    func cardFillsContentWidthAndClearButtonAligns(_ mode: AppearanceMode) throws {
        // Narrower than maxListWidth: card fills the full content width (width - 2 * CU.Space.xl).
        let narrowWidth: CGFloat = 960
        let narrow = try measureLayout(width: narrowWidth, mode: mode)
        let expectedNarrowWidth = narrowWidth - 2 * CU.Space.xl
        #expect(abs(narrow.cardLeading - CU.Space.xl) <= 2.0,
                "narrow card leading \(narrow.cardLeading) vs \(CU.Space.xl) (\(mode))")
        #expect(abs(narrow.cardWidth - expectedNarrowWidth) <= 2.0,
                "narrow card width \(narrow.cardWidth) vs content width \(expectedNarrowWidth) (\(mode))")
        #expect(abs(narrow.clearButtonTrailing - narrow.cardTrailing) <= 2.0,
                "narrow clear trailing \(narrow.clearButtonTrailing) vs card trailing \(narrow.cardTrailing) (\(mode))")

        // Wider than maxListWidth: card caps at maxListWidth and Clear button stays aligned to the card's trailing edge.
        let wideWidth: CGFloat = 1400
        let wide = try measureLayout(width: wideWidth, mode: mode)
        #expect(abs(wide.cardLeading - CU.Space.xl) <= 2.0,
                "wide card leading \(wide.cardLeading) vs \(CU.Space.xl) (\(mode))")
        #expect(abs(wide.cardWidth - CupertinoDownloads.maxListWidth) <= 2.0,
                "wide card width \(wide.cardWidth) vs maxListWidth \(CupertinoDownloads.maxListWidth) (\(mode))")
        #expect(abs(wide.clearButtonTrailing - wide.cardTrailing) <= 2.0,
                "wide clear trailing \(wide.clearButtonTrailing) vs card trailing \(wide.cardTrailing) (\(mode))")
    }

    private struct MeasuredLayout {
        let cardLeading: CGFloat
        let cardTrailing: CGFloat
        let clearButtonTrailing: CGFloat
        var cardWidth: CGFloat { cardTrailing - cardLeading }
    }

    private func measureLayout(width: CGFloat, mode: AppearanceMode) throws -> MeasuredLayout {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer { CUPalette.current = saved }

        let state = AppState(themeID: .cupertino, screen: .downloads)
        state.acquisition.showJobs(AcquisitionModelTests.sampleJobs)

        let size = NSSize(width: width, height: 640)
        let host = NSHostingView(
            rootView: CupertinoDownloads(state: state)
                .frame(width: size.width, height: size.height)
                .background(CU.content)
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

        let bg = rgb(2, 2)

        // Probe down x = 500 pt (between header title and segmented control) to find the top edge of CUPanel.
        let probeX = Int(500 * scale)
        let cardTopPx = try #require((Int(60 * scale)..<rep.pixelsHigh).first { y in
            dist(rgb(probeX, y), bg) > 0.02
        })

        // Sample below the panel's rounded top corners so we measure the straight vertical edges of CUPanel.
        let cardSampleY = cardTopPx + Int(28 * scale)
        let cardXs = (0..<rep.pixelsWide).filter { x in dist(rgb(x, cardSampleY), bg) > 0.02 }
        let cardLeadingPx = try #require(cardXs.first)
        let cardTrailingPx = try #require(cardXs.last)

        // The "Clear 1 imported" capsule sits in the band between the header (<= 50 pt) and the card top.
        let clearYs = Int(52 * scale)..<max(Int(53 * scale), cardTopPx - Int(4 * scale))
        let clearXs = (Int(400 * scale)..<rep.pixelsWide).filter { x in
            clearYs.contains { y in dist(rgb(x, y), bg) > 0.02 }
        }
        let clearTrailingPx = try #require(clearXs.last)

        return MeasuredLayout(
            cardLeading: CGFloat(cardLeadingPx) / scale,
            cardTrailing: CGFloat(cardTrailingPx + 1) / scale,
            clearButtonTrailing: CGFloat(clearTrailingPx + 1) / scale
        )
    }
}
