import DiscairLibrarian
import Foundation
import Observation

/// What Download asks of the Librarian. `LibrarianClient` is the real one; tests pass a fake.
public protocol RadioGetSource: Sendable {
    func getRadioPlay(id: Int) async throws -> RadioGetResult
}
extension LibrarianClient: RadioGetSource {}

/// The Download button's memory (S2-3 item 2): what the Mac sent for each heard song (`play_id`), and the sentence the server
/// gave back, kept so a row can show it after the request ends. One model serves the bar, the On Air panel and, later, Now
/// Playing and the Heard rows, so they never disagree.
@MainActor
@Observable
public final class RadioDownloads {
    private(set) var attempts: [Int: DownloadState.Attempt] = [:]
    public private(set) var sentences: [Int: String] = [:]

    @ObservationIgnored private var source: (any RadioGetSource)?
    /// Called after a Get was accepted, so the Heard list is read again (wired by `AppState`).
    @ObservationIgnored public var onSuccess: () async -> Void = {}

    public init() {}

    public func configure(source: (any RadioGetSource)?) {
        self.source = source
        if source == nil { attempts = [:]; sentences = [:] }
    }

    func attempt(for playID: Int?) -> DownloadState.Attempt { playID.flatMap { attempts[$0] } ?? .none }
    public func sentence(for playID: Int?) -> String? { playID.flatMap { sentences[$0] } }

    /// The state of the control for the live song. Owned first, then the request, then the 30-second rule.
    func state(now: RadioNow?) -> DownloadState {
        guard let now else { return .none }
        return DownloadState.of(now: now, attempt: attempt(for: now.playID))
    }

    /// `POST /api/radio/plays/{id}/get`. A click on a song already asked for, or in flight, does nothing. The server's sentence is
    /// kept for the row; a refusal gives "Try again" and the next click sends again.
    public func get(playID: Int) async {
        guard let source, !(attempts[playID]?.working ?? false), !(attempts[playID]?.requested ?? false) else { return }
        attempts[playID] = DownloadState.Attempt(requested: false, working: true, failed: false)
        sentences[playID] = nil
        do {
            let result = try await source.getRadioPlay(id: playID)
            if result.ok {
                attempts[playID] = DownloadState.Attempt(requested: true, working: false, failed: false)
                sentences[playID] = result.message ?? result.album.map { "Requested \($0)." } ?? "Sent to the Librarian."
                await onSuccess()
            } else {
                attempts[playID] = DownloadState.Attempt(requested: false, working: false, failed: true)
                sentences[playID] = result.message ?? "The Librarian could not get this song."
            }
        } catch {
            attempts[playID] = DownloadState.Attempt(requested: false, working: false, failed: true)
            sentences[playID] = StationsModel.message(error)
        }
    }
}
