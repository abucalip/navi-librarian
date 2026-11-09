import DiscairLibrarian
import Foundation
import Observation

/// Settings > ListenBrainz. The account lives on the server (taste, popularity and insights all read it there), so this only
/// reads and writes the server's setting. The token is write-only: it is sent once and never read back or kept here.
@MainActor
@Observable
public final class ListenBrainzModel {
    public private(set) var settings: ListenBrainzSettings?
    public private(set) var busy = false
    /// One plain line about the last action.
    public private(set) var note: String?
    public var username = ""
    public var token = ""

    public init() {}

    public var isConnected: Bool { !(settings?.username ?? "").isEmpty }
    public var canSave: Bool { !busy && !username.trimmingCharacters(in: .whitespaces).isEmpty }

    public func load(librarian: LibrarianClient?) async {
        guard let librarian else { return }
        do {
            let s = try await librarian.listenBrainzSettings()
            settings = s
            if username.isEmpty { username = s.username }
        } catch { note = "Could not read the ListenBrainz setting: " + Self.message(error) }
    }

    /// Saves, checks that the server can read the profile, then asks for a taste refresh so the answer shows without a relaunch.
    public func connect(librarian: LibrarianClient?, afterConnect: @escaping () async -> Void = {}) async {
        guard let librarian, canSave else { return }
        busy = true; defer { busy = false }
        do {
            try await librarian.saveListenBrainz(username: username.trimmingCharacters(in: .whitespaces), token: token.trimmingCharacters(in: .whitespaces))
            token = ""
            settings = try await librarian.listenBrainzSettings()
            let test = try await librarian.testListenBrainz()
            note = test.ok ? "Connected as \(settings?.username ?? username)." : "Saved, but \(test.message.lowercasedFirst)"
            if test.ok { await afterConnect() }
        } catch { note = Self.message(error) }
    }

    static func message(_ error: Error) -> String { (error as? LocalizedError)?.errorDescription ?? "the server did not answer." }
}

private extension String {
    var lowercasedFirst: String { prefix(1).lowercased() + dropFirst() }
}
