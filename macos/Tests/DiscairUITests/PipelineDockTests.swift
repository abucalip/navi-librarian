import AppKit
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

@MainActor
struct PipelineDockTests {
    private func jobs(_ json: String) -> [Acquisition] {
        struct P: Decodable { let acquisitions: [Acquisition] }
        return try! JSONDecoder().decode(P.self, from: Data(#"{"acquisitions":[\#(json)]}"#.utf8)).acquisitions
    }
    private func job(_ artist: String, _ album: String, _ status: String, pct: Double? = nil, at: Double = 1) -> String {
        let live = pct.map { #","details":{"live_progress":{"available":true,"percent":\#($0)}}"# } ?? ""
        return #"{"artist":"\#(artist)","album":"\#(album)","status":"\#(status)","updated_at":\#(at)\#(live)}"#
    }

    @Test func emptyWhenNothingMovesOrFailed() {
        let c = PipelineDockContent(jobs: jobs(job("Can", "Tago Mago", "imported")))
        #expect(c.isEmpty)
        #expect(c.rows.isEmpty)
    }

    @Test func workingBeforeQueuedAndPercentBecomesFraction() {
        let c = PipelineDockContent(jobs: jobs([
            job("A", "Queued One", "queued", at: 9),
            job("B", "Moving", "downloading", pct: 42, at: 1),
        ].joined(separator: ",")))
        #expect(c.rows.map(\.title) == ["Moving", "Queued One"])
        #expect(c.rows[0].fraction == 0.42)
        #expect(c.rows[0].status == "Downloading 42%")
        #expect(c.rows[1].waiting)
        #expect(c.headline == "2 downloads")
    }

    @Test func showsThreeRowsAndCountsTheRest() {
        let list = (1...5).map { job("A", "Album \($0)", "downloading", at: Double($0)) }.joined(separator: ",")
        let c = PipelineDockContent(jobs: jobs(list))
        #expect(c.rows.count == 3)
        #expect(c.more == 2)
        #expect(c.rows.first?.title == "Album 5")
    }

    @Test func failureKeepsTheDockOpenAndIsNamed() {
        let c = PipelineDockContent(jobs: jobs(job("A", "Broken", "no_matches")))
        #expect(!c.isEmpty)
        #expect(c.rows.isEmpty)
        #expect(c.headline == "1 failed")
    }

    @Test func percentIsClamped() {
        let c = PipelineDockContent(jobs: jobs(job("A", "X", "downloading", pct: 140)))
        #expect(c.rows[0].fraction == 1)
    }

    @Test(arguments: ThemeID.allCases)
    func rendersDock(theme: ThemeID) throws {
        RenderMode.offscreenScreenshot = true
        let state = AppState(themeID: theme, screen: .home)
        state.acquisition.showJobs(jobs([
            job("Talk Talk", "Spirit of Eden", "downloading", pct: 63, at: 3),
            job("Portishead", "Dummy", "searching", at: 2),
            job("Can", "Ege Bamyasi", "queued", at: 1),
            job("Can", "Future Days", "queued", at: 0),
        ].joined(separator: ",")))
        let host = NSHostingView(rootView: RootView(state: state))
        host.frame = NSRect(x: 0, y: 0, width: 1100, height: 700)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.4))
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let png = try #require(rep.representation(using: .png, properties: [:]))
        let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
        try png.write(to: dir.appendingPathComponent("pipeline-dock-\(theme.rawValue).png"))
    }

    // MARK: Slice D3: room for the dock

    @Test func placementFollowsTheScreenAndTheQueue() {
        let moving = PipelineDockContent(jobs: jobs(job("A", "B", "downloading", pct: 40)))
        #expect(PipelineDockPlacement.shows(screen: .home, content: moving))
        #expect(PipelineDockPlacement.shows(screen: .album, content: moving))
        #expect(!PipelineDockPlacement.shows(screen: .downloads, content: moving))
        #expect(!PipelineDockPlacement.shows(screen: .nowPlaying, content: moving))
        let idle = PipelineDockContent(jobs: jobs(job("A", "B", "imported")))
        #expect(!PipelineDockPlacement.shows(screen: .home, content: idle))
        // From the player bar's top to the card's top plus one margin.
        #expect(PipelineDockPlacement.bottomClearance(cardHeight: 72) == CGFloat(14 + 72 + 16))
        // Inside the main column, one margin clear of the queue when it is open.
        #expect(PipelineDockPlacement.trailingMargin(queueOpen: false) == 16)
        #expect(PipelineDockPlacement.trailingMargin(queueOpen: true) == CupertinoQueueInspector.width + 16)
    }

    /// The shell leaves the shared bottom inset on the page scroll view, and more of it while the dock shows, so the last
    /// row can scroll clear of the card (D3.1 and D3.2).
    @Test func pageScrollViewsLeaveRoomForTheDock() throws {
        RenderMode.offscreenScreenshot = true
        let base = try pageBottomInset(jobsJSON: nil)
        #expect(base == CU.Shell.contentBottomInset, "no dock: the shared inset only (\(base))")

        let failed = try pageBottomInset(jobsJSON: job("A", "Broken", "no_matches"))
        #expect(failed > base, "a short dock widens the inset (\(failed))")

        let three = try pageBottomInset(jobsJSON: [
            job("A", "One", "downloading", pct: 20), job("B", "Two", "downloading", pct: 40),
            job("C", "Three", "queued"),
        ].joined(separator: ","))
        #expect(three > failed, "a taller dock widens it further (\(three) against \(failed))")
    }

    /// The same page scrolled to its end with the dock showing: the last row stays above the bar and the card.
    @Test func rendersDockOverAScrolledPage() throws {
        RenderMode.offscreenScreenshot = true
        let state = AppState(themeID: .cupertino, screen: .home)
        state.acquisition.showJobs(jobs([
            job("Talk Talk", "Spirit of Eden", "downloading", pct: 63, at: 3),
            job("Portishead", "Dummy", "searching", at: 2),
            job("Can", "Ege Bamyasi", "queued", at: 1),
        ].joined(separator: ",")))
        let host = Self.host(RootView(state: state), width: 1280, height: 800)
        RunLoop.current.run(until: Date().addingTimeInterval(0.6))
        Self.scrollPageToEnd(host)
        RunLoop.current.run(until: Date().addingTimeInterval(0.3))
        let png = try Self.png(host)
        try FileManager.default.createDirectory(at: Self.outputDirectory, withIntermediateDirectories: true)
        try png.write(to: Self.outputDirectory.appendingPathComponent("pipeline-dock-home-end.png"))
    }

    private func pageBottomInset(jobsJSON: String?) throws -> CGFloat {
        let state = AppState(themeID: .cupertino, screen: .home)
        if let jobsJSON { state.acquisition.showJobs(jobs(jobsJSON)) }
        let host = Self.host(RootView(state: state), width: 1280, height: 800)
        RunLoop.current.run(until: Date().addingTimeInterval(0.6))
        let page = try #require(Self.scrollViews(host).max(by: { $0.frame.width < $1.frame.width }))
        return page.contentInsets.bottom
    }

    @MainActor private static func host(_ view: some View, width: CGFloat, height: CGFloat) -> NSHostingView<some View> {
        let host = NSHostingView(rootView: view.frame(width: width, height: height))
        host.frame = NSRect(x: 0, y: 0, width: width, height: height)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        return host
    }

    private static func scrollViews(_ view: NSView) -> [NSScrollView] {
        var found: [NSScrollView] = []
        if let scroll = view as? NSScrollView { found.append(scroll) }
        for sub in view.subviews { found.append(contentsOf: scrollViews(sub)) }
        return found
    }

    @MainActor private static func scrollPageToEnd(_ host: NSView) {
        guard let page = scrollViews(host).max(by: { $0.frame.width < $1.frame.width }),
              let document = page.documentView else { return }
        let maxY = max(0, document.frame.height - page.contentView.bounds.height + page.contentInsets.bottom + page.contentInsets.top)
        page.contentView.scroll(to: NSPoint(x: 0, y: maxY))
        page.reflectScrolledClipView(page.contentView)
    }

    private static func png(_ host: NSView) throws -> Data {
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        return try #require(rep.representation(using: .png, properties: [:]))
    }

    private static var outputDirectory: URL {
        URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
    }
}
