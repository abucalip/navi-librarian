import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

/// The radio client calls (S2-1 item 2): paths, methods, bodies and answers, against the Android contract fixtures
/// (`radio_*.json`, 13 files). Every fixture is used here or in `RadioDecoderTests`.
@Suite("Radio client") struct RadioClientTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")
    func client(_ t: MockTransport) throws -> LibrarianClient { try LibrarianClient(baseURL: base, credential: cred, transport: t) }
    func json(_ s: String) -> Data { Data(s.utf8) }
    func sentBody(_ r: URLRequest) -> [String: Any]? { r.httpBody.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] } }

    @Test func stationsFixtureKeepsServerOrder() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("radio_stations")) }
        let list = try await client(t).radioStations()
        #expect(t.sent[0].httpMethod == "GET" && t.sent[0].url!.path == "/api/radio/stations")
        #expect(list.map(\.id) == ["11", "12", "13"] && list[0].favourite && list[0].proxied)
    }

    @Test func emptyStationsFixtureIsAnEmptyList() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("radio_stations_empty")) }
        #expect(try await client(t).radioStations().isEmpty)
    }

    @Test func aStationsFailureThrowsTheServersSentence() async throws {
        let t = MockTransport { _, _ in (502, self.json(#"{"detail":"Navidrome did not answer."}"#)) }
        await #expect(throws: DiscairError.self) { _ = try await client(t).radioStations() }
    }

    @Test func nowFixturesDecodeThroughTheCall() async throws {
        let expected: [(String, RadioNowState)] = [
            ("radio_now_ok", .ok), ("radio_now_ok_waiting", .ok), ("radio_now_no_metadata", .noMetadata),
            ("radio_now_unparsed", .unparsed), ("radio_now_not_proxied", .notProxied),
            ("radio_now_unavailable", .unavailable), ("radio_now_idle", .idle)]
        for (name, state) in expected {
            let t = MockTransport { _, _ in (200, try fixtureBody(name)) }
            let now = try await client(t).radioNow(station: "11")
            #expect(t.sent[0].httpMethod == "GET" && t.sent[0].url!.path == "/api/radio/stations/11/now", "\(name)")
            #expect(now.state == state, "\(name)")
        }
        let ok = MockTransport { _, _ in (200, try fixtureBody("radio_now_ok")) }
        let now = try await client(ok).radioNow(station: "11")
        #expect(now.canDownload && now.playID == 1)
        let waiting = MockTransport { _, _ in (200, try fixtureBody("radio_now_ok_waiting")) }
        #expect(try await !client(waiting).radioNow(station: "11").canDownload)
    }

    @Test func anUnreadableNowAnswerIsUnavailableNotASong() async throws {
        let t = MockTransport { _, _ in (200, self.json("not json")) }
        #expect(try await client(t).radioNow(station: "11") == .unavailable)
    }

    @Test func nowAllFixtureIsKeyedByStation() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("radio_now_all")) }
        let all = try await client(t).radioNowAll()
        #expect(t.sent[0].url!.path == "/api/radio/now")
        #expect(!all.byStation.isEmpty && all.byStation.keys.allSatisfy { !$0.isEmpty })
    }

    @Test func favouriteSendsTheFlagAndShowsTheFixtureShape() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("radio_station_favourite")) }
        try await client(t).setRadioFavourite(station: "11", on: true)
        #expect(t.sent[0].httpMethod == "PUT" && t.sent[0].url!.path == "/api/radio/stations/11/favourite")
        #expect(sentBody(t.sent[0])?["favourite"] as? Bool == true)
        #expect(t.sent[0].value(forHTTPHeaderField: "Content-Type") == "application/json")
    }

    @Test func aRefusedFavouriteThrows() async throws {
        let t = MockTransport { _, _ in (404, self.json(#"{"detail":"No such station."}"#)) }
        await #expect(throws: DiscairError.self) { try await client(t).setRadioFavourite(station: "99", on: false) }
    }

    @Test func tagsAreSentAsAList() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("radio_station_tags")) }
        try await client(t).setRadioTags(station: "11", tags: ["rock", "local"])
        #expect(t.sent[0].httpMethod == "PUT" && t.sent[0].url!.path == "/api/radio/stations/11/tags")
        #expect(sentBody(t.sent[0])?["tags"] as? [String] == ["rock", "local"])
    }

    @Test func aStationIdIsEncodedInThePath() async throws {
        let t = MockTransport { _, _ in (200, self.json("{}")) }
        try await client(t).setRadioFavourite(station: "a/b c", on: true)
        #expect(t.sent[0].url!.absoluteString.contains("/api/radio/stations/a%2Fb%20c/favourite"))
    }

    @Test func logoAsksForTheSizeAndReturnsTheBytes() async throws {
        let png = Data([0x89, 0x50, 0x4E, 0x47])
        let t = MockTransport { _, _ in (200, png) }
        let logo = try await client(t).radioLogo(station: "12", size: .large)
        #expect(t.sent[0].httpMethod == "GET" && t.sent[0].url!.path == "/api/radio/stations/12/logo")
        #expect(t.sent[0].url!.query == "size=512")
        #expect(logo.data == png)
        _ = try await client(t).radioLogo(station: "12")
        #expect(t.sent[1].url!.query == "size=128")
        // the recorded fixture asks for 128 too
        let fixtureQuery = try fixtureRequestQuery("radio_station_logo")
        #expect(fixtureQuery["size"] == "128")
    }

    @Test func theLiveCoverIsFetchedFromAServerPathOnly() async throws {
        let png = Data([0x89, 0x50, 0x4E, 0x47])
        let t = MockTransport { _, _ in (200, png) }
        let cover = try await client(t).radioCover(path: "/api/artwork/owned/abc?size=600")
        #expect(t.sent[0].httpMethod == "GET" && t.sent[0].url!.path == "/api/artwork/owned/abc" && cover.data == png)
        await #expect(throws: DiscairError.self) { _ = try await client(t).radioCover(path: "https://other.example/x.jpg") }
        await #expect(throws: DiscairError.self) { _ = try await client(t).radioCover(path: "/elsewhere/x.jpg") }
        #expect(t.sent.count == 1)                                  // the refused paths sent nothing
    }

    @Test func aLogoFailureThrows() async throws {
        let t = MockTransport { _, _ in (404, self.json(#"{"detail":"No such station."}"#)) }
        await #expect(throws: DiscairError.self) { _ = try await client(t).radioLogo(station: "x") }
    }

    @Test func scrobblingReadsAndSwitches() async throws {
        let off = MockTransport { _, _ in (200, self.json(#"{"enabled":false,"configured":true}"#)) }
        #expect(try await client(off).radioScrobbling() == RadioScrobbling(enabled: false, configured: true))
        #expect(off.sent[0].httpMethod == "GET" && off.sent[0].url!.path == "/api/radio/scrobbling")
        let on = MockTransport { _, _ in (200, self.json(#"{"enabled":true,"configured":true}"#)) }
        #expect(try await client(on).setRadioScrobbling(true).enabled)
        #expect(on.sent[0].httpMethod == "PUT" && sentBody(on.sent[0])?["enabled"] as? Bool == true)
        let garbled = MockTransport { _, _ in (200, self.json("{}")) }
        #expect(try await client(garbled).radioScrobbling() == RadioScrobbling(enabled: false, configured: false))
    }

    @Test func scrobblingRefusedWhenLastFmIsNotSetUp() async throws {
        let t = MockTransport { _, _ in (400, self.json(#"{"detail":"Last.fm is not set up on the server."}"#)) }
        do { _ = try await client(t).setRadioScrobbling(true); Issue.record("expected a refusal") }
        catch { #expect("\(error)".contains("Last.fm is not set up")) }
    }

    @Test func uploadSendsTheRawImageNotJSON() async throws {
        let image = Data([0x89, 0x50, 0x4E, 0x47, 1, 2, 3])
        let t = MockTransport { _, _ in (200, self.json(#"{"id":"11","logo_url":"/api/radio/stations/11/logo","source":"override"}"#)) }
        try await client(t).uploadRadioLogo(station: "11", data: image, contentType: "image/png")
        #expect(t.sent[0].httpMethod == "PUT" && t.sent[0].url!.path == "/api/radio/stations/11/logo")
        #expect(t.sent[0].httpBody == image && t.sent[0].value(forHTTPHeaderField: "Content-Type") == "image/png")
    }

    @Test func anEmptyOrOversizedImageIsNotSent() async throws {
        let t = MockTransport { _, _ in (200, Data()) }
        await #expect(throws: DiscairError.self) { try await client(t).uploadRadioLogo(station: "11", data: Data()) }
        await #expect(throws: DiscairError.self) {
            try await client(t).uploadRadioLogo(station: "11", data: Data(count: radioLogoUploadLimit + 1))
        }
        #expect(t.sent.isEmpty)
        try await client(t).uploadRadioLogo(station: "11", data: Data(count: radioLogoUploadLimit))
        #expect(t.sent.count == 1)
    }

    @Test func resetDeletesTheOverride() async throws {
        let t = MockTransport { _, _ in (200, self.json(#"{"ok":true,"logo_url":"/api/radio/stations/11/logo"}"#)) }
        try await client(t).resetRadioLogo(station: "11")
        #expect(t.sent[0].httpMethod == "DELETE" && t.sent[0].url!.path == "/api/radio/stations/11/logo" && t.sent[0].httpBody == nil)
    }

    @Test func settingsShowTheAppAddressOrBlank() async throws {
        let t = MockTransport { _, _ in (200, self.json(#"{"app_url":" https://lib.example.ts.net "}"#)) }
        #expect(try await client(t).radioSettings().appURL == "https://lib.example.ts.net")
        #expect(t.sent[0].url!.path == "/api/radio/settings")
        let none = MockTransport { _, _ in (200, self.json(#"{"app_url":null}"#)) }
        #expect(try await client(none).radioSettings().appURL == "")
    }

    @Test func aSessionThatExpiredLogsInOnceAndRetriesAWrite() async throws {
        let t = MockTransport { req, n in
            if req.url!.path == "/api/auth/login" { return (200, Data("{}".utf8)) }
            return n == 1 ? (401, Data(#"{"detail":"Not signed in."}"#.utf8)) : (200, Data("{}".utf8))
        }
        try await client(t).setRadioFavourite(station: "11", on: true)
        #expect(t.sent.map { $0.url!.path } == ["/api/radio/stations/11/favourite", "/api/auth/login", "/api/radio/stations/11/favourite"])
    }
}

/// The `request.query` of a recorded fixture.
private func fixtureRequestQuery(_ name: String, file: String = #filePath) throws -> [String: String] {
    let url = URL(fileURLWithPath: file).deletingLastPathComponent().appending(path: "Fixtures/\(name).json")
    let object = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
    return ((object["request"] as! [String: Any])["query"] as? [String: String]) ?? [:]
}
