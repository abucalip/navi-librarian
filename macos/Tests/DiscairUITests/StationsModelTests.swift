import DiscairCore
import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

/// A fake Librarian: serves what the test sets and records what was asked.
final class FakeStationsSource: StationsSource, @unchecked Sendable {
    private let lock = NSLock()
    private var _stations: [RadioStation] = []
    private var _now = RadioNowAll(byStation: [:])
    private var _failList: DiscairError?
    private var _failWrite: DiscairError?
    private var _calls: [String] = []
    var stations: [RadioStation] { get { lock.withLock { _stations } } set { lock.withLock { _stations = newValue } } }
    var now: RadioNowAll { get { lock.withLock { _now } } set { lock.withLock { _now = newValue } } }
    var failList: DiscairError? { get { lock.withLock { _failList } } set { lock.withLock { _failList = newValue } } }
    var failWrite: DiscairError? { get { lock.withLock { _failWrite } } set { lock.withLock { _failWrite = newValue } } }
    var calls: [String] { lock.withLock { _calls } }
    private func note(_ s: String) { lock.withLock { _calls.append(s) } }

    func radioStations() async throws -> [RadioStation] { note("stations"); if let e = failList { throw e }; return stations }
    func radioNowAll() async throws -> RadioNowAll { note("now"); return now }
    func setRadioFavourite(station: String, on: Bool) async throws {
        note("favourite \(station) \(on)")
        if let e = failWrite { throw e }
        stations = stations.map { $0.id == station ? $0.replacing(favourite: on) : $0 }
    }
    func setRadioTags(station: String, tags: [String]) async throws {
        note("tags \(station) \(tags.joined(separator: ","))")
        if let e = failWrite { throw e }
        stations = stations.map { $0.id == station ? $0.replacing(tags: tags) : $0 }
    }
}

/// A clock the test moves by hand; `pause` returns at once so the poll loop never really waits.
final class TestClock: @unchecked Sendable {
    private let lock = NSLock()
    private var t = Date(timeIntervalSince1970: 1_800_000_000)
    var now: Date { lock.withLock { t } }
    func advance(_ s: TimeInterval) { lock.withLock { t = t.addingTimeInterval(s) } }
}

@MainActor
@Suite("Stations model") struct StationsModelTests {
    func station(_ id: String, fav: Bool = false, tags: [String] = [], proxied: Bool = true) -> RadioStation {
        RadioStation(id: id, name: "Station \(id)", proxied: proxied, playableURL: "https://relay.example/\(id)", favourite: fav, tags: tags)
    }
    func make(_ list: [RadioStation]) -> (StationsModel, FakeStationsSource, TestClock) {
        let source = FakeStationsSource(); source.stations = list
        let clock = TestClock()
        let model = StationsModel(clock: { clock.now }, pause: { _ in try? await Task.sleep(for: .seconds(3600)) })
        model.configure(source: source)
        return (model, source, clock)
    }

    @Test func reloadFillsTheListInServerOrder() async {
        let (m, _, _) = make([station("b", fav: true), station("a")])
        #expect(m.phase == .idle)
        await m.reload()
        #expect(m.phase == .loaded && m.stations.map(\.id) == ["b", "a"] && !m.isEmpty)
    }
    @Test func anEmptyListIsTheEmptyState() async {
        let (m, _, _) = make([])
        await m.reload()
        #expect(m.isEmpty && m.phase == .loaded)
    }
    @Test func anUnreachableServerIsAnErrorWithRetryAndKeepsTheList() async {
        let (m, s, _) = make([station("a")])
        await m.reload()
        s.failList = .serverUnreachable
        await m.reload()
        #expect(m.phase == .failed(message: "The server did not answer.", retryable: true))
        #expect(m.stations.map(\.id) == ["a"])
        s.failList = nil
        await m.reload()
        #expect(m.phase == .loaded)
    }
    @Test func aFirstFailureShowsNoListAndNoEmptyState() async {
        let (m, s, _) = make([])
        s.failList = .noNetwork
        await m.reload()
        #expect(m.stations.isEmpty && !m.isEmpty && m.phase == .failed(message: "No network connection.", retryable: true))
    }
    @Test func theTagFilterNarrowsTheListAndFallsBackWhenTheTagGoes() async {
        let (m, s, _) = make([station("1", tags: ["Jazz"]), station("2", tags: ["Rock"])])
        await m.reload()
        m.select(tag: "jazz")
        #expect(m.visibleStations.map(\.id) == ["1"])
        m.select(tag: "Nope")
        #expect(m.tagFilter == nil && m.visibleStations.count == 2)
        m.select(tag: "Rock")
        s.stations = [station("1", tags: ["Jazz"])]
        await m.reload()
        #expect(m.tagFilter == nil)
    }

