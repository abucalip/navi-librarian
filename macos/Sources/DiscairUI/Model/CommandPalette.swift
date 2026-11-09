import DiscairAudio
import Foundation
import Observation

/// One line in the ⌘K palette: what it is called, a small line under it, and what it does. Albums, artists and songs carry
/// the item so the row can show its artwork; an album or a song also carries a second, quieter action (a play icon).
struct PaletteCommand: Identifiable {
    enum Kind: Int { case artist, album, song, screen, playback }
    enum Action: Equatable {
        case go(Screen)
        case playPause, next, previous, toggleShuffle, cycleRepeat
        case openAlbum(AlbumItem), play(AlbumItem), get(AlbumItem)
        case openArtist(ArtistItem)
        case openSong(SongRow), playSong(SongRow)
    }
    let id: String
    /// "Open Dummy · Portishead" / "Go to Settings": what VoiceOver reads and what older callers match.
    let title: String
    let hint: String
    let kind: Kind
    let action: Action
    /// What the row shows: the name, with the artist (or the page group) under it.
    var name = ""
    var detail = ""
    var album: AlbumItem?
    var artist: ArtistItem?
    var song: SongRow?
    /// The play icon next to the row (Get for an album that is not owned).
    var secondary: Action?
    var secondaryLabel = ""
    /// The words the query is matched against.
    var searchText = ""

    /// The section the row is listed under.
    var section: String {
        switch kind {
        case .artist: "Artists"
        case .album: "Albums"
        case .song: "Songs"
        case .screen, .playback: "Pages and settings"
        }
    }
}

/// Works out what the palette lists and in what order. Pure: no window, no player, so a test can drive it.
enum PaletteCatalog {
    static let screens: [(Screen, String)] = [
        (.home, "Home"), (.recent, "Recently Added"), (.artists, "Artists"), (.albums, "Albums"), (.library, "Songs"), (.queue, "Queue"), (.nowPlaying, "Now Playing"),
        (.discover, "Discover"), (.gapRadar, "Gap Radar"), (.connections, "Connections"), (.timeline, "Timeline"), (.atlas, "Atlas"), (.smartPlaylists, "Smart Playlists"), (.history, "History"), (.insights, "Insights"), (.downloads, "Downloads"), (.equalizer, "Equalizer"), (.settings, "Settings"),
    ]

    /// Commands that exist whatever you type.
    static func fixed(playing: Bool) -> [PaletteCommand] {
        var list = screens.map { s in
            PaletteCommand(id: "go-\(s.0.rawValue)", title: "Go to \(s.1)", hint: "Screen", kind: .screen, action: .go(s.0), name: s.1, detail: "Page", searchText: "Go to \(s.1)")
        }
        func play(_ id: String, _ title: String, _ a: PaletteCommand.Action) -> PaletteCommand {
            PaletteCommand(id: id, title: title, hint: "Playback", kind: .playback, action: a, name: title, detail: "Playback", searchText: title)
        }
        list += [
            play("playpause", playing ? "Pause" : "Play", .playPause),
            play("next", "Next song", .next),
            play("previous", "Previous song", .previous),
            play("shuffle", "Toggle shuffle", .toggleShuffle),
            play("repeat", "Change repeat mode", .cycleRepeat),
        ]
        return list
    }

    /// Albums and artists the library knows about. An album has one line, "Open"; a play icon beside it plays an owned
    /// album, or gets one that is not owned.
    static func library(albums: [AlbumItem], artists: [ArtistItem]) -> [PaletteCommand] {
        var seen = Set<String>()
        var list: [PaletteCommand] = []
        for a in albums {
            guard seen.insert("\(a.artist.lowercased())|\(a.title.lowercased())").inserted else { continue }
            list.append(PaletteCommand(id: "open-album-\(a.id)-\(a.title)", title: "Open \(a.title) · \(a.artist)", hint: "Album", kind: .album, action: .openAlbum(a),
                                       name: a.title, detail: [a.artist, a.year > 0 ? String(a.year) : ""].filter { !$0.isEmpty }.joined(separator: " · "), album: a,
                                       secondary: a.owned ? .play(a) : .get(a), secondaryLabel: a.owned ? "Play" : "Get",
                                       searchText: "\(a.title) \(a.artist)"))
        }
        for a in artists {
            list.append(PaletteCommand(id: "artist-\(a.id)-\(a.name)", title: "Open \(a.name)", hint: "Artist", kind: .artist, action: .openArtist(a),
                                       name: a.name, detail: a.albumCount == 1 ? "1 album" : "\(a.albumCount) albums", artist: a, searchText: a.name))
        }
        return list
    }

