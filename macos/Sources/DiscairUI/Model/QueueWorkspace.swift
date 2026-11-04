import DiscairAudio
import DiscairCore
import DiscairNavidrome
import Foundation
import Observation

/// A queue the owner saved under a name: the songs in order. Kept on this Mac, never on the server.
public struct SavedQueue: Identifiable, Codable, Equatable, Sendable {
    public var id = UUID()
    public var name: String
    public var items: [QueueItem]
    public var savedAt: Date
    public var minutes: Int { Int(items.reduce(0) { $0 + $1.duration } / 60) }
}

/// Saved queues (contract section 6.8). Saving takes the whole queue as arranged (played songs and Up Next), so loading
/// it brings back the same running order.
@MainActor @Observable
public final class SavedQueueStore {
    public private(set) var queues: [SavedQueue]
    private let defaults: UserDefaults
    private static let key = "savedQueues.v1"
    /// Most queues kept, and most songs in one (the oldest queue goes first).
    static let maxQueues = 30
    static let maxSongs = 500

    public init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        if let data = defaults.data(forKey: Self.key), let saved = try? JSONDecoder().decode([SavedQueue].self, from: data) { queues = saved }
        else { queues = [] }
    }

    /// Saves `items` under `name`; a name already used is replaced (that is how a queue is updated). Returns nil for an
    /// empty queue.
    @discardableResult
    public func save(name: String, items: [QueueItem], now: Date = Date()) -> SavedQueue? {
        guard !items.isEmpty else { return nil }
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        let title = trimmed.isEmpty ? Self.defaultName(now) : trimmed
        var q = SavedQueue(name: title, items: Array(items.prefix(Self.maxSongs)), savedAt: now)
        if let i = queues.firstIndex(where: { $0.name.caseInsensitiveCompare(title) == .orderedSame }) {
            q.id = queues[i].id
            queues.remove(at: i)
        }
        queues.insert(q, at: 0)
        if queues.count > Self.maxQueues { queues.removeLast(queues.count - Self.maxQueues) }
        persist()
        return q
    }

    public func remove(_ id: UUID) { queues.removeAll { $0.id == id }; persist() }

    /// A copy of the songs with fresh ids, so the same song can sit in the queue twice without the rows colliding.
    public func songs(of id: UUID) -> [QueueItem] {
        (queues.first { $0.id == id }?.items ?? []).map {
            QueueItem(songID: $0.songID, title: $0.title, artist: $0.artist, album: $0.album, albumID: $0.albumID, coverArt: $0.coverArt,
                      duration: $0.duration, suffix: $0.suffix, track: $0.track, disc: $0.disc, path: $0.path)
        }
    }

    static func defaultName(_ date: Date) -> String {
        let f = DateFormatter(); f.locale = Locale(identifier: "en_GB"); f.dateFormat = "d MMM, HH:mm"
        return "Queue \(f.string(from: date))"
    }

    private func persist() { if let d = try? JSONEncoder().encode(queues) { defaults.set(d, forKey: Self.key) } }
}

/// Chooses the songs for Radio from this. Pure: the candidates come from the caller.
enum RadioPlanner {
    /// `groups` is one list of songs per similar artist (best match first). Songs already queued or equal to the seed are
    /// dropped; each artist's songs are shuffled and the artists are taken in turn, so no single artist fills the list.
    static func pick(groups: [[QueueItem]], exclude: Set<String>, count: Int, using rng: inout some RandomNumberGenerator) -> [QueueItem] {
        guard count > 0 else { return [] }
        var taken = exclude
        var lanes: [[QueueItem]] = groups.map { g in
            var seen = Set<String>()
            return g.filter { !taken.contains($0.songID) && seen.insert($0.songID).inserted }.shuffled(using: &rng)
        }
        var out: [QueueItem] = []
        while out.count < count, lanes.contains(where: { !$0.isEmpty }) {
            for i in lanes.indices where out.count < count {
                guard !lanes[i].isEmpty else { continue }
                let song = lanes[i].removeFirst()
                if taken.insert(song.songID).inserted { out.append(song) }
            }
        }
        return out
    }
}

/// Radio from this: songs by artists similar to the one playing, added to Up Next. Similarity comes from the artists
/// the server lists as similar (the same data the album spread shows), limited to artists the library holds.
@MainActor @Observable
public final class RadioModel {
    public private(set) var busy = false
    public private(set) var status: String?
    /// Keep Up Next topped up while a song plays.
    public var autoplay: Bool { didSet { defaults.set(autoplay, forKey: Self.autoplayKey) } }
    private let defaults: UserDefaults
    private static let autoplayKey = "radio.autoplay"
    static let batch = 20
    static let maxArtists = 6

    public init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        autoplay = defaults.bool(forKey: Self.autoplayKey)
    }

    /// Finds songs like `seed` and returns them (not yet queued). `candidates` returns, for the seed, one song list per
    /// similar artist the library holds.
    public func songs(like seed: QueueItem, queued: Set<String>,
                      candidates: (QueueItem) async throws -> [[QueueItem]]) async -> [QueueItem] {
        guard !busy else { return [] }
        busy = true; defer { busy = false }
        do {
            let groups = try await candidates(seed)
            var g = SystemRandomNumberGenerator()
            let picked = RadioPlanner.pick(groups: groups, exclude: queued.union([seed.songID]), count: Self.batch, using: &g)
            status = picked.isEmpty ? "No similar artists in your library for \(seed.artist)." : "Added \(picked.count) songs like \(seed.artist)."
            return picked
        } catch {
            status = (error as? DiscairError).map(AcquisitionModel.text) ?? "Could not find similar songs."
            return []
        }
    }

    /// The live source: Navidrome's similar artists for the seed's artist, then one random album from each one the
    /// library holds (at most `maxArtists` artists, so a batch costs at most about thirteen requests).
    static func liveCandidates(navidrome: NavidromeClient, artists: [ArtistItem]) -> (QueueItem) async throws -> [[QueueItem]] {
        { seed in
            guard let me = artists.first(where: { $0.name.caseInsensitiveCompare(seed.artist) == .orderedSame }), let id = me.remoteID,
                  let info = try await navidrome.artistInfo(id: id, similar: 20) else { return [] }
            let held = Dictionary(artists.compactMap { a in a.remoteID.map { ($0, a) } }, uniquingKeysWith: { a, _ in a })
            let similar = info.similarArtists.filter { held[$0.id] != nil }.prefix(maxArtists)
            var groups: [[QueueItem]] = []
            for a in similar {
                guard let detail = try? await navidrome.artist(id: a.id), let album = detail.albums.randomElement(),
                      let songs = try? await navidrome.album(id: album.id).songs else { continue }
                groups.append(songs.map(PlayerModel.item))
            }
            return groups
        }
    }
}