    // favourite and tags
    @Test func aFavouriteShowsAtOnceIsSentAndThenTheListReloads() async {
        let (m, s, _) = make([station("1"), station("2")])
        await m.reload()
        await m.setFavourite(m.stations[1], on: true)
        #expect(s.calls == ["stations", "favourite 2 true", "stations"])
        #expect(m.stations.first { $0.id == "2" }?.favourite == true && m.actionNote == nil)
    }
    @Test func aRefusedFavouriteGoesBackAndShowsTheServersSentence() async {
        let (m, s, _) = make([station("1")])
        await m.reload()
        s.failWrite = .server(status: 409, message: "Navidrome refused the change.")
        await m.setFavourite(m.stations[0], on: true)
        #expect(m.stations[0].favourite == false)
        #expect(m.actionNote == "Navidrome refused the change.")
        #expect(s.calls == ["stations", "favourite 1 true"])    // no reload after a refusal
    }
    @Test func tagsAreValidatedBeforeAnythingIsSent() async {
        let (m, s, _) = make([station("1", tags: ["a"])])
        await m.reload()
        await m.setTags(m.stations[0], to: ["a", "A"])
        #expect(m.actionNote == StationRules.TagProblem.duplicate.message)
        #expect(s.calls == ["stations"] && m.stations[0].tags == ["a"])
    }
    @Test func tagsAreTrimmedSentAndReloaded() async {
        let (m, s, _) = make([station("1", tags: ["a"])])
        await m.reload()
        await m.setTags(m.stations[0], to: [" a ", "b "])
        #expect(s.calls == ["stations", "tags 1 a,b", "stations"])
        #expect(m.stations[0].tags == ["a", "b"] && m.actionNote == nil)
    }
    @Test func aRefusedTagChangePutsTheOldTagsBack() async {
        let (m, s, _) = make([station("1", tags: ["a"])])
        await m.reload()
        s.failWrite = .serverUnreachable
        await m.setTags(m.stations[0], to: ["a", "b"])
        #expect(m.stations[0].tags == ["a"] && m.actionNote == "The server did not answer.")
    }
    @Test func removingTheChosenTagsLastStationDropsTheFilter() async {
        let (m, _, _) = make([station("1", tags: ["Jazz"]), station("2")])
        await m.reload()
        m.select(tag: "Jazz")
        await m.setTags(m.stations[0], to: [])
        #expect(m.tagFilter == nil)
    }
    @Test func sendingTheSameValueAgainSendsNothing() async {
        let (m, s, _) = make([station("1", fav: true, tags: ["a"])])
        await m.reload()
        await m.setFavourite(m.stations[0], on: true)
        await m.setTags(m.stations[0], to: ["a"])
        #expect(s.calls == ["stations"])
    }

    // polling
    @Test func nothingIsAskedWhileThePageIsNotVisible() async {
        let (m, s, _) = make([station("1")])
        await m.tick()
        #expect(s.calls.isEmpty)
    }
    @Test func aTickAsksForTheListOnlyOnceAMinuteAndTitlesEveryTime() async {
        let (m, s, c) = make([station("1")])
        m.setPageVisible(true)
        await m.tick()
        #expect(s.calls.filter { $0 == "stations" }.count == 1 && s.calls.filter { $0 == "now" }.count == 1)
        c.advance(15); await m.tick()
        c.advance(15); await m.tick()
        #expect(s.calls.filter { $0 == "stations" }.count == 1 && s.calls.filter { $0 == "now" }.count == 3)
        c.advance(30); await m.tick()
        #expect(s.calls.filter { $0 == "stations" }.count == 2)
        m.setPageVisible(false)
    }
    @Test func liveTitlesFeedTheStatusSentence() async {
        let (m, s, _) = make([station("1")])
        s.now = RadioNowAll(byStation: ["1": RadioNow(state: .ok, artist: "Can", title: "Halleluwah")])
        await m.reload(); await m.refreshNow()
        #expect(m.status(for: m.stations[0]) == .init(text: "Can – Halleluwah", isLiveTitle: true))
    }
    @Test func hidingThePageStopsThePollAndLeavesTheListAlone() async {
        let (m, s, _) = make([station("1")])
        m.setPageVisible(true)
        await m.tick()
        m.setPageVisible(false)
        let before = s.calls.count
        await m.tick()
        #expect(s.calls.count == before && m.stations.count == 1 && !m.pageVisible)
    }
    @Test func aStationNeverPutsItsAddressIntoAMessage() async {
        let (m, s, _) = make([station("1")])
        await m.reload()
        s.failWrite = .server(status: 500, message: nil)
        await m.setFavourite(m.stations[0], on: true)
        #expect(m.actionNote == "The server reported an error (500).")
        #expect(!"\(m.stations[0])".contains("relay.example"))
    }

    @Test func aNavigationToTheRadioPageTurnsPollingOnAndLeavingTurnsItOff() {
        let state = AppState()
        #expect(!state.stations.pageVisible)
        state.screen = .stations
        #expect(state.stations.pageVisible && AppState.title(of: .stations) == "Radio")
        state.screen = .home
        #expect(!state.stations.pageVisible)
    }
}
