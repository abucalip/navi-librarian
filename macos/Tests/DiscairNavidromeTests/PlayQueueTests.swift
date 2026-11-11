import Testing
import Foundation
import DiscairCore
@testable import DiscairNavidrome

@Suite("Play queue (phone handoff)") struct PlayQueueTests {
    let base = URL(string: "https://navi.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw")
    func client(_ t: MockTransport) throws -> NavidromeClient { try NavidromeClient(baseURL: base, credential: cred, transport: t) }
    func reply(_ inner: String) -> Data { Data(#"{"subsonic-response":{"status":"ok","version":"1.16.1"\#(inner)}}"#.utf8) }

    @Test func readsTheQueueAnotherClientSaved() async throws {
        let body = reply(#","playQueue":{"current":"s2","position":161000,"username":"owner","changed":"2026-11-11T09:30:00.123Z","changedBy":"discair-android","entry":[{"id":"s1","title":"One"},{"id":"s2","title":"Ascension Day","artist":"Talk Talk","duration":360}]}"#)
        let t = MockTransport { _ in (200, body) }
        let q = try #require(try await client(t).playQueue())
        #expect(t.sent[0].url!.path == "/rest/getPlayQueue")
        #expect(q.current?.title == "Ascension Day" && q.positionMs == 161_000 && q.changedBy == "discair-android" && q.songs.count == 2)
        #expect(q.changed != nil)
    }

    @Test func aNumericCurrentIdIsAccepted() async throws {
        let body = reply(#","playQueue":{"current":2,"position":5,"entry":[{"id":"2","title":"T"}]}"#)
        let q = try #require(try await client(MockTransport { _ in (200, body) }).playQueue())
        #expect(q.currentID == "2" && q.current?.title == "T" && q.changed == nil)
    }

    @Test func noSavedQueueIsNilNotAnEmptyOffer() async throws {
        #expect(try await client(MockTransport { _ in (200, self.reply("")) }).playQueue() == nil)
        let empty = reply(#","playQueue":{"entry":[]}"#)
        #expect(try await client(MockTransport { _ in (200, empty) }).playQueue() == nil)
    }
}
