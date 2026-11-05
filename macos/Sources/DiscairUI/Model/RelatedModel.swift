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
    /// Tracks the server lists for an album the library lacks (used when the pick came with none).
    public private(set) var tracks: [RelatedTrack] = []
    @ObservationIgnored private var loadedFor: String?

    public init() {}

    public var ownedArtists: [SimilarArtistEntry] { artists.filter(\.owned) }
    public var otherArtists: [SimilarArtistEntry] { artists.filter { !$0.owned } }

    public func loadAlbum(_ album: AlbumItem, librarian: LibrarianClient?) async {
        let key = "album|\(album.artist.lowercased())|\(album.title.lowercased())"
        guard let librarian else { clear(); return }
        if loadedFor == key { return }
        clear(); loading = true; loadedFor = key
        defer { loading = false }
        guard let page = try? await librarian.albumPage(artist: album.artist, album: album.title), !Task.isCancelled, loadedFor == key else { return }
        artists = Self.cleaned(page.similarArtists)
        albums = page.similarAlbums.enumerated().map { i, a in
            AlbumItem(id: 7000 + i, title: a.name, artist: a.artist, year: a.year ?? 0, genre: "", format: "", owned: false, hue: LibraryModel.hue(for: a.name))
        }
        tracks = page.tracks
    }

    public func loadArtist(name: String, remoteID: String?, librarian: LibrarianClient?) async {
        let key = "artist|\(name.lowercased())"
        guard let librarian else { clear(); return }
        if loadedFor == key { return }
        clear(); loading = true; loadedFor = key
        defer { loading = false }
        guard let list = try? await librarian.artistSimilar(name: name, id: remoteID), !Task.isCancelled, loadedFor == key else { return }
        artists = Self.cleaned(list)
    }

    public func clear() { artists = []; albums = []; tracks = []; loadedFor = nil }

    /// Entries with a name, once each.
    static func cleaned(_ list: [SimilarArtistEntry]) -> [SimilarArtistEntry] {
        var seen = Set<String>()
        return list.filter { !$0.name.isEmpty && seen.insert($0.name.lowercased()).inserted }
    }
}
