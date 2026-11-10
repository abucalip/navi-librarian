import Foundation

/// One similar artist on an album or artist page. `owned` is the server's word that the library holds them.
public struct SimilarArtistEntry: Decodable, Equatable, Sendable, Identifiable {
    public var id: String { key.isEmpty ? name.lowercased() : key }
    public let name: String
    public let key: String
    public let owned: Bool
    public let navidromeID: String?
    public let artworkURL: URL?

    enum CodingKeys: String, CodingKey { case name, key, owned, id, artworkUrl = "artwork_url" }

    public init(name: String, key: String = "", owned: Bool = false, navidromeID: String? = nil, artworkURL: URL? = nil) {
        self.name = name; self.key = key; self.owned = owned; self.navidromeID = navidromeID; self.artworkURL = artworkURL
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        name = ((try? c.decode(String.self, forKey: .name)) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        key = (try? c.decode(String.self, forKey: .key)) ?? ""
        owned = (try? c.decode(Bool.self, forKey: .owned)) ?? false
        navidromeID = try? c.decode(String.self, forKey: .id)
        // Only absolute https addresses are used; a server-relative path would need the Librarian address and its login.
        artworkURL = (try? c.decode(String.self, forKey: .artworkUrl)).flatMap(URL.init(string:)).flatMap { $0.scheme == "https" ? $0 : nil }
    }
}

/// One similar album the library does not hold.
public struct SimilarAlbumEntry: Decodable, Equatable, Sendable, Identifiable {
    public var id: String { key.isEmpty ? (artist + "|" + name).lowercased() : key }
    public let name: String
    public let artist: String
    public let key: String
    public let year: Int?
    public let owned: Bool

    enum CodingKeys: String, CodingKey { case name, artist, key, year, owned }

