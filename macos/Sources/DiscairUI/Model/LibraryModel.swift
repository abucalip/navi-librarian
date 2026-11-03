import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import Foundation
import Observation

/// What the screens show. Without a session it holds the mockup's sample data (previews, screenshot tests); after
/// a connect it holds the owner's real library (contract M5). Themes only read this; the clients stay behind it.
@MainActor
@Observable
public final class LibraryModel {
    public enum Phase: Equatable { case sample, loading, loaded, failed(String) }

    public private(set) var phase: Phase = .sample
    public var isLive: Bool { phase != .sample }

    /// Newest albums (Home "Recently added").
    public private(set) var recent: [AlbumItem] = Fixtures.albums([2, 3, 4, 5, 6])
    /// Librarian picks the library does not hold (Home "Missing from your library"). The first is the lead story.
    public private(set) var missing: [AlbumItem] = Fixtures.albums([7, 8, 9, 10, 11])
    /// The first page of the library alphabetically (Albums grid).
    public private(set) var albums: [AlbumItem] = Fixtures.albums([0, 1, 2, 3, 4, 5, 6, 13, 12, 11])
    public private(set) var artists: [ArtistItem] = LibraryModel.sampleArtists
    public private(set) var totalAlbumsText = "Library 4,812 albums"

    /// Songs of the album last opened.
    public private(set) var tracks: [TrackItem] = Fixtures.tracks
    public private(set) var tracksLoading = false
    /// Albums of the artist last opened: owned ones from Navidrome, then picks by that artist.
    public private(set) var artistAlbums: [AlbumItem] = Fixtures.albums([12, 13, 11, 1, 0])
    public private(set) var artistOwnedCount = 3
    public private(set) var artistMissingCount = 2

    private var allPicks: [AlbumItem] = []

    public init() {}

    static let sampleArtists: [ArtistItem] = ZineFixtures.artistIndex.enumerated().map {
        ArtistItem(id: $0.offset, name: $0.element.0, albumCount: $0.element.1)
    }

    // MARK: Loading

    /// Reads the home data. Picks are optional: without a Librarian login the library still shows.
    public func load(navidrome: NavidromeClient, librarian: LibrarianClient?) async {
        phase = .loading
        do {
            async let newest = navidrome.albumList(.newest, size: 24)
            async let first = navidrome.albumList(.alphabeticalByName, size: 120)
            async let artistList = navidrome.artists()
            let (n, f, a) = try await (newest, first, artistList)
            var picks: [DashboardPick] = []
            if let librarian { picks = (try? await librarian.dashboardPicks(count: 12)) ?? [] }
            apply(newest: n, first: f, artists: a, picks: picks)
        } catch let e as DiscairError {
            fail(e.summary)
        } catch {
            fail(ErrorMapping.map(error).summary)
        }
    }

    private func fail(_ message: String) {
        recent = []; missing = []; albums = []; artists = []; allPicks = []
        phase = .failed(message)
    }

    func apply(newest: [NavidromeAlbum], first: [NavidromeAlbum], artists a: [NavidromeArtist], picks: [DashboardPick]) {
        recent = newest.enumerated().map { Self.item($0.element, index: $0.offset) }
        albums = first.enumerated().map { Self.item($0.element, index: 1000 + $0.offset) }
        artists = a.enumerated().map { ArtistItem(id: $0.offset, remoteID: $0.element.id, name: $0.element.name, albumCount: $0.element.albumCount ?? 0) }
        let owned = Set((newest + first).map { Self.key($0.artist ?? "", $0.name) })
        allPicks = picks.enumerated().map { Self.item($0.element, index: 5000 + $0.offset) }
            .filter { !owned.contains(Self.key($0.artist, $0.title)) }
        missing = allPicks
        totalAlbumsText = "Library \(a.reduce(0) { $0 + ($1.albumCount ?? 0) }.formatted()) albums"
        phase = .loaded
    }

