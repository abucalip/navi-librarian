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

    @Test(arguments: [ThemeID.cupertino, ThemeID.zine])
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
}
