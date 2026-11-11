import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

/// Reads the server's own `intelligence/contract-fixtures/taste_*.json`, so the app is tested against what the server sends.
private func tasteBody(_ name: String, file: String = #filePath) throws -> Data {
    let url = URL(fileURLWithPath: file).deletingLastPathComponent().appending(path: "../../../intelligence/contract-fixtures/\(name).json").standardized
    let object = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
    return try JSONSerialization.data(withJSONObject: object["response"]!)
}

@Suite("Taste client") struct TasteClientTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")
    func client(_ t: MockTransport) throws -> LibrarianClient { try LibrarianClient(baseURL: base, credential: cred, transport: t) }

    @Test func richFixtureKeepsTheServersHeadlineAndShifts() async throws {
        let body = try tasteBody("taste_rich")
        let t = MockTransport { _, _ in (200, body) }
        let r = try await client(t).taste()
        #expect(t.sent[0].httpMethod == "GET" && t.sent[0].url!.path == "/api/insights/taste")
        let p = try #require(r.profiles)
        #expect(p.headline?.text == "More jazz, less rock lately." && p.headline?.window == "recent" && p.headline?.kind == "pair")
        #expect(p.shifts(in: "recent").map(\.value).sorted() == ["jazz", "rock"])
        #expect(p.window("all_time")?.entries("genre").first == TasteEntry(value: "rock", count: 14, share: 0.7))
        #expect(p.window("recent")?.isLowSample("era") == true)
        #expect(p.config.minListens == 4 && p.config.recentDays == 90)
    }

    @Test func thinWindowFixtureCarriesTheMidHeadline() async throws {
        let t = MockTransport { _, _ in (200, try tasteBody("taste_thin_window")) }
        let p = try #require(try await client(t).taste().profiles)
        #expect(p.headline?.window == "mid" && p.window("recent")?.lowSample == true)
    }

    @Test func emptyFixtureMeansNotComputedYet() async throws {
        let t = MockTransport { _, _ in (200, try tasteBody("taste_empty")) }
        let r = try await client(t).taste()
        #expect(r.profiles?.headline == nil)
    }

    @Test func aMissingProfilesBodyIsNil() throws {
        let r = try JSONDecoder().decode(TasteResponse.self, from: Data(#"{"profiles":null,"context":null,"data_version":0,"generation":1}"#.utf8))
        #expect(r.profiles == nil && r.generation == 1)
    }

    @Test func anUnknownFlagCountsAsLowSample() throws {
        let w = try JSONDecoder().decode(TasteWindow.self, from: Data(#"{"listens":9}"#.utf8))
        #expect(w.lowSample && w.isLowSample("genre"))
    }

    @Test func refreshPostsAndReadsTheState() async throws {
        let t = MockTransport { _, _ in (200, Data(#"{"state":"too_soon","run_id":3,"changed":false,"retry_after":1800.5,"progress":{},"error":null}"#.utf8)) }
        let r = try await client(t).refreshTaste()
        #expect(t.sent[0].httpMethod == "POST" && t.sent[0].url!.path == "/api/insights/taste/refresh")
        #expect(r.state == "too_soon" && r.retryAfter == 1800.5 && !r.changed)
    }

    @Test func anOverlappingRefreshIsAnError() async throws {
        let t = MockTransport { _, _ in (409, Data(#"{"detail":"A taste refresh is already running."}"#.utf8)) }
        await #expect(throws: (any Error).self) { try await client(t).refreshTaste() }
    }
}

@Suite("Taste context client") struct TasteContextClientTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")
    func client(_ t: MockTransport) throws -> LibrarianClient { try LibrarianClient(baseURL: base, credential: cred, transport: t) }

    @Test func timeOfDayListensAreReadPerContext() async throws {
        let t = MockTransport { _, _ in (200, try tasteBody("taste_context")) }
        let ctx = try #require(try await client(t).taste().context)
        #expect(ctx.timezone == "UTC" && ctx.listens == 470)
        #expect(ctx.listensIn("night") == 60 && ctx.listensIn("morning") == 120)
        #expect(ctx.listensIn("afternoon") == 90 && ctx.listensIn("evening") == 200)
        #expect(ctx.timeOfDay("missing") == nil && ctx.listensIn("missing") == 0)
    }

    @Test func lowSampleContrastComparesNothing() async throws {
        let t = MockTransport { _, _ in (200, try tasteBody("taste_context")) }
        let c = try #require(try await client(t).taste().context?.contrast)
        #expect(c.state == "low_sample" && c.minListens == 100)
        #expect(c.listens == ["night": 60, "morning": 120])
        #expect(c.entries.isEmpty)
    }

    @Test func statedContrastListsEachValueWithItsShareOnBothSides() async throws {
        let t = MockTransport { _, _ in (200, try tasteBody("taste_context_contrast")) }
        let c = try #require(try await client(t).taste().context?.contrast)
        #expect(c.state == "stated" && !c.entries.isEmpty)
        for e in c.entries {
            #expect(["genre", "era", "area", "label", "collaborator"].contains(e.dimension))
            #expect((0...1).contains(e.morning) && (0...1).contains(e.night))
        }
    }

    @Test func oldBodyWithoutContextStillDecodes() async throws {
        let t = MockTransport { _, _ in (200, try tasteBody("taste_rich")) }
        let r = try await client(t).taste()
        #expect(r.context == nil && r.profiles?.headline != nil)
    }
}
