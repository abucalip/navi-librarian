import DiscairCore
import Foundation

/// One artist, album or song the Librarian's search found that the library does not hold (`GET /api/search`, `owned: false`).
public struct CatalogHit: Equatable, Sendable {
    public enum Kind: String, Sendable { case artist, album, song }
    public let kind: Kind
    public let name: String
    /// The artist of an album or song; empty for an artist.
    public let artist: String
    /// The album of a song; empty otherwise.
    public let album: String
    public let year: Int?
    public let releaseGroupMBID: String?
    public let artworkURL: URL?
    public init(kind: Kind, name: String, artist: String = "", album: String = "", year: Int? = nil, releaseGroupMBID: String? = nil, artworkURL: URL? = nil) {
        self.kind = kind; self.name = name; self.artist = artist; self.album = album; self.year = year
        self.releaseGroupMBID = releaseGroupMBID; self.artworkURL = artworkURL
    }
}

/// The music the search found beyond the library, in the server's order.
public struct CatalogHits: Equatable, Sendable {
    public var artists: [CatalogHit] = []
    public var albums: [CatalogHit] = []
    public var songs: [CatalogHit] = []
    public init(artists: [CatalogHit] = [], albums: [CatalogHit] = [], songs: [CatalogHit] = []) {
        self.artists = artists; self.albums = albums; self.songs = songs
    }
    public var isEmpty: Bool { artists.isEmpty && albums.isEmpty && songs.isEmpty }

    /// Reads a whole server-sent-events body. Only `result` events with `owned: false` count; every other event, and any
    /// row that is malformed or has no name, is skipped, so one bad row never hides the rest.
    public static func parse(sse body: Data) -> CatalogHits {
        struct Row: Decodable {
            let type: String?, name: String?, artist: String?, album: String?
            let owned: Bool?, year: Int?
            let releaseGroupMBID: String?, artworkURL: String?
            enum CodingKeys: String, CodingKey { case type, name, artist, album, owned, year, releaseGroupMBID = "release_group_mbid", artworkURL = "artwork_url" }
        }
        var hits = CatalogHits()
        let text = String(decoding: body, as: UTF8.self).replacingOccurrences(of: "\r\n", with: "\n")
        for block in text.components(separatedBy: "\n\n") {
            var event = "message"
            var data: [String] = []
            for line in block.split(separator: "\n", omittingEmptySubsequences: true) {
                if line.hasPrefix("event:") { event = line.dropFirst(6).trimmingCharacters(in: .whitespaces) }
                else if line.hasPrefix("data:") { data.append(line.dropFirst(5).trimmingCharacters(in: .whitespaces)) }
            }
            guard event == "result", let row = try? JSONDecoder().decode(Row.self, from: Data(data.joined(separator: "\n").utf8)),
                  row.owned == false, let kind = row.type.flatMap(CatalogHit.Kind.init(rawValue:)),
                  let name = row.name?.trimmingCharacters(in: .whitespacesAndNewlines), !name.isEmpty else { continue }
            let url = row.artworkURL.flatMap(URL.init(string:)).flatMap { $0.scheme == "https" ? $0 : nil }
            let hit = CatalogHit(kind: kind, name: name, artist: row.artist ?? "", album: row.album ?? "", year: row.year, releaseGroupMBID: row.releaseGroupMBID, artworkURL: url)
            switch kind {
            case .artist: hits.artists.append(hit)
            case .album: hits.albums.append(hit)
            case .song: hits.songs.append(hit)
            }
        }
        return hits
    }
}

extension LibrarianClient {
    /// Artists, albums and songs matching `query` that the library does not hold. The server streams its answer and ends it
    /// within about three seconds, so the whole body is read, then parsed.
    public func searchCatalog(_ query: String, limit: Int = 5) async throws -> CatalogHits {
        var allowed = CharacterSet.urlQueryAllowed
        allowed.remove(charactersIn: "&+=#?/")
        let q = String(query.prefix(200)).addingPercentEncoding(withAllowedCharacters: allowed) ?? ""
        let (data, http) = try await authedSendPublic("GET", "api/search?q=\(q)&types=artist,album,song&scope=all&limit=\(limit)", body: nil)
        if let error = failurePublic(http, data) { throw error }
        return CatalogHits.parse(sse: data)
    }
}
