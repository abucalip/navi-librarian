import Foundation

/// DTOs for the Subsonic calls used (shapes from `android/contract-fixtures/navidrome/`).
/// Unknown fields are ignored; every field Navidrome may omit is optional.

public struct NavidromeArtist: Codable, Equatable, Sendable, Identifiable {
    public let id: String
    public let name: String
    public let albumCount: Int?
    public let coverArt: String?
    public let musicBrainzId: String?
    public init(id: String, name: String, albumCount: Int?, coverArt: String?, musicBrainzId: String?) {
        self.id = id; self.name = name; self.albumCount = albumCount; self.coverArt = coverArt; self.musicBrainzId = musicBrainzId
    }
}

public struct NavidromeAlbum: Codable, Equatable, Sendable, Identifiable {
    public let id: String
    public let name: String
    public let artist: String?
    public let artistId: String?
    public let coverArt: String?
    public let songCount: Int?
    public let duration: Int?
    public let year: Int?
    public let genre: String?
    public let created: String?
    public let musicBrainzId: String?
}

public struct NavidromeSong: Codable, Equatable, Sendable, Identifiable {
    public let id: String
    public let title: String
    public let album: String?
    public let albumId: String?
    public let artist: String?
    public let artistId: String?
    public let track: Int?
    public let discNumber: Int?
    public let year: Int?
    public let genre: String?
    public let coverArt: String?
    public let duration: Int?
    public let bitRate: Int?
    public let suffix: String?
    public let contentType: String?
    public let size: Int?
    public let path: String?
    public let playCount: Int?
    /// ISO time of the last play, when Navidrome has one.
    public let played: String?
    /// ISO time the song was added.
    public let created: String?
    public let bitDepth: Int?
    public let samplingRate: Int?
    /// The owner's star rating, 1 to 5 (absent or 0 when unrated).
    public let userRating: Int?
    public let musicBrainzId: String?
}

public struct NavidromeAlbumDetail: Equatable, Sendable {
    public let album: NavidromeAlbum
    public let songs: [NavidromeSong]
}

public struct NavidromeArtistDetail: Equatable, Sendable {
    public let artist: NavidromeArtist
    public let albums: [NavidromeAlbum]
}

public struct NavidromePlaylist: Decodable, Equatable, Sendable, Identifiable {
    public let id: String
    public let name: String
    public let songCount: Int?
    public let owner: String?
    public let `public`: Bool?
}

/// Album list types accepted by `getAlbumList2` (Subsonic API).
public enum AlbumListType: String, Sendable {
    case newest, recent, frequent, random, alphabeticalByName, alphabeticalByArtist, highest
}

// MARK: - Envelope

struct SubsonicEnvelope<Payload: Decodable>: Decodable {
    struct Inner: Decodable {
        let status: String
        let error: SubsonicFailure?
        let payload: Payload?

        init(from decoder: any Decoder) throws {
            let c = try decoder.container(keyedBy: AnyKey.self)
            status = try c.decode(String.self, forKey: AnyKey("status"))
            error = try c.decodeIfPresent(SubsonicFailure.self, forKey: AnyKey("error"))
            payload = status == "ok" ? try Payload(from: decoder) : nil
        }
    }
    let response: Inner
    enum CodingKeys: String, CodingKey { case response = "subsonic-response" }
}

struct SubsonicFailure: Decodable { let code: Int?; let message: String? }

struct AnyKey: CodingKey {
    var stringValue: String; var intValue: Int? { nil }
    init(_ s: String) { stringValue = s }
    init?(stringValue: String) { self.stringValue = stringValue }
    init?(intValue: Int) { nil }
}

struct Empty: Decodable { init(from decoder: any Decoder) throws {} }

struct ArtistsPayload: Decodable {
    struct Index: Decodable { let artist: [NavidromeArtist]? }
    struct Artists: Decodable { let index: [Index]? }
    let artists: Artists?
}

struct ArtistPayload: Decodable {
    struct Detail: Decodable {
        let id: String; let name: String
        let albumCount: Int?; let coverArt: String?; let musicBrainzId: String?
        let album: [NavidromeAlbum]?
    }
    let artist: Detail
}

struct AlbumPayload: Decodable {
    struct Detail: Decodable {
        let id: String; let name: String
        let artist: String?; let artistId: String?; let coverArt: String?
        let songCount: Int?; let duration: Int?; let year: Int?; let genre: String?
        let created: String?; let musicBrainzId: String?
        let song: [NavidromeSong]?
    }
    let album: Detail
}

struct AlbumListPayload: Decodable {
    struct List: Decodable { let album: [NavidromeAlbum]? }
    let albumList2: List?
}

struct SongSearchPayload: Decodable {
    struct Result: Decodable { let song: [NavidromeSong]? }
    let searchResult3: Result?
}

struct PlaylistsPayload: Decodable {
    struct List: Decodable { let playlist: [NavidromePlaylist]? }
    let playlists: List?
}
