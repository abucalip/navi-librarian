import AppKit
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

/// D4.6 (`docs/plans/MACOS_DESIGN_DETAILS.md`): Discover and Playlists share the small bold grey eyebrow header style, and
/// all sidebar groups (Discover, tools, Playlists) share the same `groupGap` (`CU.Space.m`).
@MainActor
struct D4SidebarHeaderTests {
    @Test func sidebarGroupHeaderStyleAndGapAreUnified() {
        #expect(CupertinoSidebar.groupGap == CU.Space.m)
        #expect(CupertinoSidebar.groupHeaderFont == CU.Font.eyebrow.font)
    }

    @Test func compactSidebarLeavesTheRadioArtworkAndItsColumnInPlace() throws {
        RenderMode.offscreenScreenshot = true
        let state = AppState(screen: .stations)
        state.sidebarCompact = true
        #expect(CU.Shell.contentReduction(for: state) == CU.Shell.sidebarWidth - CU.Shell.compactSidebarWidth)
        let station = RadioStation(id: "demo", name: "Demo FM", proxied: true, playableURL: "https://example.invalid/radio")
        state.stations.showForPreview(stations: [station])
        state.stations.recordPlayback(stationID: station.id)
        state.player.live = LiveSession(stationID: station.id, name: station.name, logoPath: "", startedAt: Date(), phase: .playing)
        state.player.liveNow = RadioNow(state: .ok, artist: "Can", title: "Vitamin C")

        let size = NSSize(width: 960, height: 700)
        func render(compact: Bool) throws -> NSBitmapImageRep {
            state.sidebarCompact = compact
            let host = NSHostingView(rootView: CupertinoWindow(state: state).frame(width: size.width, height: size.height))
            host.frame = NSRect(origin: .zero, size: size)
            let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
            window.contentView = host
            window.orderBack(nil)
            defer { window.orderOut(nil) }
            host.layoutSubtreeIfNeeded()
            RunLoop.current.run(until: Date().addingTimeInterval(0.2))
            let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
            host.cacheDisplay(in: host.bounds, to: rep)
            let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
            let png = try #require(rep.representation(using: .png, properties: [:]))
            try png.write(to: dir.appendingPathComponent(compact ? "sidebar-icons.png" : "sidebar-expanded.png"))
            return rep
        }

        let expanded = try render(compact: false)
        let compact = try render(compact: true)
        #expect(CU.Shell.contentReduction(for: state) == 0)
        let scale = CGFloat(expanded.pixelsWide) / size.width
        for x in [35, 115, 205] {
            for y in [510, 580, 665] {
                let px = Int(CGFloat(x) * scale), py = Int(CGFloat(y) * scale)
                let expected = try #require(expanded.colorAt(x: px, y: py))
                #expect(compact.colorAt(x: px, y: py) == expected)
            }
        }
    }

    @Test(arguments: AppearanceMode.allCases)
    func sidebarRendersWithEqualGroupHeaders(_ mode: AppearanceMode) throws {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer { CUPalette.current = saved }

        let state = AppState(themeID: .cupertino, screen: .home)
        state.discoverOpen = true

        let size = NSSize(width: 240, height: 640)
        let host = NSHostingView(rootView: CupertinoSidebar(state: state)
            .frame(width: size.width, height: size.height)
            .background(CU.content)
            .environment(\.colorScheme, mode == .night ? .dark : .light))
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.15))

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        var colours = Set<Int>()
        for ix in 0..<32 { for iy in 0..<32 {
            guard let c = rep.colorAt(x: (rep.pixelsWide - 1) * ix / 31, y: (rep.pixelsHigh - 1) * iy / 31)?.usingColorSpace(.sRGB) else { continue }
            colours.insert(Int(c.redComponent * 15) << 8 | Int(c.greenComponent * 15) << 4 | Int(c.blueComponent * 15))
        } }
        #expect(colours.count >= 4, "sidebar render looks blank (\(colours.count) distinct colours)")
    }
}
