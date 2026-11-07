import Foundation

// Server V2 Phase 7 sonic similarity: `GET /api/sonic/similar`, `GET /api/sonic/path` and the `sonic_available`
// flag of `GET /api/capabilities` (shapes in docs/SERVER_V2_CONTRACT.md). Tolerant decoding like Knowledge.swift.
// Every track is a song in the owner's Navidrome. `similarity` is informational only: the band is narrow
// (median 0.92) and path steps carry none, so nothing here sorts or filters on it.

/// One song the server matched by sound.
public struct SonicTrack: Decodable, Equatable, Sendable, Identifiable {
    public let songID: String
    public let title: String
    public let artist: String
    public let artistID: String?
    public let album: String
    public let albumID: String?
    public let duration: Double
    public let year: Int?
    public let mbid: String?
    public let coverArt: String?
    public let similarity: Double?
    public var id: String { songID }
    enum CodingKeys: String, CodingKey {
        case songID = "navidrome_id", title, artist, artistID = "artist_id", album, albumID = "album_id", duration, year, mbid
        case coverArt = "cover_art", similarity
    }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        songID = try c.decode(String.self, forKey: .songID)
        title = (try? c.decodeIfPresent(String.self, forKey: .title)) ?? ""
        artist = (try? c.decodeIfPresent(String.self, forKey: .artist)) ?? ""
        artistID = try? c.decodeIfPresent(String.self, forKey: .artistID)
        album = (try? c.decodeIfPresent(String.self, forKey: .album)) ?? ""
        albumID = try? c.decodeIfPresent(String.self, forKey: .albumID)
        duration = (try? c.decodeIfPresent(Double.self, forKey: .duration)) ?? 0
        year = try? c.decodeIfPresent(Int.self, forKey: .year)
        mbid = try? c.decodeIfPresent(String.self, forKey: .mbid)
        coverArt = try? c.decodeIfPresent(String.self, forKey: .coverArt)
        similarity = try? c.decodeIfPresent(Double.self, forKey: .similarity)
    }
}

/// `status` is "ok" or "empty" (the song has no analysis data); `seed` is nil on a path.
public struct SonicResponse: Decodable, Equatable, Sendable {
    public let status: String
    public let seed: SonicTrack?
    public let tracks: [SonicTrack]
    enum CodingKeys: String, CodingKey { case status, seed, tracks }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        status = (try? c.decodeIfPresent(String.self, forKey: .status)) ?? "empty"
        seed = try? c.decodeIfPresent(SonicTrack.self, forKey: .seed)
        tracks = (try? c.decodeIfPresent([SonicTrack].self, forKey: .tracks)) ?? []
    }
}

private struct CapabilitiesFlags: Decodable {
    let sonicAvailable: Bool?
    enum CodingKeys: String, CodingKey { case sonicAvailable = "sonic_available" }
}

extension LibrarianClient {
    /// Songs that sound like `songID`, in the server's order (at most 2 by the seed's own artist).
    public func sonicSimilar(songID: String, count: Int = 20) async throws -> SonicResponse {
        let (data, http) = try await authedSendPublic("GET", "api/sonic/similar?id=\(Self.enc(songID))&count=\(count)", body: nil)
        return try decodePublic(SonicResponse.self, data, http)
    }

    /// Ordered steps from `start` to `end` through sound; the first step is the start song.
    public func sonicPath(start: String, end: String, count: Int = 10) async throws -> SonicResponse {
        let (data, http) = try await authedSendPublic("GET", "api/sonic/path?start=\(Self.enc(start))&end=\(Self.enc(end))&count=\(count)", body: nil)
        return try decodePublic(SonicResponse.self, data, http)
    }

    /// Whether the server reports sonic similarity (`sonic_available` in `/api/capabilities`); false when unknown or unreachable.
    public func sonicAvailable() async -> Bool {
        guard let (data, http) = try? await authedSendPublic("GET", "api/capabilities", body: nil), http.statusCode == 200,
              let flags = try? JSONDecoder().decode(CapabilitiesFlags.self, from: data) else { return false }
        return flags.sonicAvailable ?? false
    }
}
