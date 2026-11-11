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

    /// The Gap radar: artists with albums missing from the library (sample data until live).
    public private(set) var gapRadar: [GapArtist] = LibraryModel.sampleGap
    public private(set) var gapLoading = false
    static var sampleGap: [GapArtist] {
        let sample = Fixtures.albums([12, 13, 11, 1, 0])
        return GapRadar.build(owned: sample.filter(\.owned), missing: sample.filter { !$0.owned })
    }
    /// Most artists the radar reads from Navidrome (one request each).
    static let gapArtistLimit = 12

    /// Why the Missing shelf is empty, when it is: no Librarian login, a failed read, or nothing to recommend.
    public private(set) var picksNote: String?

    private var allPicks: [AlbumItem] = []

    /// Set while the screens show a saved copy because the server could not be reached: when the copy was saved and why
    /// the server was not used. Cleared by the next good read.
    public private(set) var savedCopyDate: Date?
    public private(set) var savedCopyReason: String?
    @ObservationIgnored private var cache: PageCache?

    /// Home data as saved: what `apply` needs.
    struct HomeSnapshot: Codable {
        var newest: [NavidromeAlbum]; var first: [NavidromeAlbum]; var artists: [NavidromeArtist]
        var picks: [DashboardPick]; var picksNote: String?
    }

    /// The Songs table: sample rows until live, then pages of the whole library read from Navidrome.
    public private(set) var songs: [SongRow] = Fixtures.songs
    public private(set) var songsLoading = false
    public private(set) var songsHaveMore = false
    public private(set) var songsError: String?
    private var songsLoaded = false
    /// Server-side paths of the first Songs page (for the SMB path check only; never shown).
    public private(set) var songServerPaths: [String] = []
    static let songPage = 200

    public init() {}

    /// Points the saved pages at one server and user (nil: none are kept or read).
    func configureCache(scope: String?, root: URL = PageCache.defaultRoot, now: @escaping () -> Date = { .now }) {
        cache = scope.map { PageCache(root: root, scope: $0, now: now) }
    }

    /// Sign-out: delete every saved page.
    func clearSavedPages() { cache?.clear(); cache = nil; savedCopyDate = nil; savedCopyReason = nil }

    /// Shows the saved Home data when there is some. Used when the connection failed before any read was tried.
    @discardableResult
    func showSavedCopy(reason: String) -> Bool {
        guard let hit = cache?.get("home", as: HomeSnapshot.self) else { return false }
        apply(hit.value)
        markSaved(hit.savedAt, reason: reason)
        return true
    }

    private func markSaved(_ date: Date, reason: String) {
        if savedCopyDate == nil || date < savedCopyDate! { savedCopyDate = date }
        savedCopyReason = reason
    }

    private func apply(_ h: HomeSnapshot) {
        apply(newest: h.newest, first: h.first, artists: h.artists, picks: h.picks, picksNote: h.picksNote)
    }

    /// Test hook: shows these songs on the album page without a server.
    func showTracks(_ songs: [TrackItem]) { tracks = songs }

    static let sampleArtists: [ArtistItem] = ZineFixtures.artistIndex.enumerated().map {
        ArtistItem(id: $0.offset, name: $0.element.0, albumCount: $0.element.1)
    }

    // MARK: Loading

    /// Every album in the library (the home page holds only the first 120 by name and the newest 24, so a search over those
    /// missed most of the library). Empty until it has been read.
    public private(set) var allAlbums: [AlbumItem] = []
    /// The same list as Navidrome sent it (dates and play counts included), read once and shared with the Home figures.
    public private(set) var allNavidromeAlbums: [NavidromeAlbum] = []
    /// What a search or the Albums tab covers: the whole library once read, else what the home page holds.
    public var searchableAlbums: [AlbumItem] { allAlbums.isEmpty ? albums + recent : allAlbums }

    public func loadAllAlbums(navidrome: NavidromeClient?) async {
        guard isLive, let navidrome, let list = try? await navidrome.allAlbums() else { return }
        allNavidromeAlbums = list
        allAlbums = list.enumerated().map { Self.item($0.element, index: 1000 + $0.offset) }
    }

    /// Reads the home data. Picks are optional: without a Librarian login the library still shows.
    public func load(navidrome: NavidromeClient, librarian: LibrarianClient?) async {
        phase = .loading
        do {
            async let newest = navidrome.albumList(.newest, size: 24)
            async let first = navidrome.albumList(.alphabeticalByName, size: 120)
            async let artistList = navidrome.artists()
            let (n, f, a) = try await (newest, first, artistList)
            var picks: [DashboardPick] = []
            var note: String?
            if let librarian {
                do { picks = try await librarian.dashboardPicks(count: 12) }
                catch let e as DiscairError { note = "Recommendations are unavailable: " + e.summary }
                catch { note = "Recommendations are unavailable." }
            } else {
                note = "Add your Librarian login in Settings to see recommendations."
            }
            let snap = HomeSnapshot(newest: n, first: f, artists: a, picks: picks, picksNote: note)
            apply(snap)
            savedCopyDate = nil; savedCopyReason = nil
            cache?.put("home", snap)
        } catch let e as DiscairError {
            fallBack(e)
        } catch {
            fallBack(ErrorMapping.map(error))
        }
    }

    /// A failed read keeps the owner's library on screen from the saved copy when there is one. A refused login is not
    /// "offline", so it still fails (the Settings screen says what to do).
    func fallBackForTest(_ e: DiscairError) { fallBack(e) }

    private func fallBack(_ e: DiscairError) {
        if case .unauthorised = e { fail(e.summary); return }
        if !showSavedCopy(reason: e.summary) { fail(e.summary) }
    }

    private func fail(_ message: String) {
        recent = []; missing = []; albums = []; allAlbums = []; allNavidromeAlbums = []; artists = []; allPicks = []; picksNote = nil; gapRadar = []
        songs = []; songsLoaded = false; songsHaveMore = false; songsError = nil
        phase = .failed(message)
    }

    func apply(newest: [NavidromeAlbum], first: [NavidromeAlbum], artists a: [NavidromeArtist], picks: [DashboardPick], picksNote: String? = nil) {
        songs = []; songsLoaded = false; songsHaveMore = false; songsError = nil   // never show sample songs next to a live library
        recent = newest.enumerated().map { Self.item($0.element, index: $0.offset) }
        albums = first.enumerated().map { Self.item($0.element, index: 1000 + $0.offset) }
        artists = a.enumerated().map { ArtistItem(id: $0.offset, remoteID: $0.element.id, name: $0.element.name, albumCount: $0.element.albumCount ?? 0) }
        let owned = Set((newest + first).map { Self.key($0.artist ?? "", $0.name) })
        allPicks = picks.enumerated().map { Self.item($0.element, index: 5000 + $0.offset) }
            .filter { !owned.contains(Self.key($0.artist, $0.title)) }
        missing = allPicks
        self.picksNote = !missing.isEmpty ? nil : (picksNote ?? "The Librarian has no recommendations for you right now.")
        totalAlbumsText = "Library \(a.reduce(0) { $0 + ($1.albumCount ?? 0) }.formatted()) albums"
        phase = .loaded
    }

    /// Songs for an album. A live album reads Navidrome; a pick shows the Librarian's suggested tracks as not owned.
    public func loadTracks(for album: AlbumItem, navidrome: NavidromeClient?, librarian: LibrarianClient? = nil, related: RelatedModel? = nil) async {
        guard isLive else { tracks = Fixtures.tracks; return }
        if let id = album.remoteID, let navidrome {
            tracksLoading = true
            defer { tracksLoading = false }
            if let detail = try? await navidrome.album(id: id) {
                tracks = Self.tracks(detail.songs); cache?.put("album-\(id)", detail.songs); return
            }
            if let hit = cache?.get("album-\(id)", as: [NavidromeSong].self) {
                tracks = Self.tracks(hit.value); markSaved(hit.savedAt, reason: "The server did not answer."); return
            }
            tracks = []
        } else {
            tracks = album.suggestedTracks.enumerated().map {
                TrackItem(id: $0.offset, title: $0.element, duration: "", format: "", owned: false, playing: false)
            }
            // A pick (or a similar album) with no suggested songs: the server lists the album's songs from public sources.
            if tracks.isEmpty, let librarian {
                let listed: [RelatedTrack]
                if let related, !related.tracks.isEmpty { listed = related.tracks }
                else { listed = (try? await librarian.albumPage(artist: album.artist, album: album.title))?.tracks ?? [] }
                tracks = listed.enumerated().map {
                    TrackItem(id: $0.offset, title: $0.element.title, duration: Self.clock($0.element.durationSeconds), format: "", owned: false, playing: false)
                }
            }
        }
    }

    /// Albums for an artist: the ones in the library, then picks by the same artist (dashed, with Get).
    public func loadArtist(_ artist: ArtistItem, navidrome: NavidromeClient?) async {
        guard isLive else {
            artistAlbums = Fixtures.albums([12, 13, 11, 1, 0]); artistOwnedCount = 3; artistMissingCount = 2; return
        }
        var owned: [AlbumItem] = []
        if let id = artist.remoteID, let navidrome {
            var albums: [NavidromeAlbum]?
            if let detail = try? await navidrome.artist(id: id) { albums = detail.albums; cache?.put("artist-\(id)", detail.albums) }
            else if let hit = cache?.get("artist-\(id)", as: [NavidromeAlbum].self) {
                albums = hit.value; markSaved(hit.savedAt, reason: "The server did not answer.")
            }
            owned = (albums ?? []).enumerated().map { Self.item($0.element, index: 2000 + $0.offset) }
                .sorted { $0.year < $1.year }
        }
        let missingByArtist = allPicks.filter { $0.artist.caseInsensitiveCompare(artist.name) == .orderedSame }
        artistAlbums = owned + missingByArtist
        artistOwnedCount = owned.count
        artistMissingCount = missingByArtist.count
    }

    /// Reads the Gap radar: for each artist the Librarian has picks of that the library also holds, the artist's
    /// albums from Navidrome (or the saved copy). Safe to call from `.task`.
    public func loadGapRadar(navidrome: NavidromeClient?) async {
        guard isLive, !gapLoading else { return }
        gapLoading = true
        defer { gapLoading = false }
        var owned = albums + recent
        let names = allPicks.reduce(into: [String]()) { acc, p in
            if !acc.contains(where: { $0.caseInsensitiveCompare(p.artist) == .orderedSame }) { acc.append(p.artist) }
        }
        for name in names.prefix(Self.gapArtistLimit) {
            guard let id = artist(named: name)?.remoteID, let navidrome else { continue }
            var list: [NavidromeAlbum]?
            if let detail = try? await navidrome.artist(id: id) { list = detail.albums; cache?.put("artist-\(id)", detail.albums) }
            else if let hit = cache?.get("artist-\(id)", as: [NavidromeAlbum].self) { list = hit.value }
            owned += (list ?? []).enumerated().map { Self.item($0.element, index: 3000 + $0.offset) }
        }
        gapRadar = GapRadar.build(owned: owned, missing: allPicks)
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

    /// Reads the first page of songs, or the next one. Safe to call from `.task`; a loaded first page is not re-read.
    public func loadSongs(navidrome: NavidromeClient?, more: Bool = false) async {
        guard isLive, let navidrome, !songsLoading else { return }
        if !more && songsLoaded { return }
        songsLoading = true; songsError = nil
        defer { songsLoading = false }
        do {
            let offset = more ? songs.count : 0
            let page = try await navidrome.songs(offset: offset, count: Self.songPage)
            let rows = page.enumerated().map { Self.row($0.element, id: offset + $0.offset) }
            songs = more ? songs + rows : rows
            songsHaveMore = page.count == Self.songPage
            songsLoaded = true
            if !more { songServerPaths = page.compactMap(\.path); cache?.put("songs-first", page) }
        } catch {
            let e = (error as? DiscairError) ?? ErrorMapping.map(error)
            if !more, let hit = cache?.get("songs-first", as: [NavidromeSong].self) {
                songs = hit.value.enumerated().map { Self.row($0.element, id: $0.offset) }
                songsHaveMore = false; songsLoaded = false      // the next visit tries the server again
                markSaved(hit.savedAt, reason: e.summary)
            } else { songsError = (error as? DiscairError).map(AcquisitionModel.text) ?? e.summary }
        }
    }

    /// Reads the whole library: the first page as before (so the saved copy and the offline fallback still work), then
    /// 500-song pages, four requests at a time, appended in order as each group arrives. Stops at the first short page.
    /// An error keeps what is loaded and leaves `songsHaveMore` true, so "Load more songs" / "Try again" continue it.
    public func loadAllSongs(navidrome: NavidromeClient?) async {
        guard isLive, let navidrome else { return }
        if !songsLoaded { await loadSongs(navidrome: navidrome) }
        guard songsLoaded, songsHaveMore, !songsLoading else { return }
        songsLoading = true; songsError = nil
        defer { songsLoading = false }
        let size = Self.bulkPage, width = Self.bulkWidth
        do {
            while songsHaveMore {
                let start = songs.count
                let pages = try await withThrowingTaskGroup(of: (Int, [NavidromeSong]).self) { group in
                    for i in 0..<width { group.addTask { (i, try await navidrome.songs(offset: start + i * size, count: size)) } }
                    var out: [Int: [NavidromeSong]] = [:]
                    for try await (i, page) in group { out[i] = page }
                    return out
                }
                var added: [SongRow] = []
                var ended = false
                for i in 0..<width {
                    let page = pages[i] ?? []
                    added += page.enumerated().map { Self.row($0.element, id: start + i * size + $0.offset) }
                    songServerPaths += page.compactMap(\.path)
                    if page.count < size { ended = true; break }
                }
                songs += added
                if ended || added.isEmpty { songsHaveMore = false }
            }
        } catch {
            let e = (error as? DiscairError) ?? ErrorMapping.map(error)
            songsError = (error as? DiscairError).map(AcquisitionModel.text) ?? e.summary
        }
    }
    static let bulkPage = 500
    static let bulkWidth = 4

    /// Test hook: shows these song rows without a server.
    func showSongs(_ rows: [SongRow], more: Bool = false) { songs = rows; songsHaveMore = more; songsLoaded = true }

    static func row(_ s: NavidromeSong, id: Int) -> SongRow {
        let album = AlbumItem(id: id, title: s.album ?? "", artist: s.artist ?? "Unknown artist", year: s.year ?? 0, genre: s.genre ?? "",
                              format: "", owned: true, hue: hue(for: s.album ?? s.title), remoteID: s.albumId, coverArt: s.coverArt ?? "")
        return SongRow(id: id, album: 0, title: s.title, artist: s.artist ?? "Unknown artist", genre: s.genre ?? "",
                       format: rowFormat(s), bitrate: s.bitRate.map { "\($0) kb" } ?? "", lastPlayed: shortDate(s.played),
                       added: shortDate(s.created), year: s.year ?? 0, plays: s.playCount ?? 0, remoteID: s.id, cover: album,
                       suffix: s.suffix, seconds: Double(s.duration ?? 0), track: s.track, disc: s.discNumber, path: s.path,
                       rating: min(max(s.userRating ?? 0, 0), 5), bitrateKbps: s.bitRate ?? 0,
                       addedAt: date(s.created), playedAt: date(s.played), hasMBID: !(s.musicBrainzId ?? "").isEmpty)
    }

    /// An ISO time as a date; nil when absent or Navidrome's "never" (year 0001).
    static func date(_ iso: String?) -> Date? {
        guard let iso, !iso.hasPrefix("0001") else { return nil }
        return isoDate(iso)
    }

    /// One formatter pair for every row: making them per row cost seconds on a 12,000-song library.
    private static let isoFractional: ISO8601DateFormatter = { let f = ISO8601DateFormatter(); f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]; return f }()
    private static let isoPlain = ISO8601DateFormatter()
    static func isoDate(_ iso: String) -> Date? { isoFractional.date(from: iso) ?? isoPlain.date(from: iso) }

    /// "FLAC 16/44" when the bit depth and sample rate are known, else the short form ("MP3 320").
    static func rowFormat(_ s: NavidromeSong) -> String {
        let base = quality(s)
        guard let depth = s.bitDepth, depth > 0, let rate = s.samplingRate, rate > 0 else { return base }
        return "\((s.suffix ?? "").uppercased()) \(depth)/\(rate / 1000)"   // 44100 reads 44, as in the mockup
    }

    /// "Today", "Yesterday", else "Oct 30" (with the year when it is not this year); empty when unknown.
    static func shortDate(_ iso: String?, now: Date = .now) -> String {
        guard let iso, !iso.hasPrefix("0001") else { return "" }
        guard let d = isoDate(iso) else { return "" }
        let cal = Calendar.current
        if cal.isDate(d, inSameDayAs: now) { return "Today" }
        if let y = cal.date(byAdding: .day, value: -1, to: now), cal.isDate(d, inSameDayAs: y) { return "Yesterday" }
        return cal.isDate(d, equalTo: now, toGranularity: .year) ? d.formatted(.dateTime.month(.abbreviated).day()) : d.formatted(.dateTime.month(.abbreviated).year())
    }

    static func tracks(_ songs: [NavidromeSong]) -> [TrackItem] {
        songs.enumerated().map { i, s in
            TrackItem(id: i, title: s.title, duration: clock(s.duration), format: quality(s), owned: true, playing: false, songID: s.id)
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
