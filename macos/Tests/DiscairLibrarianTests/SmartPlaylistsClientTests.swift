import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

private func contractFixture(_ name: String, file: String = #filePath) throws -> [String: Any] {
    let url = URL(fileURLWithPath: file).deletingLastPathComponent().appending(path: "../../../intelligence/contract-fixtures/\(name).json").standardized
    return try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
}

@Suite("Smart playlists client") struct SmartPlaylistsClientTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")
    func client(_ t: MockTransport) throws -> LibrarianClient { try LibrarianClient(baseURL: base, credential: cred, transport: t) }

    @Test func listFixtureDecodesIncludingInsightFields() async throws {
        let body = try JSONSerialization.data(withJSONObject: try contractFixture("smart_playlists_list")["response"]!)
        let t = MockTransport { _, _ in (200, body) }
        let lists = try await client(t).smartPlaylists()
        #expect(t.sent[0].httpMethod == "GET" && t.sent[0].url!.path == "/api/playlists/smart")
        #expect(lists.count == 1 && lists[0].ruleID == "00000001-0000-4000-8000-00000005ba17")
        #expect(lists[0].order == "most_played" && lists[0].limit == 25 && lists[0].rules.count == 4)
        #expect(lists[0].rules[2].field == "obscurity_band")
    }

    @Test func emptyFixtureIsAnEmptyList() async throws {
        let body = try JSONSerialization.data(withJSONObject: try contractFixture("smart_playlists_empty")["response"]!)
        let t = MockTransport { _, _ in (200, body) }
        #expect(try await client(t).smartPlaylists().isEmpty)
    }

    @Test func putSendsContractKeysAndAnExplicitNullLimit() async throws {
        let t = MockTransport { _, _ in (200, Data("{\"status\":\"created\"}".utf8)) }
        let p = ServerSmartPlaylist(ruleID: "00000001-0000-4000-8000-00000005BA17", name: "Mix", match: "any",
                                    rules: [ServerSmartRule(field: "played_days_ago", op: "at_least", value: "30")], order: "title", limit: nil)
        try await client(t).putSmartPlaylist(p)
        let req = t.sent[0]
        #expect(req.httpMethod == "PUT" && req.url!.path == "/api/playlists/smart/00000001-0000-4000-8000-00000005ba17")
        let sent = try JSONSerialization.jsonObject(with: req.httpBody!) as! [String: Any]
        #expect(sent["name"] as? String == "Mix" && sent["match"] as? String == "any" && sent["order"] as? String == "title")
        #expect(sent.keys.contains("limit") && sent["limit"] is NSNull)
        #expect(sent["rule_id"] == nil)
    }

    @Test func rejectedPutThrowsAndMissingDeleteIsFine() async throws {
        let bad = MockTransport { _, _ in (400, Data("{\"status\":\"rejected\"}".utf8)) }
        let p = ServerSmartPlaylist(ruleID: "x", name: "", match: "all", rules: [], order: "random", limit: nil)
        await #expect(throws: DiscairError.self) { try await client(bad).putSmartPlaylist(p) }
        let gone = MockTransport { _, _ in (404, Data("{\"detail\":\"not found\"}".utf8)) }
        try await client(gone).deleteSmartPlaylist(id: "ABC")
        #expect(gone.sent[0].httpMethod == "DELETE" && gone.sent[0].url!.path == "/api/playlists/smart/abc")
    }
}
