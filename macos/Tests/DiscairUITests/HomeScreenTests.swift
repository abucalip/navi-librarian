import Foundation
import Testing
import DiscairLibrarian
import DiscairNavidrome
@testable import DiscairUI

@Suite("Home screen states and wording") struct HomeScreenTests {
    static let now = HomeDashboardTests.now
    static var cal: Calendar { HomeDashboardTests.cal }

    // MARK: Layout

    @Test func rowsStackBelow860() {
        #expect(HomeScreen.isStacked(contentWidth: 859))
        #expect(!HomeScreen.isStacked(contentWidth: 860))
        #expect(!HomeScreen.isStacked(contentWidth: 980))
    }

    // MARK: Pick

    @Test func pickPositionClampsAfterADismissal() {
        #expect(HomeScreen.pickPosition(index: 0, count: 7)?.label == "1 of 7")
        #expect(HomeScreen.pickPosition(index: 6, count: 6)?.index == 5)
        #expect(HomeScreen.pickPosition(index: -2, count: 3)?.index == 0)
        #expect(HomeScreen.pickPosition(index: 0, count: 0) == nil)
    }

    @Test func arrowKeysMapToTheDeckActions() {
        #expect(HomeScreen.pickKey(arrow: .right) == .get)
        #expect(HomeScreen.pickKey(arrow: .down) == .save)
        #expect(HomeScreen.pickKey(arrow: .left) == .notForMe)
    }

    @Test func spaceOnAnUnownedPickShowsANoticeAndOnAnOwnedOnePlays() {
        #expect(HomeScreen.spaceOutcome(owned: true) == .play)
        guard case .notOwned(let notice) = HomeScreen.spaceOutcome(owned: false) else { Issue.record("expected a notice"); return }
        #expect(notice.contains("not in your library"))
    }

    @Test func emptyPickStateFollowsTheSource() {
        #expect(HomeScreen.pickEmpty(librarianReachable: false, hasListeningSource: true, note: nil) == .withoutLibrarian)
        #expect(HomeScreen.pickEmpty(librarianReachable: true, hasListeningSource: false, note: nil) == .needsHistory)
        #expect(HomeScreen.pickEmpty(librarianReachable: true, hasListeningSource: true, note: "Add a key in Settings.") == .needsHistory)
        #expect(HomeScreen.pickEmpty(librarianReachable: true, hasListeningSource: true, note: "Nothing right now.") == .noneRightNow)
    }

    // MARK: Collection

    private func yearOfAlbums() -> HomeDashboard {
        var albums: [NavidromeAlbum] = []
        for i in 0..<120 { albums.append(HomeDashboardTests.album("a\(i)", year: 1990, addedDaysAgo: i * 3)) }
        return HomeDashboardTests.build(albums)
    }

    @Test func growthSubtitleStatesThePeriod() {
        let s = yearOfAlbums().series(.oneYear)
        let text = HomeScreen.growthSubtitle(s, mode: .total, calendar: Self.cal)
        #expect(text.hasPrefix("Albums in your library, from the date each was added · "))
        #expect(text.hasSuffix(" to today"))
        #expect(HomeScreen.growthSubtitle(nil, mode: .added) == "Albums added per period, from the date each was added")
    }

    @Test func growthTooltipAndAxis() throws {
        let s = try #require(yearOfAlbums().series(.oneYear))
        let detail = HomeScreen.growthDetail(s.points[3], series: s, calendar: Self.cal)
        #expect(detail.contains("added that month"))
        let labels = HomeScreen.growthAxisLabels(s, calendar: Self.cal)
        #expect(labels.count == 7)
        #expect(HomeScreen.periodNoun(try #require(yearOfAlbums().series(.threeMonths)), calendar: Self.cal) == "week")
    }

