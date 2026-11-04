import AppKit
import DiscairCore
import SwiftUI
import Testing
@testable import DiscairUI

/// Renders each theme screen to PNG. Output goes to `DISCAIR_SCREENSHOT_DIR` (CI uploads it) or a temp folder.
/// Baseline comparison is added once the owner approves the look on the Mac (contract M4 gate).
@MainActor
struct ScreenshotTests {
    @Test(arguments: ThemeID.allCases, [Screen.home, Screen.album, Screen.nowPlaying, Screen.queue, Screen.library, Screen.albums, Screen.artist, Screen.settings, Screen.downloads, Screen.discover])
    func rendersWindow(theme: ThemeID, screen: Screen) throws {
        RenderMode.offscreenScreenshot = true
        // Settings needs a session; a throwaway one with a sample profile and an in-memory keychain.
        let session = SessionModel(store: ProfileStore(fileURL: FileManager.default.temporaryDirectory.appending(path: "discair-shot-\(UUID().uuidString)/profiles.json")), secrets: InMemorySecretStore())
        try session.addProfile(name: "Home", librarianURL: "http://192.168.1.87:8686", navidromeURL: "http://192.168.1.87:4533")
        try session.saveLogin(.navidrome, username: "owner", password: "not-shown")
        let state = AppState(themeID: theme, screen: screen, session: screen == .settings ? session : nil)
        let size = NSSize(width: 1280, height: 800)
        let host = NSHostingView(rootView: RootView(state: state).frame(width: size.width, height: size.height))
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        if screen == .downloads { state.acquisition.showJobs(AcquisitionModelTests.sampleJobs) }
        if screen == .discover { state.discovery.show(.personal, Fixtures.albums([7, 8, 9])) }
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.5))
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let png = try #require(rep.representation(using: .png, properties: [:]))
        // A blank render is one flat colour; real UI has many. Sample a grid and count distinct quantised colours, which
        // does not depend on the render scale (CI and a Retina Mac produce different image sizes).
        var colours = Set<Int>()
        for ix in 0..<48 {
            for iy in 0..<30 {
                let x = (rep.pixelsWide - 1) * ix / 47, y = (rep.pixelsHigh - 1) * iy / 29
                guard let c = rep.colorAt(x: x, y: y)?.usingColorSpace(.sRGB) else { continue }
                colours.insert(Int(c.redComponent * 15) << 8 | Int(c.greenComponent * 15) << 4 | Int(c.blueComponent * 15))
            }
        }
        #expect(colours.count >= 8, "render looks blank (\(colours.count) distinct colours)")
        let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try png.write(to: dir.appendingPathComponent("\(theme.rawValue)-\(screen.rawValue).png"))
    }

    @Test func everyThemeIDResolves() {
        for id in ThemeID.allCases { #expect(ThemeRegistry.theme(id).id == id) }
    }
}
