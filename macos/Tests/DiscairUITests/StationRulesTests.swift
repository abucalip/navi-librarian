import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

@Suite("Station rules") struct StationRulesTests {
    var cal: Calendar { var c = Calendar(identifier: .gregorian); c.timeZone = TimeZone(identifier: "UTC")!; return c }
    func at(_ day: Int, _ h: Int = 12, _ m: Int = 0) -> Date { cal.date(from: DateComponents(year: 2026, month: 11, day: day, hour: h, minute: m))! }
    func station(_ id: String = "1", proxied: Bool = true, tags: [String] = [], played: Date? = nil) -> RadioStation {
        RadioStation(id: id, name: "S\(id)", proxied: proxied, playableURL: "https://relay.example/s", tags: tags, lastPlayedAt: played?.timeIntervalSince1970)
    }
    func status(_ s: RadioStation, _ now: RadioNow?, on: Date? = nil) -> StationRules.Status {
        StationRules.status(for: s, now: now, at: on ?? at(14), calendar: cal)
    }

    // MARK: status sentence
    @Test func aSongBeingHeardIsTheLiveTitleInTheAccent() {
        let s = status(station(), RadioNow(state: .ok, artist: "Can", title: "Vitamin C"))
        #expect(s == .init(text: "Can – Vitamin C", isLiveTitle: true))
        #expect(status(station(), RadioNow(state: .ok, rawTitle: "Jingle")).text == "Jingle")
    }
    @Test func aStationThatIsNotRelayedHasNoTitles() {
        #expect(status(station(proxied: false), RadioNow(state: .ok, title: "x")).text == "Not relayed · no song titles")
    }
    @Test func noTitlesUnreachableAndUnknownWordsAreHonest() {
        #expect(status(station(), RadioNow(state: .noMetadata)).text == "Sends no song titles")
        #expect(status(station(), RadioNow(state: .unparsed)).text == "Sends no song titles")
        #expect(status(station(), RadioNow(state: .unknown)).text == "Sends no song titles")
        #expect(status(station(), RadioNow(state: .ok)).text == "Sends no song titles")
        #expect(status(station(), RadioNow(state: .unavailable)).text == "Station unreachable")
        #expect(!status(station(), RadioNow(state: .unavailable)).isLiveTitle)
    }
    @Test func aStationNobodyListensToSaysWhenItWasLastPlayed() {
        #expect(status(station(played: at(14, 18, 40)), nil).text == "Played today, 18:40")
        #expect(status(station(played: at(14, 7, 5)), RadioNow(state: .idle)).text == "Played today, 07:05")
        #expect(status(station(played: at(13, 23, 59)), nil).text == "Played yesterday")
        #expect(status(station(played: at(11, 1, 0)), nil).text == "Played 3 days ago")
        #expect(status(station(), nil).text == "Never played")
    }
    @Test func calendarDaysCountNotTwentyFourHourSpans() {
        // 23:50 yesterday is "yesterday" at 00:10 today, only 20 minutes later.
        #expect(StationRules.playedText(at(13, 23, 50).timeIntervalSince1970, at: at(14, 0, 10), calendar: cal) == "Played yesterday")
        // A clock a little ahead of the server's still reads as today.
        #expect(StationRules.playedText(at(14, 13, 0).timeIntervalSince1970, at: at(14, 12, 0), calendar: cal) == "Played today, 13:00")
    }

    // MARK: chips
    @Test func chipsAreAllThenEachTagOnceMostUsedFirst() {
        let list = [station("1", tags: ["Jazz", "News"]), station("2", tags: ["jazz", "Rock"]), station("3", tags: ["JAZZ", "rock", "News"]), station("4", tags: ["Ambient", "Ambient"])]
        let chips = StationRules.chips(for: list)
        #expect(chips.map(\.label) == ["All", "Jazz", "News", "Rock", "Ambient"])
        #expect(chips.first == .all && chips.first?.tag == nil)
    }
    @Test func blankTagsMakeNoChipAndNoStationsMakesOnlyAll() {
        #expect(StationRules.chips(for: [station(tags: ["  ", ""])]).map(\.label) == ["All"])
        #expect(StationRules.chips(for: []).map(\.label) == ["All"])
    }
    @Test func aChipFiltersWithoutCaseAndKeepsServerOrder() {
        let list = [station("1", tags: ["Jazz"]), station("2", tags: ["Rock"]), station("3", tags: ["jazz"])]
        #expect(StationRules.filter(list, tag: "JAZZ").map(\.id) == ["1", "3"])
        #expect(StationRules.filter(list, tag: nil).map(\.id) == ["1", "2", "3"])
    }

