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
    /// Placeholder cover colour (0..360) until real cover art is wired in.
    public let hue: Double
}

public struct TrackItem: Identifiable, Equatable, Sendable {
    public let id: Int
    public let title: String
    public let duration: String
    public let format: String
    public let owned: Bool
    public let playing: Bool
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

    public static func albums(_ ids: [Int]) -> [AlbumItem] { ids.map { albums[$0] } }
}
