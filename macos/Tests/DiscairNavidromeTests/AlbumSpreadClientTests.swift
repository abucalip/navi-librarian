import Foundation
import Testing
import DiscairCore
@testable import DiscairNavidrome

/// Placeholder names only: the structure of the answers, never real data.
@Suite("Album spread client") struct AlbumSpreadClientTests {
    func client(_ body: @escaping @Sendable (URLRequest) -> String) throws -> (NavidromeClient, MockTransport) {
        let t = MockTransport { (200, Data(body($0).utf8)) }
        return (try NavidromeClient(baseURL: URL(string: "https://navi.example.ts.net")!, credential: Credential(username: "o", password: "pw"), transport: t), t)
    }

    @Test func factsReadLabelsDateTypesAndCreditsOfEverySong() async throws {
        let json = """
        {"subsonic-response":{"status":"ok","album":{"id":"al1","name":"A","musicBrainzId":"11111111-2222-3333-4444-555555555555",
         "releaseTypes":["Album","Live"],"recordLabels":[{"name":"Label One"},{"name":""}],
         "originalReleaseDate":{"year":1988,"month":9,"day":5},"version":"Deluxe","isCompilation":false,
         "song":[{"id":"s1","contributors":[{"role":"composer","artist":{"name":"Person A"}},{"role":"performer","subRole":"bass","artist":{"name":"Person B"}}]},
                 {"id":"s2"},{"id":"s3","contributors":[{"role":"","artist":{"name":"Nobody"}},{"role":"mixer","artist":{"name":""}}]}]}}}
        """
        let (c, t) = try client { _ in json }
        let f = try await c.albumFacts(id: "al1")
        #expect(f.musicBrainzId == "11111111-2222-3333-4444-555555555555")
        #expect(f.releaseTypes == ["Album", "Live"] && f.recordLabels == ["Label One"])
        #expect(f.originalReleaseDate == "1988-09-05" && f.version == "Deluxe" && f.isCompilation == false)
        #expect(f.credits == [NavidromeCredit(role: "composer", subRole: nil, name: "Person A", songID: "s1"),
                              NavidromeCredit(role: "performer", subRole: "bass", name: "Person B", songID: "s1")])
        #expect(t.sent.first?.url?.path.hasSuffix("rest/getAlbum") == true && queryValue(t.sent[0], "id") == "al1")
    }

    @Test func aPlainAlbumGivesEmptyFactsAndYearOnlyDatesStayYearOnly() async throws {
        let json = #"{"subsonic-response":{"status":"ok","album":{"id":"al1","name":"A","originalReleaseDate":{"year":1971}}}}"#
        let (c, _) = try client { _ in json }
        let f = try await c.albumFacts(id: "al1")
        #expect(f.originalReleaseDate == "1971" && f.credits.isEmpty && f.recordLabels.isEmpty && f.musicBrainzId == nil)
    }

    @Test func albumInfoReturnsNotesAndLinksAndNilWhenNotFound() async throws {
        let ok = #"{"subsonic-response":{"status":"ok","albumInfo":{"notes":"Hello","musicBrainzId":"m","lastFmUrl":"https://www.last.fm/music/x"}}}"#
        let (c, t) = try client { _ in ok }
        let i = try await c.albumInfo(id: "al1")
        #expect(i == NavidromeAlbumInfo(notes: "Hello", musicBrainzId: "m", lastFmUrl: "https://www.last.fm/music/x"))
        #expect(t.sent.first?.url?.path.hasSuffix("rest/getAlbumInfo2") == true)

        let missing = #"{"subsonic-response":{"status":"failed","error":{"code":70,"message":"not found"}}}"#
        let (c2, _) = try client { _ in missing }
        #expect(try await c2.albumInfo(id: "al1") == nil)
    }

    @Test func artistInfoReturnsSimilarArtistsAndAsksForOnesTheLibraryHolds() async throws {
        let json = #"{"subsonic-response":{"status":"ok","artistInfo2":{"biography":"Bio","similarArtist":[{"id":"a2","name":"Other","albumCount":2}]}}}"#
        let (c, t) = try client { _ in json }
        let i = try await c.artistInfo(id: "a1", similar: 99)
        #expect(i?.biography == "Bio" && i?.similarArtists.map(\.name) == ["Other"])
        #expect(queryValue(t.sent[0], "count") == "50" && queryValue(t.sent[0], "includeNotPresent") == "false")
    }

    @Test func anUnsafeIDIsRefusedBeforeAnyRequest() async throws {
        let (c, t) = try client { _ in "{}" }
        await #expect(throws: DiscairError.self) { _ = try await c.albumFacts(id: "../x") }
        await #expect(throws: DiscairError.self) { _ = try await c.albumInfo(id: "a b") }
        #expect(t.sent.isEmpty)
    }
}
