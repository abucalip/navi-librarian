import Foundation
import Testing
import DiscairLibrarian
import DiscairNavidrome
@testable import DiscairUI

@Suite("Home dashboard figures") struct HomeDashboardTests {
    /// 2026-11-11 12:00 UTC.
    static let now = Date(timeIntervalSince1970: 1_794_398_400)
    static var cal: Calendar { var c = Calendar(identifier: .gregorian); c.timeZone = TimeZone(identifier: "UTC")!; return c }

    static func ago(days: Int) -> String {
        ISO8601DateFormatter().string(from: cal.date(byAdding: .day, value: -days, to: now)!)
    }

    static func album(_ id: String, year: Int? = nil, addedDaysAgo: Int? = nil, plays: Int? = nil, playedDaysAgo: Int? = nil) -> NavidromeAlbum {
        var f = [#""id":"\#(id)","name":"Album \#(id)","artist":"Artist""#]
        if let year { f.append(#""year":\#(year)"#) }
        if let d = addedDaysAgo { f.append(#""created":"\#(ago(days: d))""#) }
        if let plays { f.append(#""playCount":\#(plays)"#) }
        if let d = playedDaysAgo { f.append(#""played":"\#(ago(days: d))""#) }
        return try! JSONDecoder().decode(NavidromeAlbum.self, from: Data("{\(f.joined(separator: ","))}".utf8))
    }

    static func job(_ status: String, album: String = "Spirit", message: String? = nil, updated: Double = 1) -> Acquisition {
        let details = message.map { #","details":{"message":"\#($0)"}"# } ?? ""
        return try! JSONDecoder().decode(Acquisition.self, from: Data(#"{"artist":"Talk Talk","album":"\#(album)","status":"\#(status)","updated_at":\#(updated)\#(details)}"#.utf8))
    }

    static func build(_ albums: [NavidromeAlbum]?, jobs: [Acquisition] = [], taste: TasteProfiles? = nil, picks: Int? = nil,
                      up: Bool = true, baseline: HomeDashboard.NeverPlayedBaseline? = nil) -> HomeDashboard {
        HomeDashboard.build(.init(albums: albums, jobs: jobs, taste: taste, picksCount: picks, librarianReachable: up,
                                  neverPlayedBaseline: baseline, now: now, calendar: cal))
    }

    static func taste(low: Bool = false, eraLow: Bool = false) -> TasteProfiles {
        let w = #"{"listens":200,"low_sample":\#(low),"attributed":{"era":200},"dimension_low_sample":{"era":\#(eraLow)},"dimensions":{"era":[{"value":"1980s","count":100,"share":0.5},{"value":"2020s","count":60,"share":0.3}]}}"#
        return try! JSONDecoder().decode(TasteResponse.self, from: Data(#"{"profiles":{"windows":{"recent":\#(w)},"shifts":[]}}"#.utf8)).profiles!
    }

    // MARK: Empty and missing

    @Test func unreadListGivesNoFigures() {
        let d = Self.build(nil)
        #expect(d.load == .notLoaded && d.albumCount == nil && d.neverPlayed == nil && d.added == nil && d.shelfLife == nil)
        #expect(d.growth.isEmpty && d.decades.isEmpty && d.waiting == nil)
    }

    @Test func emptyLibraryIsZeroAlbumsAndNothingElse() {
        let d = Self.build([], picks: 3)
        #expect(d.load == .empty && d.albumCount == 0)
        #expect(d.added == nil && d.neverPlayed == nil && d.shelfLife == nil && d.growth.isEmpty)
        #expect(d.waiting == .init(picks: 3, unplayedArrivals: 0))
    }

    // MARK: Hero

    @Test func addedLast30AgainstThe30Before() {
        let d = Self.build([Self.album("a", addedDaysAgo: 3), Self.album("b", addedDaysAgo: 29), Self.album("c", addedDaysAgo: 31),
                            Self.album("d", addedDaysAgo: 59), Self.album("e", addedDaysAgo: 61), Self.album("f")])
        #expect(d.albumCount == 6)
        #expect(d.added == .init(last: 2, before: 2))
        #expect(d.added?.delta == 0)
    }

    @Test func noAddedDatesMeansNoComparisonNotZero() {
        let d = Self.build([Self.album("a"), Self.album("b")])
        #expect(d.albumCount == 2 && d.added == nil && d.growth.isEmpty)
    }

    // MARK: Never played and shelf life

    @Test func neverPlayedCountsAlbumsWithNoPlaysAndChangeNeedsABaseline() {
        let albums = [Self.album("a"), Self.album("b", plays: 0), Self.album("c", plays: 4, playedDaysAgo: 2), Self.album("d", plays: 1, playedDaysAgo: 400)]
        #expect(Self.build(albums).neverPlayed == 2)
        #expect(Self.build(albums).neverPlayedChange == nil)
        let since = Self.cal.date(byAdding: .day, value: -41, to: Self.now)!
        let d = Self.build(albums, baseline: .init(count: 5, date: since))
        #expect(d.neverPlayedChange == .init(delta: -3, since: since))
    }

    @Test func shelfLifeBinsAreExhaustiveAndOrdered() {
        let albums = [Self.album("a", plays: 1, playedDaysAgo: 5),      // this month
                      Self.album("b", plays: 1, playedDaysAgo: 80),     // 2 months
                      Self.album("c", plays: 1, playedDaysAgo: 250),    // 8 months
                      Self.album("d", plays: 1, playedDaysAgo: 500),    // 1 to 2 years
                      Self.album("e", plays: 1, playedDaysAgo: 1200),   // 2+ years
                      Self.album("f"),                                  // never
                      Self.album("g", plays: 7)]                        // plays but no time
        let s = Self.build(albums).shelfLife!
        #expect(s.bins.map(\.bin) == HomeDashboard.ShelfBin.allCases)
        #expect(s.bins.map(\.count) == [1, 1, 1, 1, 1, 1])
        #expect(s.unknownPlayed == 1)
        #expect(s.bins.map(\.count).reduce(0, +) + s.unknownPlayed == albums.count)
    }

    @Test func longestUnplayedIsOldestAddedNeverPlayedThenOldestLastPlay() {
        let albums = [Self.album("new", addedDaysAgo: 2), Self.album("old", addedDaysAgo: 900), Self.album("mid", addedDaysAgo: 300),
                      Self.album("undated"), Self.album("p1", plays: 1, playedDaysAgo: 700), Self.album("p2", plays: 1, playedDaysAgo: 100)]
        #expect(Self.build(albums).shelfLife?.longestUnplayed == ["old", "mid", "new", "undated"])
        let few = [Self.album("x", addedDaysAgo: 5), Self.album("p1", plays: 1, playedDaysAgo: 700), Self.album("p2", plays: 1, playedDaysAgo: 100)]
        #expect(Self.build(few).shelfLife?.longestUnplayed == ["x", "p1", "p2"])
    }

    @Test func noPlaysAtAllMeansEveryAlbumIsNeverPlayed() {
        let d = Self.build([Self.album("a"), Self.album("b"), Self.album("c")])
        #expect(d.neverPlayed == 3 && d.shelfLife?.count(.never) == 3 && d.shelfLife?.unknownPlayed == 0)
    }

    // MARK: Growth

    @Test func growthTotalsAreCumulativeAndReconcile() {
        let albums = [Self.album("a", addedDaysAgo: 400), Self.album("b", addedDaysAgo: 100), Self.album("c", addedDaysAgo: 40),
                      Self.album("d", addedDaysAgo: 3), Self.album("e", addedDaysAgo: 2), Self.album("u")]
        let d = Self.build(albums)
        let year = d.series(.oneYear)!
        #expect(year.points.count == 12 && year.undated == 1)
        #expect(year.points.last?.total == 5)                       // everything dated, a was added before the window
        #expect(year.points.first!.total >= 1)                      // a is already counted at the start
        #expect(year.points.map(\.added).reduce(0, +) + 1 == 5)     // 4 added inside the window plus the 1 before it
        #expect(year.points.map(\.total) == year.points.map(\.total).sorted())
        let all = d.series(.all)!
        #expect(all.points.map(\.added).reduce(0, +) == 5 && all.points.last?.total == 5)
        let q = d.series(.threeMonths)!
        #expect(q.points.count == 13 && q.points.last?.total == 5)
    }

    @Test func oneDatedAlbumCannotDrawAnAllTimeLine() {
        let d = Self.build([Self.album("a", addedDaysAgo: 3), Self.album("b")])
        #expect(d.series(.all) == nil)          // one bucket
        #expect(d.series(.oneYear)?.points.last?.total == 1)
    }

    @Test func aLongHistoryGroupsByThreeMonths() {
        let d = Self.build([Self.album("a", addedDaysAgo: 365 * 8), Self.album("b", addedDaysAgo: 10)])
        let all = d.series(.all)!
        #expect(all.points.count <= 60 && all.points.count > 20)
        #expect(all.points.map(\.added).reduce(0, +) == 2)
    }

    // MARK: Decades

    @Test func decadeSharesCoverDatedAlbumsAndNeedASoundTasteWindow() {
        let albums = [Self.album("a", year: 1985), Self.album("b", year: 1989), Self.album("c", year: 2021), Self.album("d", year: 1971), Self.album("e")]
        let none = Self.build(albums)
        #expect(none.decades.map(\.label) == ["1970s", "1980s", "2020s"])
        #expect(none.decades.map(\.ownedShare) == [0.25, 0.5, 0.25])
        #expect(none.decades.allSatisfy { $0.listenShare == nil } && !none.listenSharesAvailable)

        let sound = Self.build(albums, taste: Self.taste())
        #expect(sound.listenSharesAvailable)
        #expect(sound.decades.map(\.listenShare) == [0, 0.5, 0.3])      // a decade the window lists nothing for is 0 once the window is sound

        #expect(!Self.build(albums, taste: Self.taste(low: true)).listenSharesAvailable)
        #expect(!Self.build(albums, taste: Self.taste(eraLow: true)).listenSharesAvailable)
    }

    @Test func noYearsMeansNoDecades() {
        #expect(Self.build([Self.album("a"), Self.album("b", year: 0)]).decades.isEmpty)
    }

    // MARK: Arrivals, waiting, notice

    @Test func arrivalsOrderNeedsYouThenMovingThenWaitingThenArrivedUnplayed() {
        let jobs = [Self.job("imported", album: "Done"), Self.job("queued", album: "Q", updated: 1), Self.job("downloading", album: "D", updated: 2),
                    Self.job("no_matches", album: "F", message: "Nothing found", updated: 3)]
        let albums = [Self.album("fresh", addedDaysAgo: 2), Self.album("playedFresh", addedDaysAgo: 3, plays: 1, playedDaysAgo: 1), Self.album("old", addedDaysAgo: 90)]
        let d = Self.build(albums, jobs: jobs, picks: 2)
        #expect(d.arrivals.count == 4 && d.arrivalsHidden == 0)
        guard case .job(_, let t0, _, let s0, let f0) = d.arrivals[0] else { Issue.record("first row should be a job"); return }
        #expect(t0 == "F" && s0 == .found && f0 == "Nothing found")
        guard case .job(_, let t1, _, let s1, let f1) = d.arrivals[1] else { Issue.record("second row should be a job"); return }
        #expect(t1 == "D" && s1 == .downloading && f1 == nil)
        guard case .job(_, let t2, _, let s2, _) = d.arrivals[2] else { Issue.record("third row should be a job"); return }
        #expect(t2 == "Q" && s2 == .found)
        #expect(d.arrivals[3] == .arrived(albumID: "fresh", title: "Album fresh", artist: "Artist"))
        #expect(d.waiting == .init(picks: 2, unplayedArrivals: 1))
        #expect(d.waiting?.total == 3)
    }

    @Test func arrivalsAreCappedAtFourAndTheRestIsCounted() {
        let jobs = (0..<6).map { Self.job("downloading", album: "A\($0)", updated: Double($0)) }
        let d = Self.build([Self.album("a")], jobs: jobs)
        #expect(d.arrivals.count == 4 && d.arrivalsHidden == 2)
    }

    @Test func stagesFollowTheServerStatus() {
        #expect(HomeDashboard.stage(of: Self.job("searching")) == .found)
        #expect(HomeDashboard.stage(of: Self.job("downloading")) == .downloading)
        #expect(HomeDashboard.stage(of: Self.job("importing")) == .importing)
        #expect(HomeDashboard.stage(of: Self.job("imported")) == .inLibrary)
        #expect(HomeDashboard.stage(of: Self.job("slskd_error")) == .downloading)
    }

    @Test func aFailedGetBecomesTheNoticeWithItsReason() {
        let d = Self.build([Self.album("a")], jobs: [Self.job("no_matches", album: "X", message: "No source was found."), Self.job("queue_failed", album: "Y", updated: 0)])
        #expect(d.notice == .failedJob(title: "X", reason: "No source was found.", others: 1))
        #expect(Self.build([Self.album("a")], jobs: [Self.job("downloading")]).notice == nil)
    }

    // MARK: Librarian down

    @Test func librarianDownKeepsNavidromeFiguresAndDropsTheRest() {
        let albums = [Self.album("a", year: 1985, addedDaysAgo: 3), Self.album("b", year: 1990, addedDaysAgo: 40)]
        let d = Self.build(albums, jobs: [Self.job("no_matches", message: "x")], taste: Self.taste(), picks: 5, up: false)
        #expect(d.notice == .librarianUnreachable)                  // outranks a failed Get
        #expect(d.albumCount == 2 && d.added == .init(last: 1, before: 1) && d.neverPlayed == 2 && d.shelfLife != nil && d.series(.oneYear) != nil)
        #expect(d.waiting?.picks == nil && !d.listenSharesAvailable && d.decades.allSatisfy { $0.listenShare == nil })
    }
}
