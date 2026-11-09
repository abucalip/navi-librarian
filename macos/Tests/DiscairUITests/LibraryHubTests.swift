import AppKit
import Foundation
import Testing
@testable import DiscairUI

@Suite("Library hub") @MainActor struct LibraryHubTests {
    private func song(_ id: Int, _ title: String, _ artist: String, played: Date?) -> SongRow {
        var r = Fixtures.songs[0]
        r = SongRow(id: id, album: r.album, title: title, artist: artist, genre: "", format: "FLAC", bitrate: "", lastPlayed: "", added: "", year: 2000, plays: 1)
        r.playedAt = played
        return r
    }

    @Test func searchIgnoresCaseAndAccentsAndNeedsEveryWord() {
        #expect(LibrarySearch.matches(["Beyoncé"], query: "beyonce"))
        #expect(LibrarySearch.matches(["Talk Talk", "Laughing Stock"], query: "talk stock"))
        #expect(!LibrarySearch.matches(["Talk Talk"], query: "talk zebra"))
        #expect(LibrarySearch.matches(["x"], query: "  "))
    }

    @Test func resultsAreLimitedAndEmptyForNoQuery() {
        let artists = (0..<9).map { ArtistItem(id: $0, name: "Band \($0)", albumCount: 1) }
        let r = LibrarySearch.results(query: "band", artists: artists, albums: [], songs: [])
        #expect(r.artists.count == 5 && r.albums.isEmpty)
        #expect(LibrarySearch.results(query: " ", artists: artists, albums: [], songs: []).isEmpty)
    }

    @Test func albumSearchSkipsAlbumsTheLibraryDoesNotOwn() {
        let owned = Fixtures.albums.first { $0.owned }!
        let missing = Fixtures.albums.first { !$0.owned }
        let found = LibrarySearch.albums([owned] + (missing.map { [$0] } ?? []), query: "")
        #expect(found.allSatisfy { $0.owned })
    }

    @Test func recentlyPlayedIsTheLatest20NewestFirst() {
        let now = Date()
        let rows = (0..<30).map { song($0, "S\($0)", "A", played: now.addingTimeInterval(Double($0) * -60)) } + [song(99, "Never", "A", played: nil)]
        let recent = LibrarySearch.recentlyPlayed(rows.shuffled())
        #expect(recent.count == 20 && recent.first?.title == "S0" && recent.last?.title == "S19")
    }

    @Test func gapCardsGrowWithTheirAlbumsAndSmallOnesStayNarrow() {
        #expect(GapCardWidth.width(albums: 2) == GapCardWidth.minimum)
        #expect(GapCardWidth.width(albums: 12) > GapCardWidth.width(albums: 6))
        #expect(GapCardWidth.width(albums: 2) * 3 + 28 < 1000)   // three small artists fit one row
    }

    @Test func tintIsDarkEnoughForWhiteText() {
        let bright = ArtworkTint.from(red: 1, green: 1, blue: 0.9)
        #expect(bright.brightness <= 0.5 && bright.brightness >= 0.28)
        let red = ArtworkTint.from(red: 0.8, green: 0.1, blue: 0.1)
        #expect(red.saturation > 0.5)
    }

    @Test func openingASongFromSearchMarksItOnTheAlbum() {
        let state = AppState()
        let a = Fixtures.albums[0]
        state.open(album: a, highlighting: "After the Flood")
        #expect(state.screen == .album && state.highlightedSong == "After the Flood")
        state.open(album: a)
        #expect(state.highlightedSong == nil)
    }
}
