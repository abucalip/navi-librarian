import Testing
import Foundation
@testable import DiscairLibrarian

@Suite("Insight Why paragraphs") struct InsightNarrativeTests {
    private func cards() throws -> [String: InsightCard] {
        let r = try JSONDecoder().decode(InsightsResponse.self, from: insightsBody("insights_three_on"))
        return Dictionary(uniqueKeysWithValues: r.lenses.compactMap { k, l in l.cards.first.map { (k, $0) } })
    }
    private func card(_ json: String) throws -> InsightCard { try JSONDecoder().decode(InsightCard.self, from: Data(json.utf8)) }

    @Test func seriesNamesCountsAndTheMissingRun() throws {
        let t = InsightNarrative.why(try #require(cards()["series_completion"]))
        #expect(t == "Example label catalogue is a series on MusicBrainz with 4 releases, and your library holds 2 of them. The 2 you do not have form one run (positions 3 to 4: Title 2 (2002) and Title 3 (2003)).")
    }

    @Test func hiddenCanonUsesListensGenreAndRank() throws {
        let t = InsightNarrative.why(try #require(cards()["hidden_canon"]))
        #expect(t == "Loveless by My Bloody Valentine (1991) has been listened to 5,000 times on ListenBrainz. It belongs to shoegaze, which is your top genre, and it is not in your library.")
    }

    @Test func anniversaryStatesTheDateAndYears() throws {
        let t = InsightNarrative.why(try #require(cards()["anniversary"]))
        #expect(t == "Example Album by Example Artist was released on 1 June 2016, which is 10 years ago today.")
    }

    @Test func forgottenGemJoinsItsReasonsIntoOneSentence() throws {
        let c = try card(#"{"kind":"forgotten_gem","title":"Third","body":"x","subject":{"key":"k","title":"Third","artist":"Portishead"},"reasons":[{"kind":"dormant","evidence":{"days_since_last_play":900}},{"kind":"played_often","evidence":{"play_count":212}},{"kind":"starred","evidence":{}},{"kind":"rated","evidence":{"rating":5}}]}"#)
        #expect(InsightNarrative.why(c) == "You have not played Third by Portishead for about 2 years. Before that you played it 212 times, starred it and rated it 5 out of 5.")
    }

    @Test func blindSpotComparesWithoutAdvising() throws {
        let c = try card(#"{"kind":"blind_spot","title":"Radiohead","body":"x","subject":{"key":"k","artist":"Radiohead"},"reasons":[{"kind":"comparison_set","evidence":{"set_kind":"studio_release_groups","source":"musicbrainz","owned":5,"total":9}}]}"#)
        let t = InsightNarrative.why(c)
        #expect(t == "MusicBrainz lists 9 studio release groups for Radiohead, and your library holds 5 of them. The other 4 are shown as a comparison, not as a recommendation.")
        #expect(!t.lowercased().contains("should"))
    }

    @Test func anUnknownKindStillExplainsItself() throws {
        let c = try card(#"{"kind":"mood_match","title":"Dub","body":"x","subject":{"key":"k"},"reasons":[{"kind":"mood_fit","evidence":{"tempo":70}}]}"#)
        #expect(InsightNarrative.why(c) == "Dub is shown because of mood fit (tempo 70).")
    }

    @Test func missingNumbersFallBackToTheGenericText() throws {
        let c = try card(#"{"kind":"hidden_canon","title":"Loveless","body":"x","subject":{"key":"k"},"reasons":[{"kind":"taste_vs_world","evidence":{}}]}"#)
        #expect(InsightNarrative.why(c) == "Loveless is shown because of taste vs world.")
    }
}
