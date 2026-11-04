import DiscairAudio
import DiscairNavidrome
import Foundation

/// Reports plays to Navidrome so the listening history (and the discovery that reads it) stays current.
///
/// One *play* is one start of one song: a new queue entry, a repeat-one loop or choosing the same song again each begin a
/// new play with a fresh tracker. A restored queue begins nothing until the owner presses play. Rules and trade-offs:
/// ANDROID_PLAYER_CONTRACT section 4. In short: now-playing is sent once and never retried; the final scrobble is sent once,
/// and is sent again only when the request provably never left the Mac (3 more tries after 2 s, 10 s and 30 s, with the
/// original start time). A request that may have arrived is never repeated. Failures never touch playback.
@MainActor
public final class ScrobbleCoordinator {
    public static let retryDelays: [Duration] = [.seconds(2), .seconds(10), .seconds(30)]

    private struct Play {
        let id = UUID()
        let songID: String
        let startedAt: Date
        var tracker: ScrobbleTracker
    }

    private var client: (any Scrobbling)?
    private var play: Play?
    private var retries: [UUID: Task<Void, Never>] = [:]
    private let sleep: @Sendable (Duration) async -> Void
    private let now: () -> Date

    /// Off sends nothing, cancels pending retries, and drops the current play. On mid-song starts counting from that moment.
    public var isEnabled: Bool { didSet { if isEnabled != oldValue { enabledChanged() } } }
    /// The song the current play belongs to (kept so turning the switch on mid-song can start a play for it).
    private var currentSong: (id: String, duration: Double?)?

    public init(enabled: Bool = true, now: @escaping () -> Date = Date.init, sleep: @escaping @Sendable (Duration) async -> Void = { try? await Task.sleep(for: $0) }) {
        isEnabled = enabled
        self.now = now
        self.sleep = sleep
    }

    public func configure(client: (any Scrobbling)?) {
        self.client = client
        if client == nil { cancelRetries(); play = nil }
    }

    /// A song started playing: a new play. Nothing is sent until `update` sees the player actually playing.
    public func begin(songID: String, duration: Double?) {
        currentSong = (songID, duration)
        play = isEnabled ? Play(songID: songID, startedAt: now(), tracker: ScrobbleTracker(serverDuration: duration)) : nil
    }

    /// The song stopped, or the queue ended.
    public func end() { play = nil; currentSong = nil }

    /// A reading of the player (about four times a second).
    public func update(position: Double, playerDuration: Double?, isPlaying: Bool) {
        guard isEnabled, var p = play else { return }
        let actions = p.tracker.update(position: position, playerDuration: playerDuration, isPlaying: isPlaying)
        play = p
        guard let client else { return }
        for action in actions {
            switch action {
            case .nowPlaying:
                let id = p.songID, time = p.startedAt
                Task { _ = await client.scrobble(songID: id, time: time, submission: false) }
            case .scrobble:
                send(p, client: client)
            }
        }
    }

    private func send(_ p: Play, client: any Scrobbling) {
        let id = p.id, song = p.songID, time = p.startedAt, delays = Self.retryDelays, sleep = self.sleep
        retries[id] = Task { [weak self] in
            var attempt = 0
            while true {
                let outcome = await client.scrobble(songID: song, time: time, submission: true)
                guard !Task.isCancelled, outcome == .notSent, attempt < delays.count else { break }
                await sleep(delays[attempt]); attempt += 1
                if Task.isCancelled { break }
            }
            self?.retries[id] = nil
        }
    }

    private func enabledChanged() {
        if isEnabled {
            if let s = currentSong { begin(songID: s.id, duration: s.duration) }   // from this moment, no backfill
        } else {
            cancelRetries(); play = nil
        }
    }

    private func cancelRetries() {
        retries.values.forEach { $0.cancel() }
        retries = [:]
    }
}
