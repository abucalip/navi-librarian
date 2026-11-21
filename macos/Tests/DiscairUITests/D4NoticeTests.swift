import AppKit
import SwiftUI
import Testing
@testable import DiscairUI

/// D4.3 (`docs/plans/MACOS_DESIGN_DETAILS.md`): the phone handoff banner ("Playing on your phone: …") and other one-line notices
/// centre-align their icon, text line and trailing capsule button on the banner's vertical centre.
@MainActor
struct D4NoticeTests {
    @Test func noticeRowUsesCentreAlignment() {
        #expect(CUNotice.rowAlignment == .center)
    }

    @Test(arguments: [false, true])
    func phoneBannerCentresIconTextAndButton(night: Bool) throws {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = night ? .night : .day
        defer { CUPalette.current = saved }

        let size = NSSize(width: 980, height: 72)
        let handoff = HomeDashboard.Handoff(songID: "s1", title: "Ascension Day", artist: "Talk Talk", positionSeconds: 161, durationSeconds: 360)
        let view = CUNotice(kind: .info, lead: "Playing on your phone:", message: HomeScreen.handoffText(handoff),
                            actionTitle: "Continue on this Mac") {}
            .padding(16)
            .frame(width: size.width, height: size.height)
            .background(CU.content)
            .environment(\.colorScheme, night ? .dark : .light)
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

        let bg = rgb(2, 2)
        let midX = Int(490 * scale)
        let bannerYs = (0..<rep.pixelsHigh).filter { dist(rgb(midX, $0), bg) > 0.03 }
        let bannerTop = try #require(bannerYs.first)
        let bannerBottom = try #require(bannerYs.last)
        let bannerCentre = CGFloat(bannerTop + bannerBottom) / (2 * scale)
        let tint = rgb(midX, bannerTop + Int(3 * scale))

        func verticalCentre(from x0: CGFloat, to x1: CGFloat) throws -> CGFloat {
            let xs = Int(x0 * scale)..<Int(x1 * scale)
            let ys = (bannerTop...bannerBottom).filter { y in xs.contains { x in dist(rgb(x, y), tint) > 0.10 } }
            let first = try #require(ys.first)
            let last = try #require(ys.last)
            return CGFloat(first + last) / (2 * scale)
        }

        let iconCentre = try verticalCentre(from: 30, to: 50)
        let textCentre = try verticalCentre(from: 56, to: 420)
        let buttonCentre = try verticalCentre(from: 810, to: 940)

        #expect(abs(iconCentre - bannerCentre) <= 1.0, "icon centre \(iconCentre) vs banner \(bannerCentre)")
        #expect(abs(textCentre - bannerCentre) <= 1.0, "text centre \(textCentre) vs banner \(bannerCentre)")
        #expect(abs(buttonCentre - bannerCentre) <= 1.0, "button centre \(buttonCentre) vs banner \(bannerCentre)")
    }
}
