import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

/// Reads the server's own `intelligence/contract-fixtures/insights_*.json` (format: `request` and `response`), so the app is tested
/// against the exact files the server tests rebuild, with no copy to drift. Swift tests run locally from the repository.
func insightsBody(_ name: String, file: String = #filePath) throws -> Data {
    let root = URL(fileURLWithPath: file).deletingLastPathComponent().appending(path: "../../../intelligence/contract-fixtures/\(name).json").standardized
    let object = try JSONSerialization.jsonObject(with: Data(contentsOf: root)) as! [String: Any]
    return try JSONSerialization.data(withJSONObject: object["response"]!)
}

@Suite("Insight cards") struct InsightCardsTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")

    @Test func everyLensIsOffByDefaultAndShowsNoCards() throws {
        let r = try JSONDecoder().decode(InsightsResponse.self, from: insightsBody("insights_all_off"))
        #expect(r.lenses.count == 5)
        #expect(r.lenses.values.allSatisfy { !$0.enabled && $0.cards.isEmpty })
        #expect(r.orderedKinds == ["forgotten_gem", "series_completion", "blind_spot", "hidden_canon", "anniversary"])
    }

    @Test func enabledLensesCarryExplainableCards() throws {
        let r = try JSONDecoder().decode(InsightsResponse.self, from: insightsBody("insights_three_on"))
        let on = r.orderedKinds.filter { r.lenses[$0]!.enabled }
        #expect(on == ["series_completion", "hidden_canon", "anniversary"])
        for kind in on {
            let card = try #require(r.lenses[kind]!.cards.first)
            #expect(card.kind == kind && !card.title.isEmpty && !card.body.isEmpty)
            #expect(!card.subject.key.isEmpty && !card.reasons.isEmpty && card.dismissible)
        }
        #expect(r.lenses["blind_spot"]!.enabled == false)
    }

    @Test func seriesCardKeepsCountersAndMissingRuns() throws {
        let r = try JSONDecoder().decode(InsightsResponse.self, from: insightsBody("insights_three_on"))
        let card = try #require(r.lenses["series_completion"]!.cards.first)
        #expect(card.owned == 2 && card.total == 4)
        #expect(card.missingRuns.first?.firstPosition == 3 && card.missingRuns.first?.lastPosition == 4)
        #expect(card.subject.key == "series_completion:fx-series")
    }

    @Test func evidenceIsShownAsPlainText() throws {
        let r = try JSONDecoder().decode(InsightsResponse.self, from: insightsBody("insights_three_on"))
        let reason = try #require(r.lenses["anniversary"]!.cards.first?.reasons.first)
        #expect(reason.evidence["years"]?.text == "10" && reason.evidence["date"]?.text == "2016-06-01")
    }

    @Test func aCardWithoutAKeyOrReasonsIsDroppedAndUnknownLensesFollow() throws {
        let json = """
        {"lenses":{"zeta":{"enabled":true,"cards":[
           {"kind":"zeta","title":"No key","body":"x","subject":{"key":""},"reasons":[{"kind":"r"}]},
           {"kind":"zeta","title":"No reasons","body":"x","subject":{"key":"k"},"reasons":[]},
           {"kind":"zeta","title":"Fine","body":"x","subject":{"key":"k2"},"reasons":[{"kind":"r"}],"surprise":1}]},
         "anniversary":{"enabled":false,"cards":[]}},"data_version":1,"generation":1}
        """
        let r = try JSONDecoder().decode(InsightsResponse.self, from: Data(json.utf8))
        #expect(r.lenses["zeta"]!.cards.map(\.title) == ["Fine"])
        #expect(r.orderedKinds == ["anniversary", "zeta"])
    }

    @Test func clientAsksForTheClampedLimit() async throws {
        let t = MockTransport { _, _ in (200, try insightsBody("insights_all_off")) }
        let c = try LibrarianClient(baseURL: base, credential: cred, transport: t)
        let r = try await c.insights(limit: 5000)
        #expect(r.lenses.count == 5)
        #expect(t.sent[0].httpMethod == "GET" && t.sent[0].url!.path == "/api/insights")
        #expect(t.sent[0].url!.query == "limit=100")
    }
}
