import Foundation

/// The tabs of the Library page. `overview` is the landing view: Recently Added tiles and the Recently played pane.
public enum LibraryTab: String, CaseIterable, Sendable, Identifiable {
    case overview = "Overview", artists = "Artists", albums = "Albums", songs = "Songs"
    public var id: String { rawValue }
}

/// What the Library search finds. Owned music only: nothing from the Librarian's picks or missing albums.
struct LibrarySearchResults: Equatable {
    var artists: [ArtistItem] = []
    var albums: [AlbumItem] = []
    var songs: [SongRow] = []
    var isEmpty: Bool { artists.isEmpty && albums.isEmpty && songs.isEmpty }
}

/// Search and filtering of the owned library by typed text. Pure, so it is tested without a window.
enum LibrarySearch {
    /// Lower case without accents, so "beyonce" finds "Beyoncé".
    static func fold(_ s: String) -> String { s.folding(options: [.diacriticInsensitive, .caseInsensitive], locale: nil) }

    /// True when every word of `query` appears in one of the fields. An empty query matches everything.
    static func matches(_ fields: [String], query: String) -> Bool {
        let words = fold(query).split(whereSeparator: \.isWhitespace)
        guard !words.isEmpty else { return true }
        let hay = fields.map(fold)
        return words.allSatisfy { w in hay.contains { $0.contains(w) } }
    }

    static func artists(_ list: [ArtistItem], query: String) -> [ArtistItem] { list.filter { matches([$0.name], query: query) } }
    static func albums(_ list: [AlbumItem], query: String) -> [AlbumItem] { list.filter { $0.owned && matches([$0.title, $0.artist], query: query) } }
    static func songs(_ list: [SongRow], query: String) -> [SongRow] { list.filter { matches([$0.title, $0.artist, $0.albumItem.title], query: query) } }

    /// The few best matches of each kind for the floating sheet.
    static func results(query: String, artists a: [ArtistItem], albums b: [AlbumItem], songs c: [SongRow], limit: Int = 5) -> LibrarySearchResults {
        guard !fold(query).trimmingCharacters(in: .whitespaces).isEmpty else { return LibrarySearchResults() }
        return LibrarySearchResults(artists: Array(artists(a, query: query).prefix(limit)),
                                    albums: Array(albums(b, query: query).prefix(limit)),
                                    songs: Array(songs(c, query: query).prefix(limit)))
    }

    /// The latest played songs first, at most `limit`.
    static func recentlyPlayed(_ songs: [SongRow], limit: Int = 20) -> [SongRow] {
        Array(songs.filter { $0.playedAt != nil }.sorted { ($0.playedAt ?? .distantPast) > ($1.playedAt ?? .distantPast) }.prefix(limit))
    }
}
