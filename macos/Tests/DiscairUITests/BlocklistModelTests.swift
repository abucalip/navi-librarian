import DiscairCore
import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

final class FakeBlocklistSource: BlocklistSource, @unchecked Sendable {
    private let lock = NSLock()
    private var _list = Blocklist(genres: ["Shoegaze"], hiddenArtists: ["Ride"], leans: [ArtistLean(artist: "Lush", lean: .more)])
    private var _fail: DiscairError?
    private var _calls: [String] = []
    var list: Blocklist { get { lock.withLock { _list } } set { lock.withLock { _list = newValue } } }
    var fail: DiscairError? { get { lock.withLock { _fail } } set { lock.withLock { _fail = newValue } } }
    var calls: [String] { lock.withLock { _calls } }
    private func note(_ s: String) throws { lock.withLock { _calls.append(s) }; if let e = fail { throw e } }

    func blocklist() async throws -> Blocklist { try note("read"); return list }
    func blockGenre(_ genre: String) async throws { try note("block \(genre)") }
    func unblockGenre(_ genre: String) async throws { try note("unblock \(genre)"); list.genres.removeAll { $0 == genre } }
    func unblockArtist(_ artist: String) async throws { try note("unblock artist \(artist)"); list.hiddenArtists.removeAll { $0 == artist } }
    func setArtistLean(_ artist: String, _ lean: ArtistLeanKind, genres: [String]) async throws { try note("lean \(artist) \(lean.rawValue) \(genres)") }
    func clearArtistLean(_ artist: String) async throws { try note("clear \(artist)"); list.leans.removeAll { $0.artist == artist } }
}

@MainActor
@Suite("Blocklist model") struct BlocklistModelTests {
    func make() -> (BlocklistModel, FakeBlocklistSource) {
        let source = FakeBlocklistSource()
        let model = BlocklistModel()
        model.configure(source: source)
        return (model, source)
    }
    func album(genre: String = "Shoegaze") -> AlbumItem {
        AlbumItem(id: 1, title: "Souvlaki", artist: "Slowdive", year: 1993, genre: genre, format: "", owned: false, hue: 10)
    }

    @Test func parsingDropsWhatItCannotUse() {
        let l = Blocklist.parse(
            genres: Data(#"{"genres":[{"genre":"Shoegaze"},{"genre":" "}]}"#.utf8),
            artists: Data(#"{"artists":[{"artist":"Ride"},{}]}"#.utf8),
            leans: Data(#"{"artists":[{"artist":"Lush","lean":"less"},{"artist":"X","lean":"sideways"}]}"#.utf8))
        #expect(l == Blocklist(genres: ["Shoegaze"], hiddenArtists: ["Ride"], leans: [ArtistLean(artist: "Lush", lean: .less)]))
        #expect(Blocklist.parse(genres: Data(), artists: Data("x".utf8), leans: Data("{}".utf8)).isEmpty)
    }

    @Test func loadingReadsTheThreeLists() async {
        let (m, _) = make()
        await m.load()
        #expect(m.phase == .loaded && m.list.count == 3)
    }

    @Test func liftingSendsThenReadsAgain() async {
        let (m, s) = make()
        await m.load()
        await m.unblockGenre("Shoegaze")
        await m.unblockArtist("Ride")
        await m.clearLean("Lush")
        #expect(m.list.isEmpty && m.note == nil)
        #expect(s.calls.filter { $0 != "read" } == ["unblock Shoegaze", "unblock artist Ride", "clear Lush"])
    }

    @Test func aRefusedLiftKeepsTheListAndSaysWhy() async {
        let (m, s) = make()
        await m.load()
        s.fail = .server(status: 502, message: "Could not unblock the genre.")
        await m.unblockGenre("Shoegaze")
        #expect(m.note == "Could not unblock the genre." && m.list.genres == ["Shoegaze"])
    }

    @Test func theMenuSendsTheAlbumsOwnGenreAndSaysWhatHappened() async {
        let (m, s) = make()
        var said: [String] = []
        var blocked = 0
        m.onNotice = { said.append($0) }
        m.onBlocked = { blocked += 1 }
        await m.lean(.more, on: album())
        await m.lean(.less, on: album(genre: ""))
        await m.blockGenre(of: album(genre: "  Post   Punk "))
        await m.blockGenre(of: album(genre: ""))
        #expect(s.calls == ["lean Slowdive more [\"Shoegaze\"]", "lean Slowdive less []", "block Post Punk"])
        #expect(blocked == 1)
        #expect(said == ["More like Slowdive next time.", "Fewer picks like Slowdive. Nothing is hidden.",
                         "Blocked Post Punk. Your library is not affected. Undo it in Settings › Blocklist."])
    }

    @Test func aFailedMenuActionIsReportedNotThrown() async {
        let (m, s) = make()
        var said: [String] = []
        m.onNotice = { said.append($0) }
        s.fail = .server(status: 502, message: "Could not save the artist preference.")
        await m.lean(.more, on: album())
        #expect(said == ["Could not save that: Could not save the artist preference."])
    }

    @Test func withoutAConnectionTheMenuSaysSo() async {
        let m = BlocklistModel()
        var said: [String] = []
        m.onNotice = { said.append($0) }
        await m.lean(.more, on: album())
        #expect(said == ["Not connected to the Librarian. Check Settings."])
    }
}
