import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

private func feedbackFixture(_ name: String, file: String = #filePath) throws -> [String: Any] {
    let url = URL(fileURLWithPath: file).deletingLastPathComponent().appending(path: "../../../intelligence/contract-fixtures/\(name).json").standardized
    return try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
}

@Suite("Feedback events") struct FeedbackEventsTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")

    @Test func fixtureResponseDecodesWithPerItemReasons() throws {
        let fx = try feedbackFixture("feedback_events_first")
        let data = try JSONSerialization.data(withJSONObject: fx["response"]!)
        let r = try JSONDecoder().decode(FeedbackEventsResponse.self, from: data)
        #expect(r.received == 5 && r.inserted == 2 && r.accepted == 3 && r.rejected == 2)
        #expect(r.results[2].accepted && r.results[2].duplicate)
        #expect(!r.results[3].accepted && r.results[3].reason == "bad_played_seconds")
    }

    @Test func replayFixtureStoresNothingNew() throws {
        let fx = try feedbackFixture("feedback_events_replay")
        let r = try JSONDecoder().decode(FeedbackEventsResponse.self, from: JSONSerialization.data(withJSONObject: fx["response"]!))
        #expect(r.inserted == 0)
    }

    @Test func requestUsesTheContractKeysAndOmitsAbsentOnes() async throws {
        let ok = try JSONSerialization.data(withJSONObject: try feedbackFixture("feedback_events_first")["response"]!)
        let t = MockTransport { _, _ in (200, ok) }
        let c = try LibrarianClient(baseURL: base, credential: cred, transport: t)
        let e = FeedbackEvent(eventID: "00000001-0000-4000-8000-00000000f00d", kind: .skip, subjectKind: .track, subjectID: "tr-1",
                              occurredAt: 1699827200, playedSeconds: 12, durationSeconds: 240)
        _ = try await c.reportFeedback([e])
        let req = t.sent[0]
        #expect(req.httpMethod == "POST" && req.url!.path == "/api/feedback/events")
        let sent = try JSONSerialization.jsonObject(with: req.httpBody!) as! [String: Any]
        let ev = (sent["events"] as! [[String: Any]])[0]
        #expect(ev["client"] as? String == "macos" && ev["kind"] as? String == "skip" && ev["subject_kind"] as? String == "track")
        #expect(ev["subject_id"] as? String == "tr-1" && ev["event_id"] as? String == e.eventID)
        #expect(ev["played_seconds"] as? Double == 12 && ev["duration_seconds"] as? Double == 240 && ev["mbid"] == nil)
    }

    @Test func emptyAndOversizeBatchesAreRefusedBeforeSending() async throws {
        let t = MockTransport { _, _ in (200, Data("{}".utf8)) }
        let c = try LibrarianClient(baseURL: base, credential: cred, transport: t)
        await #expect(throws: DiscairError.self) { _ = try await c.reportFeedback([]) }
        let many = (0..<101).map { FeedbackEvent(kind: .dismiss, subjectKind: .card, subjectID: "gem:\($0)", occurredAt: 1) }
        await #expect(throws: DiscairError.self) { _ = try await c.reportFeedback(many) }
        #expect(t.sent.isEmpty)
    }
}
