import Foundation

/// The Songs table's columns and ordering (contract section 6.1). Pure, so the order is tested without a window.
public enum SongColumn: String, CaseIterable, Sendable {
    case title = "Title", artist = "Artist", year = "Year", genre = "Genre", format = "Format", bitrate = "Bitrate"
    case rating = "Rating", plays = "Plays", lastPlayed = "Last played", added = "Added", mbid = "MBID"

    /// The order a first click gives: text A to Z, everything else with the most (or newest) first.
    public var startsAscending: Bool {
        switch self {
        case .title, .artist, .genre, .format, .mbid: true
        default: false
        }
    }
}

public enum SongTable {
    /// Rows ordered by one column. Unknown values (no rating, never played, no bitrate, no year) come last in both
    /// directions so a half-empty column does not bury the songs that have data. Ties keep the library order.
    public static func sorted(_ rows: [SongRow], by column: SongColumn, ascending: Bool, onlyMissingMBID: Bool = false) -> [SongRow] {
        let base = onlyMissingMBID ? rows.filter { !$0.hasMBID } : rows
        func text(_ a: String, _ b: String) -> Int? {
            switch a.localizedCaseInsensitiveCompare(b) { case .orderedAscending: -1; case .orderedDescending: 1; case .orderedSame: nil }
        }
        func num<T: Comparable>(_ a: T, _ b: T) -> Int? { a < b ? -1 : (a > b ? 1 : nil) }
        // nil result = tie. A known value always beats an unknown one.
        func compare(_ a: SongRow, _ b: SongRow) -> (result: Int?, unknown: Bool) {
            func known<T: Comparable>(_ x: T?, _ y: T?) -> (Int?, Bool) {
                switch (x, y) {
                case let (x?, y?): return (num(x, y), false)
                case (nil, nil): return (nil, false)
                case (nil, _): return (1, true)
                default: return (-1, true)
                }
            }
            switch column {
            case .title: return (text(a.title, b.title), false)
            case .artist: return (text(a.artist, b.artist), false)
            case .genre: return (text(a.genre, b.genre), false)
            case .format: return (text(a.format, b.format), false)
            case .year: let r = known(a.year > 0 ? a.year : nil, b.year > 0 ? b.year : nil); return (r.0, r.1)
            case .bitrate: let r = known(a.bitrateKbps > 0 ? a.bitrateKbps : nil, b.bitrateKbps > 0 ? b.bitrateKbps : nil); return (r.0, r.1)
            case .rating: let r = known(a.rating > 0 ? a.rating : nil, b.rating > 0 ? b.rating : nil); return (r.0, r.1)
            case .plays: return (num(a.plays, b.plays), false)
            case .lastPlayed: let r = known(a.playedAt, b.playedAt); return (r.0, r.1)
            case .added: let r = known(a.addedAt, b.addedAt); return (r.0, r.1)
            case .mbid: return (num(a.hasMBID ? 1 : 0, b.hasMBID ? 1 : 0), false)   // ascending = missing first
            }
        }
        return base.enumerated().sorted { l, r in
            let (c, unknown) = compare(l.element, r.element)
            guard let c else { return l.offset < r.offset }
            return unknown ? c < 0 : (ascending ? c < 0 : c > 0)
        }.map(\.element)
    }

    /// "★★★☆☆" for 3; empty for unrated.
    public static func stars(_ rating: Int) -> String {
        guard rating > 0 else { return "" }
        let n = min(rating, 5)
        return String(repeating: "★", count: n) + String(repeating: "☆", count: 5 - n)
    }
}
