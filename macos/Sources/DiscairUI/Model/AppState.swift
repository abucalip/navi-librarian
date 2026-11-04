import DiscairAudio
import DiscairCore
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
    /// The 10-band equalizer (M5 slice 5; no mockup, each theme draws it).
    case equalizer
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
    public let lyrics = LyricsModel()
    /// Playback: the queue, the audio engine and the controls.
    public let player: PlayerModel
    private let systemMedia: AnyObject?
    /// Sample data until a session connects, then the owner's library.
    public let library = LibraryModel()
    public let artwork: ArtworkStore
    /// The optional on-disk copy of played songs and covers (off by default; Settings).
    public let cache: CacheModel
    /// The optional SMB mount of the music folder (Settings; off by default).
    public let share: ShareModel
    public var selectedArtist: ArtistItem = ArtistItem(id: 0, name: "Talk Talk", albumCount: 5)
    /// The letter shown in the Zine A-Z index.
    public var selectedLetter = "T"

    public init(themeID: ThemeID = .cupertino, screen: Screen = .home, actions: DiscairActions? = nil, session: SessionModel? = nil, output: AudioOutput? = nil) {
        // Previews and screenshot tests get their own throwaway settings, so they never read or write the real ones.
        let defaults = session == nil ? (UserDefaults(suiteName: "discair-preview-\(UUID().uuidString)") ?? .standard) : UserDefaults.standard
        let acquisition = AcquisitionModel(defaults: defaults)
        self.acquisition = acquisition
        self.session = session
        self.themeID = themeID
        self.screen = screen
        // Previews and tests keep their cache in a throwaway folder, so they never touch the real one.
        let media = MediaCache(root: session == nil ? FileManager.default.temporaryDirectory.appending(path: "discair-preview-media-\(UUID().uuidString)") : MediaCache.defaultRoot)
        self.cache = CacheModel(media: media, defaults: defaults)
        // Previews and tests never touch the Keychain or mount anything.
        self.share = session == nil ? ShareModel(defaults: defaults, secrets: InMemorySecretStore(), mounter: NoMounter()) : ShareModel(defaults: defaults)
        self.artwork = ArtworkStore(media: media)
        let player = PlayerModel(output: output ?? EngineOutput(), fetcher: CachingFetcher(cache: media), defaults: defaults)
        self.player = player
        self.systemMedia = session != nil ? SystemMedia(player) : nil   // media keys only in the running app
        if let actions { self.actions = actions }
        else if session != nil {
            let live = AcquisitionActions(acquisition)
            self.actions = live
            live.onPlay = { [weak self] album in self?.playAlbum(album) }
            live.onResume = { [weak self] in self?.player.togglePlayPause() }
        } else { self.actions = NoopActions() }
        session?.onConnected = { [weak self] in self?.share.startIfNeeded(); await self?.refreshLibrary() }
        session?.onNavidromeSignOut = { [weak self] in self?.lyrics.clearAll(); self?.library.clearSavedPages(); self?.cache.media.clear() }
        session?.onConnectFailed = { [weak self] e in
            guard let self, session != nil, !self.library.isLive else { return }
            self.configureSavedPages()
            self.library.showSavedCopy(reason: e.summary)
        }
    }

    // MARK: Library

    /// Points artwork at the active profile and loads the home data.
    public func refreshLibrary() async {
        guard let session, let navidrome = session.navidrome else { return }
        configureSavedPages()
        artwork.configure(navidrome.urls)
        acquisition.configure(librarian: session.librarian)
        discovery.configure(librarian: session.librarian)
        player.configure(urls: navidrome.urls, scrobbler: navidrome)
        lyrics.configure(navidrome: navidrome, scope: "\(session.activeProfile?.navidromeURL.absoluteString ?? "")|\(session.navidromeUsername ?? "")")
        await library.load(navidrome: navidrome, librarian: session.librarian)
        await library.loadSongs(navidrome: navidrome)
        share.noteServerPaths(library.songServerPaths)
        if library.isLive { selectedArtist = library.artists.first ?? selectedArtist; selectedLetter = selectedArtist.letter }
        if library.isLive, let first = library.recent.first ?? library.albums.first { selectedAlbum = first }
    }

    /// Saved pages are kept per Navidrome user. (They are not tied to the server address, so the LAN and Tailscale
    /// profiles of one library share them.)
    private func configureSavedPages() {
        let scope = session?.navidromeUsername.map { "navidrome|\($0)" }
        library.configureCache(scope: scope)
        cache.media.setScope(scope)
    }

    /// One line for the offline banner, or nil when the screens show fresh data.
    public var offlineNotice: String? {
        guard let date = library.savedCopyDate else { return nil }
        let when = date.formatted(.relative(presentation: .named, unitsStyle: .wide))
        let why = library.savedCopyReason.map { $0 + " " } ?? ""
        return "Offline. \(why)Showing your library as saved \(when). Get, Save and Not for me need the server."
    }

    /// The banner's Retry: connect again, or read the library again when the connection itself is fine.
    public func retryConnection() async {
        guard let session else { return }
        if session.isGood { await refreshLibrary() } else { await session.connect() }
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

/// A mounter that does nothing: previews and screenshot tests.
struct NoMounter: ShareMounter {
    func mount(_ address: URL, credential: Credential?) async -> ShareMountOutcome { .failed(.unreachable) }
}
