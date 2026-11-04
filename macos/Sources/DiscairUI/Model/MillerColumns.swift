import Foundation

/// Miller columns over the songs already loaded (contract section 6.3): Genre, Artist, Album, then the tracks.
/// Pure, so the grouping is tested without a window. A choice in one column narrows the next.
public enum MillerColumns {
    public struct Entry: Identifiable, Equatable, Sendable {
        public let name: String
        public let count: Int
        public var id: String { name }
    }

    public static let unknownGenre = "Unknown genre"
    public static let unknownAlbum = "Unknown album"

    public static func genreName(_ r: SongRow) -> String { r.genre.isEmpty ? unknownGenre : r.genre }
    public static func albumName(_ r: SongRow) -> String { r.albumItem.title.isEmpty ? unknownAlbum : r.albumItem.title }

    public static func genres(_ rows: [SongRow]) -> [Entry] { entries(rows.map(genreName)) }

    public static func artists(_ rows: [SongRow], genre: String?) -> [Entry] {
        entries(rows.filter { genre == nil || genreName($0) == genre }.map(\.artist))
    }

    public static func albums(_ rows: [SongRow], genre: String?, artist: String?) -> [Entry] {
        entries(narrowed(rows, genre, artist, nil).map(albumName))
    }

    /// Disc, then track number, then title; songs without a number follow the numbered ones.
    public static func tracks(_ rows: [SongRow], genre: String?, artist: String?, album: String?) -> [SongRow] {
        narrowed(rows, genre, artist, album).enumerated().sorted { l, r in
            let a = l.element, b = r.element
            if (a.disc ?? 1) != (b.disc ?? 1) { return (a.disc ?? 1) < (b.disc ?? 1) }
            switch (a.track, b.track) {
            case let (x?, y?) where x != y: return x < y
            case (.some, nil): return true
            case (nil, .some): return false
            default:
                let c = a.title.localizedCaseInsensitiveCompare(b.title)
                return c == .orderedSame ? l.offset < r.offset : c == .orderedAscending
            }
        }.map(\.element)
    }

    /// The choice is kept only while it still exists after the column before it changed; otherwise it is cleared.
    public static func valid(_ choice: String?, in entries: [Entry]) -> String? {
        guard let choice, entries.contains(where: { $0.name == choice }) else { return nil }
        return choice
    }

    private static func narrowed(_ rows: [SongRow], _ genre: String?, _ artist: String?, _ album: String?) -> [SongRow] {
        rows.filter {
            (genre == nil || genreName($0) == genre) && (artist == nil || $0.artist == artist) && (album == nil || albumName($0) == album)
        }
    }

    /// Distinct names with song counts, A to Z ignoring case; the "Unknown ..." group goes last.
    private static func entries(_ names: [String]) -> [Entry] {
        var counts: [String: Int] = [:]
        for n in names { counts[n, default: 0] += 1 }
        return counts.map { Entry(name: $0.key, count: $0.value) }.sorted {
            let au = $0.name == unknownGenre || $0.name == unknownAlbum, bu = $1.name == unknownGenre || $1.name == unknownAlbum
            if au != bu { return bu }
            return $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending
        }
    }
}
