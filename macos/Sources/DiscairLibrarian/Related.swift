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

public struct AlbumPageRelated: Equatable, Sendable {
    public var similarArtists: [SimilarArtistEntry] = []
    public var similarAlbums: [SimilarAlbumEntry] = []
    public var tracks: [RelatedTrack] = []
}

struct Section<T: Decodable>: Decodable { let items: [T]? }

struct AlbumPageEnvelope: Decodable {
    struct Sections: Decodable {
        let similarArtists: Section<SimilarArtistEntry>?
        let similarAlbums: Section<SimilarAlbumEntry>?
        let tracks: Section<RelatedTrack>?
        enum CodingKeys: String, CodingKey { case similarArtists = "similar_artists", similarAlbums = "similar_albums", tracks }
    }
    let sections: Sections
    var related: AlbumPageRelated {
        AlbumPageRelated(similarArtists: sections.similarArtists?.items ?? [], similarAlbums: (sections.similarAlbums?.items ?? []).filter { !$0.owned && !$0.name.isEmpty },
                         tracks: sections.tracks?.items ?? [])
    }
}

struct ArtistPageEnvelope: Decodable {
    struct Sections: Decodable { let similar: Section<SimilarArtistEntry>? }
    let sections: Sections
}
