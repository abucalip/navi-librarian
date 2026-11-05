import Testing
import DiscairLibrarian
@testable import DiscairUI

@MainActor @Suite("Insights model") struct InsightsModelTests {
    @Test func sampleShowsThreeLensesOnAndTwoOff() {
        let m = InsightsModel()
        #expect(m.kinds == InsightsResponse.knownOrder)
        #expect(m.kinds.filter(m.isEnabled) == ["series_completion", "hidden_canon", "anniversary"])
        #expect(m.shownCount == 3)
    }

    @Test func dismissHidesTheCardAndUndoBringsItBack() throws {
        let m = InsightsModel()
        let card = try #require(m.cards("hidden_canon").first)
        m.dismiss(card, librarian: nil)
        #expect(m.cards("hidden_canon").isEmpty && m.lastDismissed?.id == card.id)
        m.undoDismiss(librarian: nil)
        #expect(m.cards("hidden_canon").count == 1 && m.lastDismissed == nil)
    }

    @Test func whyTogglesOneCardAtATime() throws {
        let m = InsightsModel()
        let a = try #require(m.cards("hidden_canon").first), b = try #require(m.cards("anniversary").first)
        m.toggleWhy(a); #expect(m.openWhy == a.id)
        m.toggleWhy(b); #expect(m.openWhy == b.id)
        m.toggleWhy(b); #expect(m.openWhy == nil)
    }

    @Test func onlyAlbumCardsGetAGetTarget() throws {
        let m = InsightsModel()
        let canon = try #require(m.cards("hidden_canon").first)
        let album = try #require(InsightsModel.album(for: canon))
        #expect(album.title == "Loveless" && album.artist == "My Bloody Valentine" && album.year == 1991 && !album.owned)
        #expect(InsightsModel.album(for: canon)?.id == album.id)
        #expect(InsightsModel.album(for: try #require(m.cards("series_completion").first)) == nil)
        #expect(InsightsModel.album(for: try #require(m.cards("anniversary").first)) == nil)
    }
}
