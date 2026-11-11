import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

/// The feeds behind the redesigned Home. The radio and popularity routes exist on the server; the insight-refresh status route
/// and `listens_by_day` (D2, D3) are proposals, so those answers are tested from the contract in `docs/SERVER_V2_CONTRACT.md`.
@Suite("Home feeds client") struct HomeFeedsClientTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")
    func client(_ t: MockTransport) throws -> LibrarianClient { try LibrarianClient(baseURL: base, credential: cred, transport: t) }
    func json(_ s: String) -> Data { Data(s.utf8) }

    @Test func radioPlaysDecodeAndOneBadRowDoesNotHideTheRest() async throws {
        let body = json(#"{"items":[{"id":7,"station_id":"fip","station_name":"FIP","raw_title":"x","artist":"The Blue Nile","title":"Sea Song","album":null,"year":null,"listened_seconds":120,"heard_at":1794398400.5,"last_heard_at":1794398500,"grabbed":0,"scrobbled":0,"loved":0,"in_library":false},{"station_name":"broken"},{"id":8,"station_name":"FIP","title":"B","heard_at":1,"grabbed":1,"in_library":true}]}"#)
        let t = MockTransport { _, _ in (200, body) }
        let plays = try await client(t).radioPlays(limit: 50)
        #expect(t.sent[0].url!.path == "/api/radio/plays" && t.sent[0].url!.query == "limit=50")
        #expect(plays.map(\.id) == [7, 8])
        #expect(plays[0] == RadioPlay(id: 7, stationName: "FIP", artist: "The Blue Nile", title: "Sea Song", heardAt: 1794398400.5))
        #expect(plays[1].grabbed && plays[1].inLibrary && plays[1].artist == nil)
    }

    @Test func radioGetCarriesTheServersSentence() async throws {
        let t = MockTransport { _, _ in (200, self.json(#"{"ok":false,"message":"Could not find which album this song is on."}"#)) }
        let r = try await client(t).getRadioPlay(id: 7)
        #expect(t.sent[0].httpMethod == "POST" && t.sent[0].url!.path == "/api/radio/plays/7/get")
        #expect(!r.ok && r.message == "Could not find which album this song is on.")
        let ok = MockTransport { _, _ in (200, self.json(#"{"ok":true,"status":"downloading","album":"Hats"}"#)) }
        #expect(try await client(ok).getRadioPlay(id: 8).album == "Hats")
    }

    @Test func popularityStatusReadsTheRunnerShape() async throws {
        let body = json(#"{"status":{"id":4,"job":"taste_popularity","scope":"","generation":1,"state":"succeeded","progress":{"requests":5,"filled":380,"absent":12,"pending":340},"started_at":100.0,"finished_at":160.5,"error":null},"last_good":{"state":"succeeded","progress":{"pending":340},"finished_at":160.5},"running":false}"#)
        let t = MockTransport { _, _ in (200, body) }
        let s = try await client(t).popularityStatus()
        #expect(t.sent[0].url!.path == "/api/insights/popularity/status")
        #expect(s.status?.state == "succeeded" && s.status?.progress["pending"] == 340 && s.lastGood?.finishedAt == 160.5 && !s.running)
        #expect(s.retryAfter == nil && s.minInterval == nil)
    }

    @Test func emptyStatusIsNilRunsNotZero() async throws {
        let t = MockTransport { _, _ in (200, self.json(#"{"status":null,"last_good":null,"running":false}"#)) }
        let s = try await client(t).popularityStatus()
        #expect(s.status == nil && s.lastGood == nil)
    }

    @Test func fillSendsABoundedBatchAndReadsTheAnswer() async throws {
        let t = MockTransport { _, _ in (200, self.json(#"{"run_id":9,"state":"queued","progress":{"requests":5,"filled":400,"absent":3,"pending":280},"error":null,"max_requests":5}"#)) }
        let r = try await client(t).fillPopularity(maxRequests: 99)
        #expect(t.sent[0].httpMethod == "POST" && t.sent[0].url!.path == "/api/insights/popularity/fill")
        #expect(String(decoding: t.sent[0].httpBody ?? Data(), as: UTF8.self).contains("\"max_requests\":20"))
        #expect(r.state == "queued" && r.progress["pending"] == 280 && r.error == nil)
    }

    @Test func insightsRefreshStatusIsShapedLikeTheTasteOne() async throws {
        let body = json(#"{"status":{"state":"succeeded","progress":{},"finished_at":1794391200},"last_good":{"state":"succeeded","finished_at":1794391200},"running":false,"min_interval":21600,"retry_after":14400.0}"#)
        let t = MockTransport { _, _ in (200, body) }
        let s = try await client(t).insightsRefreshStatus()
        #expect(t.sent[0].url!.path == "/api/insights/refresh/status")
        #expect(s.retryAfter == 14400 && s.minInterval == 21600 && s.lastGood?.finishedAt == 1794391200)
        let taste = MockTransport { _, _ in (200, body) }
        _ = try await client(taste).tasteRefreshStatus()
        #expect(taste.sent[0].url!.path == "/api/insights/taste/refresh/status")
    }

    @Test func tasteBodyCarriesListensByDayWhenServedAndNilWhenNot() async throws {
        let served = json(#"{"profiles":null,"context":null,"data_version":1,"generation":1,"listens_by_day":[{"date":"2026-11-09","count":31},{"date":"2026-11-10","count":0},{"bad":true}]}"#)
        let t = MockTransport { _, _ in (200, served) }
        #expect(try await client(t).taste().listensByDay == [ListensDay(date: "2026-11-09", count: 31), ListensDay(date: "2026-11-10", count: 0)])
        let absent = MockTransport { _, _ in (200, self.json(#"{"profiles":null,"context":null,"data_version":1,"generation":1}"#)) }
        #expect(try await client(absent).taste().listensByDay == nil)
    }
}
