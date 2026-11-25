import Foundation

public struct PlaylistInbox: Decodable, Equatable, Sendable {
    public let state: String
    public let items: [PlaylistInboxEdition]
}

public struct PlaylistInboxEdition: Decodable, Equatable, Identifiable, Sendable {
    public let id: Int64
    public let title: String?
    public let sourceKind: String
    public let generatedAt: String?
    public let totalCount: Int
    public let ownedCount: Int?

    enum CodingKeys: String, CodingKey {
        case id = "edition_id", title, sourceKind = "source_kind", generatedAt = "generated_at"
        case totalCount = "total_count", ownedCount = "owned_count"
    }
}

public struct PlaylistInboxDetail: Decodable, Equatable, Sendable {
    public let edition: PlaylistInboxEdition
    public let tracks: [PlaylistInboxTrack]

    private enum CodingKeys: String, CodingKey { case tracks }

    public init(from decoder: any Decoder) throws {
        edition = try PlaylistInboxEdition(from: decoder)
        tracks = try decoder.container(keyedBy: CodingKeys.self).decode([PlaylistInboxTrack].self, forKey: .tracks)
    }
}

public struct PlaylistInboxTrack: Decodable, Equatable, Identifiable, Sendable {
    public var id: Int { position }
    public let position: Int
    public let title: String?
    public let artist: String?
    public let album: String?
    public let durationMs: Int?
    public let recordingMBID: String?
    public let matchState: String?
    public let songID: String?

    enum CodingKeys: String, CodingKey {
        case position, title, artist, album, durationMs = "duration_ms", recordingMBID = "recording_mbid"
        case matchState = "match_state", songID = "song_id"
    }
}

extension LibrarianClient {
    public func playlistInbox() async throws -> PlaylistInbox {
        let (data, http) = try await authedSendPublic("GET", "api/playlists/inbox", body: nil)
        return try decodePublic(PlaylistInbox.self, data, http)
    }

    public func playlistInboxEdition(id: Int64) async throws -> PlaylistInboxDetail {
        let (data, http) = try await authedSendPublic("GET", "api/playlists/inbox/\(id)", body: nil)
        return try decodePublic(PlaylistInboxDetail.self, data, http)
    }
}
