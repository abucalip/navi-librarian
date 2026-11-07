import DiscairAudio
import Foundation
import Observation

/// One line in the ⌘K palette: a title, a small right-hand hint, and what it does.
struct PaletteCommand: Identifiable {
    enum Kind: Int { case screen, playback, album, artist }
    enum Action: Equatable {
        case go(Screen)
        case playPause, next, previous, toggleShuffle, cycleRepeat
        case openAlbum(AlbumItem), play(AlbumItem), get(AlbumItem)
        case openArtist(ArtistItem)
    }
    let id: String
    let title: String
    let hint: String
    let kind: Kind
    let action: Action
}

/// Works out what the palette lists and in what order. Pure: no window, no player, so a test can drive it.
enum PaletteCatalog {
    static let screens: [(Screen, String)] = [
        (.home, "Home"), (.recent, "Recently Added"), (.artists, "Artists"), (.albums, "Albums"), (.library, "Songs"), (.queue, "Queue"), (.nowPlaying, "Now Playing"),
        (.discover, "Discover"), (.gapRadar, "Gap Radar"), (.connections, "Connections"), (.smartPlaylists, "Smart Playlists"), (.history, "History"), (.insights, "Insights"), (.downloads, "Downloads"), (.equalizer, "Equalizer"), (.settings, "Settings"),
    ]

    /// Commands that exist whatever you type.
    static func fixed(playing: Bool) -> [PaletteCommand] {
        var list = screens.map { PaletteCommand(id: "go-\($0.0.rawValue)", title: "Go to \($0.1)", hint: "Screen", kind: .screen, action: .go($0.0)) }
        list += [
            PaletteCommand(id: "playpause", title: playing ? "Pause" : "Play", hint: "Playback", kind: .playback, action: .playPause),
            PaletteCommand(id: "next", title: "Next song", hint: "Playback", kind: .playback, action: .next),
            PaletteCommand(id: "previous", title: "Previous song", hint: "Playback", kind: .playback, action: .previous),
            PaletteCommand(id: "shuffle", title: "Toggle shuffle", hint: "Playback", kind: .playback, action: .toggleShuffle),
            PaletteCommand(id: "repeat", title: "Change repeat mode", hint: "Playback", kind: .playback, action: .cycleRepeat),
        ]
        return list
    }

    /// Albums and artists the library knows about: each album can be opened and played (or got, when not owned).
    static func library(albums: [AlbumItem], artists: [ArtistItem]) -> [PaletteCommand] {
        var seen = Set<String>()
        var list: [PaletteCommand] = []
        for a in albums {
            guard seen.insert("\(a.artist.lowercased())|\(a.title.lowercased())").inserted else { continue }
            let label = "\(a.title) · \(a.artist)"
            list.append(PaletteCommand(id: "open-album-\(a.id)-\(a.title)", title: "Open \(label)", hint: "Album", kind: .album, action: .openAlbum(a)))
            if a.owned { list.append(PaletteCommand(id: "play-album-\(a.id)-\(a.title)", title: "Play \(label)", hint: "Album", kind: .album, action: .play(a))) }
            else { list.append(PaletteCommand(id: "get-album-\(a.id)-\(a.title)", title: "Get \(label)", hint: "Album", kind: .album, action: .get(a))) }
        }
        for a in artists {
            list.append(PaletteCommand(id: "artist-\(a.id)-\(a.name)", title: "Open \(a.name)", hint: "Artist", kind: .artist, action: .openArtist(a)))
        }
        return list
    }

    static func fold(_ s: String) -> String { s.folding(options: [.diacriticInsensitive, .caseInsensitive], locale: nil) }

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
            else if isSubsequence(part, of: t) { total += 5 }
            else { return 0 }
        }
        return total
    }

    private static func isSubsequence(_ small: String, of big: String) -> Bool {
        var it = big.makeIterator()
        return small.allSatisfy { ch in while let c = it.next() { if c == ch { return true } }; return false }
    }

    /// With no query: screens and playback. With one: the best matches from everything, library entries last on a tie.
    static func results(query: String, playing: Bool, albums: [AlbumItem], artists: [ArtistItem], limit: Int = 9) -> [PaletteCommand] {
        let trimmed = query.trimmingCharacters(in: .whitespaces)
        let fixed = fixed(playing: playing)
        if trimmed.isEmpty { return Array(fixed.prefix(limit)) }
        let all = fixed + library(albums: albums, artists: artists)
        return all.enumerated()
            .compactMap { i, c -> (Int, Int, PaletteCommand)? in let s = score(c.title, query: trimmed); return s > 0 ? (s, i, c) : nil }
            .sorted { $0.0 != $1.0 ? $0.0 > $1.0 : $0.1 < $1.1 }
            .prefix(limit).map { $0.2 }
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
