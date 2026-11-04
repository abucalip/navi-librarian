import DiscairCore
import Foundation

/// What Navidrome knows about an album beyond its song list, for the album spread (contract section 6.9).
/// Every field is optional or empty when the server has nothing; nothing here is made up.

/// One credit on a song, from OpenSubsonic `contributors` (role "composer", "producer", "mixer", ...).
public struct NavidromeCredit: Equatable, Sendable {
    public let role: String
    public let subRole: String?
    public let name: String
    public let songID: String
    public init(role: String, subRole: String?, name: String, songID: String) {
        self.role = role; self.subRole = subRole; self.name = name; self.songID = songID
    }
}

/// Album-level facts from OpenSubsonic `getAlbum`, plus the credits of every song on it.
public struct NavidromeAlbumFacts: Equatable, Sendable {
    public var musicBrainzId: String?
    public var releaseTypes: [String] = []
    public var recordLabels: [String] = []
    public var originalReleaseDate: String?
    public var version: String?
    public var isCompilation: Bool?
    public var credits: [NavidromeCredit] = []
    public init() {}
}

/// `getAlbumInfo2`: the liner notes (often from Last.fm) and the links the server holds.
public struct NavidromeAlbumInfo: Equatable, Sendable {
    public var notes: String?
    public var musicBrainzId: String?
    public var lastFmUrl: String?
    public init(notes: String? = nil, musicBrainzId: String? = nil, lastFmUrl: String? = nil) {
        self.notes = notes; self.musicBrainzId = musicBrainzId; self.lastFmUrl = lastFmUrl
    }
}

/// `getArtistInfo2`: biography and similar artists as Navidrome knows them.
public struct NavidromeArtistInfo: Equatable, Sendable {
    public var biography: String?
    public var lastFmUrl: String?
    public var musicBrainzId: String?
    public var similarArtists: [NavidromeArtist] = []
    public init(biography: String? = nil, lastFmUrl: String? = nil, musicBrainzId: String? = nil, similarArtists: [NavidromeArtist] = []) {
        self.biography = biography; self.lastFmUrl = lastFmUrl; self.musicBrainzId = musicBrainzId; self.similarArtists = similarArtists
    }
}

// MARK: - Payloads

struct AlbumFactsPayload: Decodable {
    struct Named: Decodable { let name: String? }
    struct ReleaseDate: Decodable { let year: Int?; let month: Int?; let day: Int? }
    struct Contributor: Decodable {
        struct Who: Decodable { let name: String? }
        let role: String?; let subRole: String?; let artist: Who?
    }
    struct Song: Decodable { let id: String; let contributors: [Contributor]? }
    struct Detail: Decodable {
        let musicBrainzId: String?
        let releaseTypes: [String]?
        let recordLabels: [Named]?
        let originalReleaseDate: ReleaseDate?
        let version: String?
        let isCompilation: Bool?
        let song: [Song]?
    }
    let album: Detail
}

struct AlbumInfoPayload: Decodable {
    struct Info: Decodable { let notes: String?; let musicBrainzId: String?; let lastFmUrl: String? }
    let albumInfo: Info?
}

struct ArtistInfoPayload: Decodable {
    struct Info: Decodable {
        let biography: String?; let musicBrainzId: String?; let lastFmUrl: String?
        let similarArtist: [NavidromeArtist]?
    }
    let artistInfo2: Info?
}

extension NavidromeClient {
    /// Release types, labels, original date, MusicBrainz id and every song's credits (OpenSubsonic `getAlbum`).
    /// A server without the extension answers with the plain album, which gives empty facts.
    public func albumFacts(id: String) async throws -> NavidromeAlbumFacts {
        try requireSafeID(id)
        let d = try await call("getAlbum", [.init(name: "id", value: id)], as: AlbumFactsPayload.self).album
        var facts = NavidromeAlbumFacts()
        facts.musicBrainzId = d.musicBrainzId.flatMap { $0.isEmpty ? nil : $0 }
        facts.releaseTypes = d.releaseTypes ?? []
        facts.recordLabels = (d.recordLabels ?? []).compactMap { $0.name }.filter { !$0.isEmpty }
        if let r = d.originalReleaseDate, let y = r.year, y > 0 {
            var text = String(y)
            if let m = r.month, m > 0 {
                text += String(format: "-%02d", m)
                if let day = r.day, day > 0 { text += String(format: "-%02d", day) }
            }
            facts.originalReleaseDate = text
        }
        facts.version = d.version.flatMap { $0.isEmpty ? nil : $0 }
        facts.isCompilation = d.isCompilation
        for song in d.song ?? [] {
            for c in song.contributors ?? [] {
                guard let role = c.role, !role.isEmpty, let name = c.artist?.name, !name.isEmpty else { continue }
                facts.credits.append(NavidromeCredit(role: role, subRole: c.subRole.flatMap { $0.isEmpty ? nil : $0 }, name: name, songID: song.id))
            }
        }
        return facts
    }

    /// Liner notes. nil when the server has no info for the album (an unknown id, code 70, is also "none").
    public func albumInfo(id: String) async throws -> NavidromeAlbumInfo? {
        try requireSafeID(id)
        do {
            let p = try await call("getAlbumInfo2", [.init(name: "id", value: id)], as: AlbumInfoPayload.self, notFoundAs404: true)
            guard let i = p.albumInfo else { return nil }
            return NavidromeAlbumInfo(notes: i.notes, musicBrainzId: i.musicBrainzId, lastFmUrl: i.lastFmUrl)
        } catch DiscairError.server(404, _) { return nil }
    }

    /// Biography and similar artists (`count` of them, library artists first as Navidrome orders them).
    public func artistInfo(id: String, similar count: Int = 12) async throws -> NavidromeArtistInfo? {
        try requireSafeID(id)
        do {
            let p = try await call("getArtistInfo2", [.init(name: "id", value: id), .init(name: "count", value: String(min(max(count, 0), 50))),
                                                      .init(name: "includeNotPresent", value: "false")],
                                   as: ArtistInfoPayload.self, notFoundAs404: true)
            guard let i = p.artistInfo2 else { return nil }
            return NavidromeArtistInfo(biography: i.biography, lastFmUrl: i.lastFmUrl, musicBrainzId: i.musicBrainzId, similarArtists: i.similarArtist ?? [])
        } catch DiscairError.server(404, _) { return nil }
    }
}