    /// Songs the server found: open the album at the song, or play the song with the icon.
    static func songs(_ rows: [SongRow]) -> [PaletteCommand] {
        rows.compactMap { s in
            guard let id = s.remoteID else { return nil }
            return PaletteCommand(id: "song-\(id)", title: "Open \(s.title) · \(s.artist)", hint: "Song", kind: .song, action: .openSong(s),
                                  name: s.title, detail: "\(s.artist) — \(s.albumItem.title)", song: s, secondary: .playSong(s), secondaryLabel: "Play",
                                  searchText: "\(s.title) \(s.artist) \(s.albumItem.title)")
        }
    }

    static func fold(_ s: String) -> String { LibrarySearch.fold(s) }

    /// 0 = no match. Higher is better: starts with the query, then a word starts with it, then it appears inside, then
    /// its letters appear in order. Every word of the query must match somewhere.
    static func score(_ title: String, query: String) -> Int {
        let q = fold(query).split(separator: " ").map(String.init)
        guard !q.isEmpty else { return 1 }
        let t = fold(title)
        let words = t.split(whereSeparator: { !$0.isLetter && !$0.isNumber }).map(String.init)
        var total = 0
        for part in q {
            if t.hasPrefix(part) || words.first?.hasPrefix(part) == true { total += 40 }
            else if words.contains(where: { $0.hasPrefix(part) }) { total += 30 }
            else if t.contains(part) { total += 20 }
            else if t.count <= 20, isSubsequence(part, of: t) { total += 5 }      // letters in order: short names only, or everything matches
            else { return 0 }
        }
        return total
    }

    private static func isSubsequence(_ small: String, of big: String) -> Bool {
        var it = big.makeIterator()
        return small.allSatisfy { ch in while let c = it.next() { if c == ch { return true } }; return false }
    }

    /// Most rows listed under each heading.
    static let perSection = [PaletteCommand.Kind.artist: 4, .album: 5, .song: 5, .screen: 4, .playback: 4]

    /// With no query: screens and playback. With one: the best matches, grouped as artists, albums, songs, then pages and
    /// settings (playback commands count with pages).
    static func results(query: String, playing: Bool, albums: [AlbumItem], artists: [ArtistItem], songs rows: [SongRow] = [], limit: Int = 9) -> [PaletteCommand] {
        let trimmed = query.trimmingCharacters(in: .whitespaces)
        let fixed = fixed(playing: playing)
        if trimmed.isEmpty { return Array(fixed.prefix(limit)) }
        let all = library(albums: albums, artists: artists) + songs(rows) + fixed
        let scored = all.enumerated()
            .compactMap { i, c -> (Int, Int, PaletteCommand)? in let s = score(c.searchText.isEmpty ? c.title : c.searchText, query: trimmed); return s > 0 ? (s, i, c) : nil }
            .sorted { $0.0 != $1.0 ? $0.0 > $1.0 : $0.1 < $1.1 }
            .map { $0.2 }
        var out: [PaletteCommand] = []
        for kinds in [[PaletteCommand.Kind.artist], [.album], [.song], [.screen, .playback]] {
            let group = scored.filter { kinds.contains($0.kind) }
            out += Array(group.prefix(perSection[kinds[0]] ?? 4))
        }
        return out
    }
}

/// The palette's open state, query and highlighted row.
@MainActor
@Observable
public final class PaletteModel {
    public var isOpen = false
    public var query = "" { didSet { highlight = 0 } }
    public var highlight = 0

    public init() {}

    public func toggle() { isOpen ? close() : open() }
    public func open() { query = ""; highlight = 0; isOpen = true }
    public func close() { isOpen = false }

    func move(_ delta: Int, count: Int) {
        guard count > 0 else { highlight = 0; return }
        highlight = (highlight + delta + count) % count
    }
}
