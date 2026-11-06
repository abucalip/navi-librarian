import Foundation
import Testing
import DiscairLibrarian
@testable import DiscairUI

@MainActor @Suite("Insights model") struct InsightsModelTests {
    /// An outbox that never reaches the server, so queued events stay visible to the test.
    private func localOutbox() -> FeedbackOutbox {
        let file = FileManager.default.temporaryDirectory.appending(path: "insights-dismiss-\(UUID().uuidString)/feedback-outbox.json")
        return FeedbackOutbox(fileURL: file, send: { _ in throw FeedbackUnavailable() })
    }

    /// The dismissal event is queued by a detached task, so wait briefly for it.
    private func pendingEvents(_ box: FeedbackOutbox) async -> [FeedbackEvent] {
        for _ in 0..<100 {
            let queued = await box.pending
            if !queued.isEmpty { return queued }
            try? await Task.sleep(for: .milliseconds(10))
        }
        return await box.pending
    }

    @Test func dismissQueuesOneCardEventKeyedBySubject() async throws {
        let m = InsightsModel()
        let box = localOutbox()
        m.configureFeedback(box)
        let card = try #require(m.cards("hidden_canon").first)

        m.dismiss(card, librarian: nil)

        let queued = await pendingEvents(box)
        #expect(queued.count == 1)
        let event = try #require(queued.first)
        #expect(event.kind == .dismiss && event.subjectKind == .card && event.subjectID == card.subject.key)
        #expect(event.client == "macos" && event.mbid == nil && event.playedSeconds == nil)
        #expect(abs(event.occurredAt - Date().timeIntervalSince1970) < 60)
    }

    @Test func aCardWithoutAKeyQueuesNothing() async throws {
        let m = InsightsModel()
        let box = localOutbox()
        m.configureFeedback(box)
        let json = #"{"kind":"hidden_canon","title":"Untitled","body":"","subject":{"key":""},"reasons":[],"dismissible":true,"score":1}"#
        let card = try JSONDecoder().decode(InsightCard.self, from: Data(json.utf8))

        m.dismiss(card, librarian: nil)

        try await Task.sleep(for: .milliseconds(100))
        #expect(await box.pending.isEmpty)
        #expect(m.lastDismissed?.id == card.id)   // the card is still hidden and undoable on screen
    }

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