    @Test func biggestPeriodIsAnnotatedOnlyWhenThereAreEnoughPoints() throws {
        let s = try #require(yearOfAlbums().series(.oneYear))
        let note = try #require(HomeScreen.biggestPeriod(s, calendar: Self.cal))
        #expect(note.text.hasPrefix("Biggest month: "))
        #expect(s.points[note.index].added == s.points.map(\.added).max())
    }

    // MARK: Taste

    static func taste(headline: String?, shifts: String = "[]", recent: Int = 1240) -> TasteProfiles {
        let h = headline.map { #""headline":{"text":"\#($0)","kind":"shift","window":"recent","subjects":[]},"# } ?? ""
        let json = #"{"profiles":{\#(h)"windows":{"recent":{"listens":\#(recent),"low_sample":false},"all_time":{"listens":48912,"low_sample":false}},"shifts":\#(shifts)}}"#
        return try! JSONDecoder().decode(TasteResponse.self, from: Data(json.utf8)).profiles!
    }

    @Test func tasteIsLoadingUntilARead_finishes() {
        #expect(HomeScreen.taste(profiles: nil, loaded: false) == .loading)
    }

    @Test func noHeadlineShowsProgressNotAClaim() {
        #expect(HomeScreen.taste(profiles: nil, loaded: true) == .progress(listens: 0, need: 50))
        #expect(HomeScreen.taste(profiles: Self.taste(headline: nil, recent: 31), loaded: true) == .progress(listens: 31, need: 50))
    }

    @Test func headlineAndShiftsAreTheServersOwn() {
        let shifts = #"[{"window":"recent","dimension":"genre","value":"ambient","direction":"up","from_share":0.09,"to_share":0.17},{"window":"recent","dimension":"genre","value":"post-punk","direction":"down","from_share":0.14,"to_share":0.08}]"#
        let state = HomeScreen.taste(profiles: Self.taste(headline: "More ambient, less post-punk lately.", shifts: shifts), loaded: true)
        guard case .ready(let headline, let rows, let label, let recent, let all) = state else { Issue.record("not ready"); return }
        #expect(headline == "More ambient, less post-punk lately.")
        #expect(rows.map(\.label) == ["Ambient", "Post-punk"])
        #expect(abs(rows[0].before - 9) < 0.001 && abs(rows[0].now - 17) < 0.001)
        #expect(label == "Last 90 days" && recent == 1240 && all == 48912)
    }

    @Test func aHeadlineWithNoListedShiftDrawsNoDumbbell() {
        guard case .ready(_, let rows, _, _, _) = HomeScreen.taste(profiles: Self.taste(headline: "Steady."), loaded: true) else { Issue.record("not ready"); return }
        #expect(rows.isEmpty)
    }

    // MARK: Shelf life

    @Test func shelfLifeNeedsAnAlbumInABin() {
        #expect(!HomeScreen.shelfAvailable(nil))
        #expect(HomeScreen.shelfAvailable(HomeDashboardTests.build([HomeDashboardTests.album("a")]).shelfLife))
        #expect(HomeScreen.shortLabel(.oneToSixMonths) == "1–6 mo")
    }

    // MARK: Server activity

    private func input(up: Bool = true, live: Bool = true, error: Bool = false, taste: Bool = true, note: String? = nil, coverage: String? = "broad") -> HomeScreen.ActivityInput {
        .init(librarianReachable: up, insightsLive: live, insightsError: error, insightsLoadedAt: Self.now.addingTimeInterval(-7200), lensesOn: 3, lensesTotal: 5,
              tasteLoaded: taste, tasteRefreshing: false, tasteNote: note, tasteListens: 1240, graphCoverage: coverage, now: Self.now)
    }

    @Test func unreachableLibrarianMakesEverythingUnknownNotFailed() {
        let rows = HomeScreen.activity(input(up: false))
        #expect(!rows.isEmpty && rows.allSatisfy { $0.status == .unknown })
    }

    @Test func healthyActivityHasAWordAndALinePerJob() {
        let rows = HomeScreen.activity(input())
        #expect(rows.map(\.name) == ["Insight lenses", "Taste profile", "Artist popularity", "MusicBrainz data"])
        #expect(rows.map(\.status) == [.done, .done, .notLoaded, .loaded])
        #expect(rows[0].line == "Read 2 hours ago · 3 of 5 on")
        #expect(rows[1].line == "At launch · 1,240 listens in the recent window")
        #expect(rows[3].line == "Graph coverage: broad")
    }

    @Test func failedReadsSayNotUpdatingAndKeepWhatWasSaved() {
        let rows = HomeScreen.activity(input(error: true, note: "The taste refresh could not run."))
        #expect(rows[0].status == .notUpdating && rows[0].line.hasPrefix("The last read failed."))
        #expect(rows[1].status == .notUpdating && rows[1].line == "The taste refresh could not run.")
    }

    @Test func unreadSourcesAreNotLoadedAndNoCoverageIsNotLoaded() {
        let rows = HomeScreen.activity(input(live: false, taste: false, coverage: "none"))
        #expect(rows.map(\.status) == [.notLoaded, .notLoaded, .notLoaded, .notLoaded])
        #expect(HomeScreen.activity(input(coverage: nil)).map(\.name) == ["Insight lenses", "Taste profile", "Artist popularity"])
    }

    // MARK: Page

    @Test func loadingOnlyWhileTheFirstReadRuns() {
        #expect(HomeScreen.page(dashboard: .notLoaded, libraryPhaseLoading: true) == .loading)
        #expect(HomeScreen.page(dashboard: .notLoaded, libraryPhaseLoading: false) == .ready)
        #expect(HomeScreen.page(dashboard: HomeDashboardTests.build([]), libraryPhaseLoading: true) == .ready)
    }

    // MARK: Never-played baseline

    @Test func baselineIsTheEarliestReadingSinceTheFirstOfLastMonth() {
        func at(_ m: Int, _ d: Int) -> Date { Self.cal.date(from: DateComponents(year: 2026, month: m, day: d, hour: 9))! }
        let readings = [HomeScreen.Reading(count: 120, date: at(9, 20)), HomeScreen.Reading(count: 100, date: at(10, 1)), HomeScreen.Reading(count: 98, date: at(11, 3))]
        let b = HomeScreen.baseline(readings, now: Self.now, calendar: Self.cal)
        #expect(b == .init(count: 100, date: at(10, 1)))
        // A reading from before the window is ignored.
        #expect(HomeScreen.baseline([readings[0]], now: Self.now, calendar: Self.cal) == nil)
    }

    @Test func aReadingTakenTodayIsNotAComparison() {
        let today = HomeScreen.Reading(count: 96, date: Self.now)
        #expect(HomeScreen.baseline([today], now: Self.now, calendar: Self.cal) == nil)
        #expect(HomeScreen.baseline([], now: Self.now, calendar: Self.cal) == nil)
    }

    @Test func recordingKeepsOneReadingADayAndForgetsOldOnes() {
        let old = HomeScreen.Reading(count: 150, date: Self.cal.date(byAdding: .month, value: -3, to: Self.now)!)
        let first = HomeScreen.recording([old], count: 96, now: Self.now, calendar: Self.cal)
        #expect(first == [.init(count: 96, date: Self.now)])
        let again = HomeScreen.recording(first, count: 90, now: Self.now.addingTimeInterval(3600), calendar: Self.cal)
        #expect(again == first)
    }

    // MARK: Words

    @Test func datesAreWrittenInFull() {
        let d = Self.cal.date(from: DateComponents(year: 2026, month: 11, day: 11))!
        #expect(HomeScreen.headerDate(d, calendar: Self.cal) == "Wednesday 11 November")
        #expect(HomeScreen.fullDate(d, calendar: Self.cal) == "11 November 2026")
        #expect(HomeScreen.relative(Self.now.addingTimeInterval(-7200), now: Self.now) == "2 hours ago")
        #expect(HomeScreen.parseDate("2026-11-01T10:00:00.123Z") != nil && HomeScreen.parseDate("2026-11-01T10:00:00Z") != nil && HomeScreen.parseDate(nil) == nil)
    }

    // MARK: Handoff (D5)

    static func queue(by: String = "discair-android", ageHours: Double = 1, current: String = "s2", position: Int = 161_000) -> NavidromePlayQueue {
        let songs = [#"{"id":"s1","title":"One"}"#, #"{"id":"s2","title":"Ascension Day","artist":"Talk Talk","duration":360}"#]
            .map { try! JSONDecoder().decode(NavidromeSong.self, from: Data($0.utf8)) }
        return NavidromePlayQueue(songs: songs, currentID: current, positionMs: position, changed: Self.now.addingTimeInterval(-ageHours * 3600), changedBy: by)
    }

    @Test func aRecentQueueFromAnotherClientIsOffered() {
        let h = HomeScreen.handoff(queue: Self.queue(), now: Self.now, clientName: "discair", playingSongID: nil)
        #expect(h == .init(songID: "s2", title: "Ascension Day", artist: "Talk Talk", positionSeconds: 161, durationSeconds: 360))
        #expect(HomeScreen.handoffText(try! #require(h)) == "Ascension Day, Talk Talk · 2:41 of 6:00")
    }

    @Test func ownOldOrAlreadyPlayingQueuesAreNotOffered() {
        #expect(HomeScreen.handoff(queue: Self.queue(by: "Discair"), now: Self.now, clientName: "discair", playingSongID: nil) == nil)
        #expect(HomeScreen.handoff(queue: Self.queue(ageHours: 30), now: Self.now, clientName: "discair", playingSongID: nil) == nil)
        #expect(HomeScreen.handoff(queue: Self.queue(), now: Self.now, clientName: "discair", playingSongID: "s2") == nil)
        #expect(HomeScreen.handoff(queue: nil, now: Self.now, clientName: "discair", playingSongID: nil) == nil)
    }

    @Test func continuingStartsAtTheSongThePhoneWasOn() {
        let start = HomeScreen.handoffStart(queue: Self.queue())
        #expect(start.startAt == 1 && start.songs.count == 2)
        #expect(HomeScreen.handoffStart(queue: Self.queue(current: "gone")).startAt == 0)
    }

    // MARK: Artist popularity and the insight job

    private func job(_ state: String, pending: Double = 0, finished: Double? = nil, error: String? = nil, running: Bool = false, last: Bool = true) -> JobStatus {
        let run = JobRun(state: state, finishedAt: finished, progress: ["pending": pending], error: error)
        return JobStatus(status: run, lastGood: last ? run : nil, running: running)
    }

    @Test func popularityIsPausedWithTheArtistsLeftAndAContinueButton() {
        let r = HomeScreen.popularityRow(job("queued", pending: 340), now: Self.now)
        #expect(r.status == .paused && r.line == "340 artists left · runs only when you ask" && r.fix == .fillPopularity && r.fixTitle == "Continue")
    }

    @Test func popularityStatesDone_failed_neverRun_unread() {
        let done = HomeScreen.popularityRow(job("succeeded", finished: Self.now.timeIntervalSince1970 - 7200), now: Self.now)
        #expect(done.status == .done && done.line == "Figures are up to date · filled 2 hours ago" && done.fix == nil)
        let failed = HomeScreen.popularityRow(job("failed", error: "timeout", last: false), now: Self.now)
        #expect(failed.status == .notUpdating && failed.line.contains("timeout") && failed.fixTitle == "Try again")
        let never = HomeScreen.popularityRow(JobStatus(status: nil, lastGood: nil), now: Self.now)
        #expect(never.status == .paused && never.fixTitle == "Start")
        #expect(HomeScreen.popularityRow(nil, now: Self.now).status == .notLoaded)
        #expect(HomeScreen.popularityRow(job("running", pending: 120, running: true), now: Self.now).line == "Filling now · 120 artists left")
    }

    @Test func insightsJobGivesLastRefreshAndNextRun() {
        var i = input()
        let run = JobRun(state: "succeeded", finishedAt: Self.now.timeIntervalSince1970 - 7200)
        i.insightsJob = JobStatus(status: run, lastGood: run, minInterval: 21_600, retryAfter: 14_400)
        #expect(HomeScreen.activity(i)[0].line == "Refreshed 2 hours ago · next in 4 hours" && HomeScreen.activity(i)[0].status == .done)
        i.insightsJob = JobStatus(status: JobRun(state: "failed"), lastGood: run, retryAfter: 0)
        let failed = HomeScreen.activity(i)[0]
        #expect(failed.status == .notUpdating && failed.line.hasSuffix("next due now"))
        #expect(HomeScreen.duration(35 * 60) == "35 minutes" && HomeScreen.duration(60) == "1 minute" && HomeScreen.duration(3 * 3600) == "3 hours")
    }

    // MARK: New on the shelf, Waiting longest, next picks, summary line (H1 item 2)

    static func arrivedRow(_ id: String) -> HomeDashboard.ArrivalRow { .arrived(albumID: id, title: "T \(id)", artist: "A") }
    static func recent(_ id: String, addedDaysAgo: Int) -> NavidromeAlbum { HomeDashboardTests.album(id, addedDaysAgo: addedDaysAgo) }
    static func kind(_ t: HomeScreen.ShelfTile) -> String {
        switch t { case .job: "job"; case .arrived: "arrived"; case .radio: "radio"; case .added: "added" }
    }
    static func daysAgo(_ n: Int) -> Date { cal.date(byAdding: .day, value: -n, to: now)! }

    @Test func shelfTilesKeepArrivalOrderThenAddSoleRecentAlbumsUpToSix() {
        let arrivals: [HomeDashboard.ArrivalRow] = [
            .job(id: "j1", title: "J", artist: "A", stage: .downloading, failure: nil),
            Self.arrivedRow("a1"),
            .radio(playID: 7, title: "R", artist: "B", station: "FIP", heardAt: Date(timeIntervalSince1970: 0)),
        ]
        let recent = (1...8).map { (i: Int) -> NavidromeAlbum in Self.recent("r\(i)", addedDaysAgo: 400 + i) }
        let tiles = HomeScreen.shelfTiles(arrivals: arrivals, recentlyAdded: recent)
        #expect(tiles.count == 6)
        #expect(tiles.prefix(3).map(Self.kind) == ["job", "arrived", "radio"])
        #expect(tiles.suffix(3).map(Self.kind) == ["added", "added", "added"])
        if case let .added(albumID, _, _, _) = tiles.last { #expect(albumID == "r3") } else { Issue.record("last tile should be added") }
    }

    @Test func shelfTilesLeaveOutAlbumsAlreadyShownAsArrivals() {
        let recent = [Self.recent("a1", addedDaysAgo: 1), Self.recent("x", addedDaysAgo: 500)]
        let tiles = HomeScreen.shelfTiles(arrivals: [Self.arrivedRow("a1")], recentlyAdded: recent)
        #expect(tiles.count == 2)
        if case let .added(albumID, _, _, _) = tiles.last { #expect(albumID == "x") } else { Issue.record("expected the other album") }
    }

    @Test func shelfTilesSkipUndatedRecentAlbumsAndTakeArrivedDates() {
        let undated = HomeDashboardTests.album("u")
        let tiles = HomeScreen.shelfTiles(arrivals: [Self.arrivedRow("a1")], recentlyAdded: [undated], arrivedDates: ["a1": Self.daysAgo(1)])
        #expect(tiles.count == 1)
        if case let .arrived(_, _, _, addedAt) = tiles[0] { #expect(addedAt == Self.daysAgo(1)) } else { Issue.record("expected arrived") }
    }

    @Test func tileLabelIsTitleByArtistThenStatus() {
        #expect(HomeScreen.tileLabel(title: "Spirit", artist: "Talk Talk", status: "Arrived today") == "Spirit by Talk Talk, Arrived today")
        #expect(HomeScreen.tileLabel(title: "Spirit", artist: "Talk Talk", status: "") == "Spirit by Talk Talk")
    }

    @Test func shelfStatusWordsForEveryTileKind() {
        let now = Self.now
        let found = HomeScreen.shelfStatus(.job(id: "1", title: "T", artist: "A", stage: .found, failure: nil), now: now, calendar: Self.cal)
        #expect(found == .init(text: "Looking for a source", role: .warning))
        #expect(HomeScreen.shelfStatus(.job(id: "1", title: "T", artist: "A", stage: .downloading, failure: nil), now: now, calendar: Self.cal).text == "Downloading")
        #expect(HomeScreen.shelfStatus(.job(id: "1", title: "T", artist: "A", stage: .importing, failure: nil), now: now, calendar: Self.cal).text == "Importing")
        let failed = HomeScreen.shelfStatus(.job(id: "1", title: "T", artist: "A", stage: .found, failure: "No source"), now: now, calendar: Self.cal)
        #expect(failed == .init(text: "Failed · No source", role: .danger))
        #expect(HomeScreen.shelfStatus(.arrived(albumID: "a", title: "T", artist: "A", addedAt: now), now: now, calendar: Self.cal) == .init(text: "Arrived today", role: .accent))
        #expect(HomeScreen.shelfStatus(.arrived(albumID: "a", title: "T", artist: "A", addedAt: Self.daysAgo(1)), now: now, calendar: Self.cal).text == "Arrived yesterday")
        #expect(HomeScreen.shelfStatus(.arrived(albumID: "a", title: "T", artist: "A", addedAt: Self.daysAgo(2)), now: now, calendar: Self.cal).text == "Arrived 9 November")
        #expect(HomeScreen.shelfStatus(.arrived(albumID: "a", title: "T", artist: "A", addedAt: nil), now: now, calendar: Self.cal).text == "Arrived recently")
        #expect(HomeScreen.shelfStatus(.radio(playID: 1, title: "T", artist: "A", station: "FIP"), now: now, calendar: Self.cal) == .init(text: "Heard on FIP · Get", role: .accent))
        #expect(HomeScreen.shelfStatus(.added(albumID: "r", title: "T", artist: "A", addedAt: Self.daysAgo(2)), now: now, calendar: Self.cal) == .init(text: "Added 9 November", role: .secondary))
    }

    @Test func shelfSubtitleIsRecentlyAddedOnlyWhenEveryTileIsAnAddedAlbum() {
        let added = HomeScreen.ShelfTile.added(albumID: "r", title: "T", artist: "A", addedAt: Self.now)
        let arrived = HomeScreen.ShelfTile.arrived(albumID: "a", title: "T", artist: "A", addedAt: nil)
        #expect(HomeScreen.shelfSubtitle(tiles: [added, added]) == "recently added")
        #expect(HomeScreen.shelfSubtitle(tiles: []) == "recently added")
        #expect(HomeScreen.shelfSubtitle(tiles: [arrived, added]) == "arriving, just arrived and heard on the radio")
    }

    @Test func stageFractionsAreQuartersAndNoRingOnceInLibrary() {
        #expect(HomeScreen.stageFraction(.found) == 0.25)
        #expect(HomeScreen.stageFraction(.downloading) == 0.5)
        #expect(HomeScreen.stageFraction(.importing) == 0.75)
        #expect(HomeScreen.stageFraction(.inLibrary) == nil)
    }

    @Test func waitingCaptionsNameTheMonth() {
        let added = HomeScreen.parseDate("2023-03-15T00:00:00Z")!
        let played = HomeScreen.parseDate("2025-06-02T10:00:00Z")!
        #expect(HomeScreen.monthAndYear(added, calendar: Self.cal) == "March 2023")
        #expect(HomeScreen.waitingCaption(created: added, played: nil, neverPlayed: true, calendar: Self.cal) == "Since March 2023")
        #expect(HomeScreen.waitingCaption(created: added, played: played, neverPlayed: false, calendar: Self.cal) == "Last played June 2025")
        #expect(HomeScreen.waitingCaption(created: nil, played: nil, neverPlayed: true, calendar: Self.cal) == nil)
        #expect(HomeScreen.waitingSubtitle(allNeverPlayed: true) == "albums you own and have never played")
        #expect(HomeScreen.waitingSubtitle(allNeverPlayed: false) == "albums you have not played for the longest time")
    }

    @Test func nextPicksWrapRoundWithoutTheCurrentOne() {
        #expect(HomeScreen.nextPicks(index: 0, count: 1) == [])
        #expect(HomeScreen.nextPicks(index: 0, count: 2) == [1])
        #expect(HomeScreen.nextPicks(index: 1, count: 2) == [0])
        #expect(HomeScreen.nextPicks(index: 0, count: 8) == [1, 2, 3, 4, 5, 6])
        #expect(HomeScreen.nextPicks(index: 6, count: 8) == [7, 0, 1, 2, 3, 4])
        #expect(HomeScreen.nextPicks(index: 99, count: 3) == [0, 1])
    }

    @Test func summaryFiguresLeaveOutNilsAndUseSingularForOne() {
        let one = HomeDashboardTests.build([HomeDashboardTests.album("a", plays: 1, playedDaysAgo: 5)])
        #expect(HomeScreen.summaryFigures(one, now: Self.now) == [.init(text: "1 album", target: .library), .init(text: "0 never played", target: .neverPlayed)])
        #expect(HomeScreen.summaryFigures(.notLoaded, now: Self.now) == [])
    }

    @Test func summaryListensSayTheirWindowAndGoStaleWhenOld() {
        let fresh = HomeDashboard.build(.init(albums: [HomeDashboardTests.album("a")], listensByDay: HomeDashboardTests.days(Array(repeating: 1, count: 14)), now: Self.now, calendar: Self.cal))
        #expect(HomeScreen.summaryFigures(fresh, now: Self.now).contains(.init(text: "7 listens in 7 days", target: .history)))
        let stale = HomeDashboard.build(.init(albums: [HomeDashboardTests.album("a")], listensByDay: HomeDashboardTests.days(Array(repeating: 1, count: 14), endingDaysAgo: 4), now: Self.now, calendar: Self.cal))
        #expect(HomeScreen.summaryFigures(stale, now: Self.now).contains(.init(text: "7 listens in the 7 days to 7 November", target: .history)))
    }

    @Test func summaryListenSaysSingularForOne() {
        let one = HomeDashboard.build(.init(albums: [HomeDashboardTests.album("a")], listensByDay: HomeDashboardTests.days(Array(repeating: 0, count: 13) + [1]), now: Self.now, calendar: Self.cal))
        #expect(HomeScreen.summaryFigures(one, now: Self.now).contains(.init(text: "1 listen in 7 days", target: .history)))
    }

    @Test func summaryFiguresLeaveOutTheNilOnes() {
        // Undated albums and no listen series: no "added" figure and no listens figure, only the figures that have values.
        let d = HomeDashboardTests.build([HomeDashboardTests.album("a", plays: 0), HomeDashboardTests.album("b", plays: 0)])
        #expect(d.added == nil && d.listens == nil)
        #expect(HomeScreen.summaryFigures(d, now: Self.now) == [.init(text: "2 albums", target: .library), .init(text: "2 never played", target: .neverPlayed)])
    }
}
