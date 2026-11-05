import DiscairCore
import DiscairLibrarian
import Foundation
import Observation

/// What the Librarian knows about the album or artist on screen: similar artists (marked owned or not) and similar
/// albums the library lacks. Loaded beside the Navidrome data; a failure leaves the section out, never a guess.
@MainActor
@Observable
public final class RelatedModel {
    public private(set) var artists: [SimilarArtistEntry] = []
    public private(set) var albums: [AlbumItem] = []
    public private(set) var loading = false
    /// Artist page: the biography and the most listened songs.
    public private(set) var bio: String?
    public private(set) var bioSource: String?
    public private(set) var topSongs: [TopSongEntry] = []
    /// Tracks the server lists for an album the library lacks (used when the pick came with none).
    public private(set) var tracks: [RelatedTrack] = []
    @ObservationIgnored private var loadedFor: String?

    public init() {}

    public var ownedArtists: [SimilarArtistEntry] { artists.filter(\.owned) }
    public var otherArtists: [SimilarArtistEntry] { artists.filter { !$0.owned } }

    /// Pauses between asks. The server ends a slow page at its deadline and keeps what finished in its cache, so asking
    /// again a little later fills what was missing. Tests shorten it.
    @ObservationIgnored var retryPause: Duration = .seconds(2)
    static let attempts = 4
    /// Set while a page is still partial after every ask.
    public private(set) var incomplete = false
    /// Albums of an artist the library does not hold (unowned artist page).
    public private(set) var artistAlbums: [AlbumItem] = []

    public func loadAlbum(_ album: AlbumItem, librarian: LibrarianClient?) async {
        let key = "album|\(album.artist.lowercased())|\(album.title.lowercased())"
        guard let librarian else { clear(); return }
        if loadedFor == key, !incomplete { return }
        if loadedFor != key { clear() }
        loadedFor = key; loading = true; incomplete = false
        defer { loading = false; if Task.isCancelled { loadedFor = nil } }
        for attempt in 1...Self.attempts {
            guard let page = await ask({ try await librarian.albumPage(artist: album.artist, album: album.title) }) else {
                if attempt == Self.attempts { incomplete = true }
                else { try? await Task.sleep(for: retryPause) }
                if Task.isCancelled { return }
                continue
            }
            guard !Task.isCancelled, loadedFor == key else { return }
            if !page.similarArtists.isEmpty { artists = Self.cleaned(page.similarArtists) }
            if !page.similarAlbums.isEmpty {
                albums = page.similarAlbums.enumerated().map { i, a in
                    AlbumItem(id: 7000 + i, title: a.name, artist: a.artist, year: a.year ?? 0, genre: "", format: "", owned: false, hue: LibraryModel.hue(for: a.name))
                }
            }
            if !page.tracks.isEmpty { tracks = page.tracks }
            if !page.partial { incomplete = false; return }
            incomplete = true
            if attempt < Self.attempts { try? await Task.sleep(for: retryPause); if Task.isCancelled { return } }
        }
    }

    public func loadArtist(name: String, remoteID: String?, librarian: LibrarianClient?) async {
        let key = "artist|\(name.lowercased())"
        guard let librarian else { clear(); return }
        if loadedFor == key, !incomplete { return }
        if loadedFor != key { clear() }
        loadedFor = key; loading = true; incomplete = false
        defer { loading = false; if Task.isCancelled { loadedFor = nil } }
        for attempt in 1...Self.attempts {
            guard let page = await ask({ try await librarian.artistPage(name: name, id: remoteID) }) else {
                if attempt == Self.attempts { incomplete = true }
                else { try? await Task.sleep(for: retryPause) }
                if Task.isCancelled { return }
                continue
            }
            guard !Task.isCancelled, loadedFor == key else { return }
            // Keep what an earlier ask already brought; a later ask only adds.
            if !page.similar.isEmpty { artists = Self.cleaned(page.similar) }
            if let b = page.bio { bio = b; bioSource = page.bioSource }
            if !page.topSongs.isEmpty { topSongs = page.topSongs }
            // Albums the server does not mark as held: the whole list for an unowned artist, the missing ones for a partly owned one.
            let notHeld = page.albums.filter { !$0.owned }
            if !page.albums.isEmpty {
                artistAlbums = notHeld.enumerated().map { i, a in
                    AlbumItem(id: 7500 + i, title: a.name, artist: name, year: a.year ?? 0, genre: "", format: "", owned: false, hue: LibraryModel.hue(for: a.name))
                }
            }
            if !page.partial { incomplete = false; return }
            incomplete = true
            if attempt < Self.attempts { try? await Task.sleep(for: retryPause); if Task.isCancelled { return } }
        }
    }

    /// What the Librarian said when the last ask failed (shown under the page so a missing section is explained).
    public private(set) var lastError: String?

    private func ask<T>(_ call: () async throws -> T) async -> T? {
        do { let v = try await call(); lastError = nil; return v }
        catch { lastError = ((error as? DiscairError)?.summary) ?? "The Librarian did not answer."; return nil }
    }

    public func clear() { artists = []; albums = []; tracks = []; bio = nil; bioSource = nil; topSongs = []; artistAlbums = []; incomplete = false; loadedFor = nil }

    /// Entries with a name, once each.
    static func cleaned(_ list: [SimilarArtistEntry]) -> [SimilarArtistEntry] {
        var seen = Set<String>()
        return list.filter { !$0.name.isEmpty && seen.insert($0.name.lowercased()).inserted }
    }
}
