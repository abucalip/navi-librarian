import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

@Suite("Librarian discovery") struct DiscoveryClientTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")
    func client(_ t: MockTransport) throws -> LibrarianClient { try LibrarianClient(baseURL: base, credential: cred, transport: t) }

    @Test func personalListKeepsTheServersOrderAndReasons() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("discovery_personal")) }
        let list = try await client(t).discoveryList("personal", count: 10)
        #expect(list.items.first?.artist == "Black Sabbath" && list.items.first?.album == "Paranoid")
        #expect(list.items.first?.suggestedTracks?.first == "Paranoid")
        #expect(t.sent[0].url!.path == "/api/discovery/personal" && t.sent[0].url!.query == "count=10")
    }

    @Test func anEmptyListCarriesTheServersMessage() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("discovery_classics")) }
        let list = try await client(t).discoveryList("classics")
        #expect(list.items.isEmpty && list.message == "No saved list yet. Use discovery_refresh_list or wait for the daily background refresh.")
    }

    @Test func savedListReadsItsItems() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("discovery_for_me")) }
        let list = try await client(t).discoveryList("for_me")
        #expect(list.items.map(\.album) == ["Contract Fixture Album"])
    }

    @Test func buildPostsTheCountClampedToTwenty() async throws {
        let t = MockTransport { _, _ in (200, Data(#"{"ok":true}"#.utf8)) }
        try await client(t).refreshDiscoveryList("classics", count: 99)
        #expect(t.sent[0].url!.path == "/api/discovery/classics/refresh" && t.sent[0].httpMethod == "POST")
        let b = try JSONSerialization.jsonObject(with: t.sent[0].httpBody ?? Data()) as? [String: Any]
        #expect(b?["count"] as? Int == 20)
    }
}
