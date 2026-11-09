import DiscairLibrarian
import Foundation
import Observation

/// "Your taste" inside Insights (Server V2 Phase 6 presentation slice 5). Holds the saved profiles the server describes and the
/// picker state. The server writes every sentence and decides every claim: this model states a shift only when the server
/// listed it, and shows a window or dimension the server flagged low-sample as progress, never as a finding.
@MainActor
@Observable
public final class TasteModel {
    public private(set) var profiles: TasteProfiles?
    /// True once a read finished (so "not computed yet" is not confused with "still loading").
    public private(set) var loaded = false
    public private(set) var refreshing = false
    /// One plain line when the last refresh could not run; the saved profiles stay on screen.
    public private(set) var note: String?
    public var window = "recent"
    public var dimension = "genre"
    @ObservationIgnored private var launched = false

    public init() {}

    public func load(librarian: LibrarianClient?) async {
        guard let librarian else { return }
        do {
            profiles = try await librarian.taste().profiles
            loaded = true
        } catch {
            if !loaded { note = "Could not read your taste profile: " + Self.message(error) }
        }
    }

    /// Reads what is saved, then asks the server to refresh once per app launch (owner decision). A changed run is read again.
    /// `too_soon` and `unchanged` need nothing more; a failure keeps the saved profiles and says so.
    public func refreshOnLaunch(librarian: LibrarianClient?) async {
        guard let librarian, !launched else { return }
        launched = true
        await load(librarian: librarian)
        refreshing = true; defer { refreshing = false }
        do {
            let result = try await librarian.refreshTaste()
            switch result.state {
            case "refreshed":
                note = nil
                await load(librarian: librarian)
            case "unchanged", "too_soon": note = nil
            case "no_listens_source": note = "No ListenBrainz account is set on the server, so taste cannot be computed yet."
            default: note = "The taste refresh did not finish" + (result.error.map { ": \($0)" } ?? "") + ". Showing what was last saved."
            }
        } catch {
            note = "The taste refresh could not run: " + Self.message(error) + ". Showing what was last saved."
        }
    }

    /// Test and preview seam: replaces the saved profiles without a server.
    func set(_ p: TasteProfiles?) { profiles = p; loaded = true }

    // MARK: What the cards show

    /// The window the headline speaks about (`recent`, or `mid` when recent is thin).
    public var headlineWindow: String { profiles?.headline?.window ?? "recent" }
    public var shifts: [TasteShift] { profiles?.shifts(in: headlineWindow) ?? [] }
    public var selectedWindow: TasteWindow? { profiles?.window(window) }
    public var recent: TasteWindow? { profiles?.window("recent") }
    public var allTime: TasteWindow? { profiles?.window("all_time") }
    public var minListens: Int { profiles?.config.minListens ?? 50 }
    public var minAttributed: Int { profiles?.config.minAttributed ?? 30 }

    /// Decades for the era card: only when the dimension is sound in the recent and all-time windows, because it compares them.
    public var decades: [(label: String, recent: Double, allTime: Double)]? {
        guard let r = recent, let a = allTime, !r.lowSample, !a.lowSample, !r.isLowSample("era"), !a.isLowSample("era") else { return nil }
        let labels = Set(r.entries("era").map(\.value) + a.entries("era").map(\.value)).sorted()
        guard !labels.isEmpty else { return nil }
        let rs = Dictionary(uniqueKeysWithValues: r.entries("era").map { ($0.value, $0.share) })
        let ts = Dictionary(uniqueKeysWithValues: a.entries("era").map { ($0.value, $0.share) })
        return labels.map { ($0, rs[$0] ?? 0, ts[$0] ?? 0) }
    }

    /// Actions for the cards (slice 7). The shift card offers the first listed rise that is a genre or decade; the window card
    /// offers its top entry, never from a low-sample window or dimension.
    public var shiftAction: TasteAction? {
        shifts.first { $0.direction == "up" && TasteAction(dimension: $0.dimension, value: $0.value) != nil }
            .flatMap { TasteAction(dimension: $0.dimension, value: $0.value) }
    }
    public var windowAction: TasteAction? {
        guard let w = selectedWindow, !w.lowSample, !w.isLowSample(dimension), let top = w.entries(dimension).first else { return nil }
        return TasteAction(dimension: dimension, value: top.value)
    }

    /// Share of the `min_listens` bar a window has reached, for progress states.
    public func progress(listens: Int, need: Int) -> Double { need > 0 ? min(1, Double(listens) / Double(need)) : 1 }

    static func message(_ error: Error) -> String { (error as? LocalizedError)?.errorDescription ?? "the server did not answer" }
}
