import Foundation

/// One skip or dismissal reported to the Librarian (`docs/SERVER_V2_CONTRACT.md`, `POST /api/feedback/events`, D-027).
/// Record-only: the server stores it and nothing ranks with it. Carries no path, token, device name or free text.
public struct FeedbackEvent: Encodable, Equatable, Sendable {
    public enum Kind: String, Encodable, Sendable { case skip, dismiss }
    public enum Subject: String, Encodable, Sendable { case track, album, artist, card }

    /// Client-generated; a retry of the same event must reuse it so the server can treat the replay as a duplicate.
    public let eventID: String
    public let client = "macos"
    public let kind: Kind
    public let subjectKind: Subject
    public let subjectID: String
    public let mbid: String?
    public let occurredAt: Double
    public let playedSeconds: Double?
    public let durationSeconds: Double?

    enum CodingKeys: String, CodingKey {
        case eventID = "event_id", client, kind, subjectKind = "subject_kind", subjectID = "subject_id", mbid
        case occurredAt = "occurred_at", playedSeconds = "played_seconds", durationSeconds = "duration_seconds"
    }

    public init(eventID: String = UUID().uuidString.lowercased(), kind: Kind, subjectKind: Subject, subjectID: String,
                mbid: String? = nil, occurredAt: Double, playedSeconds: Double? = nil, durationSeconds: Double? = nil) {
        self.eventID = eventID; self.kind = kind; self.subjectKind = subjectKind; self.subjectID = subjectID
        self.mbid = mbid; self.occurredAt = occurredAt; self.playedSeconds = playedSeconds; self.durationSeconds = durationSeconds
    }

    /// The server's batch limit; a longer list is sent in several requests.
    public static let batchLimit = 100
}

/// What the server said about one event. A `rejected` item must not be retried unchanged.
public struct FeedbackEventResult: Decodable, Equatable, Sendable {
    public let index: Int
    public let accepted: Bool
    public let duplicate: Bool
    public let reason: String?

    enum CodingKeys: String, CodingKey { case index, status, duplicate, reason }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        index = (try? c.decode(Int.self, forKey: .index)) ?? -1
        accepted = ((try? c.decode(String.self, forKey: .status)) ?? "") == "accepted"
        duplicate = (try? c.decode(Bool.self, forKey: .duplicate)) ?? false
        reason = try? c.decode(String.self, forKey: .reason)
    }
}

public struct FeedbackEventsResponse: Decodable, Equatable, Sendable {
    public let received: Int
    public let inserted: Int
    public let accepted: Int
    public let rejected: Int
    public let results: [FeedbackEventResult]

    enum CodingKeys: String, CodingKey { case received, inserted, accepted, rejected, results }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        received = (try? c.decode(Int.self, forKey: .received)) ?? 0
        inserted = (try? c.decode(Int.self, forKey: .inserted)) ?? 0
        accepted = (try? c.decode(Int.self, forKey: .accepted)) ?? 0
        rejected = (try? c.decode(Int.self, forKey: .rejected)) ?? 0
        results = (try? c.decode([FeedbackEventResult].self, forKey: .results)) ?? []
    }
}
