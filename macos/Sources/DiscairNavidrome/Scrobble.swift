import DiscairCore
import Foundation

/// What happened to one `scrobble.view` request (macOS contract section 5, ANDROID_PLAYER_CONTRACT section 4).
public enum ScrobbleOutcome: Equatable, Sendable {
    /// The server accepted it.
    case sent
    /// The request provably never left the Mac (no network, DNS or connect failure). Safe to send again.
    case notSent
    /// The request may have reached the server (timeout, reset, error answer, unreadable answer). Never sent again.
    case unknown
}

/// Something that can report a play to Navidrome. `NavidromeClient` is the real one; tests supply a fake.
public protocol Scrobbling: Sendable {
    /// `submission` false is "now playing"; true is the final scrobble. `time` is when the play started.
    func scrobble(songID: String, time: Date, submission: Bool) async -> ScrobbleOutcome
}

extension NavidromeClient: Scrobbling {
    public func scrobble(songID: String, time: Date, submission: Bool) async -> ScrobbleOutcome {
        guard isValidSongID(songID) else { return .notSent }
        let q: [URLQueryItem] = [
            .init(name: "id", value: songID),
            .init(name: "time", value: String(Int64((time.timeIntervalSince1970 * 1000).rounded()))),
            .init(name: "submission", value: submission ? "true" : "false"),
        ]
        do {
            _ = try await call("scrobble", q, as: Empty.self, rawTransportErrors: true)
            return .sent
        } catch let e as URLError where Self.neverLeftTheMac(e.code) {
            return .notSent
        } catch {
            return .unknown
        }
    }

    /// Failures that happen before any request bytes are written. A timeout is not in this list: it may be a read timeout.
    static func neverLeftTheMac(_ code: URLError.Code) -> Bool {
        [.notConnectedToInternet, .dataNotAllowed, .cannotFindHost, .cannotConnectToHost, .dnsLookupFailed].contains(code)
    }
}
