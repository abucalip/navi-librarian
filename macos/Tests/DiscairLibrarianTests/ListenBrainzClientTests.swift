import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

@Suite("ListenBrainz settings client") struct ListenBrainzClientTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")
    func client(_ t: MockTransport) throws -> LibrarianClient { try LibrarianClient(baseURL: base, credential: cred, transport: t) }

    @Test func readsUsernameAndTokenFlagOnly() async throws {
        let t = MockTransport { _, _ in (200, Data(#"{"username":"abc","token_configured":true}"#.utf8)) }
        let s = try await client(t).listenBrainzSettings()
        #expect(s == ListenBrainzSettings(username: "abc", tokenConfigured: true))
        #expect(t.sent[0].httpMethod == "GET" && t.sent[0].url!.path == "/api/settings/listenbrainz")
    }

    @Test func saveSendsUsernameAndTokenAsPut() async throws {
        let t = MockTransport { _, _ in (200, Data(#"{"ok":true,"username":"abc"}"#.utf8)) }
        try await client(t).saveListenBrainz(username: "abc", token: "tok_1")
        let r = t.sent[0]
        #expect(r.httpMethod == "PUT" && r.url!.path == "/api/settings/listenbrainz")
        let body = try #require(r.httpBody)
        let o = try JSONSerialization.jsonObject(with: body) as! [String: String]
        #expect(o == ["username": "abc", "token": "tok_1"])
    }

    @Test func aRejectedUsernameThrowsTheServersSentence() async throws {
        let t = MockTransport { _, _ in (400, Data(#"{"detail":"Enter a valid ListenBrainz username"}"#.utf8)) }
        await #expect(throws: DiscairError.self) { try await client(t).saveListenBrainz(username: "a b") }
    }

    @Test func testRouteDecodes() async throws {
        let t = MockTransport { _, _ in (200, Data(#"{"ok":false,"status":"not_found","message":"ListenBrainz user was not found."}"#.utf8)) }
        let r = try await client(t).testListenBrainz()
        #expect(!r.ok && r.status == "not_found")
        #expect(t.sent[0].httpMethod == "POST" && t.sent[0].url!.path == "/api/settings/listenbrainz/test")
    }
}

@Suite("Long taste calls") struct LongCallTests {
    @Test func refreshAllowsMoreThanTheDefaultTimeout() async throws {
        let t = MockTransport { _, _ in (200, Data(#"{"state":"unchanged"}"#.utf8)) }
        let c = try LibrarianClient(baseURL: URL(string: "https://lib.example.ts.net")!, credential: Credential(username: "o", password: "p"), transport: t)
        _ = try? await c.refreshTaste()
        #expect(t.sent[0].timeoutInterval > 60)
    }
}
