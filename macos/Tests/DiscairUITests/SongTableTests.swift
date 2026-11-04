import DiscairNavidrome
import Foundation
import Testing
@testable import DiscairUI

@MainActor
struct SongTableTests {
    private func row(_ id: Int, _ title: String, year: Int = 0, rating: Int = 0, kbps: Int = 0, plays: Int = 0,
                     played: Date? = nil, added: Date? = nil, mbid: Bool = true) -> SongRow {
        var r = SongRow(id: id, album: 0, title: title, artist: "A", genre: "", format: "", bitrate: "", lastPlayed: "", added: "", year: year, plays: plays)
        r.rating = rating; r.bitrateKbps = kbps; r.playedAt = played; r.addedAt = added; r.hasMBID = mbid
        return r
    }
    private func titles(_ rows: [SongRow]) -> [String] { rows.map(\.title) }

    @Test func numericColumnsSortAsNumbersNotText() {
        let rows = [row(0, "a", kbps: 320), row(1, "b", kbps: 1000), row(2, "c", kbps: 96)]
        #expect(titles(SongTable.sorted(rows, by: .bitrate, ascending: true)) == ["c", "a", "b"])
        #expect(titles(SongTable.sorted(rows, by: .bitrate, ascending: false)) == ["b", "a", "c"])
    }

    @Test func unknownValuesComeLastInBothDirections() {
        let rows = [row(0, "none"), row(1, "four", rating: 4), row(2, "two", rating: 2)]
        #expect(titles(SongTable.sorted(rows, by: .rating, ascending: true)) == ["two", "four", "none"])
        #expect(titles(SongTable.sorted(rows, by: .rating, ascending: false)) == ["four", "two", "none"])
    }

    @Test func datesSortByTimeAndNeverPlayedIsLast() {
        let old = Date(timeIntervalSince1970: 1_000), new = Date(timeIntervalSince1970: 9_000)
        let rows = [row(0, "never"), row(1, "new", played: new), row(2, "old", played: old)]
        #expect(titles(SongTable.sorted(rows, by: .lastPlayed, ascending: false)) == ["new", "old", "never"])
        #expect(titles(SongTable.sorted(rows, by: .lastPlayed, ascending: true)) == ["old", "new", "never"])
    }

    @Test func missingMBIDSortsFirstAndCanBeTheOnlyRows() {
        let rows = [row(0, "ok"), row(1, "gap", mbid: false), row(2, "ok2")]
        #expect(titles(SongTable.sorted(rows, by: .mbid, ascending: true)).first == "gap")
        #expect(titles(SongTable.sorted(rows, by: .title, ascending: true, onlyMissingMBID: true)) == ["gap"])
    }

    @Test func tiesKeepLibraryOrderAndTextIgnoresCase() {
        let rows = [row(0, "b", plays: 5), row(1, "A", plays: 5), row(2, "c", plays: 9)]
        #expect(titles(SongTable.sorted(rows, by: .plays, ascending: false)) == ["c", "b", "A"])
        #expect(titles(SongTable.sorted(rows, by: .title, ascending: true)) == ["A", "b", "c"])
    }

    @Test func starsAndFirstClickDirection() {
        #expect(SongTable.stars(3) == "★★★☆☆" && SongTable.stars(0) == "" && SongTable.stars(9) == "★★★★★")
        #expect(SongColumn.title.startsAscending && !SongColumn.rating.startsAscending && !SongColumn.added.startsAscending)
    }

    @Test func liveRowsCarryTheNewFields() throws {
        let json = #"{"id":"s1","title":"T","bitRate":900,"userRating":4,"musicBrainzId":"","created":"2020-10-12T13:44:03Z","played":"0001-01-01T00:00:00Z"}"#
        let song = try JSONDecoder().decode(NavidromeSong.self, from: Data(json.utf8))
        let r = LibraryModel.row(song, id: 0)
        #expect(r.rating == 4 && r.bitrateKbps == 900 && !r.hasMBID && r.addedAt != nil && r.playedAt == nil)
        let tagged = try JSONDecoder().decode(NavidromeSong.self, from: Data(#"{"id":"s2","title":"T","musicBrainzId":"abc"}"#.utf8))
        #expect(LibraryModel.row(tagged, id: 1).hasMBID)
    }
}
