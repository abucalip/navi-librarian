import Testing
import Foundation
import DiscairCore
@testable import DiscairNavidrome

@Suite("Navidrome client") struct NavidromeClientTests {
    let base = URL(string: "https://navi.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw")

    func client(_ transport: MockTransport, hint: @escaping @Sendable () -> Bool = { false }) throws -> NavidromeClient {
        try NavidromeClient(baseURL: base, credential: cred, transport: transport, tailscaleHint: hint)
    }
    func fixtureServer(_ files: [String: String]) -> MockTransport {   // endpoint name -> fixture name
        MockTransport { req in
            let endpoint = req.url!.lastPathComponent
            guard let name = files[endpoint] else { return (404, Data()) }
            return (200, try fixtureBody("navidrome", name))
        }
    }

    @Test func ping() async throws {
        try await client(fixtureServer(["ping": "ping"])).ping()
    }

    @Test func requestShape() async throws {
        let t = fixtureServer(["ping": "ping"])
        try await client(t).ping()
        let req = t.sent[0]
        #expect(req.httpMethod == "GET" && req.url!.path == "/rest/ping")
        #expect(req.httpBody == nil)
        let s = queryValue(req, "s")!
        #expect(queryValue(req, "t") == SubsonicAuth.token(password: "s3cret-pw", salt: s))
        #expect(!req.url!.absoluteString.contains("s3cret-pw"))
    }

    @Test func eachRequestUsesAFreshSalt() async throws {
        let t = fixtureServer(["ping": "ping"])
        let c = try client(t)
        for _ in 0..<5 { try await c.ping() }
        #expect(Set(t.sent.map { queryValue($0, "s")! }).count == 5)
        #expect(Set(t.sent.map { queryValue($0, "t")! }).count == 5)
    }

    @Test func artistsFromFixture() async throws {
        let artists = try await client(fixtureServer(["getArtists": "get_artists"])).artists()
        #expect(!artists.isEmpty)
        let first = try #require(artists.first { $0.name == "5.6.7.8's" })
        #expect(first.id == "3rPoD7qONIBTqzc4kSCBON" && first.albumCount == 1)
        let withArt = try #require(artists.first { $0.coverArt != nil })
        #expect(withArt.coverArt!.hasPrefix("ar-"))
    }

    @Test func artistWithAlbumsFromFixture() async throws {
        let t = fixtureServer(["getArtist": "get_artist"])
        let detail = try await client(t).artist(id: "3rPoD7qONIBTqzc4kSCBON")
        #expect(queryValue(t.sent[0], "id") == "3rPoD7qONIBTqzc4kSCBON")
        #expect(detail.artist.name == "5.6.7.8's")
        #expect(detail.albums.first?.name == "Kill Bill (Volume One)" && detail.albums.first?.year == 2003)
    }

    @Test func albumWithSongsFromFixture() async throws {
        let detail = try await client(fixtureServer(["getAlbum": "get_album"])).album(id: "7y8UEyluchKVjyUsqNJQRQ")
        #expect(detail.album.name == "Kill Bill (Volume One)" && detail.album.songCount == 1 && detail.album.genre == "Soundtrack")
        let song = try #require(detail.songs.first)
        #expect(song.id == "1aF3pKQJpLQmSVb50IlxsP" && song.title == "''Woo Hoo''" && song.track == 11)
        #expect(song.bitRate == 192 && song.suffix == "mp3" && song.contentType == "audio/mpeg" && song.duration == 118)
        #expect(song.coverArt == "mf-1aF3pKQJpLQmSVb50IlxsP")
    }

    @Test func albumListFromFixtureAndPagingParameters() async throws {
        let t = fixtureServer(["getAlbumList2": "get_album_list2_newest"])
        let albums = try await client(t).albumList(.newest, size: 10, offset: 20)
        #expect(!albums.isEmpty && albums[0].name == "Ken Andi Habib")
        #expect(queryValue(t.sent[0], "type") == "newest" && queryValue(t.sent[0], "size") == "10" && queryValue(t.sent[0], "offset") == "20")
        _ = try await client(t).albumList(.newest, size: 99999, offset: -5)
        #expect(queryValue(t.sent[1], "size") == "500" && queryValue(t.sent[1], "offset") == "0")
    }

