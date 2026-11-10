import Foundation

// Album paths (`GET /api/knowledge/paths?type=release`, the Paths button on an album page) and the album sonic
// neighbours (`GET /api/sonic/album-neighbours`). Same bodies and tolerant decoding as KnowledgeGraph.swift and
// Sonic.swift; shapes in docs/SERVER_V2_CONTRACT.md. `album_room` and `album_gaps` are read the same way (Gaps adds `play` and `history`).

/// The album graph kinds the server builds for a release start.
public enum AlbumPathKind: String, Sendable, CaseIterable {
    case studioCrew = "album_crew"
    case guestList = "album_guests"
    case coversAndSources = "album_works"
    case sameYearSameScene = "album_moment"
    case sameRoom = "album_room"
    case listenThroughGaps = "album_gaps"
}

/// A person or work whose albums were cut at the server's cap; `more` albums were left out and must be said so.
public struct PathCapped: Decodable, Equatable, Sendable {
    public let via: String
    public let more: Int
    enum CodingKeys: String, CodingKey { case via, more }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let name: String?
        if let plain = try? c.decodeIfPresent(String.self, forKey: .via) {
            name = plain
        } else if let ref = try? c.decodeIfPresent(PathCappedRef.self, forKey: .via) {
            name = ref.canonical_name
        } else {
            name = nil
        }
        let count = (try? c.decodeIfPresent(Int.self, forKey: .more)) ?? 0
        guard let trimmed = name?.trimmingCharacters(in: .whitespacesAndNewlines), !trimmed.isEmpty, count > 0 else {
            throw DecodingError.dataCorruptedError(forKey: .via, in: c, debugDescription: "capped entry without a name or count")
        }
        via = trimmed
        more = count
    }
}

private struct PathCappedRef: Decodable { let canonical_name: String? }

/// Decodes one list entry, or nil when it is malformed, so one bad entry does not drop the rest.
struct LenientEntry<T: Decodable>: Decodable {
    let value: T?
    init(from decoder: any Decoder) throws { value = try? T(from: decoder) }
}

/// One owned album a sample of tracks sounds like. `matchCount` is the number of distinct seeds it matched.
public struct SonicAlbumNeighbour: Decodable, Equatable, Sendable, Identifiable {
    public let albumID: String
    public let album: String
    public let artist: String
    public let artistID: String?
    public let year: Int?
    public let coverArt: String?
    public let owned: Bool
    public let matchCount: Int
    public let reasonText: String?
    public var id: String { albumID }
    enum CodingKeys: String, CodingKey { case albumID = "album_id", album, artist, artistID = "artist_id", year, coverArt = "cover_art", owned, match_count, reasons }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        albumID = try c.decode(String.self, forKey: .albumID)
        album = (try? c.decodeIfPresent(String.self, forKey: .album)) ?? ""
        artist = (try? c.decodeIfPresent(String.self, forKey: .artist)) ?? ""
        artistID = try? c.decodeIfPresent(String.self, forKey: .artistID)
        year = try? c.decodeIfPresent(Int.self, forKey: .year)
        coverArt = try? c.decodeIfPresent(String.self, forKey: .coverArt)
        owned = (try? c.decodeIfPresent(Bool.self, forKey: .owned)) ?? false
        matchCount = (try? c.decodeIfPresent(Int.self, forKey: .match_count)) ?? 0
        let reasons = (try? c.decodeIfPresent([SonicReasonText].self, forKey: .reasons)) ?? []
        reasonText = reasons.compactMap { $0.text }.first { !$0.isEmpty }
    }
}

private struct SonicReasonText: Decodable { let text: String? }

/// `GET /api/sonic/album-neighbours`. `similarity` is never read; a seed without analysis data is in `skipped`.
public struct SonicAlbumNeighbours: Decodable, Equatable, Sendable {
    public struct Start: Decodable, Equatable, Sendable {
        public let album: String
        public let albumID: String
        public let artist: String
        public let tracks: Int
        public let year: Int?
        enum CodingKeys: String, CodingKey { case album, albumID = "album_id", artist, tracks, year }
    }
    public struct Seed: Decodable, Equatable, Sendable {
        public let songID: String
        public let title: String
        enum CodingKeys: String, CodingKey { case songID = "navidrome_id", title }
    }
    public struct Skipped: Decodable, Equatable, Sendable {
        public let songID: String
        public let title: String
        public let reason: String
        enum CodingKeys: String, CodingKey { case songID = "navidrome_id", title, reason }
    }
    public let status: String
    public let start: Start?
    public let seeds: [Seed]
    public let skipped: [Skipped]
    public let stops: [SonicAlbumNeighbour]
    public let truncated: String?
    enum CodingKeys: String, CodingKey { case status, start, seeds, skipped, stops, truncated }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        status = (try? c.decodeIfPresent(String.self, forKey: .status)) ?? ""
        start = try? c.decodeIfPresent(Start.self, forKey: .start)
        seeds = (try? c.decodeIfPresent([Seed].self, forKey: .seeds)) ?? []
        skipped = (try? c.decodeIfPresent([Skipped].self, forKey: .skipped)) ?? []
        stops = ((try? c.decodeIfPresent([LenientEntry<SonicAlbumNeighbour>].self, forKey: .stops)) ?? []).compactMap { $0.value }
        truncated = try? c.decodeIfPresent(String.self, forKey: .truncated)
    }
}

private struct PathsFeatureFlags: Decodable {
    struct Features: Decodable { struct Paths: Decodable { let available: Bool? }; let paths: Paths? }
    let features: Features?
}

extension LibrarianClient {
    /// One album path from an owned album, by its Navidrome album id (`GET /api/knowledge/paths?type=release`).
    public func albumPaths(albumID: String, kind: AlbumPathKind) async throws -> KnowledgePaths {
        let q = "kind=\(kind.rawValue)&navidrome_id=\(Self.enc(albumID))&type=release"
        let (data, http) = try await authedSendPublic("GET", "api/knowledge/paths?\(q)", body: nil)
        return try decodePublic(KnowledgePaths.self, data, http)
    }

    /// Albums that sound like an owned album (`GET /api/sonic/album-neighbours`).
    public func sonicAlbumNeighbours(albumID: String) async throws -> SonicAlbumNeighbours {
        let (data, http) = try await authedSendPublic("GET", "api/sonic/album-neighbours?album_id=\(Self.enc(albumID))", body: nil)
        return try decodePublic(SonicAlbumNeighbours.self, data, http)
    }

    /// Whether the server reports the paths feature (`features.paths.available` in `/api/capabilities`); false when unknown or unreachable.
    public func pathsAvailable() async -> Bool {
        guard let (data, http) = try? await authedSendPublic("GET", "api/capabilities", body: nil), http.statusCode == 200,
              let flags = try? JSONDecoder().decode(PathsFeatureFlags.self, from: data) else { return false }
        return flags.features?.paths?.available ?? false
    }
}
