import DiscairCore
import Foundation

/// More like this or Less like this on an artist (Star Operation S2c, `/api/discovery/artist-lean`). Neither hides anything.
public enum ArtistLeanKind: String, Sendable, Equatable { case more, less }

public struct ArtistLean: Sendable, Equatable {
    public let artist: String
    public let lean: ArtistLeanKind
    public init(artist: String, lean: ArtistLeanKind) { self.artist = artist; self.lean = lean }
}

/// What the owner told the Librarian to leave out of picks, or to lean on. A block hides picks only; the library is never touched.
public struct Blocklist: Sendable, Equatable {
    public var genres: [String]
    /// Artists hidden with Not this artist.
    public var hiddenArtists: [String]
    public var leans: [ArtistLean]
    public init(genres: [String] = [], hiddenArtists: [String] = [], leans: [ArtistLean] = []) {
        self.genres = genres; self.hiddenArtists = hiddenArtists; self.leans = leans
    }
    public var isEmpty: Bool { genres.isEmpty && hiddenArtists.isEmpty && leans.isEmpty }
    public var count: Int { genres.count + hiddenArtists.count + leans.count }

    /// The three answers, read leniently: a blank name or a lean this app does not know is dropped, never an error.
    public static func parse(genres: Data, artists: Data, leans: Data) -> Blocklist {
        func rows(_ data: Data, _ key: String) -> [[String: Any]] {
            ((try? JSONSerialization.jsonObject(with: data)) as? [String: Any])?[key] as? [[String: Any]] ?? []
        }
        func name(_ row: [String: Any], _ key: String) -> String? {
            guard let s = (row[key] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines), !s.isEmpty else { return nil }
            return s
        }
        return Blocklist(
            genres: rows(genres, "genres").compactMap { name($0, "genre") },
            hiddenArtists: rows(artists, "artists").compactMap { name($0, "artist") },
            leans: rows(leans, "artists").compactMap { row in
                guard let artist = name(row, "artist"), let kind = (row["lean"] as? String).flatMap(ArtistLeanKind.init(rawValue:)) else { return nil }
                return ArtistLean(artist: artist, lean: kind)
            })
    }
}

extension LibrarianClient {
    /// Reads the three lists live (`blocked-genres`, `blocked-artists`, `artist-lean`).
    public func blocklist() async throws -> Blocklist {
        async let g = blocklistRead("api/discovery/blocked-genres")
        async let a = blocklistRead("api/discovery/blocked-artists")
        async let l = blocklistRead("api/discovery/artist-lean")
        return Blocklist.parse(genres: try await g, artists: try await a, leans: try await l)
    }

    public func blockGenre(_ genre: String) async throws { try await blocklistWrite("POST", "blocked-genres", ["genre": genre]) }
    public func unblockGenre(_ genre: String) async throws { try await blocklistWrite("DELETE", "blocked-genres", ["genre": genre]) }
    /// Lifts a "Not this artist" (the hide and its score penalty).
    public func unblockArtist(_ artist: String) async throws { try await blocklistWrite("DELETE", "blocked-artists", ["artist": artist]) }
    public func clearArtistLean(_ artist: String) async throws { try await blocklistWrite("DELETE", "artist-lean", ["artist": artist]) }

    /// `genres` rides along as the server's metadata (it keeps only `genres` and `lens`).
    public func setArtistLean(_ artist: String, _ lean: ArtistLeanKind, genres: [String] = []) async throws {
        var body: [String: Any] = ["artist": artist, "lean": lean.rawValue]
        if !genres.isEmpty { body["metadata"] = ["genres": genres] }
        try await blocklistWrite("POST", "artist-lean", body)
    }

    private func blocklistRead(_ path: String) async throws -> Data {
        let (data, http) = try await authedSendPublic("GET", path, body: nil)
        if let failure = failurePublic(http, data) { throw failure }
        return data
    }

    private func blocklistWrite(_ method: String, _ route: String, _ body: [String: Any]) async throws {
        let (data, http) = try await authedSendPublic(method, "api/discovery/" + route, body: try JSONSerialization.data(withJSONObject: body, options: [.sortedKeys]))
        if let failure = failurePublic(http, data) { throw failure }
    }
}
