import Foundation

/// The tabs of the Library page. `overview` is the landing view: Recently Added tiles and the Recently played pane.
public enum LibraryTab: String, CaseIterable, Sendable, Identifiable {
    case overview = "Overview", artists = "Artists", albums = "Albums", songs = "Songs"
    public var id: String { rawValue }
}

/// What the Library search finds. Owned music only: nothing from the Librarian's picks or missing albums.
struct LibrarySearchResults: Equatable, Sendable {
    var artists: [ArtistItem] = []
    var albums: [AlbumItem] = []
    var songs: [SongRow] = []
    var isEmpty: Bool { artists.isEmpty && albums.isEmpty && songs.isEmpty }
}

struct SearchLibrarySnapshot: Equatable, Sendable {
    var artists: [ArtistItem] = []
    var albums: [AlbumItem] = []
    var recent: [AlbumItem] = []
    var dismissed: Set<String> = []
    var dismissedArtists: Set<String> = []

    func visibleAlbums(including additional: [AlbumItem] = []) -> [AlbumItem] {
        (albums + recent + additional).filter {
            !Task.isCancelled && !dismissed.contains(AcquisitionModel.key($0)) && !dismissedArtists.contains($0.artist.lowercased())
        }
    }
}

struct LibrarySearchRequest: Equatable, Sendable {
    let query: String
    let tab: LibraryTab
    var library = SearchLibrarySnapshot()
    var songs: [SongRow] = []
    var serverSongs: [SongRow] = []

    func results() async -> LibrarySearchResults {
        await LibrarySearch.inBackground {
            switch tab {
            case .overview:
                LibrarySearch.results(query: query, artists: library.artists, albums: library.visibleAlbums(),
                                      songs: songs, serverSongs: serverSongs)
            case .artists:
                LibrarySearchResults(artists: LibrarySearch.artists(library.artists, query: query))
            case .albums:
                LibrarySearchResults(albums: LibrarySearch.albums(library.visibleAlbums(), query: query))
            case .songs:
                LibrarySearchResults(songs: LibrarySearch.songs(songs, query: query))
            }
        }
    }
}

/// Search and filtering of the owned library by typed text. Pure, so it is tested without a window.
enum LibrarySearch {
    /// Keep filtering and ranking away from the text field's main actor. Superseded queries can stop during a scan.
    static func inBackground<Value: Sendable>(_ work: @escaping @Sendable () -> Value) async -> Value {
        let worker = Task.detached(priority: .userInitiated, operation: work)
        return await withTaskCancellationHandler {
            await worker.value
        } onCancel: {
            worker.cancel()
        }
    }

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
        Query(query).matches(fields)
    }

    private struct Query {
        let words: [Substring]
        let compact: String

        init(_ query: String) {
            let folded = LibrarySearch.fold(query)
            words = folded.split(separator: " ")
            compact = words.joined()
        }

        func matches(_ fields: [String]) -> Bool {
            guard !Task.isCancelled else { return false }
            guard !words.isEmpty else { return true }
            let hay = fields.map(LibrarySearch.fold)
            if words.allSatisfy({ word in hay.contains { $0.contains(word) } }) { return true }
            return hay.contains { $0.replacingOccurrences(of: " ", with: "").contains(compact) }
        }
    }

    static func artists(_ list: [ArtistItem], query: String) -> [ArtistItem] {
        let query = Query(query)
        return list.filter { query.matches([$0.name]) }
    }

    static func albums(_ list: [AlbumItem], query: String) -> [AlbumItem] {
        let query = Query(query)
        return list.filter { $0.owned && query.matches([$0.title, $0.artist]) }
    }

    static func songs(_ list: [SongRow], query: String) -> [SongRow] {
        let query = Query(query)
        return list.filter { query.matches([$0.title, $0.artist, $0.albumItem.title]) }
    }

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
