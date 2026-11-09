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
    /// Lower case without accents, so "beyonce" finds "Beyoncé", and without apostrophes, so "somethin else" finds
    /// "Somethin’ Else" (straight or curly). Other punctuation becomes a space.
    static func fold(_ s: String) -> String {
        let plain = s.folding(options: [.diacriticInsensitive, .caseInsensitive, .widthInsensitive], locale: nil)
        var out = ""
        for ch in plain {
            if "'’‘`´ʼ".contains(ch) { continue }
            out.append(ch.isLetter || ch.isNumber ? ch : " ")
        }
        return out.split(whereSeparator: \.isWhitespace).joined(separator: " ")
    }

    /// True when every word of `query` appears in one of the fields. An empty query matches everything. A query typed without
    /// spaces ("acdc") also matches a field written with punctuation ("AC/DC").
    static func matches(_ fields: [String], query: String) -> Bool {
        let folded = fold(query)
        let words = folded.split(separator: " ")
        guard !words.isEmpty else { return true }
        let hay = fields.map(fold)
        if words.allSatisfy({ w in hay.contains { $0.contains(w) } }) { return true }
        let compact = folded.replacingOccurrences(of: " ", with: "")
        return hay.contains { $0.replacingOccurrences(of: " ", with: "").contains(compact) }
    }

    static func artists(_ list: [ArtistItem], query: String) -> [ArtistItem] { list.filter { matches([$0.name], query: query) } }
    static func albums(_ list: [AlbumItem], query: String) -> [AlbumItem] { list.filter { $0.owned && matches([$0.title, $0.artist], query: query) } }
    static func songs(_ list: [SongRow], query: String) -> [SongRow] { list.filter { matches([$0.title, $0.artist, $0.albumItem.title], query: query) } }

    /// The few best matches of each kind for the floating sheet.
    /// `serverSongs` are the server's own matches (the whole library); they follow the loaded songs that match, without repeats.
    static func results(query: String, artists a: [ArtistItem], albums b: [AlbumItem], songs c: [SongRow], serverSongs: [SongRow] = [], limit: Int = 5) -> LibrarySearchResults {
        guard !fold(query).isEmpty else { return LibrarySearchResults() }
        let local = songs(c, query: query)
        let seen = Set(local.compactMap(\.remoteID))
        return LibrarySearchResults(artists: Array(artists(a, query: query).prefix(limit)),
                                    albums: Array(albums(b, query: query).prefix(limit)),
                                    songs: Array((local + serverSongs.filter { !seen.contains($0.remoteID ?? "") }).prefix(limit)))
    }

    /// The latest played songs first, at most `limit`.
    static func recentlyPlayed(_ songs: [SongRow], limit: Int = 20) -> [SongRow] {
        Array(songs.filter { $0.playedAt != nil }.sorted { ($0.playedAt ?? .distantPast) > ($1.playedAt ?? .distantPast) }.prefix(limit))
    }
}
