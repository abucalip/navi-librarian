import Foundation
import Testing
import DiscairLibrarian
@testable import DiscairUI

@MainActor @Suite("Taste actions") struct TasteActionTests {
    @Test func onlyGenreAndDecadeBecomeActions() {
        #expect(TasteAction(dimension: "genre", value: "Shoegaze") == .genre("Shoegaze"))
        #expect(TasteAction(dimension: "era", value: "1980s") == .era(label: "1980s", years: 1980...1989))
        #expect(TasteAction(dimension: "area", value: "UK") == nil)
        #expect(TasteAction(dimension: "label", value: "4AD") == nil)
        #expect(TasteAction(dimension: "collaborator", value: "Flood") == nil)
        #expect(TasteAction(dimension: "era", value: "eighties") == nil)
        #expect(TasteAction(dimension: "era", value: "1985s") == nil)
        #expect(TasteAction(dimension: "genre", value: "  ") == nil)
    }

    @Test func rulesMatchTheValue() {
        let g = TasteAction.genre("Jazz").playlist
        #expect(g.name == "Taste: Jazz" && g.matchAll && g.rules.map(\.field) == [.genre] && g.rules[0].op == .contains && g.rules[0].value == "Jazz")
        let e = TasteAction(dimension: "era", value: "1990s")!.playlist
        #expect(e.rules.map(\.field) == [.year, .year] && e.rules.map(\.op) == [.atLeast, .atMost] && e.rules.map(\.value) == ["1990", "1999"])
    }

    @Test func filterKeepsOnlyMatchingSongs() {
        let songs = Fixtures.songs
        let jazz = TasteAction.genre(songs[0].genre)
        #expect(!songs.filter(jazz.matches).isEmpty)
        let none = TasteAction.era(label: "1000s", years: 1000...1009)
        #expect(songs.filter(none.matches).isEmpty)
    }

    @Test func smartPlaylistStartsFromTheCardAndOpensIt() {
        let state = AppState()
        let a = TasteAction.genre("Shoegaze")
        state.makeSmartPlaylist(from: a)
        #expect(state.screen == .smartPlaylists && state.smart.selected?.name == "Taste: Shoegaze")
        state.openLibrary(filteredBy: a)
        #expect(state.screen == .library && state.libraryTab == .songs && state.tasteFilter == a && state.librarySearch.isEmpty)
    }
}
