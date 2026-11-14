import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

/// The three cases of the Home radio card (E7, S2-3 item 6).
@Suite("Home radio card") struct HomeRadioCardTests {
    var cal: Calendar { var c = Calendar(identifier: .gregorian); c.timeZone = TimeZone(identifier: "UTC")!; return c }
    func at(_ day: Int, _ h: Int = 12, _ m: Int = 0) -> Date { cal.date(from: DateComponents(year: 2026, month: 11, day: day, hour: h, minute: m))! }
    func station(_ id: String, played: Date? = nil) -> RadioStation {
        RadioStation(id: id, name: "S\(id)", proxied: true, playableURL: "https://relay.example/\(id)", lastPlayedAt: played?.timeIntervalSince1970)
    }
    func live(_ id: String, phase: LiveSession.Phase = .playing) -> LiveSession {
        LiveSession(stationID: id, name: "S\(id)", logoPath: "", startedAt: at(14), phase: phase)
    }

    @Test func aPlayingStationShowsOnAirWithItsSong() {
        let line = LiveSongLine.of(RadioNow(state: .ok, artist: "Talk Talk", title: "Life's What You Make It"))
        let card = HomeRadioCard.of(live: live("1"), line: line, lastStationID: "2", stations: [station("1"), station("2")], at: at(14), calendar: cal)
        #expect(card == .onAir(stationID: "1", name: "S1", line: line))
    }

    @Test func aPlayingStationWithoutASongShowsTheStateSentence() {
        let line = LiveSongLine.of(RadioNow(state: .noMetadata), phase: .playing)
        guard case .onAir(_, _, let shown)? = HomeRadioCard.of(live: live("1"), line: line, lastStationID: nil, stations: [], at: at(14), calendar: cal)
        else { Issue.record("expected the on-air card"); return }
        #expect(!shown.hasSong && shown.sentence == "This station sends no song titles.")
    }

    @Test func aPlayingStationNeedsNoListEntry() {
        // The card shows while a station plays even before the list is read.
        #expect(HomeRadioCard.of(live: live("9"), line: .waiting, lastStationID: nil, stations: [], at: at(14), calendar: cal) != nil)
    }

    @Test func nothingPlayingAndALastStationInTheListOffersResume() {
        let list = [station("1"), station("2", played: at(14, 9, 5))]
        #expect(HomeRadioCard.of(live: nil, line: .waiting, lastStationID: "2", stations: list, at: at(14, 22), calendar: cal)
                == .resume(station: list[1], lastPlayed: "Last played today, 09:05"))
    }

    @Test func noLastStationOrOneNoLongerInTheListMeansNoCard() {
        #expect(HomeRadioCard.of(live: nil, line: .waiting, lastStationID: nil, stations: [station("1")], at: at(14), calendar: cal) == nil)
        #expect(HomeRadioCard.of(live: nil, line: .waiting, lastStationID: "7", stations: [station("1")], at: at(14), calendar: cal) == nil)
        #expect(HomeRadioCard.of(live: nil, line: .waiting, lastStationID: "1", stations: [], at: at(14), calendar: cal) == nil)
    }

    @Test func lastPlayedReadsLikeTheListWithLastInFront() {
        #expect(HomeRadioCard.lastPlayedText(at(13, 20).timeIntervalSince1970, at: at(14), calendar: cal) == "Last played yesterday")
        #expect(HomeRadioCard.lastPlayedText(at(11, 20).timeIntervalSince1970, at: at(14), calendar: cal) == "Last played 3 days ago")
        #expect(HomeRadioCard.lastPlayedText(nil, at: at(14), calendar: cal) == "Never played")
    }
}
