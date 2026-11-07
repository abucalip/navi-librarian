import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

@Suite("Sonic similarity client") struct SonicTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")
    func client(_ t: MockTransport) throws -> LibrarianClient { try LibrarianClient(baseURL: base, credential: cred, transport: t) }

    @Test func similarKeepsServerOrderAndFields() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("sonic_similar")) }
        let r = try await client(t).sonicSimilar(songID: "s 1", count: 6)
        #expect(r.status == "ok" && r.seed != nil && r.tracks.count == 6)
        #expect(r.tracks.allSatisfy { !$0.songID.isEmpty && !$0.title.isEmpty })
        #expect(r.tracks.first?.similarity != nil)
        let url = t.sent[0].url!
        #expect(url.path == "/api/sonic/similar" && url.query == "id=s%201&count=6")
    }

    @Test func songWithoutAnalysisIsEmptyNotAnError() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("sonic_similar_empty")) }
        let r = try await client(t).sonicSimilar(songID: "s1")
        #expect(r.status == "empty" && r.tracks.isEmpty)
    }

    @Test func pathHasNoScoresAndNoSeed() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("sonic_path")) }
        let r = try await client(t).sonicPath(start: "a", end: "b", count: 6)
        #expect(r.tracks.count == 6 && r.tracks.allSatisfy { $0.similarity == nil })
        #expect(t.sent[0].url!.path == "/api/sonic/path" && t.sent[0].url!.query == "start=a&end=b&count=6")
    }

    @Test func unknownSongAndUnavailableAreErrors() async throws {
        for (name, status) in [("sonic_error_not_found", 404), ("sonic_error_unavailable", 502)] {
            let t = MockTransport { _, _ in (status, try fixtureBody(name)) }
            await #expect(throws: DiscairError.self) { try await client(t).sonicSimilar(songID: "x") }
        }
    }

    @Test func capabilityFlagIsFalseWhenUnknownOrUnreachable() async throws {
        let on = MockTransport { _, _ in (200, Data(#"{"sonic_available": true}"#.utf8)) }
        #expect(await (try client(on)).sonicAvailable())
        let off = MockTransport { _, _ in (200, Data(#"{"contract_version": 1}"#.utf8)) }
        #expect(await (try client(off)).sonicAvailable() == false)
        let down = MockTransport { _, _ in (502, Data()) }
        #expect(await (try client(down)).sonicAvailable() == false)
    }
}