    @Test func songsReadsAPageOfTheWholeLibrary() async throws {
        let t = fixtureServer(["search3": "search3"])
        let songs = try await client(t).songs(offset: 400, count: 99999)
        #expect(!songs.isEmpty && songs[0].title == "''Woo Hoo''" && songs[0].created != nil && songs[0].samplingRate == 44100)
        #expect(queryValue(t.sent[0], "query") == "" && queryValue(t.sent[0], "songOffset") == "400")
        #expect(queryValue(t.sent[0], "songCount") == "500" && queryValue(t.sent[0], "artistCount") == "0" && queryValue(t.sent[0], "albumCount") == "0")
    }

    @Test func allAlbumsPagesUntilAShortPage() async throws {
        let page: @Sendable (Int) -> Data = { n in
            let albums = (0..<n).map { "{\"id\":\"a\($0)\",\"name\":\"A\($0)\"}" }.joined(separator: ",")
            return Data("{\"subsonic-response\":{\"status\":\"ok\",\"albumList2\":{\"album\":[\(albums)]}}}".utf8)
        }
        let t = MockTransport { req in (200, page(Int(queryValue(req, "offset")!)! < 4 ? 2 : 1)) }
        let all = try await client(t).allAlbums(pageSize: 2, maxPages: 10)
        #expect(all.count == 2 + 2 + 1 && t.sent.count == 3)
        let capped = try await client(MockTransport { _ in (200, page(2)) }).allAlbums(pageSize: 2, maxPages: 3)
        #expect(capped.count == 6)
    }

