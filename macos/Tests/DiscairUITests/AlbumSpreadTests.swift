import DiscairCore
import DiscairLibrarian
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

private final class AlbumReviewCaptureTransport: HTTPTransport, @unchecked Sendable {
    private let lock = NSLock()
    private var requests: [URLRequest] = []
    var sent: [URLRequest] { lock.withLock { requests } }

    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        lock.withLock { requests.append(request) }
        let body = request.url?.path == "/api/album-description"
            ? #"{\"paragraphs\":[]}"#
            : #"{\"critiquebrainz\":[],\"reviews\":[]}"#
        return (Data(body.utf8), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
    }
}

    @Test func critiqueBrainzRequestUsesTheAlbumPageReleaseGroupMBID() async throws {
        let group = "c2c0e5e7-dc91-3e4e-b5bf-a26f06328926"
        let transport = AlbumReviewCaptureTransport()
        let librarian = try LibrarianClient(
            baseURL: URL(string: "https://lib.example.ts.net")!,
            credential: Credential(username: "owner", password: "test"),
            transport: transport
        )
        let album = AlbumItem(id: 99, title: "Tupelo Honey", artist: "Van Morrison", year: 1971, genre: "", format: "", owned: false, hue: 0)
        let model = AlbumSpreadModel()

        await model.load(album: album, navidrome: nil, librarian: librarian, libraryArtists: [], releaseGroupMBID: group)

        let request = transport.sent.first { $0.url?.path == "/api/album-reviews" }
        let query = request?.url.flatMap { URLComponents(url: $0, resolvingAgainstBaseURL: false)?.queryItems }
        #expect(query?.first(where: { $0.name == "mbid" })?.value == group)
    }

    @Test func withoutASessionTheSampleShowsAndAPickShowsNothing() async {
        let m = AlbumSpreadModel()
        let pick = AlbumItem(id: 1, title: "T", artist: "A", year: 0, genre: "", format: "", owned: false, hue: 0)
        await m.load(album: pick, navidrome: nil, libraryArtists: [])
        #expect(m.content == AlbumSpread.sample && !m.isLive)
    }

    @Test func theLibrariansDescriptionFillsTheNotesOnlyWhenNavidromeHasNone() {
        let d = AlbumDescription(paragraphs: ["First.", " ", "Second."], source: "Wikipedia", url: "https://en.wikipedia.org/wiki/X", license: "CC BY-SA")
        let fill = AlbumSpread.build(facts: nil, info: nil, artist: nil, description: d, libraryArtists: [])
        #expect(fill.notes == "First.\n\nSecond." && fill.notesSource == "Wikipedia · CC BY-SA" && fill.notesURL?.host == "en.wikipedia.org")
        let own = AlbumSpread.build(facts: nil, info: NavidromeAlbumInfo(notes: "Mine"), artist: nil, description: d, libraryArtists: [])
        #expect(own.notes == "Mine" && own.notesSource == nil)
        let none = AlbumDescription(paragraphs: [], source: nil, url: nil, license: nil)
        #expect(AlbumSpread.build(facts: nil, info: nil, artist: nil, description: none, libraryArtists: []).isEmpty)
    }

    @Test func reviewsKeepTextAndWebLinksOnlyAndAtMostThree() {
        func r(_ q: String, _ u: String) -> AlbumReview { AlbumReview(source: "S", quote: q, url: u) }
        let out = AlbumSpread.reviews([r("a", "https://x.example/1"), r("  ", "https://x.example/2"), r("b", "javascript:alert(1)"),
                                       r("c", "file:///etc/passwd"), r("d", "http://x.example/4"), r("e", "https://x.example/5"), r("f", "https://x.example/6")])
        #expect(out.map(\.quote) == ["a", "d", "e"])
    }

    @Test func critiqueBrainzReviewsFilterInvalidAndNormalizeFields() {
        let valid = CritiqueBrainzReview(
            id: "1", origin: " BBC ", paragraphs: [" One. ", "  ", "Two."],
            url: "https://critiquebrainz.org/review/1", language: "ar", author: "A",
            rating: 4, license: "CC BY 3.0", licenseUrl: "https://creativecommons.org/licenses/by/3.0/"
        )
        let badURL = CritiqueBrainzReview(
            id: "2", paragraphs: ["Valid."], url: "javascript:alert(1)",
            language: "en", author: "B", license: "CC0", licenseUrl: "https://creativecommons.org/publicdomain/zero/1.0/"
        )
        let emptyParas = CritiqueBrainzReview(
            id: "3", paragraphs: ["   "], url: "https://critiquebrainz.org/review/3",
            language: "fr", author: "C", license: "CC0", licenseUrl: "https://creativecommons.org/publicdomain/zero/1.0/"
        )
        let out = AlbumSpread.critiquebrainz([valid, badURL, emptyParas])
        #expect(out.count == 1)
        #expect(out[0].id == "1")
        #expect(out[0].origin == "BBC")
        #expect(out[0].language == "AR")
        #expect(out[0].paragraphs == ["One.", "Two."])
        #expect(out[0].rating == 4)
        #expect(out[0].licenseUrl?.absoluteString == "https://creativecommons.org/licenses/by/3.0/")
    }
}
