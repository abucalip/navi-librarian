import Foundation

/// Presentation models and sample data for the UI layer (contract M4).
/// Sample data mirrors the mockup (`docs/design/macos-m4/mockups.html`) so screenshots can be compared with it.
/// Real data arrives through `DiscairActions` / the view model in later slices; themes never talk to the network.

public struct AlbumItem: Identifiable, Equatable, Sendable {
    public let id: Int
    public let title: String
    public let artist: String
    public let year: Int
    public let genre: String
    public let format: String
    public let owned: Bool
    /// Placeholder cover colour (0..360), used when there is no artwork.
    public let hue: Double
    /// Set for live albums: the Navidrome album id (nil for a Librarian pick, which the library does not hold yet).
    public var remoteID: String? = nil
    /// Navidrome cover art id; the image is fetched through `ArtworkStore`.
    public var coverArt: String? = nil
    /// Librarian's reason and suggested tracks, for picks.
    public var reason: String? = nil
    public var suggestedTracks: [String] = []
    public var artistRemoteID: String? = nil
    public var songCount: Int? = nil
    public var durationSeconds: Int? = nil

    /// "Artist · 1991 · Genre" without empty parts (live data may not know a year or genre).
    public func line(_ parts: [String]) -> String { parts.filter { !$0.isEmpty }.joined(separator: " · ") }
    public var yearText: String { year > 0 ? String(year) : "" }
}

public struct ArtistItem: Identifiable, Equatable, Sendable {
    public let id: Int
    /// Navidrome artist id (nil for sample data).
    public var remoteID: String? = nil
    public let name: String
    public let albumCount: Int
    /// First letter for the A-Z index ("#" for anything that is not a letter).
    public var letter: String {
        guard let c = name.folding(options: .diacriticInsensitive, locale: nil).uppercased().first, c.isLetter else { return "#" }
        return String(c)
    }
}

public struct TrackItem: Identifiable, Equatable, Sendable {
    public let id: Int
    public let title: String
    public let duration: String
    public let format: String
    public let owned: Bool
    public let playing: Bool
}

public struct SongRow: Identifiable, Equatable, Sendable {
    public let id: Int
    public let album: Int
    public let title, artist, genre, format, bitrate, lastPlayed, added: String
    public let year, plays: Int
    /// Live rows: the Navidrome song id and the album the cover comes from (nil for the sample rows).
    public var remoteID: String? = nil
    public var cover: AlbumItem? = nil
    public var suffix: String? = nil
    public var seconds: Double = 0
    public var track: Int? = nil
    public var disc: Int? = nil
    /// The path Navidrome reports (used to find the file on the SMB mount).
    public var path: String? = nil
    /// Sortable values behind the table's text columns. 0 / nil = unknown (sorted last in either direction).
    public var rating = 0
    public var bitrateKbps = 0
    public var addedAt: Date? = nil
    public var playedAt: Date? = nil
    /// False when the song has no MusicBrainz id (the Librarian cannot match it until the tag is fixed).
    public var hasMBID = true
    /// The album whose cover this row shows.
    public var albumItem: AlbumItem { cover ?? Fixtures.albums[album] }
}

public enum Fixtures {
    public static let albums: [AlbumItem] = [
        ("Laughing Stock", "Talk Talk", 1991, "Post-rock", "FLAC 16/44", true, 28),
        ("Spirit of Eden", "Talk Talk", 1988, "Art rock", "FLAC 16/44", true, 150),
        ("Music Has the Right to Children", "Boards of Canada", 1998, "IDM", "FLAC 16/44", true, 200),
        ("Dummy", "Portishead", 1994, "Trip hop", "FLAC 16/44", true, 340),
        ("Hounds of Love", "Kate Bush", 1985, "Art pop", "FLAC 24/96", true, 8),
        ("Con Todo El Mundo", "Khruangbin", 2018, "Psychedelic soul", "MP3 320", true, 48),
        ("Kind of Blue", "Miles Davis", 1959, "Jazz", "FLAC 24/192", true, 215),
        ("Tago Mago", "Can", 1971, "Krautrock", "", false, 95),
        ("Dots and Loops", "Stereolab", 1997, "Electronic", "", false, 270),
        ("Heaven or Las Vegas", "Cocteau Twins", 1990, "Dream pop", "", false, 310),
        ("Zombie", "Fela Kuti", 1976, "Afrobeat", "", false, 18),
        ("The Colour of Spring", "Talk Talk", 1986, "Art pop", "", false, 62),
        ("The Party's Over", "Talk Talk", 1982, "Synth-pop", "", false, 240),
        ("It's My Life", "Talk Talk", 1984, "Synth-pop", "FLAC 16/44", true, 180),
    ].enumerated().map { i, a in
        AlbumItem(id: i, title: a.0, artist: a.1, year: a.2, genre: a.3, format: a.4, owned: a.5, hue: Double(a.6))
    }