    public init(name: String, artist: String, key: String = "", year: Int? = nil, owned: Bool = false) {
        self.name = name; self.artist = artist; self.key = key; self.year = year; self.owned = owned
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        name = ((try? c.decode(String.self, forKey: .name)) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        artist = ((try? c.decode(String.self, forKey: .artist)) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        key = (try? c.decode(String.self, forKey: .key)) ?? ""
        year = try? c.decode(Int.self, forKey: .year)
        owned = (try? c.decode(Bool.self, forKey: .owned)) ?? false
    }
}

/// A track the server lists for an album the library does not hold.
public struct RelatedTrack: Decodable, Equatable, Sendable {
    public let title: String
    public let number: Int?
    public let durationSeconds: Int?
    enum CodingKeys: String, CodingKey { case title, number = "track_number", durationSeconds = "duration_seconds" }
}

/// One album on an artist page (`albums`: owned and not owned together, most listened first).
public struct ArtistAlbumEntry: Decodable, Equatable, Sendable, Identifiable {
    public var id: String { key.isEmpty ? name.lowercased() : key }
    public let name: String
    public let key: String
    public let year: Int?
    public let owned: Bool
    enum CodingKeys: String, CodingKey { case name, key, year, owned }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        name = ((try? c.decode(String.self, forKey: .name)) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        key = (try? c.decode(String.self, forKey: .key)) ?? ""
        year = try? c.decode(Int.self, forKey: .year)
        owned = (try? c.decode(Bool.self, forKey: .owned)) ?? false
    }
}

/// The server's `done` event: `partial` means a section ended early (its deadline) or failed, so asking again may fill it.
struct PageDone: Decodable { let partial: Bool? }

public struct AlbumPageRelated: Equatable, Sendable {
    public var partial = false
    public var similarArtists: [SimilarArtistEntry] = []
    public var similarAlbums: [SimilarAlbumEntry] = []
    public var tracks: [RelatedTrack] = []
    /// The album's MusicBrainz release group, which keys its artwork index. nil when the server did not say.
    public var releaseGroupMBID: String?
}

struct Section<T: Decodable>: Decodable { let items: [T]? }

struct AlbumPageEnvelope: Decodable {
    struct Sections: Decodable {
        let similarArtists: Section<SimilarArtistEntry>?
        let similarAlbums: Section<SimilarAlbumEntry>?
        let tracks: Section<RelatedTrack>?
        struct AlbumBlock: Decodable {
            struct Info: Decodable {
                let releaseGroupMBID: String?
                enum CodingKeys: String, CodingKey { case releaseGroupMBID = "release_group_mbid" }
                init(from decoder: Decoder) throws {
                    let c = try decoder.container(keyedBy: CodingKeys.self)
                    releaseGroupMBID = try? c.decodeIfPresent(String.self, forKey: .releaseGroupMBID)
                }
            }
            let album: Info?
        }
        let album: AlbumBlock?
        enum CodingKeys: String, CodingKey { case album, similarArtists = "similar_artists", similarAlbums = "similar_albums", tracks }
    }
    let sections: Sections
    let done: PageDone?
    var related: AlbumPageRelated {
        AlbumPageRelated(partial: done?.partial ?? false, similarArtists: sections.similarArtists?.items ?? [], similarAlbums: (sections.similarAlbums?.items ?? []).filter { !$0.owned && !$0.name.isEmpty },
                         tracks: sections.tracks?.items ?? [],
                         releaseGroupMBID: sections.album?.album?.releaseGroupMBID.flatMap { $0.isEmpty ? nil : $0 })
    }
}

/// One of an artist's most listened songs (`top_songs` on the artist page).
public struct TopSongEntry: Decodable, Equatable, Sendable, Identifiable {
    public var id: Int { rank }
    public let rank: Int
    public let name: String
    public let listenCount: Int?
    public let source: String?
    public let owned: Bool
    public let album: String?

    enum CodingKeys: String, CodingKey { case rank, name, listenCount = "listen_count", source, owned, album }

    public init(rank: Int, name: String, listenCount: Int? = nil, source: String? = nil, owned: Bool = false, album: String? = nil) {
        self.rank = rank; self.name = name; self.listenCount = listenCount; self.source = source; self.owned = owned; self.album = album
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        rank = (try? c.decode(Int.self, forKey: .rank)) ?? 0
        name = ((try? c.decode(String.self, forKey: .name)) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        listenCount = try? c.decode(Int.self, forKey: .listenCount)
        source = try? c.decode(String.self, forKey: .source)
        owned = (try? c.decode(Bool.self, forKey: .owned)) ?? false
        album = (try? c.decode(String.self, forKey: .album)).map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.flatMap { $0.isEmpty ? nil : $0 }
    }

    /// "7.6K", "1.2M", or the plain number; nil when the source gave no count.
    public var listensText: String? {
        guard let n = listenCount, n > 0 else { return nil }
        if n >= 1_000_000 { return String(format: "%.1fM", Double(n) / 1_000_000) }
        if n >= 1_000 { return String(format: "%.1fK", Double(n) / 1_000) }
        return String(n)
    }
}

/// The parts of an artist page the macOS app shows besides the library's own albums.
public struct ArtistPageRelated: Equatable, Sendable {
    public var partial = false
    public var albums: [ArtistAlbumEntry] = []
    public var similar: [SimilarArtistEntry] = []
    public var bio: String?
    public var bioSource: String?
    public var topSongs: [TopSongEntry] = []
}

struct ArtistPageEnvelope: Decodable {
    struct Bio: Decodable { let text: String?; let source: String? }
    struct BioSection: Decodable { let bio: Bio? }
    struct Sections: Decodable {
        let similar: Section<SimilarArtistEntry>?
        let bio: BioSection?
        let topSongs: Section<TopSongEntry>?
        let albums: Section<ArtistAlbumEntry>?
        enum CodingKeys: String, CodingKey { case similar, bio, albums, topSongs = "top_songs" }
    }
    let sections: Sections
    let done: PageDone?
    var related: ArtistPageRelated {
        let text = sections.bio?.bio?.text?.trimmingCharacters(in: .whitespacesAndNewlines)
        return ArtistPageRelated(partial: done?.partial ?? false, albums: (sections.albums?.items ?? []).filter { !$0.name.isEmpty }, similar: sections.similar?.items ?? [], bio: (text?.isEmpty == false) ? text : nil,
                                 bioSource: sections.bio?.bio?.source,
                                 topSongs: (sections.topSongs?.items ?? []).filter { !$0.name.isEmpty }.sorted { $0.rank < $1.rank })
    }
}
