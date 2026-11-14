import Foundation

/// When to try a live station again (docs/RADIO_PLAYBACK_PROPOSAL.md S2-4 item 1; the same rule as Android's `DEFAULT_BACKOFF_MS`).
/// Pure: the model feeds it drops and sound and does the waiting. After a drop, an error status, or 20 s without sound, the
/// tries come after 2, 5, 10, 20 and 30 s; sound resets the count; when the fifth try has also failed the station is unreachable.
public struct ReconnectPolicy: Equatable, Sendable {
    public static let delays: [TimeInterval] = [2, 5, 10, 20, 30]
    /// How long a station may stay without sound (connecting or buffering) before it counts as a drop.
    public static let silenceLimit: TimeInterval = 20
    public static var attempts: Int { delays.count }

    public enum Step: Equatable, Sendable {
        /// Try again after `delay` seconds; `attempt` counts from 1.
        case retry(delay: TimeInterval, attempt: Int)
        /// Every try failed: show "Station unreachable" with Retry and stop trying.
        case giveUp
    }

    /// Tries already started since the last sound.
    public private(set) var tries = 0

    public init() {}

    /// A drop was seen. Returns what to do next and counts the try.
    public mutating func drop() -> Step {
        guard tries < Self.delays.count else { return .giveUp }
        tries += 1
        return .retry(delay: Self.delays[tries - 1], attempt: tries)
    }

    /// Sound arrived: the count starts again.
    public mutating func sound() { tries = 0 }

    /// A fresh round (wake from sleep, or the owner pressed Retry).
    public mutating func reset() { tries = 0 }
}