    @Test func emptyLibraryDecodes() async throws {
        let body = Data(#"{"subsonic-response":{"status":"ok","version":"1.16.1","artists":{"index":[]}}}"#.utf8)
        #expect(try await client(MockTransport { _ in (200, body) }).artists().isEmpty)
        let bare = Data(#"{"subsonic-response":{"status":"ok","version":"1.16.1"}}"#.utf8)
        #expect(try await client(MockTransport { _ in (200, bare) }).artists().isEmpty)
    }

    @Test func coverArtURLsComeFromTheSameBuilder() async throws {
        let c = try client(fixtureServer([:]))
        let url = try c.urls.coverArtURL(coverArtID: "al-1_abc", size: 200)
        #expect(url.host == "navi.example.ts.net" && url.path == "/rest/getCoverArt")
    }

    // MARK: error mapping

    func failure(_ body: String, status: Int = 200) async -> DiscairError? {
        do { try await client(MockTransport { _ in (status, Data(body.utf8)) }).ping(); return nil }
        catch let e as DiscairError { return e }
        catch { return .serverUnreachable }
    }

    @Test(arguments: [40, 41, 44, 50]) func subsonicAuthCodesAreUnauthorised(_ code: Int) async {
        let e = await failure(#"{"subsonic-response":{"status":"failed","version":"1.16.1","error":{"code":\#(code),"message":"Wrong username or password"}}}"#)
        #expect(e == .unauthorised(message: "Wrong username or password"))
    }
    @Test func otherSubsonicErrorsAreServerErrors() async {
        let e = await failure(#"{"subsonic-response":{"status":"failed","error":{"code":70,"message":"Data not found"}}}"#)
        #expect(e == .server(status: 200, message: "Data not found"))
    }
    @Test func httpStatuses() async {
        #expect(await failure("", status: 401) == .unauthorised(message: nil))
        #expect(await failure("", status: 403) == .unauthorised(message: nil))
        #expect(await failure("oops", status: 500) == .server(status: 500, message: nil))
        #expect(await failure("", status: 502) == .server(status: 502, message: nil))
    }
    @Test func notNavidrome() async {
        for body in ["<html>hi</html>", "{}", #"{"subsonic-response":"x"}"#, ""] {
            guard case .server(let status, _)? = await failure(body) else { Issue.record("no failure for \(body)"); continue }
            #expect(status == 200)
        }
    }
    @Test func transportFailures() async throws {
        func run(_ code: URLError.Code, hint: Bool = false) async -> DiscairError? {
            do { try await client(MockTransport { _ in throw URLError(code) }, hint: { hint }).ping(); return nil }
            catch { return error as? DiscairError }
        }
        #expect(await run(.notConnectedToInternet) == .noNetwork)
        #expect(await run(.cannotConnectToHost) == .serverUnreachable)
        #expect(await run(.timedOut) == .serverUnreachable)
        #expect(await run(.timedOut, hint: true) == .tailscaleNotConnected)
    }
    @Test func errorsNeverContainSecrets() async {
        let e = await failure(#"{"subsonic-response":{"status":"failed","error":{"code":40,"message":"bad"}}}"#)
        let text = "\(String(describing: e)) \(e?.summary ?? "")"
        for leak in ["s3cret-pw", "owner", "rest/ping", "salt"] { #expect(!text.contains(leak)) }
    }
    @Test func theTransportRulesApplyToTheClient() {
        #expect(throws: DiscairError.insecureOrInvalidAddress(reason: .publicHTTP)) {
            try NavidromeClient(baseURL: URL(string: "http://music.example.com")!, credential: cred)
        }
        #expect(throws: Never.self) { try NavidromeClient(baseURL: URL(string: "http://192.168.1.87:4533")!, credential: cred) }
    }
    @Test func badIDsNeverReachTheNetwork() async throws {
        let t = fixtureServer([:])
        await #expect(throws: DiscairError.self) { try await client(t).album(id: "a&b=c") }
        await #expect(throws: DiscairError.self) { try await client(t).artist(id: "") }
        #expect(t.sent.isEmpty)
    }

    // MARK: playlists (shapes follow the Subsonic 1.16.1 specification; not yet captured from the owner's Navidrome, see contract 6a)

    @Test func playlistCalls() async throws {
        let t = MockTransport { req in
            switch req.url!.lastPathComponent {
            case "getPlaylists": return (200, Data(#"{"subsonic-response":{"status":"ok","playlists":{"playlist":[{"id":"p1","name":"Mix","songCount":2,"owner":"owner","public":false}]}}}"#.utf8))
            case "createPlaylist": return (200, Data(#"{"subsonic-response":{"status":"ok","playlist":{"id":"p2","name":"New","songCount":1,"entry":[{"id":"s1","title":"T"}]}}}"#.utf8))
            case "getPlaylist": return (200, Data(#"{"subsonic-response":{"status":"ok","playlist":{"id":"p2","name":"New","entry":[{"id":"s1","title":"T"},{"id":"s2","title":"U"}]}}}"#.utf8))
            default: return (200, Data(#"{"subsonic-response":{"status":"ok"}}"#.utf8))
            }
        }
        let c = try client(t)
        #expect(try await c.playlists() == [NavidromePlaylist(id: "p1", name: "Mix", songCount: 2, owner: "owner", public: false)])
        #expect(try await c.createPlaylist(name: "New", songIDs: ["s1"]).id == "p2")
        #expect(try await c.playlistSongIDs(id: "p2") == ["s1", "s2"])
        try await c.addToPlaylist(id: "p2", songIDs: ["s3", "s4"])
        try await c.deletePlaylist(id: "p2")
        let add = t.sent[3]
        #expect(add.url!.lastPathComponent == "updatePlaylist" && queryValue(add, "playlistId") == "p2")
        let addIDs = URLComponents(url: add.url!, resolvingAgainstBaseURL: false)!.queryItems!.filter { $0.name == "songIdToAdd" }.map(\.value)
        #expect(addIDs == ["s3", "s4"])
        #expect(t.sent[4].url!.lastPathComponent == "deletePlaylist")
    }
}
