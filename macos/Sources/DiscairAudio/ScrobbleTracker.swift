import Foundation

/// Counts the played time of one play and says when to report it (ANDROID_PLAYER_CONTRACT section 4, kept for the Mac).
///
/// Pure value logic: feed it the player's position about four times a second and it answers with what to send.
/// - *Now playing* once, the first time the player is actually playing.
/// - *Scrobble* once, when played time reaches `min(duration / 2, 240 s)`, only for songs of at least 30 s.
/// - Played time counts small forward steps while playing. Pauses, seeks (any jump over `maxStep`) and backward moves
///   add nothing, and seeking never removes time.
public struct ScrobbleTracker: Sendable {
    public enum Action: Equatable, Sendable { case nowPlaying, scrobble }

    public static let maxStep = 2.0
    public static let minimumLength = 30.0
    public static let ceiling = 240.0

    /// The song's length according to the server (authoritative when positive).
    public let serverDuration: Double?
    public private(set) var played = 0.0
    public private(set) var nowPlayingSent = false
    public private(set) var scrobbled = false
    private var last: Double?

    public init(serverDuration: Double?) {
        self.serverDuration = serverDuration
    }

    /// The length used for the rules, or nil when neither side knows it. If the two disagree by more than 10 %, the
    /// larger applies.
    public static func effectiveDuration(server: Double?, player: Double?) -> Double? {
        let s = (server ?? 0) > 0 ? server : nil
        let p = (player ?? 0) > 0 && player!.isFinite ? player : nil
        switch (s, p) {
        case let (s?, p?): return abs(s - p) > 0.1 * max(s, p) ? max(s, p) : s
        case let (s?, nil): return s
        case let (nil, p?): return p
        default: return nil
        }
    }

    /// Played seconds needed before the scrobble: half the length, at most 240 s; 240 s when the length is unknown.
    public static func threshold(duration: Double?) -> Double {
        guard let duration else { return ceiling }
        return min(duration / 2, ceiling)
    }

    /// One reading of the player. `playerDuration` is what the engine reports for the opened file.
    public mutating func update(position: Double, playerDuration: Double?, isPlaying: Bool) -> [Action] {
        defer { last = position }
        guard isPlaying else { return [] }
        var actions: [Action] = []
        if !nowPlayingSent { nowPlayingSent = true; actions.append(.nowPlaying) }
        if let last {
            let step = position - last
            if step > 0, step <= Self.maxStep { played += step }
        }
        if !scrobbled {
            let length = Self.effectiveDuration(server: serverDuration, player: playerDuration)
            let eligible = length.map { $0 >= Self.minimumLength } ?? true
            if eligible, played >= Self.threshold(duration: length) { scrobbled = true; actions.append(.scrobble) }
        }
        return actions
    }
}
