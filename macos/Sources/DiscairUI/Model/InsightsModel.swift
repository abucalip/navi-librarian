import DiscairLibrarian
import Foundation
import Observation

/// The three lenses the server's fixture turns on, shown until a session connects (previews and screenshots) so both
/// themes can be judged with cards on screen. Live data always replaces it.
enum InsightsSample {
    static let json = """
    {"data_version":3,"generation":1,"lenses":{
     "forgotten_gem":{"enabled":false,"cards":[]},
     "blind_spot":{"enabled":false,"cards":[]},
     "series_completion":{"enabled":true,"cards":[{"kind":"series_completion","title":"Example label catalogue","body":"You own 2 of 4 in this series; 2 not in your library.","owned":2,"total":4,"score":0.5,"dismissible":true,
       "subject":{"key":"series_completion:fx-series","type":"series","title":"Example label catalogue"},
       "missing_runs":[{"first_position":3,"last_position":4,"items":[{"title":"Title 2","year":2002},{"title":"Title 3","year":2003}]}],
       "reasons":[{"kind":"series_progress","evidence":{"source":"musicbrainz","owned":2,"total":4,"missing_runs":1}}]}]},
     "hidden_canon":{"enabled":true,"cards":[{"kind":"hidden_canon","title":"Loveless","body":"Heard 5,000 times worldwide; matches your top genre shoegaze; not in your library.","score":1.0,"dismissible":true,
       "subject":{"key":"hidden_canon:fx-w1","type":"release_group","title":"Loveless","artist":"My Bloody Valentine","year":1991},
       "reasons":[{"kind":"taste_vs_world","evidence":{"source":"listenbrainz","listens":5000,"matched_genre":"shoegaze","genre_rank":1}}]}]},
     "anniversary":{"enabled":true,"cards":[{"kind":"anniversary","title":"Example Album","body":"Released 10 years ago today (2016-06-01).","score":10.0,"dismissible":true,
       "subject":{"key":"anniversary:album_release:fx-a1:2026","type":"release_group","title":"Example Album","artist":"Example Artist"},
       "reasons":[{"kind":"anniversary","evidence":{"event":"album_release","date":"2016-06-01","years":10}}]}]}}}
    """
    static var response: InsightsResponse { try! JSONDecoder().decode(InsightsResponse.self, from: Data(json.utf8)) }
}

/// Insights dashboard state: what the server says per lens, which cards the owner dismissed this session (so Undo works),
/// and which card's "Why?" is open. A lens the server did not enable shows as off; this model never invents cards.
@MainActor
@Observable
public final class InsightsModel {
    public private(set) var response: InsightsResponse = InsightsSample.response
    public private(set) var isLive = false
    public private(set) var loading = false
    public private(set) var error: String?
    /// When the cards on screen were last read from the server (nil for the sample).
    public private(set) var loadedAt: Date?
    /// How often an open Insights page reads again.
    public static let refreshSeconds = 300
    public var updatedText: String? { loadedAt.map { "Updated " + $0.formatted(date: .omitted, time: .shortened) + "." } }
    /// Card ids hidden now. Kept after a failed write too, so the owner never sees a card come back by surprise.
    public private(set) var hidden: Set<String> = []
    public private(set) var lastDismissed: InsightCard?
    public var openWhy: String?
    @ObservationIgnored private var feedback: FeedbackOutbox?

    public init() {}

    /// Sends each card dismissal to the feedback outbox (record-only, D-027). Set once the session is connected.
    public func configureFeedback(_ outbox: FeedbackOutbox) { feedback = outbox }

    public func load(librarian: LibrarianClient?) async {
        guard let librarian else { return }
        loading = true; defer { loading = false }
        do {
            response = try await librarian.insights(limit: 20)
            isLive = true; error = nil; loadedAt = Date()
        } catch {
            // Keep what is on screen; say plainly that the server could not be read.
            self.error = Self.message(error)
        }
    }

    /// Preview and test seam: shows a prepared answer without a server.
    func showForPreview(_ r: InsightsResponse, live: Bool = true) { response = r; isLive = live; loadedAt = live ? Date() : nil }

    public func cards(_ kind: String) -> [InsightCard] { (response.lenses[kind]?.cards ?? []).filter { !hidden.contains($0.id) } }
    public func isEnabled(_ kind: String) -> Bool { response.lenses[kind]?.enabled ?? false }
    /// Kinds shown on the dashboard: the five known ones always (so "off" is visible), then any kind the server added.
    public var kinds: [String] {
        let known = InsightsResponse.knownOrder
        return known + response.orderedKinds.filter { !known.contains($0) }
    }
    public var shownCount: Int { kinds.reduce(0) { $0 + cards($1).count } }

    public func toggleWhy(_ card: InsightCard) { openWhy = openWhy == card.id ? nil : card.id }

    public func dismiss(_ card: InsightCard, librarian: LibrarianClient?) {
        hidden.insert(card.id); lastDismissed = card
        if openWhy == card.id { openWhy = nil }
        recordDismissal(card)
        guard let librarian, isLive else { return }
        Task {
            do { try await librarian.dismissInsight(kind: card.kind, key: card.subject.key) }
            catch { self.error = "Could not save the dismissal: " + Self.message(error) }
        }
    }

    /// Queues a `dismiss` event for the card, keyed by its subject key (`docs/SERVER_V2_CONTRACT.md`, `POST /api/feedback/events`).
    /// Queued even when the server is offline, so the outbox sends it later. Nothing is sent for a card without a key.
    private func recordDismissal(_ card: InsightCard) {
        let key = card.subject.key
        guard let feedback, !key.isEmpty, key.count <= 200 else { return }
        let event = FeedbackEvent(kind: .dismiss, subjectKind: .card, subjectID: key, occurredAt: Date().timeIntervalSince1970)
        Task { await feedback.enqueue(event); await feedback.flush() }
    }

    public func undoDismiss(librarian: LibrarianClient?) {
        guard let card = lastDismissed else { return }
        hidden.remove(card.id); lastDismissed = nil
        guard let librarian, isLive else { return }
        Task { try? await librarian.restoreInsight(kind: card.kind, key: card.subject.key) }
    }

    public func clearUndo() { lastDismissed = nil }

    /// Records Get / Play on a card as an accept (scorecard input only). Silent on failure: it must never block the action.
    public func accepted(_ card: InsightCard, librarian: LibrarianClient?) {
        guard let librarian, isLive else { return }
        Task { try? await librarian.acceptInsight(kind: card.kind, key: card.subject.key) }
    }

    /// A Get / Save target for cards that point at an album the library lacks (hidden canon, blind spots).
    public static func album(for card: InsightCard) -> AlbumItem? {
        guard card.kind == "hidden_canon" || card.kind == "blind_spot",
              let title = card.subject.title, let artist = card.subject.artist else { return nil }
        var h = 5381; for u in card.subject.key.unicodeScalars { h = (h &* 33 &+ Int(u.value)) & 0x7fffff }
        return AlbumItem(id: 900_000 + h, title: title, artist: artist, year: card.subject.year ?? 0, genre: "", format: "", owned: false,
                         hue: Double(h % 360), reason: card.body)
    }

    static func message(_ error: Error) -> String { (error as? LocalizedError)?.errorDescription ?? "the server did not answer" }
}