    public static let tracks: [TrackItem] = [
        ("Myrrhman", "6:52", "FLAC 16/44", true, false),
        ("Ascension Day", "5:44", "FLAC 16/44", true, false),
        ("After the Flood", "9:41", "FLAC 16/44", true, true),
        ("Taphead", "4:47", "", false, false),
        ("New Grass", "8:46", "FLAC 16/44", true, false),
        ("Runeii", "4:49", "FLAC 16/44", true, false),
    ].enumerated().map { i, t in
        TrackItem(id: i, title: t.0, duration: t.1, format: t.2, owned: t.3, playing: t.4)
    }

    /// Library table sample, from the mockup (`lib_rows`).
    public static let songs: [SongRow] = [
        (2, "Roygbiv", "Boards of Canada", 1998, "Pop", "FLAC 16/44", "1.0 Mb", 41, "Today", "Oct 12"),
        (0, "After the Flood", "Talk Talk", 1991, "Post-rock", "FLAC 16/44", "0.9 Mb", 88, "Today", "Aug 3"),
        (3, "Glory Box", "Portishead", 1994, "Trip hop", "FLAC 16/44", "0.9 Mb", 63, "Yesterday", "Aug 3"),
        (4, "Cloudbusting", "Kate Bush", 1985, "Art pop", "FLAC 24/96", "2.4 Mb", 57, "Oct 30", "Sep 18"),
        (6, "So What", "Miles Davis", 1959, "Jazz", "FLAC 24/192", "4.1 Mb", 102, "Oct 28", "Jun 2"),
        (5, "Maria También", "Khruangbin", 2018, "Soul", "MP3 320", "320 kb", 35, "Oct 27", "Jul 21"),
        (1, "I Believe in You", "Talk Talk", 1988, "Art rock", "FLAC 16/44", "0.9 Mb", 29, "Oct 25", "Aug 3"),
        (13, "Such a Shame", "Talk Talk", 1984, "Synth-pop", "FLAC 16/44", "0.8 Mb", 44, "Oct 22", "Aug 3"),
        (3, "Roads", "Portishead", 1994, "Trip hop", "FLAC 16/44", "0.9 Mb", 21, "Oct 20", "Aug 3"),
        (2, "Aquarius", "Boards of Canada", 1998, "IDM", "FLAC 16/44", "0.9 Mb", 18, "Oct 14", "Oct 12"),
        (6, "Blue in Green", "Miles Davis", 1959, "Jazz", "FLAC 24/192", "4.0 Mb", 77, "Oct 9", "Jun 2"),
        (5, "Evan Finds the Third Room", "Khruangbin", 2018, "Soul", "MP3 320", "320 kb", 24, "Oct 5", "Jul 21"),
    ].enumerated().map { i, r in
        var row = SongRow(id: i, album: r.0, title: r.1, artist: r.2, genre: r.4, format: r.5, bitrate: r.6, lastPlayed: r.8, added: r.9, year: r.3, plays: r.7)
        row.rating = [5, 4, 5, 3, 5, 0, 4, 2, 0, 3, 5, 0][i]
        row.hasMBID = ![5, 9].contains(i)
        return row
    }

    /// Up Next sample (title, album index into `albums`, time), from the mockup.
    public static let queue: [(title: String, album: Int, time: String)] = [
        ("After the Flood", 2, "3:12"), ("Glory Box", 3, "9:41"), ("Cloudbusting", 4, "5:44"), ("Maria También", 5, "6:52"),
        ("So What", 6, "4:47"), ("Such a Shame", 13, "8:46"), ("I Believe in You", 1, "4:49"), ("Myrrhman", 0, "3:12"),
    ]

    public static func albums(_ ids: [Int]) -> [AlbumItem] { ids.map { albums[$0] } }
}
