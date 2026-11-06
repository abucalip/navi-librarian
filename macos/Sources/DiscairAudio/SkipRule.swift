import Foundation

/// Decides whether an abandoned track counts as a skip (`docs/SERVER_V2_CONTRACT.md`, `POST /api/feedback/events`).
/// A skip is a track the owner moved away from before `min(30 s, 50 % of its length)` of played time, and not at the end of
/// the queue. The numbers are starting values, not measured. The server stores what is reported and never re-derives it.
public enum SkipRule {
    public static let seconds = 30.0
    public static let fraction = 0.5

    /// Played seconds below which leaving counts as a skip; 30 s when the length is unknown.
    public static func limit(duration: Double?) -> Double {
        guard let duration, duration > 0, duration.isFinite else { return seconds }
        return min(seconds, duration * fraction)
    }

    /// - Parameters:
    ///   - played: counted played seconds (`ScrobbleTracker.played`; pauses and seeks add nothing).
    ///   - leftByOwner: true for next, previous or picking another song; false when the song ended or playback stopped.
    ///   - wasLastInQueue: leaving the final song is never a skip.
    public static func isSkip(played: Double, duration: Double?, leftByOwner: Bool, wasLastInQueue: Bool) -> Bool {
        guard leftByOwner, !wasLastInQueue, played.isFinite, played >= 0 else { return false }
        return played < limit(duration: duration)
    }
}
