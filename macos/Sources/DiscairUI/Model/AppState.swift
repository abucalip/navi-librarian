import DiscairAudio
import DiscairNavidrome
import Observation
import SwiftUI

/// The six screens every theme must provide (contract section 9, M3 mockups).
public enum Screen: String, CaseIterable, Sendable {
    case home, album, nowPlaying, queue, library, artist
    /// Profiles, logins and the connection (M5; no mockup exists, each theme draws it in its own language).
    case settings
    /// The Albums grid on its own (the queue screen shows the same grid under the Up Next inspector).
    case albums
    /// The job list: progress, retry, next source, dismiss (M5 slice 2b; no mockup, each theme draws it).
    case downloads
    /// Discover lists: For you, Classics, New releases, Saved (M5 slice 3a; no mockup).
    case discover
}

/// What a theme may ask the app to do. Themes call these; they never reach the network or the audio engine.
/// Get, Save and Not for me always exist as actions so every theme can show them with text labels.
@MainActor
public protocol DiscairActions: AnyObject {
    func play(album: AlbumItem)
    func get(album: AlbumItem)
    func getSong(album: AlbumItem, title: String, trackNumber: Int?)
    func save(album: AlbumItem)
    func notForMe(album: AlbumItem)
    func resume()
}

/// Do-nothing actions used by previews, screenshot tests and until the real engine lands (M5).
@MainActor
public final class NoopActions: DiscairActions {
    public init() {}
    public func play(album: AlbumItem) {}
    public func get(album: AlbumItem) {}
    public func getSong(album: AlbumItem, title: String, trackNumber: Int?) {}
    public func save(album: AlbumItem) {}
    public func notForMe(album: AlbumItem) {}
    public func resume() {}
}

/// Everything a theme reads. Themes own layout; this owns state.
@MainActor
@Observable
public final class AppState {
    public var themeID: ThemeID
    public var screen: Screen
    public var selectedAlbum: AlbumItem = Fixtures.albums[0]
    /// The live connection and logins. `nil` in previews and screenshot tests, which show the sample label.
    public let session: SessionModel?
    public var connectionLabel: String { session?.label ?? "Home network · http (local)" }
    public var connectionIsGood: Bool { session?.isGood ?? true }
    public let actions: DiscairActions
    /// Get, Save, Not for me and the job list. Live only once a session connects.
    public let acquisition: AcquisitionModel
    public let discovery = DiscoveryModel()
    /// Playback: the queue, the audio engine and the controls.
    public let player: PlayerModel
    /// Sample data until a session connects, then the owner's library.
    public let library = LibraryModel()
    public let artwork = ArtworkStore()
    public var selectedArtist: ArtistItem = ArtistItem(id: 0, name: "Talk Talk", albumCount: 5)
    /// The letter shown in the Zine A-Z index.
    public var selectedLetter = "T"

    public init(themeID: ThemeID = .cupertino, screen: Screen = .home, actions: DiscairActions? = nil, session: SessionModel? = nil, output: AudioOutput? = nil) {
        let acquisition = AcquisitionModel()
        self.acquisition = acquisition
        self.session = session
        self.themeID = themeID
        self.screen = screen
        self.player = PlayerModel(output: output ?? EngineOutput())
        if let actions { self.actions = actions }
        else if session != nil {
            let live = AcquisitionActions(acquisition)
            self.actions = live
            live.onPlay = { [weak self] album in self?.playAlbum(album) }
            live.onResume = { [weak self] in self?.player.togglePlayPause() }
        } else { self.actions = NoopActions() }
        session?.onConnected = { [weak self] in await self?.refreshLibrary() }
    }

    // MARK: Library

    /// Points artwork at the active profile and loads the home data.
    public func refreshLibrary() async {
        guard let session, let navidrome = session.navidrome else { return }
        artwork.configure(navidrome.urls)
        acquisition.configure(librarian: session.librarian)
        discovery.configure(librarian: session.librarian)
        player.configure(urls: navidrome.urls)
        await library.load(navidrome: navidrome, librarian: session.librarian)
        await library.loadSongs(navidrome: navidrome)
        if library.isLive { selectedArtist = library.artists.first ?? selectedArtist; selectedLetter = selectedArtist.letter }
        if library.isLive, let first = library.recent.first ?? library.albums.first { selectedAlbum = first }
    }

    public func loadSongs(more: Bool = false) async {
        await library.loadSongs(navidrome: session?.navidrome, more: more)
    }

    // MARK: Playback

    /// Plays an owned album from its first song. A recommendation the library does not hold cannot be played.
    public func playAlbum(_ album: AlbumItem) {
        guard let id = album.remoteID, album.owned, let navidrome = session?.navidrome else { return }
        Task {
            guard let detail = try? await navidrome.album(id: id), !detail.songs.isEmpty else { return }
            player.play(detail.songs.map(PlayerModel.item), startAt: 0)
        }
    }

    /// Plays the Songs table from a row; the queue is the table in the order shown.
    public func play(rows: [SongRow], startAt index: Int) {
        let items = rows.compactMap(PlayerModel.item)
        guard !items.isEmpty else { return }
        let id = rows.indices.contains(index) ? rows[index].remoteID : nil
        player.play(items, startAt: items.firstIndex { $0.songID == id } ?? 0)
    }

    public func loadSelectedAlbum() async {
        await library.loadTracks(for: selectedAlbum, navidrome: session?.navidrome)
    }

    public func loadSelectedArtist() async {
        await library.loadArtist(selectedArtist, navidrome: session?.navidrome)
    }

    /// Library lists without the albums the owner dismissed.
    public func visible(_ albums: [AlbumItem]) -> [AlbumItem] { albums.filter { !acquisition.isHidden($0) } }

    public func open(album: AlbumItem) { selectedAlbum = album; screen = .album }

    public func open(artist: ArtistItem) { selectedArtist = artist; selectedLetter = artist.letter; screen = .artist }

    /// Opens an artist by name when the library has them; otherwise nothing happens.
    public func openArtist(named name: String) {
        if let a = library.artist(named: name) { open(artist: a) }
        else if !library.isLive { screen = .artist }
    }
}
