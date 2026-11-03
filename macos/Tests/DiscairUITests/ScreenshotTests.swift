import AppKit
import SwiftUI
import Testing
@testable import DiscairUI

/// Renders each theme screen to PNG. Output goes to `DISCAIR_SCREENSHOT_DIR` (CI uploads it) or a temp folder.
/// Baseline comparison is added once the owner approves the look on the Mac (contract M4 gate).
@MainActor
struct ScreenshotTests {
    @Test(arguments: [ThemeID.cupertino], [Screen.home, Screen.album, Screen.nowPlaying])
    func rendersWindow(theme: ThemeID, screen: Screen) throws {
        RenderMode.offscreenScreenshot = true
        let state = AppState(themeID: theme, screen: screen)
        let size = NSSize(width: 1280, height: 800)
        let host = NSHostingView(rootView: RootView(state: state).frame(width: size.width, height: size.height))
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.5))
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let png = try #require(rep.representation(using: .png, properties: [:]))
        // A blank render compresses to almost nothing; real UI is far larger.
        #expect(png.count > 400_000, "render looks blank (\(png.count) bytes)")
        let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try png.write(to: dir.appendingPathComponent("\(theme.rawValue)-\(screen.rawValue).png"))
    }

    @Test func everyThemeIDResolves() {
        for id in ThemeID.allCases { #expect(ThemeRegistry.theme(id).id == id) }
    }
}
