import Foundation

/// The play queue Navidrome keeps for the user (`getPlayQueue`), written by whichever client last saved it.
/// A phone that calls `savePlayQueue` makes this the "playing on your phone" handoff (redesign D5).
public struct NavidromePlayQueue: Equatable, Sendable {
    public let songs: [NavidromeSong]
    /// The song that was playing.
    public let currentID: String?
    /// Where in that song, in milliseconds.
    public let positionMs: Int
    /// When the queue was last saved.
    public let changed: Date?
    /// The client name that saved it ("discair" for this app).
    public let changedBy: String?

    public init(songs: [NavidromeSong], currentID: String?, positionMs: Int, changed: Date?, changedBy: String?) {
        self.songs = songs; self.currentID = currentID; self.positionMs = positionMs; self.changed = changed; self.changedBy = changedBy
    }

    public var current: NavidromeSong? { songs.first { $0.id == currentID } ?? songs.first }
}

struct PlayQueuePayload: Decodable {
    struct Queue: Decodable {
        let current: String?
        let position: Int?
        let changed: String?
        let changedBy: String?
        let entry: [NavidromeSong]?

        enum CodingKeys: String, CodingKey { case current, position, changed, changedBy, entry }
        init(from decoder: any Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            // Servers write `current` as a string; some write a number.
            current = (try? c.decode(String.self, forKey: .current)) ?? (try? c.decode(Int.self, forKey: .current)).map(String.init)
            position = (try? c.decode(Int.self, forKey: .position)) ?? (try? c.decode(Double.self, forKey: .position)).map { Int($0) }
            changed = try? c.decode(String.self, forKey: .changed)
            changedBy = try? c.decode(String.self, forKey: .changedBy)
            entry = try? c.decode([NavidromeSong].self, forKey: .entry)
        }
    }
    let playQueue: Queue?
}

extension NavidromeClient {
    /// `getPlayQueue`: nil when nothing was saved. Read-only.
    public func playQueue() async throws -> NavidromePlayQueue? {
        let q = try await call("getPlayQueue", [], as: PlayQueuePayload.self).playQueue
        guard let q, let songs = q.entry, !songs.isEmpty else { return nil }
        let fractional = ISO8601DateFormatter(); fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let changed = q.changed.flatMap { fractional.date(from: $0) ?? ISO8601DateFormatter().date(from: $0) }
        return NavidromePlayQueue(songs: songs, currentID: q.current, positionMs: max(0, q.position ?? 0), changed: changed, changedBy: q.changedBy)
    }
}
