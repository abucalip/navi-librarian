import DiscairNavidrome
import Foundation
import Testing
@testable import DiscairUI

@MainActor
struct AlbumSpreadTests {
    private func credit(_ role: String, _ name: String, sub: String? = nil, song: String = "s1") -> NavidromeCredit {
        NavidromeCredit(role: role, subRole: sub, name: name, songID: song)
    }

    @Test func creditsGroupByRoleWithoutRepeatsAndCommonRolesFirst() {
        let g = AlbumSpread.credits([credit("performer", "B", sub: "bass"), credit("composer", "A"), credit("composer", "a", song: "s2"),
                                     credit("composer", "C", song: "s2"), credit("mixer", "M"), credit("zither", "Z")])
        #expect(g.map(\.title) == ["Composer", "Mixer", "Performer · bass", "Zither"])
        #expect(g[0].names == ["A", "C"])                       // "a" is the same person, listed once
    }

    @Test func notesLoseTagsEntitiesAndTheReadMoreLine() {
        let raw = #"Fourth &amp; best.<br/>Second line. <a href="https://www.last.fm/x">Read more on Last.fm</a>. User-contributed text is available under the Creative Commons By-SA License"#
        #expect(AlbumSpread.cleanNotes(raw) == "Fourth & best.\n\nSecond line.")
        #expect(AlbumSpread.cleanNotes("  <a href=\"x\">Read more on Last.fm</a>  ") == nil)
        #expect(AlbumSpread.cleanNotes("") == nil)
    }

    @Test func onlyAValidMBIDAndAnHTTPSLastFmLinkBecomeLinks() {
        let good = NavidromeAlbumInfo(notes: nil, musicBrainzId: "11111111-2222-3333-4444-555555555555", lastFmUrl: "https://www.last.fm/music/x")
        let c = AlbumSpread.build(facts: nil, info: good, artist: nil, libraryArtists: [])
        #expect(c.musicBrainzURL?.absoluteString == "https://musicbrainz.org/release/11111111-2222-3333-4444-555555555555")
        #expect(c.lastFmURL?.host == "www.last.fm")
        #expect(c.facts.map(\.label) == ["MusicBrainz"])

        let bad = NavidromeAlbumInfo(notes: nil, musicBrainzId: "../../evil", lastFmUrl: "http://last.fm.evil.example/x")
        let d = AlbumSpread.build(facts: nil, info: bad, artist: nil, libraryArtists: [])
        #expect(d.musicBrainzURL == nil && d.lastFmURL == nil && d.isEmpty)
        #expect(AlbumSpread.lastFmURL("https://evil.example/last.fm") == nil)
    }

    @Test func factsListTypeLabelDateAndEdition() {
        var f = NavidromeAlbumFacts()
        f.releaseTypes = ["Album"]; f.recordLabels = ["L1", "L2"]; f.originalReleaseDate = "1988"; f.version = "Deluxe"; f.isCompilation = true
        let c = AlbumSpread.build(facts: f, info: nil, artist: nil, libraryArtists: [])
        #expect(c.facts.map(\.label) == ["Release type", "Label", "First released", "Edition", "Compilation"])
        #expect(c.facts[1].value == "L1, L2")
    }

    @Test func similarArtistsAreFlaggedWhenTheLibraryHoldsThemAndRepeatsDrop() {
        func a(_ n: String) -> NavidromeArtist { NavidromeArtist(id: n, name: n, albumCount: nil, coverArt: nil, musicBrainzId: nil) }
        let info = NavidromeArtistInfo(similarArtists: [a("Mine"), a("Other"), a("MINE"), a("  ")])
        let c = AlbumSpread.build(facts: nil, info: nil, artist: info, libraryArtists: ["mine"])
        #expect(c.similar == [SpreadSimilar(name: "Mine", inLibrary: true), SpreadSimilar(name: "Other", inLibrary: false)])
    }

    @Test func nothingFromTheServerIsAnEmptySpread() {
        #expect(AlbumSpread.build(facts: nil, info: nil, artist: nil, libraryArtists: []).isEmpty)
        #expect(!AlbumSpread.sample.isEmpty)
    }

    @Test func withoutASessionTheSampleShowsAndAPickShowsNothing() async {
        let m = AlbumSpreadModel()
        let pick = AlbumItem(id: 1, title: "T", artist: "A", year: 0, genre: "", format: "", owned: false, hue: 0)
        await m.load(album: pick, navidrome: nil, libraryArtists: [])
        #expect(m.content == AlbumSpread.sample && !m.isLive)
    }
}
