import AppKit
import DiscairLibrarian
import DiscairNavidrome
import SwiftUI
import Testing
@testable import DiscairUI

/// Renders the redesigned Cupertino Home in the states of `docs/design/redesign/macos/cupertino/home--*` to PNG, to be put
/// beside the mockups. Output goes to `DISCAIR_SCREENSHOT_DIR` (or a temp folder) as `cupertino-home-<state>.png`.
@MainActor
struct HomeRenderTests {
    /// A library of 1,284 albums with a spread of added dates, release years and last plays, shaped like the mockup's numbers.
    static func albums(now: Date) -> [NavidromeAlbum] {
        let iso = ISO8601DateFormatter()
        func ago(_ days: Int) -> String { iso.string(from: Calendar(identifier: .gregorian).date(byAdding: .day, value: -days, to: now)!) }
        let playedAgo = [10, 90, 250, 500, 900]
        return (0..<1284).map { i in
            let added = i < 12 ? i * 2 + 1 : i < 19 ? 31 + (i - 12) * 4 : 61 + Int(Double(i - 19) * 1.4)
            var f = [#""id":"a\#(i)","name":"Album \#(i)","artist":"Artist \#(i % 40)","year":\#(1960 + (i * 7) % 64)"#, #""created":"\#(ago(added))""#]
            if i % 13 != 0 { f.append(#""playCount":\#(1 + i % 9),"played":"\#(ago(playedAgo[i % 5] + i % 20))""#) }
            return try! JSONDecoder().decode(NavidromeAlbum.self, from: Data("{\(f.joined(separator: ","))}".utf8))
        }
    }

    static var taste: TasteProfiles {
        let shifts = #"[{"window":"recent","dimension":"genre","value":"ambient","direction":"up","from_share":0.09,"to_share":0.17},{"window":"recent","dimension":"genre","value":"post-punk","direction":"down","from_share":0.14,"to_share":0.08}]"#
        let era = #"[{"value":"1960s","count":50,"share":0.04},{"value":"1970s","count":150,"share":0.12},{"value":"1980s","count":236,"share":0.19},{"value":"1990s","count":470,"share":0.38},{"value":"2000s","count":174,"share":0.14},{"value":"2010s","count":110,"share":0.09},{"value":"2020s","count":50,"share":0.04}]"#
        let json = #"{"profiles":{"headline":{"text":"More ambient, less post-punk lately.","kind":"shift","window":"recent","subjects":[]},"windows":{"recent":{"listens":1240,"low_sample":false,"attributed":{"era":1240},"dimension_low_sample":{"era":false},"dimensions":{"era":\#(era)}},"all_time":{"listens":48912,"low_sample":false}},"shifts":\#(shifts)}}"#
        return try! JSONDecoder().decode(TasteResponse.self, from: Data(json.utf8)).profiles!
    }

    static let offLenses: InsightsResponse = {
        let off = #"{"enabled":false,"cards":[]}"#
        return try! JSONDecoder().decode(InsightsResponse.self, from: Data(#"{"data_version":3,"generation":1,"lenses":{"forgotten_gem":\#(off),"blind_spot":\#(off),"series_completion":\#(off),"hidden_canon":\#(off),"anniversary":\#(off)}}"#.utf8))
    }()

    enum Scenario { case normal, firstRun, unreachable, loading }

    func state(_ scenario: Scenario) -> AppState {
        let now = Date()
        let state = AppState(themeID: .cupertino, screen: .home)
        switch scenario {
        case .normal:
            state.taste.set(Self.taste)
            let song = try! JSONDecoder().decode(NavidromeSong.self, from: Data(#"{"id":"s2","title":"Ascension Day","artist":"Talk Talk","duration":360}"#.utf8))
            let queue = NavidromePlayQueue(songs: [song], currentID: "s2", positionMs: 161_000, changed: now.addingTimeInterval(-600), changedBy: "discair-android")
            let plays = [RadioPlay(id: 1, stationName: "FIP", artist: "The Blue Nile", title: "Sea Song", heardAt: now.timeIntervalSince1970 - 3600)]
            let finished = now.timeIntervalSince1970 - 7200
            let pop = JobRun(state: "queued", finishedAt: finished, progress: ["pending": 340])
            let insights = JobRun(state: "succeeded", finishedAt: finished)
            state.showHomeFeeds(radio: plays, popularity: JobStatus(status: pop, lastGood: pop),
                                insightsJob: JobStatus(status: insights, lastGood: insights, minInterval: 21_600, retryAfter: 14_400), queue: queue)
            let days = (0..<84).map { i -> ListensDay in
                let f = DateFormatter(); f.calendar = Calendar(identifier: .gregorian); f.timeZone = TimeZone(identifier: "UTC"); f.locale = Locale(identifier: "en_US_POSIX"); f.dateFormat = "yyyy-MM-dd"
                return ListensDay(date: f.string(from: now.addingTimeInterval(-Double(84 - i) * 86_400)), count: i >= 77 ? 31 : (i >= 70 ? 26 : 20))
            }
            state.showHome(HomeDashboard.build(.init(albums: Self.albums(now: now), taste: Self.taste, picksCount: 7, radioPlays: plays, listensByDay: days,
                                                     handoff: HomeScreen.handoff(queue: queue, now: now, clientName: "discair", playingSongID: nil), now: now)))
        case .firstRun:
            state.library.apply(newest: [], first: [], artists: [], picks: [])
            state.insights.showForPreview(Self.offLenses)
            state.showHome(HomeDashboard.build(.init(albums: Self.albums(now: now), picksCount: 0, now: now)))
            state.taste.set(nil)
        case .unreachable:
            state.showHome(HomeDashboard.build(.init(albums: Self.albums(now: now), librarianReachable: false, now: now)))
        case .loading:
            break
        }
        return state
    }

    private func render(_ scenario: Scenario, name: String, width: CGFloat = 1044, height: CGFloat = 2300) throws {
        RenderMode.offscreenScreenshot = true
        let s = state(scenario)
        let size = NSSize(width: width, height: height)
        let view = CupertinoHome(state: s).frame(width: width, height: height).background(Color.white).environment(\.colorScheme, .light)
        let host = NSHostingView(rootView: view)
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(1.2))
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let png = try #require(rep.representation(using: .png, properties: [:]))
        var colours = Set<Int>()
        for ix in 0..<48 { for iy in 0..<48 {
            guard let c = rep.colorAt(x: (rep.pixelsWide - 1) * ix / 47, y: (rep.pixelsHigh - 1) * iy / 47)?.usingColorSpace(.sRGB) else { continue }
            colours.insert(Int(c.redComponent * 15) << 8 | Int(c.greenComponent * 15) << 4 | Int(c.blueComponent * 15))
        } }
        #expect(colours.count >= 4, "render looks blank (\(colours.count) distinct colours)")
        let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try png.write(to: dir.appendingPathComponent("cupertino-home-\(name).png"))
    }

    @Test func rendersDefault() throws { try render(.normal, name: "default") }
    @Test func rendersFirstRun() throws { try render(.firstRun, name: "first-run", height: 1200) }
    @Test func rendersLibrarianUnreachable() throws { try render(.unreachable, name: "librarian-unreachable", height: 1300) }
    @Test func rendersLoading() throws { try render(.loading, name: "loading", height: 1000) }
    @Test func rendersStackedUnder860() throws { try render(.normal, name: "stacked", width: 760, height: 3400) }
}
