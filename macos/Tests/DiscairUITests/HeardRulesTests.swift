import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

/// The Heard list's rules and the Download states of a heard song (docs/RADIO_PLAYBACK_PROPOSAL.md S2-3 items 3 to 5).
@MainActor
@Suite("Heard rules") struct HeardRulesTests {
    static var cal: Calendar { var c = Calendar(identifier: .gregorian); c.timeZone = TimeZone(identifier: "UTC")!; return c }
    /// 2026-11-14 22:00 UTC.
    static let now = Date(timeIntervalSince1970: 1_794_693_600)

    static func play(_ id: Int, _ title: String = "Song", station: String = "FIP", artist: String? = "Artist", hoursAgo: Double = 1,
                     grabbed: Bool = false, owned: Bool = false) -> RadioPlay {
        RadioPlay(id: id, stationName: station, artist: artist, title: title, heardAt: now.timeIntervalSince1970 - hoursAgo * 3600, grabbed: grabbed, inLibrary: owned)
    }

    // MARK: Heard on this station tonight (Now Playing)

    @Test func tonightIsThisStationsLast12HoursNewestFirst() {
        let plays = [Self.play(1, hoursAgo: 13), Self.play(2, hoursAgo: 11.9), Self.play(3, hoursAgo: 0.5), Self.play(4, station: "KEXP", hoursAgo: 1)]
        #expect(HeardRules.tonight(on: "FIP", in: plays, at: Self.now).map(\.id) == [3, 2])
    }

    @Test func tonightHasAtMostEightRows() {
        let plays = (1...12).map { Self.play($0, hoursAgo: Double($0) * 0.5) }
        let rows = HeardRules.tonight(on: "FIP", in: plays, at: Self.now)
        #expect(rows.count == 8 && rows.first?.id == 1 && rows.last?.id == 8)
    }

    @Test func theSongOnNowIsLeftOutOfItsOwnList() {
        let plays = [Self.play(1, hoursAgo: 0.1), Self.play(2, hoursAgo: 1)]
        #expect(HeardRules.tonight(on: "FIP", in: plays, at: Self.now, excluding: 1).map(\.id) == [2])
        #expect(HeardRules.latest(on: "FIP", in: plays, excluding: 1).map(\.id) == [2])
    }

    @Test func theStationMatchIgnoresCaseAndSpaces() {
        #expect(HeardRules.isOn(Self.play(1, station: " fip "), station: "FIP"))
        #expect(!HeardRules.isOn(Self.play(1, station: "FIP 2"), station: "FIP"))
    }

    // MARK: Heard on the On Air panel

    @Test func thePanelListsTheLastThreePlaysOfTheStation() {
        let plays = (1...6).map { Self.play($0, hoursAgo: Double($0)) } + [Self.play(9, station: "KEXP", hoursAgo: 0.1)]
        #expect(HeardRules.latest(on: "FIP", in: plays).map(\.id) == [1, 2, 3])
    }

    @Test func thePanelIgnoresHowOldThePlaysAre() {
        #expect(HeardRules.latest(on: "FIP", in: [Self.play(1, hoursAgo: 90)]).map(\.id) == [1])
    }

    // MARK: Heard tab

    @Test func theTabGroupsEveryPlayByCalendarDayNewestFirst() {
        // 22:00 now: 21:00 and 03:00 are today, 23:30 the evening before is yesterday, three days back has a date.
        let plays = [Self.play(1, hoursAgo: 22.5), Self.play(2, hoursAgo: 1), Self.play(3, hoursAgo: 19), Self.play(4, hoursAgo: 72)]
        let days = HeardRules.grouped(plays, at: Self.now, calendar: Self.cal)
        #expect(days.map(\.title) == ["Today", "Yesterday", "Wednesday 11 November"])
        #expect(days[0].plays.map(\.id) == [2, 3] && days[1].plays.map(\.id) == [1] && days[2].plays.map(\.id) == [4])
    }

