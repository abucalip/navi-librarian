import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

/// Bodies are written from the server's serializers in `settings/service.py` and `app/api/` (they are not live captures);
/// `health` uses the recorded contract fixture.
@Suite("Service settings client") struct ServiceSettingsClientTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")
    func client(_ t: MockTransport) throws -> LibrarianClient { try LibrarianClient(baseURL: base, credential: cred, transport: t) }
    func answer(_ json: String, status: Int = 200) -> MockTransport { MockTransport { _, _ in (status, Data(json.utf8)) } }

    @Test func navidromeSettingsDecodeWithoutAPassword() async throws {
        let t = answer(#"{"navidrome_url":"http://192.168.1.87:4533","username":"the-owner","password_configured":true,"music_library_path":"/music"}"#)
        let s = try await client(t).navidromeSettings()
        #expect(s == NavidromeSettings(url: "http://192.168.1.87:4533", username: "the-owner", passwordConfigured: true, musicLibraryPath: "/music"))
        #expect(t.sent[0].httpMethod == "GET" && t.sent[0].url!.path == "/api/settings/navidrome")
    }

    @Test func lastFMSlskdAndDiscogsSettingsDecode() async throws {
        #expect(try await client(answer(#"{"api_key_configured":true,"username":"abc"}"#)).lastFMSettings() == LastFMSettings(apiKeyConfigured: true, username: "abc"))
        let slskd = try await client(answer(#"{"music_library_path":"/music","slskd_url":"http://nas:5030","api_key_configured":true,"slskd_downloads_path":"/dl","quality_priority":["mp3_320","flac_cd"],"quality_labels":{"mp3_320":"MP3 320 kbps"}}"#)).slskdSettings()
        #expect(slskd == SlskdSettings(url: "http://nas:5030", apiKeyConfigured: true, downloadsPath: "/dl", musicLibraryPath: "/music", qualityPriority: ["mp3_320", "flac_cd"]))
        #expect(try await client(answer(#"{"token_configured":true,"source":"environment"}"#)).discogsSettings() == DiscogsSettings(tokenConfigured: true, source: "environment"))
    }

    @Test func missingFieldsReadAsNotConfigured() async throws {
        #expect(try await client(answer("{}")).lastFMSettings() == LastFMSettings(apiKeyConfigured: false))
        #expect(try await client(answer("{}")).discogsSettings() == DiscogsSettings(tokenConfigured: false, source: "none"))
    }

    @Test func testRoutesArePostsAndDecodeEachShape() async throws {
        let nav = answer(#"{"ok":true,"status":"connected","message":"Navidrome connection succeeded."}"#)
        #expect(try await client(nav).testNavidrome().ok)
        #expect(nav.sent[0].httpMethod == "POST" && nav.sent[0].url!.path == "/api/settings/navidrome/test")

        let last = try await client(answer(#"{"ok":false,"status":"authentication_failed","message":"Last.fm rejected the API key. Check the key in Settings."}"#)).testLastFM()
        #expect(!last.ok && last.status == "authentication_failed")

        // slskd adds http_status on success; unknown fields are ignored.
        let slskd = try await client(answer(#"{"ok":true,"status":"connected","http_status":200,"message":"slskd API connection succeeded."}"#)).testSlskd()
        #expect(slskd.ok && slskd.status == "connected")
    }

    @Test func discogsTestSendsErrorInsteadOfStatusAndIsFolded() async throws {
        let rejected = try await client(answer(#"{"ok":false,"error":"Discogs rejected the token. Check the token in Settings."}"#)).testDiscogs()
        #expect(!rejected.ok && rejected.status == "authentication_failed" && rejected.message.contains("rejected"))
        let missing = try await client(answer(#"{"ok":false,"error":"Add a Discogs token first."}"#)).testDiscogs()
        #expect(missing.status == "not_configured")
        let down = try await client(answer(#"{"ok":false,"error":"Could not reach Discogs or validate the token."}"#)).testDiscogs()
        #expect(down.status == "connection_failed")
        #expect(try await client(answer(#"{"ok":true}"#)).testDiscogs() == ServiceTestResult(ok: true, status: "connected"))
    }

    @Test func aFailedTestRouteThrowsTheServersSentence() async throws {
        let t = answer(#"{"detail":"Could not test the slskd connection."}"#, status: 502)
        await #expect(throws: DiscairError.self) { try await client(t).testSlskd() }
    }

    @Test func healthDecodesTheRecordedFixture() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("health")) }
        let h = try await client(t).health()
        #expect(h.isOK && h.service == "Navidrome")
        #expect(t.sent[0].url!.path == "/api/health")
    }

    @Test func healthThrowsWhenNavidromeIsUnavailable() async throws {
        let t = answer(#"{"detail":"Navidrome is unavailable or authentication failed."}"#, status: 503)
        await #expect(throws: DiscairError.self) { try await client(t).health() }
    }

    @Test func capabilitiesReadCoverageSonicListenBrainzAndFeatures() async throws {
        let json = #"{"contract_version":1,"graph_coverage":"broad","sonic_available":true,"listenbrainz_connected":false,"features":{"insights":{"available":true,"resource":"insights","data_version":3},"paths":{"available":false,"reason":"not_populated"}},"data_versions":{}}"#
        let c = try await client(answer(json)).capabilities()
        #expect(c == ServerCapabilities(graphCoverage: "broad", sonicAvailable: true, listenBrainzConnected: false, availableFeatures: ["insights"]))
    }

    @Test func anUnknownCoverageClassReadsAsNone() async throws {
        #expect(try await client(answer(#"{"graph_coverage":"huge"}"#)).capabilities().graphCoverage == "none")
    }

    @Test func savesSendOnlyWhatTheServerTakes() async throws {
        let t = answer(#"{"ok":true}"#)
        let c = try client(t)
        try await c.saveNavidrome(url: "http://nd:4533", username: "me")
        try await c.saveLastFM(apiKey: "k")
        try await c.saveSlskd(url: "http://sl:5030", qualityPriority: ["mp3_320"])
        try await c.saveDiscogs(token: "")
        func body(_ i: Int) throws -> [String: Any] { try JSONSerialization.jsonObject(with: #require(t.sent[i].httpBody)) as! [String: Any] }
        #expect(t.sent.allSatisfy { $0.httpMethod == "PUT" })
        #expect(try body(0) as NSDictionary == ["navidrome_url": "http://nd:4533", "username": "me", "password": ""] as NSDictionary)
        #expect(try body(1) as NSDictionary == ["api_key": "k"] as NSDictionary)      // no username key: the server keeps it
        #expect(try body(2)["quality_priority"] as? [String] == ["mp3_320"])
        #expect(try body(3) as NSDictionary == ["token": ""] as NSDictionary)
    }

    @Test func slskdFoldersAreSentOnlyWhenGiven() async throws {
        let t = answer(#"{"ok":true}"#)
        let c = try client(t)
        try await c.saveSlskd(url: "http://sl:5030", qualityPriority: ["mp3_320"])
        try await c.saveSlskd(url: "http://sl:5030", apiKey: "k", qualityPriority: ["mp3_320"], downloadsPath: "/downloads", musicLibraryPath: "/music")
        func body(_ i: Int) throws -> [String: Any] { try JSONSerialization.jsonObject(with: #require(t.sent[i].httpBody)) as! [String: Any] }
        #expect(try body(0).keys.sorted() == ["api_key", "quality_priority", "slskd_url"])      // the server keeps a folder it is not sent
        #expect(try body(1)["slskd_downloads_path"] as? String == "/downloads" && body(1)["music_library_path"] as? String == "/music")
    }

    @Test func aRejectedSaveThrows() async throws {
        let t = answer(#"{"detail":"Enter a valid HTTP or HTTPS Navidrome URL."}"#, status: 400)
        await #expect(throws: DiscairError.self) { try await client(t).saveNavidrome(url: "x", username: "me") }
    }
}
