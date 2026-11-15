import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

@Suite("Catalog search") struct CatalogSearchTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")

    static let body = """
    event: capabilities
    data: {"types":{}}

    event: result
    data: {"type":"artist","owned":true,"id":"1","key":"talk talk","name":"Talk Talk","sources":["navidrome"],"artwork_url":null,"album_count":5}

    event: result
    data: {"type":"artist","owned":false,"id":"mb1","key":"portishead","name":"Portishead","mbid":"x","sources":["musicbrainz"],"artwork_url":"https://img.example/p.jpg","album_count":3}

    event: result
    data: {"type":"album","owned":false,"id":"rg1","key":"third","name":"Third","artist":"Portishead","year":2008,"release_group_mbid":"rg-1","sources":["musicbrainz"],"artwork_url":"http://insecure.example/a.jpg"}

    event: result
    data: {"type":"song","owned":false,"id":"s1","key":"machine gun","name":"Machine Gun","artist":"Portishead","album":"Third","sources":["lastfm"],"artwork_url":null}

    event: result
    data: {not json}

    event: result
    data: {"type":"genre","owned":false,"id":"g","key":"trip hop","name":"Trip Hop","tag":"trip hop","sources":["musicbrainz"],"artwork_url":null}

    event: source
    data: {"source":"musicbrainz","state":"done","count":3,"ms":400}

    event: done
    data: {"elapsed_ms":900,"deadline_hit":false,"partial":false}


    """

    @Test func onlyResultsTheLibraryLacksAreKeptAndBadRowsAreSkipped() {
        let hits = CatalogHits.parse(sse: Data(Self.body.utf8))
        #expect(hits.artists.map(\.name) == ["Portishead"])
        #expect(hits.artists[0].artworkURL?.absoluteString == "https://img.example/p.jpg")
        #expect(hits.albums == [CatalogHit(kind: .album, name: "Third", artist: "Portishead", year: 2008, releaseGroupMBID: "rg-1")])
        #expect(hits.songs.first?.album == "Third" && hits.songs.count == 1)
    }

    @Test func anEmptyOrOwnedOnlyAnswerIsEmpty() {
        #expect(CatalogHits.parse(sse: Data()).isEmpty)
        let owned = "event: result\ndata: {\"type\":\"album\",\"owned\":true,\"name\":\"X\"}\n\n"
        #expect(CatalogHits.parse(sse: Data(owned.utf8)).isEmpty)
    }

    @Test func searchAsksForAllScopeWithTheQueryEncoded() async throws {
        let t = MockTransport { _, _ in (200, Data(Self.body.utf8)) }
        let c = try LibrarianClient(baseURL: base, credential: cred, transport: t)
        let hits = try await c.searchCatalog("Beyoncé & co", limit: 4)
        let url = try #require(t.sent.last?.url)
        #expect(url.path == "/api/search")
        let items = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems ?? []
        #expect(items.first { $0.name == "q" }?.value == "Beyoncé & co")
        #expect(items.first { $0.name == "scope" }?.value == "all" && items.first { $0.name == "limit" }?.value == "4")
        #expect(hits.artists.count == 1)
    }

    @Test func aServerErrorIsThrown() async throws {
        let t = MockTransport { _, _ in (400, Data(#"{"detail":"q must be 1 to 200 characters."}"#.utf8)) }
        let c = try LibrarianClient(baseURL: base, credential: cred, transport: t)
        var threw = false
        do { _ = try await c.searchCatalog("x") } catch { threw = true }
        #expect(threw)
    }
}
