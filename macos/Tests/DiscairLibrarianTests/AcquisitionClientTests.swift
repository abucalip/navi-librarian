import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

@Suite("Librarian acquisition") struct AcquisitionClientTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")
    func client(_ t: MockTransport) throws -> LibrarianClient { try LibrarianClient(baseURL: base, credential: cred, transport: t) }
    func body(_ r: URLRequest) -> [String: Any] { (try? JSONSerialization.jsonObject(with: r.httpBody ?? Data())) as? [String: Any] ?? [:] }

    @Test func getAlbumSendsAutoQueueAndReadsARefusal() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("acquire_album")) }
        let r = try await client(t).acquire(artist: "Contract Fixture Artist", album: "Contract Fixture Album", metadata: ["source": "macos"])
        #expect(r.ok == false && r.status == "settings_required")          // HTTP 200, but not a success
        #expect(r.message == "Add the slskd API key in Discovery Settings first.")
        let sent = t.sent[0]
        #expect(sent.url!.path == "/api/acquire" && sent.httpMethod == "POST")
        #expect(body(sent)["auto_queue"] as? Bool == true)
        #expect(body(sent)["artist"] as? String == "Contract Fixture Artist")
        #expect((body(sent)["metadata"] as? [String: String]) == ["source": "macos"])
    }

    @Test func getSongSendsTitleAndOptionalNumber() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("acquire_track")) }
        let r = try await client(t).acquireTrack(artist: "A", album: "B", title: "C", trackNumber: 4)
        #expect(r.ok == false && r.status == "settings_required")
        #expect(t.sent[0].url!.path == "/api/acquire/track")
        #expect(body(t.sent[0])["title"] as? String == "C" && body(t.sent[0])["track_number"] as? Int == 4)
        _ = try await client(t).acquireTrack(artist: "A", album: "B", title: "C", trackNumber: 0)
        #expect(body(t.sent[1])["track_number"] == nil)                      // 0 is not a valid track number
    }

    @Test func listsJobsAndGroupsTheirPhase() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("acquisitions")) }
        let jobs = try await client(t).acquisitions()
        #expect(jobs.count == 1)
        #expect(jobs[0].isSong && jobs[0].title == "Contract Fixture Song" && jobs[0].status == "settings_required")
        #expect(jobs[0].phase == .failed)
        #expect(t.sent[0].httpMethod == "GET" && t.sent[0].url!.path == "/api/acquisitions")
    }

    @Test func readsLiveProgressOfADownload() throws {
        let json = #"{"ok":true,"acquisitions":[{"artist":"Can","album":"Tago Mago","status":"downloading","details":{"live_progress":{"available":true,"total_tracks":7,"completed_tracks":2,"remaining_tracks":5,"percent":41.5,"speed_bytes_per_second":1200000}},"created_at":1.0,"updated_at":2.0}]}"#
        let jobs = try JSONDecoder().decode(AcquisitionsPayload.self, from: Data(json.utf8)).acquisitions
        #expect(jobs[0].phase == .working && jobs[0].details?.liveProgress?.percent == 41.5)
        #expect(jobs[0].details?.liveProgress?.completedTracks == 2 && !jobs[0].isSong)
    }

    @Test func dismissReturnsTheServerMessage() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("acquisitions_dismiss")) }
        let message = try await client(t).dismissAcquisition(artist: "A", album: "B")
        #expect(message?.contains("dismissed") == true)
        #expect(t.sent[0].url!.path == "/api/acquisitions/dismiss")
    }

    @Test func skipRefusalKeepsTheServersText() async throws {
        let t = MockTransport { _, _ in (409, try fixtureBody("acquisitions_skip")) }
        await #expect(throws: DiscairError.server(status: 409, message: "This acquisition is not downloading.")) {
            try await client(t).skipSource(artist: "A", album: "B")
        }
    }

    @Test func feedbackSendsTheActionName() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("discovery_feedback")) }
        let c = try client(t)
        try await c.feedback(artist: "A", album: "B", action: .save)
        try await c.feedback(artist: "A", album: "B", action: .dismissArtist)
        #expect(t.sent.map { body($0)["action"] as? String } == ["save", "dismiss_artist"])
        #expect(t.sent[0].url!.path == "/api/discovery/feedback")
    }

    @Test func aRejectedSessionIsRenewedOnceThenRetried() async throws {
        let t = MockTransport { req, n in
            if req.url!.path == "/api/auth/login" { return (200, try fixtureBody("auth_login")) }
            return n == 1 ? (401, Data(#"{"detail":"Not authenticated"}"#.utf8)) : (200, try fixtureBody("discovery_feedback"))
        }
        try await client(t).feedback(artist: "A", album: "B", action: .dismiss)
        #expect(t.sent.map(\.url!.path) == ["/api/discovery/feedback", "/api/auth/login", "/api/discovery/feedback"])
    }

    @Test func aServerErrorOnFeedbackIsNamed() async throws {
        let t = MockTransport { _, _ in (502, Data(#"{"detail":"Could not save discovery feedback."}"#.utf8)) }
        await #expect(throws: DiscairError.server(status: 502, message: "Could not save discovery feedback.")) {
            try await client(t).feedback(artist: "A", album: "B", action: .save)
        }
    }
}