    @Test func anEmptyListHasNoDaysAndTheEmptySentenceIsFixed() {
        #expect(HeardRules.grouped([], at: Self.now, calendar: Self.cal).isEmpty)
        #expect(HeardRules.emptyText == "Songs you hear for 30 seconds on a relayed station are listed here.")
    }

    @Test func aRowReadsArtistStationAndTime() {
        let p = Self.play(1, "Pyramid Song", station: "KEXP", artist: "Radiohead", hoursAgo: 1)
        #expect(HeardRules.detail(p, showStation: true, calendar: Self.cal) == "Radiohead · KEXP · 21:00")
        #expect(HeardRules.detail(p, showStation: false, calendar: Self.cal) == "Radiohead · 21:00")
        #expect(HeardRules.detail(Self.play(2, artist: nil, hoursAgo: 2), showStation: false, calendar: Self.cal) == "20:00")
        #expect(HeardRules.spoken(p, showStation: false, calendar: Self.cal) == "Pyramid Song, Radiohead · 21:00")
    }

    // MARK: Download on a heard song (S2.7)

    @Test func everyStateOfAHeardSong() {
        #expect(DownloadState.of(play: Self.play(1)) == .ready)
        #expect(DownloadState.of(play: Self.play(1, grabbed: true)) == .done)
        #expect(DownloadState.of(play: Self.play(1, owned: true)) == .owned)
        #expect(DownloadState.of(play: Self.play(1, grabbed: true, owned: true)) == .owned)       // Owned wins
        #expect(DownloadState.of(play: Self.play(1), attempt: .init(working: true)) == .working)
        #expect(DownloadState.of(play: Self.play(1), attempt: .init(failed: true)) == .failed)
        #expect(DownloadState.of(play: Self.play(1), attempt: .init(requested: true)) == .done)
    }

    @Test func aGetShowsDownloadingThenDownloadedWithTheServersSentenceKept() async {
        let downloads = RadioDownloads()
        let source = FakeGetSource()
        downloads.configure(source: source)
        var reloaded = 0
        downloads.onSuccess = { reloaded += 1 }
        await downloads.get(playID: 5)
        #expect(source.sent == [5] && reloaded == 1)
        #expect(downloads.attempt(for: 5).requested)
        #expect(downloads.sentence(for: 5) == "Requested “Moon Safari”.")
        await downloads.get(playID: 5)                       // a second click on a song already asked for sends nothing
        #expect(source.sent == [5])
    }

    @Test func aRefusalGivesTryAgainAndTheServersSentence() async {
        let downloads = RadioDownloads()
        let source = FakeGetSource()
        source.result = .make(ok: false, message: "No exact match on MusicBrainz")
        downloads.configure(source: source)
        await downloads.get(playID: 6)
        #expect(downloads.attempt(for: 6).failed && downloads.sentence(for: 6) == "No exact match on MusicBrainz")
        source.result = .make(ok: true)
        await downloads.get(playID: 6)                       // Try again sends again
        #expect(source.sent == [6, 6] && downloads.attempt(for: 6).requested)
    }

    @Test func theAppReadsAHeardSongsStateFromTheListThenFromTheClicks() async {
        let state = AppState(themeID: .cupertino)
        state.showHomeFeeds(radio: [Self.play(1), Self.play(2, grabbed: true), Self.play(3, owned: true)])
        #expect(state.downloadState(playID: 1) == .ready && state.downloadState(playID: 2) == .done && state.downloadState(playID: 3) == .owned)
        #expect(state.downloadState(playID: 99) == .waiting || state.downloadState(playID: 99) == .ready)   // no list entry: the request alone decides
        let source = FakeGetSource()
        state.radioDownloads.configure(source: source)
        await state.radioDownloads.get(playID: 1)
        #expect(state.downloadState(playID: 1) == .done)
    }
}
