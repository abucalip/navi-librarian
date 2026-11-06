import DiscairAudio
import DiscairLibrarian
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
        /// The song's MusicBrainz id, only when it is already known and is a valid UUID.
        let mbid: String?
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
    private var currentSong: (id: String, duration: Double?, mbid: String?)?
    /// Told of each skip when a song the owner left early ends (see `end`). PlayerModel sends these to the feedback outbox.
    public var onSkip: (@MainActor (FeedbackEvent) -> Void)?

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
    public func begin(songID: String, duration: Double?, mbid: String? = nil) {
        currentSong = (songID, duration, mbid)
        play = isEnabled ? Play(songID: songID, mbid: Self.validMBID(mbid), startedAt: now(), tracker: ScrobbleTracker(serverDuration: duration)) : nil
    }

    /// The song leaves. `leftByOwner` is true for Next, Previous, a jump to Up Next, or starting another list; false when the
    /// song ended by itself or playback stopped. `wasLastInQueue` is true when nothing was queued after it. A song the owner
    /// left before `SkipRule` allows counts as a skip and is passed to `onSkip`. Scrobbling is not affected.
    public func end(leftByOwner: Bool = false, wasLastInQueue: Bool = false) {
        if let p = play, SkipRule.isSkip(played: p.tracker.played, duration: p.tracker.serverDuration,
                                         leftByOwner: leftByOwner, wasLastInQueue: wasLastInQueue) {
            let length = p.tracker.serverDuration.flatMap { $0 > 0 ? $0 : nil }
            onSkip?(FeedbackEvent(kind: .skip, subjectKind: .track, subjectID: p.songID, mbid: p.mbid,
                                  occurredAt: now().timeIntervalSince1970, playedSeconds: p.tracker.played, durationSeconds: length))
        }
        play = nil; currentSong = nil
    }

    /// Only a real MusicBrainz UUID is reported; the server refuses anything else. Lower case, as the server stores it.
    static func validMBID(_ raw: String?) -> String? {
        guard let raw, UUID(uuidString: raw) != nil else { return nil }
        return raw.lowercased()
    }

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
            if let s = currentSong { begin(songID: s.id, duration: s.duration, mbid: s.mbid) }   // from this moment, no backfill
        } else {
            cancelRetries(); play = nil
        }
    }

    private func cancelRetries() {
        retries.values.forEach { $0.cancel() }
        retries = [:]
    }
}