    // MARK: Download state
    @Test func ownedWinsOverEverything() {
        let now = RadioNow(state: .ok, playID: 4, inLibrary: true)
        #expect(DownloadState.of(now: now, attempt: .init(requested: true, working: true, failed: true)) == .owned)
        #expect(DownloadState.of(now: RadioNow(state: .noMetadata, inLibrary: true)) == .owned)
    }
    @Test func theThirtySecondRuleDecidesWaitingOrReady() {
        #expect(DownloadState.of(now: RadioNow(state: .ok)) == .waiting)
        #expect(DownloadState.of(now: RadioNow(state: .ok, playID: 9)) == .ready)
    }
    @Test func theRequestMovesTheStateThroughWorkingDoneAndFailed() {
        let now = RadioNow(state: .ok, playID: 9)
        #expect(DownloadState.of(now: now, attempt: .init(working: true)) == .working)
        #expect(DownloadState.of(now: now, attempt: .init(requested: true)) == .done)
        #expect(DownloadState.of(now: now, attempt: .init(failed: true)) == .failed)
    }
    @Test func statesWithoutASongHaveNoButton() {
        for state in [RadioNowState.noMetadata, .unparsed, .notProxied, .unavailable, .idle, .unknown] {
            #expect(DownloadState.of(now: RadioNow(state: state, playID: 9)) == .none)
        }
    }
    @Test func aHeardSongReadsGrabbedAndInLibraryFromTheServer() throws {
        func play(grabbed: Bool, owned: Bool) throws -> RadioPlay {
            try JSONDecoder().decode(RadioPlay.self, from: Data(#"{"id":7,"title":"T","heard_at":1,"grabbed":\#(grabbed),"in_library":\#(owned)}"#.utf8))
        }
        let fresh = try play(grabbed: false, owned: false), grabbed = try play(grabbed: true, owned: false), owned = try play(grabbed: true, owned: true)
        #expect(DownloadState.of(play: fresh) == .ready)
        #expect(DownloadState.of(play: grabbed) == .done)
        #expect(DownloadState.of(play: owned) == .owned)
        #expect(DownloadState.of(play: fresh, attempt: .init(working: true)) == .working)
    }
    @Test func wordsAndEnabledMatchTheTable() {
        #expect(DownloadState.waiting.label(listeningSeconds: 18) == "Listening · 18 s")
        #expect(DownloadState.waiting.label() == "Listening")
        #expect(DownloadState.ready.label() == "Download")
        #expect(DownloadState.working.label() == "Downloading…")
        #expect(DownloadState.done.label() == "✓ Downloaded")
        #expect(DownloadState.owned.label() == "✓ Owned")
        #expect(DownloadState.failed.label() == "Try again")
        #expect(DownloadState.none.label() == nil)
        #expect([DownloadState.ready, .failed].allSatisfy { $0.isEnabled })
        #expect([DownloadState.waiting, .working, .done, .owned, .none].allSatisfy { !$0.isEnabled })
    }
    @Test func listeningSecondsAreCappedAtThirty() {
        let t = at(14)
        #expect(DownloadState.listeningSeconds(since: t, now: t.addingTimeInterval(18.9)) == 18)
        #expect(DownloadState.listeningSeconds(since: t, now: t.addingTimeInterval(95)) == 30)
        #expect(DownloadState.listeningSeconds(since: t, now: t.addingTimeInterval(-3)) == 0)
    }

    // MARK: tag validation
    @Test func aTagIsTrimmed() {
        #expect(StationRules.check(tag: "  Jazz \n", among: []) == .ok("Jazz"))
    }
    @Test func blankDuplicateAndTooLongAreRefused() {
        #expect(StationRules.check(tag: "   ", among: []) == .rejected(.blank))
        #expect(StationRules.check(tag: "JAZZ", among: ["jazz"]) == .rejected(.duplicate))
        #expect(StationRules.check(tag: String(repeating: "a", count: 24), among: []) == .ok(String(repeating: "a", count: 24)))
        #expect(StationRules.check(tag: String(repeating: "a", count: 25), among: []) == .rejected(.tooLong))
    }
    @Test func anEleventhTagIsRefused() {
        let ten = (1...10).map { "t\($0)" }
        #expect(StationRules.check(tag: "t11", among: ten) == .rejected(.tooMany))
        #expect(StationRules.check(tag: "T9", among: Array(ten.prefix(9))) == .rejected(.duplicate))
        #expect(StationRules.check(tag: "new", among: Array(ten.prefix(9))) == .ok("new"))
    }
    @Test func aWholeListIsValidatedAndTheFirstProblemWins() {
        #expect(StationRules.validated(tags: [" a ", "b"]) == .success(["a", "b"]))
        #expect(StationRules.validated(tags: ["a", "A"]) == .failure(.duplicate))
        #expect(StationRules.validated(tags: ["a", " "]) == .failure(.blank))
        #expect(StationRules.validated(tags: (1...11).map { "t\($0)" }) == .failure(.tooMany))
        #expect(StationRules.validated(tags: []) == .success([]))
        #expect(!StationRules.TagProblem.tooMany.message.isEmpty)
    }

    // MARK: Edit Tags draft
    @Test func returnAddsATrimmedTagAndClearsTheField() {
        var d = TagDraft(tags: ["Jazz"])
        d.typed = "  Late night "
        d.commitTyped()
        #expect(d.tags == ["Jazz", "Late night"] && d.typed.isEmpty && d.problem == nil)
    }
    @Test func aRejectedTagStaysTypedWithItsSentence() {
        var d = TagDraft(tags: ["Jazz"])
        d.typed = "jazz"; d.commitTyped()
        #expect(d.tags == ["Jazz"] && d.typed == "jazz" && d.problem == .duplicate)
        d.typed = "   "; d.commitTyped()
        #expect(d.problem == .blank)
        d.typed = String(repeating: "x", count: 25); d.commitTyped()
        #expect(d.problem == .tooLong)
    }
    @Test func theListStopsAtTenAndRemovingMakesRoom() {
        var d = TagDraft(tags: (1...10).map { "t\($0)" })
        #expect(d.isFull && d.countLine == "10 of 10 tags")
        d.typed = "extra"; d.commitTyped()
        #expect(d.problem == .tooMany && d.tags.count == 10)
        d.remove("t3")
        #expect(d.problem == nil && !d.isFull)
        d.commitTyped()
        #expect(d.tags.last == "extra")
    }
    @Test func saveTakesAStillTypedTagAndRefusesABadOne() {
        var d = TagDraft(tags: ["Jazz"])
        d.typed = "Live"
        #expect(d.result() == ["Jazz", "Live"])
        var bad = TagDraft(tags: ["Jazz"])
        bad.typed = "JAZZ"
        #expect(bad.result() == nil && bad.problem == .duplicate)
    }
    @Test func theDraftKnowsWhenItChanged() {
        var d = TagDraft(tags: ["Jazz"])
        #expect(!d.isChanged)
        d.remove("Jazz")
        #expect(d.isChanged && d.result() == [])
    }

    // MARK: station shortcuts (S2-4 item 4)
    func favs(_ n: Int, extra: [RadioStation] = []) -> [RadioStation] {
        (1...n).map { RadioStation(id: "f\($0)", name: "Fav \($0)", playableURL: "https://relay.example/f\($0)", favourite: true) } + extra
    }
    @Test func onlyTheFirstNineFavouritesGetAKey() {
        #expect(StationRules.shortcutStations(favs(12)).map(\.id) == (1...9).map { "f\($0)" })
        #expect(StationRules.shortcutStations(favs(3)).count == 3)
        #expect(StationRules.shortcutStations([]).isEmpty)
    }
    @Test func aStationThatIsNotAFavouriteNeverGetsAKey() {
        let plain = RadioStation(id: "p", name: "Plain", playableURL: "https://relay.example/p")
        let list = [plain] + favs(2)                      // the server's order is kept; the plain one is skipped
        #expect(StationRules.shortcutStations(list).map(\.id) == ["f1", "f2"])
    }
    @Test func aKeyPicksTheFavouriteWithThatNumber() {
        let list = favs(3)
        #expect(StationRules.shortcutTarget(number: 1, in: list, live: nil)?.id == "f1")
        #expect(StationRules.shortcutTarget(number: 3, in: list, live: nil)?.id == "f3")
        #expect(StationRules.shortcutTarget(number: 4, in: list, live: nil) == nil)
        #expect(StationRules.shortcutTarget(number: 0, in: list, live: nil) == nil)
        #expect(StationRules.shortcutTarget(number: 10, in: favs(12), live: nil) == nil)
    }
    @Test func theStationThatIsPlayingIsLeftAloneUnlessItGaveUp() {
        let list = favs(2)
        var live = LiveSession(stationID: "f1", name: "Fav 1", logoPath: "", startedAt: at(14), phase: .playing)
        #expect(StationRules.shortcutTarget(number: 1, in: list, live: live) == nil)
        #expect(StationRules.shortcutTarget(number: 2, in: list, live: live)?.id == "f2")
        live.phase = .reconnecting
        #expect(StationRules.shortcutTarget(number: 1, in: list, live: live) == nil)
        live.phase = .unreachable
        #expect(StationRules.shortcutTarget(number: 1, in: list, live: live)?.id == "f1")
    }
}
