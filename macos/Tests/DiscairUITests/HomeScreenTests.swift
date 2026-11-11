import Foundation
import Testing
import DiscairLibrarian
import DiscairNavidrome
@testable import DiscairUI

@Suite("Home screen states and wording") struct HomeScreenTests {
    static let now = HomeDashboardTests.now
    static var cal: Calendar { HomeDashboardTests.cal }

    static func card(_ kind: String, _ title: String, body: String = "Body.") -> InsightCard {
        try! JSONDecoder().decode(InsightCard.self, from: Data(#"{"kind":"\#(kind)","title":"\#(title)","body":"\#(body)","subject":{"key":"\#(kind):\#(title)"}}"#.utf8))
    }

    // MARK: Layout

    @Test func rowsStackBelow860() {
        #expect(HomeScreen.isStacked(contentWidth: 859))
        #expect(!HomeScreen.isStacked(contentWidth: 860))
        #expect(!HomeScreen.isStacked(contentWidth: 980))
    }

    // MARK: Briefing band

    @Test func addedLineNamesBothPeriods() {
        let line = HomeScreen.addedLine(.init(last: 12, before: 7))
        #expect(line.text == "12 added in the last 30 days · 7 in the 30 before")
        #expect(line.trend == .up)
        #expect(HomeScreen.addedLine(.init(last: 3, before: 9)).trend == .down)
        #expect(HomeScreen.addedLine(.init(last: 3, before: 3)).trend == .flat)
    }

    @Test func missingAddedDatesAreSaidNotZero() {
        let line = HomeScreen.addedLine(nil)
        #expect(line.trend == nil && line.text.contains("not available"))
    }

    @Test func neverPlayedChangeUsesTheBaselineDate() {
        let since = Self.cal.date(from: DateComponents(year: 2026, month: 10, day: 1))!
        #expect(HomeScreen.neverPlayedLine(.init(delta: -4, since: since), calendar: Self.cal) == .init(trend: .down, text: "4 fewer than on 1 October"))
        #expect(HomeScreen.neverPlayedLine(.init(delta: 6, since: since), calendar: Self.cal) == .init(trend: .up, text: "6 more than on 1 October"))
        #expect(HomeScreen.neverPlayedLine(.init(delta: 0, since: since), calendar: Self.cal) == .init(trend: .flat, text: "No change since 1 October"))
        #expect(HomeScreen.neverPlayedLine(nil).text == "First count today, no change yet")
    }

    @Test func listensTileIsNeverANumberUntilTheServerServesIt() {
        #expect(HomeScreen.listensTile(librarianReachable: true, listenBrainzConnected: false) == .needsListenBrainz)
        #expect(HomeScreen.listensTile(librarianReachable: true, listenBrainzConnected: true) == .notServedYet)
        #expect(HomeScreen.listensTile(librarianReachable: false, listenBrainzConnected: true) == .withoutLibrarian)
        #expect(HomeScreen.ListensTile.needsListenBrainz.offersConnect && !HomeScreen.ListensTile.notServedYet.offersConnect)
    }

    @Test func waitingTileWords() {
        #expect(HomeScreen.waitingTile(.init(picks: 7, unplayedArrivals: 2)) == .init(picks: 7, detail: "2 arrivals not played yet"))
        #expect(HomeScreen.waitingTile(.init(picks: 1, unplayedArrivals: 1)).detail == "1 arrival not played yet")
        #expect(HomeScreen.waitingTile(.init(picks: 0, unplayedArrivals: 0)) == .init(picks: 0, detail: "Nothing on its way"))
        #expect(HomeScreen.waitingTile(.init(picks: nil, unplayedArrivals: 3)).picks == nil)
        #expect(HomeScreen.waitingTile(nil).picks == nil)
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

    // MARK: Lenses

    @Test func lensRowsAreTheTopCardOfUpTo3EnabledLenses() {
        let inputs = [
            HomeScreen.LensInput(kind: "forgotten_gem", name: "Forgotten Gems", enabled: false, cards: [Self.card("forgotten_gem", "Off one")]),
            HomeScreen.LensInput(kind: "hidden_canon", name: "Hidden Canon", enabled: true, cards: [Self.card("hidden_canon", "A"), Self.card("hidden_canon", "A2")]),
            HomeScreen.LensInput(kind: "blind_spot", name: "Blind Spots", enabled: true, cards: []),
            HomeScreen.LensInput(kind: "series_completion", name: "Series", enabled: true, cards: [Self.card("series_completion", "B")]),
            HomeScreen.LensInput(kind: "anniversary", name: "Anniversaries", enabled: true, cards: [Self.card("anniversary", "C")]),
            HomeScreen.LensInput(kind: "extra", name: "Extra", enabled: true, cards: [Self.card("extra", "D")]),
        ]
        let s = HomeScreen.lenses(inputs)
        #expect(s.rows.map(\.card.title) == ["A", "B", "C"])
        #expect(s.countText == "5 of 6 on")
        #expect(s.off == ["Forgotten Gems"])
    }

    @Test func noLensOnIsItsOwnState() {
        let s = HomeScreen.lenses(["Forgotten Gems", "Series"].map { HomeScreen.LensInput(kind: $0, name: $0, enabled: false, cards: []) })
        #expect(s.enabledCount == 0 && s.rows.isEmpty && s.countText == "0 of 2 on" && s.off.count == 2)
    }

    // MARK: Shelf life

    @Test func ageIsYearsAndMonths() {
        let since = Self.cal.date(byAdding: .month, value: -(4 * 12 + 1), to: Self.now)!
        #expect(HomeScreen.ageText(since: since, now: Self.now, calendar: Self.cal) == "4 y 1 m")
        #expect(HomeScreen.ageText(since: Self.cal.date(byAdding: .month, value: -3, to: Self.now)!, now: Self.now, calendar: Self.cal) == "3 m")
        #expect(HomeScreen.ageText(since: Self.cal.date(byAdding: .year, value: -2, to: Self.now)!, now: Self.now, calendar: Self.cal) == "2 y")
        #expect(HomeScreen.ageText(since: Self.now, now: Self.now, calendar: Self.cal) == "< 1 m")
    }

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

    // MARK: Listens (D2)

    @Test func listensTileShowsTheFigureOnceServed() {
        let f = HomeDashboard.ListensFigure(last: 214, before: 181, asOf: Self.now)
        #expect(HomeScreen.listensTile(librarianReachable: true, listenBrainzConnected: true, figure: f) == .figure(f))
        #expect(HomeScreen.listensTile(librarianReachable: false, listenBrainzConnected: true, figure: f) == .withoutLibrarian)
        #expect(f.percent == 18 && f.delta == 33)
    }

    @Test func listensLineSaysTheDirectionInWordsAndWhenStale() {
        let up = HomeScreen.listensLine(.init(last: 214, before: 181, asOf: Self.now), now: Self.now, calendar: Self.cal)
        #expect(up == .init(trend: .up, text: "18% more than the 7 days before (181)"))
        #expect(HomeScreen.listensLine(.init(last: 90, before: 100, asOf: Self.now), now: Self.now, calendar: Self.cal).text == "10% fewer than the 7 days before (100)")
        #expect(HomeScreen.listensLine(.init(last: 5, before: 0, asOf: Self.now), now: Self.now, calendar: Self.cal).text == "No listens in the 7 days before")
        let stale = HomeScreen.listensLine(.init(last: 5, before: 5, asOf: Self.now.addingTimeInterval(-3 * 86_400)), now: Self.now, calendar: Self.cal)
        #expect(stale.text.hasSuffix("· as of 8 November") && stale.trend == .flat)
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
}
