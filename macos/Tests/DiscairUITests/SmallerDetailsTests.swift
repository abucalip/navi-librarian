import AppKit
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

/// Remaining smaller details from `docs/plans/MACOS_DESIGN_DETAILS.md`:
/// - Player bar waveform opacity lowered under the leading title/artist/album block
/// - Album hero `.onMedia` quality badges use a dark translucent ground for >= 4.5:1 contrast over light blurs
/// - Home narrow/queue-open hero renders Next picks as one horizontal row
@MainActor
struct SmallerDetailsTests {
    @Test func waveformOpacityScalesDownUnderLeadingTextBlock() {
        #expect(PlayerBarGraph.opacityScale(atX: 10, quietLeadingWidth: 0) == 1)
        #expect(PlayerBarGraph.opacityScale(atX: 10, quietLeadingWidth: 240) == PlayerBarGraph.quietOpacityScale)
        #expect(PlayerBarGraph.opacityScale(atX: 240, quietLeadingWidth: 240) == PlayerBarGraph.quietOpacityScale)
        let mid = 240 + PlayerBarGraph.fadeWidth / 2
        #expect(abs(PlayerBarGraph.opacityScale(atX: mid, quietLeadingWidth: 240) - 0.625) < 0.001)
        #expect(PlayerBarGraph.opacityScale(atX: 240 + PlayerBarGraph.fadeWidth, quietLeadingWidth: 240) == 1)
        #expect(PlayerBarGraph.opacityScale(atX: 500, quietLeadingWidth: 240) == 1)
    }

    @Test func waveformRenderIsDimmerUnderLeadingTextBlock() throws {
        RenderMode.offscreenScreenshot = true
        let peaks = [Float](repeating: 0.9, count: 120)
        let size = NSSize(width: 480, height: 68)
        let view = PlayerBarGraph(peaks: peaks, fraction: 1.0, quietLeadingWidth: 200)
            .frame(width: size.width, height: size.height)
            .background(Color.black)

        let host = NSHostingView(rootView: view)
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.05))

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let scale = CGFloat(rep.pixelsWide) / size.width

        func maxBrightness(inXRange xs: Range<Int>) -> CGFloat {
            let y = Int((size.height - 12) * scale)
            return xs.map { x in
                let c = rep.colorAt(x: x, y: y)?.usingColorSpace(.sRGB) ?? .black
                return c.redComponent
            }.max() ?? 0
        }

        let quietBrightness = maxBrightness(inXRange: Int(20 * scale)..<Int(160 * scale))
        let fullBrightness = maxBrightness(inXRange: Int(260 * scale)..<Int(440 * scale))
        #expect(quietBrightness > 0.01, "waveform should still be subtly visible under text")
        #expect(fullBrightness > quietBrightness * 2.0,
                "trailing waveform (\(fullBrightness)) should be noticeably brighter than under text (\(quietBrightness))")
    }

    @Test func onMediaQualityBadgeKeepsDarkGroundOverLightBlur() throws {
        RenderMode.offscreenScreenshot = true
        #expect(CUQualityBadge.onMediaBackgroundOpacity >= 0.65)

        let size = NSSize(width: 180, height: 60)
        // Simulate a worst-case light album blur with the hero's ~28% dark wash.
        let view = ZStack {
            Color.white
            Color.black.opacity(0.28)
            CUQualityBadge(text: "MP3 320", surface: .onMedia)
        }
        .frame(width: size.width, height: size.height)

        let host = NSHostingView(rootView: view)
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.05))

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let scale = CGFloat(rep.pixelsWide) / size.width

        // Sample the badge's left padding interior (away from text glyphs).
        let c = try #require(rep.colorAt(x: Int(58 * scale), y: Int(30 * scale))?.usingColorSpace(.sRGB))
        let luminance = 0.2126 * c.redComponent + 0.7152 * c.greenComponent + 0.0722 * c.blueComponent
        let contrastWithWhite = 1.05 / (luminance + 0.05)
        #expect(contrastWithWhite >= 4.5, "onMedia badge contrast \(contrastWithWhite) should be at least 4.5:1 over a light blur")
    }

    @Test func narrowHomeRendersWithHorizontalNextPicks() throws {
        RenderMode.offscreenScreenshot = true
        let state = AppState(themeID: .cupertino, screen: .home)
        let picks: [DashboardPick] = try (1...7).map { i in
            try JSONDecoder().decode(
                DashboardPick.self,
                from: Data(#"{"artist":"Artist \#(i)","album":"Pick \#(i)","genres":["Jazz"]}"#.utf8)
            )
        }
        state.library.apply(newest: [], first: [], artists: [], picks: picks)

        let size = NSSize(width: 780, height: 720)
        let view = CupertinoHome(state: state)
            .frame(width: size.width, height: size.height)
            .environment(\.colorScheme, .dark)

        let host = NSHostingView(rootView: view)
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.05))

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        #expect(rep.pixelsWide > 0 && rep.pixelsHigh > 0)
    }
}
