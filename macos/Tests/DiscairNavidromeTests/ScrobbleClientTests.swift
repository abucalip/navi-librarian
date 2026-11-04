import Testing
import Foundation
import DiscairCore
@testable import DiscairNavidrome

@Suite("Scrobble client") struct ScrobbleClientTests {
    let base = URL(string: "https://navi.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw")
    let ok = Data(#"{"subsonic-response":{"status":"ok","version":"1.16.1"}}"#.utf8)
    let started = Date(timeIntervalSince1970: 1_700_000_000.5)

    func client(_ t: MockTransport) throws -> NavidromeClient { try NavidromeClient(baseURL: base, credential: cred, transport: t) }

    @Test func sendsIdTimeInMillisecondsAndSubmissionFlag() async throws {
        let t = MockTransport { _ in (200, self.ok) }
        let c = try client(t)
        #expect(await c.scrobble(songID: "abc123", time: started, submission: false) == .sent)
        #expect(await c.scrobble(songID: "abc123", time: started, submission: true) == .sent)
        #expect(t.sent[0].url!.path == "/rest/scrobble")
        #expect(queryValue(t.sent[0], "id") == "abc123" && queryValue(t.sent[0], "time") == "1700000000500")
        #expect(queryValue(t.sent[0], "submission") == "false" && queryValue(t.sent[1], "submission") == "true")
    }

    @Test func aRefusedConnectionWasNeverSent() async throws {
        let t = MockTransport { _ in throw URLError(.cannotConnectToHost) }
        #expect(await (try client(t)).scrobble(songID: "a1", time: started, submission: true) == .notSent)
        let dns = MockTransport { _ in throw URLError(.dnsLookupFailed) }
        #expect(await (try client(dns)).scrobble(songID: "a1", time: started, submission: true) == .notSent)
    }

    @Test func aTimeoutResetOrServerErrorMayHaveArrived() async throws {
        for failure in [URLError(.timedOut), URLError(.networkConnectionLost)] {
            let t = MockTransport { _ in throw failure }
            #expect(await (try client(t)).scrobble(songID: "a1", time: started, submission: true) == .unknown)
        }
        let five = MockTransport { _ in (503, Data()) }
        #expect(await (try client(five)).scrobble(songID: "a1", time: started, submission: true) == .unknown)
        let junk = MockTransport { _ in (200, Data("not json".utf8)) }
        #expect(await (try client(junk)).scrobble(songID: "a1", time: started, submission: true) == .unknown)
        let err = MockTransport { _ in (200, Data(#"{"subsonic-response":{"status":"failed","version":"1.16.1","error":{"code":70,"message":"x"}}}"#.utf8)) }
        #expect(await (try client(err)).scrobble(songID: "a1", time: started, submission: true) == .unknown)
    }
}