    /// Songs for an album. A live album reads Navidrome; a pick shows the Librarian's suggested tracks as not owned.
    public func loadTracks(for album: AlbumItem, navidrome: NavidromeClient?) async {
        guard isLive else { tracks = Fixtures.tracks; return }
        if let id = album.remoteID, let navidrome {
            tracksLoading = true
            defer { tracksLoading = false }
            if let detail = try? await navidrome.album(id: id) { tracks = Self.tracks(detail.songs); return }
            tracks = []
        } else {
            tracks = album.suggestedTracks.enumerated().map {
                TrackItem(id: $0.offset, title: $0.element, duration: "", format: "", owned: false, playing: false)
            }
        }
    }

    /// Albums for an artist: the ones in the library, then picks by the same artist (dashed, with Get).
    public func loadArtist(_ artist: ArtistItem, navidrome: NavidromeClient?) async {
        guard isLive else {
            artistAlbums = Fixtures.albums([12, 13, 11, 1, 0]); artistOwnedCount = 3; artistMissingCount = 2; return
        }
        var owned: [AlbumItem] = []
        if let id = artist.remoteID, let navidrome, let detail = try? await navidrome.artist(id: id) {
            owned = detail.albums.enumerated().map { Self.item($0.element, index: 2000 + $0.offset) }
                .sorted { $0.year < $1.year }
        }
        let missingByArtist = allPicks.filter { $0.artist.caseInsensitiveCompare(artist.name) == .orderedSame }
        artistAlbums = owned + missingByArtist
        artistOwnedCount = owned.count
        artistMissingCount = missingByArtist.count
    }

    /// Other albums by the same artist among those already loaded.
    public func more(by album: AlbumItem) -> [AlbumItem] {
        guard isLive else { return Fixtures.albums([1, 13, 11]) }
        return (albums + recent).filter { $0.artist == album.artist && $0.id != album.id && $0.title != album.title }
            .reduce(into: [AlbumItem]()) { acc, a in if !acc.contains(where: { $0.title == a.title }) { acc.append(a) } }
            .prefix(4).map { $0 }
    }

    public func artist(named name: String) -> ArtistItem? {
        artists.first { $0.name.caseInsensitiveCompare(name) == .orderedSame }
    }

    // MARK: Mapping (pure, tested)

    static func key(_ artist: String, _ title: String) -> String { "\(artist.lowercased())|\(title.lowercased())" }

    /// A stable colour per title, so placeholder covers do not change between launches.
    static func hue(for text: String) -> Double {
        var h: UInt32 = 5381
        for b in text.lowercased().utf8 { h = (h &* 33) &+ UInt32(b) }
        return Double(h % 360)
    }

    static func item(_ a: NavidromeAlbum, index: Int) -> AlbumItem {
        AlbumItem(id: index, title: a.name, artist: a.artist ?? "Unknown artist", year: a.year ?? 0, genre: a.genre ?? "",
                  format: "", owned: true, hue: hue(for: a.name), remoteID: a.id, coverArt: a.coverArt,
                  artistRemoteID: a.artistId, songCount: a.songCount, durationSeconds: a.duration)
    }

    static func item(_ p: DashboardPick, index: Int) -> AlbumItem {
        AlbumItem(id: index, title: p.album, artist: p.artist, year: 0, genre: p.genres?.first ?? "", format: "", owned: false,
                  hue: hue(for: p.album), reason: p.reason, suggestedTracks: p.suggestedTracks ?? [])
    }

    static func tracks(_ songs: [NavidromeSong]) -> [TrackItem] {
        songs.enumerated().map { i, s in
            TrackItem(id: i, title: s.title, duration: clock(s.duration), format: quality(s), owned: true, playing: false)
        }
    }

    static func clock(_ seconds: Int?) -> String {
        guard let seconds, seconds >= 0 else { return "" }
        return "\(seconds / 60):" + String(format: "%02d", seconds % 60)
    }

    /// "FLAC" for lossless, "MP3 320" for lossy (the bit depth and sample rate are not in the Subsonic song).
    static func quality(_ s: NavidromeSong) -> String {
        let fmt = (s.suffix ?? "").uppercased()
        let lossless: Set<String> = ["FLAC", "ALAC", "WAV", "AIFF", "APE", "WV"]
        if fmt.isEmpty { return "" }
        if lossless.contains(fmt) { return fmt }
        return s.bitRate.map { "\(fmt) \($0)" } ?? fmt
    }
}
