import DiscairAudio
import DiscairCore
import DiscairLibrarian
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
    /// Artists with albums missing from the library, on a year axis (M6 slice 7; contract section 6.4).
    case gapRadar
    /// Rule-built playlists, saved to Navidrome (M6 slice 8; contract section 6.7).
    case smartPlaylists
    /// Days and a heatmap of when songs were last played (M6 slice 9; contract section 6.6).
    case history
    /// The A-Z list of artists (the Artists tab). `.artist` is one artist's page.
    case artists
    /// Albums added to the library most recently (the Recently Added tab).
    case recent
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
    /// The ⌘K command palette.
    public let palette = PaletteModel()
    public let lyrics = LyricsModel()
    /// Playback: the queue, the audio engine and the controls.
    public let player: PlayerModel
    private let systemMedia: AnyObject?
    /// Sample data until a session connects, then the owner's library.
    public let library = LibraryModel()
    public let smart = SmartPlaylistModel()
    /// Saved queues and Radio from this (M6 slice 12).
    public let savedQueues: SavedQueueStore
    public let radio: RadioModel
    public let spread = AlbumSpreadModel()
    /// Similar artists and albums from the Librarian, for the album and artist pages.
    public let related = RelatedModel()
    public let artwork: ArtworkStore
    /// The optional on-disk copy of played songs and covers (off by default; Settings).
    public let cache: CacheModel
    /// The optional SMB mount of the music folder (Settings; off by default).
    public let share: ShareModel
    public var selectedArtist: ArtistItem = ArtistItem(id: 0, name: "Talk Talk", albumCount: 5)
    /// The letter shown in the Zine A-Z index.
    public var selectedLetter = "T"
    /// Cupertino's Up Next inspector. It sits over whatever screen is showing, so opening it never changes the screen.
    public var queueOpen = false

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
        self.share = session == nil ? ShareModel(defaults: defaults, secrets: InMemorySecretStore(), mounter: NoMounter()) : ShareModel(defaults: defaults, secrets: session?.secrets ?? InMemorySecretStore())
        self.artwork = ArtworkStore(media: media)
        let player = PlayerModel(output: output ?? EngineOutput(), fetcher: CachingFetcher(cache: media), defaults: defaults)
        self.player = player
        self.savedQueues = SavedQueueStore(defaults: defaults)
        self.radio = RadioModel(defaults: defaults)
        self.systemMedia = session != nil ? SystemMedia(player, artwork: artwork, widget: WidgetPublisher()) : nil   // media keys only in the running app
        if let actions { self.actions = actions }
        else if session != nil {
            let live = AcquisitionActions(acquisition)
            self.actions = live
            live.onPlay = { [weak self] album in self?.playAlbum(album) }
            live.onResume = { [weak self] in self?.player.togglePlayPause() }
            let notifier = SystemGetNotifier()
            notifier.onOpen = { [weak self] in self?.screen = .downloads }
            acquisition.notifier = notifier
        } else { self.actions = NoopActions() }
        player.onUpNextLow = { [weak self] in if self?.radio.autoplay == true { self?.startRadio() } }
        player.waveformFileURL = { [weak self] item in item.path.flatMap { self?.share.localURL(forServerPath: $0) } }
        session?.onConnected = { [weak self] in self?.share.startIfNeeded(); await self?.refreshLibrary() }
        session?.onNavidromeSignOut = { [weak self] in self?.lyrics.clearAll(); self?.library.clearSavedPages(); self?.cache.media.clear(); self?.player.waveformCache.clear() }
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
        artwork.configure(librarian: session.librarian)
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
        player.waveformCache.setScope(scope)
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

    public func loadAllSongs() async { await library.loadAllSongs(navidrome: session?.navidrome) }

    public func loadSongs(more: Bool = false) async {
        await library.loadSongs(navidrome: session?.navidrome, more: more)
    }

    // MARK: Playback

    /// Plays an owned album from its first song. A recommendation the library does not hold cannot be played.
    public func playAlbum(_ album: AlbumItem, startAt: Int = 0) {
        guard let id = album.remoteID, album.owned, let navidrome = session?.navidrome else { return }
        Task {
            guard let detail = try? await navidrome.album(id: id), !detail.songs.isEmpty else { return }
            player.play(detail.songs.map(PlayerModel.item), startAt: min(max(startAt, 0), detail.songs.count - 1))
        }
    }

    /// True when this track of the album on screen is the song loaded in the player.
    public func isCurrent(_ track: TrackItem) -> Bool {
        guard let c = player.current, c.title == track.title else { return false }
        return c.albumID == selectedAlbum.remoteID || c.album == selectedAlbum.title
    }

    // MARK: Queue workspace

    /// Radio from this: adds songs by similar artists after what is queued, seeded by the song playing now.
    public func startRadio() {
        guard let seed = player.current, let navidrome = session?.navidrome else { return }
        let queued = Set(player.queue.items.map(\.songID))
        let source = RadioModel.liveCandidates(navidrome: navidrome, artists: library.artists)
        Task {
            let songs = await radio.songs(like: seed, queued: queued, candidates: source)
            player.addToQueue(songs)
        }
    }

    /// Saves the whole queue under `name` (a used name is replaced).
    public func saveQueue(named name: String) {
        savedQueues.save(name: name, items: player.queue.items)
    }

    /// Replaces the queue with a saved one and plays it from the top.
    public func playSavedQueue(_ id: UUID) {
        let songs = savedQueues.songs(of: id)
        guard !songs.isEmpty else { return }
        player.play(songs, startAt: 0)
    }

    /// Adds a saved queue after what is queued.
    public func addSavedQueue(_ id: UUID) { player.addToQueue(savedQueues.songs(of: id)) }

    /// Plays the Songs table from a row; the queue is the table in the order shown.
    public func play(rows: [SongRow], startAt index: Int) {
        let items = rows.compactMap(PlayerModel.item)
        guard !items.isEmpty else { return }
        let id = rows.indices.contains(index) ? rows[index].remoteID : nil
        player.play(items, startAt: items.firstIndex { $0.songID == id } ?? 0)
    }

    public func loadSelectedAlbum() async {
        async let relatedLoad: Void = related.loadAlbum(selectedAlbum, librarian: session?.librarian)
        await library.loadTracks(for: selectedAlbum, navidrome: session?.navidrome, librarian: session?.librarian, related: related)
        await relatedLoad
        await spread.load(album: selectedAlbum, navidrome: session?.navidrome, librarian: session?.librarian, libraryArtists: library.artists.map(\.name))
    }

    public func retrySpreadReviews() async { await spread.loadReviews(album: selectedAlbum, librarian: session?.librarian) }

    public func loadSelectedArtist() async {
        async let relatedLoad: Void = related.loadArtist(name: selectedArtist.name, remoteID: selectedArtist.remoteID, librarian: session?.librarian)
        await library.loadArtist(selectedArtist, navidrome: session?.navidrome)
        await relatedLoad
    }

    public func loadGapRadar() async { await library.loadGapRadar(navidrome: session?.navidrome) }

    /// Reads every song so rules see the whole library, then the playlists already on Navidrome.
    public func loadSmartPlaylists() async {
        let nav = session?.navidrome
        await library.loadAllSongs(navidrome: nav)
        await smart.loadRemote(navidrome: nav)
    }

    /// Reads every song so the history sees each song's latest play.
    public func loadHistory() async {
        let nav = session?.navidrome
        await library.loadAllSongs(navidrome: nav)
    }

    /// The songs a smart playlist holds right now.
    public func smartSongs(_ p: SmartPlaylist) -> [SongRow] { SmartEngine.run(p, over: library.songs) }

    public func saveSmart(_ p: SmartPlaylist, songs: [SongRow]) {
        Task { await smart.save(p, songs: songs, navidrome: session?.navidrome) }
    }

    /// Gets every missing album of one Gap radar artist that can be fetched now.
    public func getAllMissing(_ artist: GapArtist) {
        for a in artist.missing where acquisition.canGet(a) { actions.get(album: a) }
    }

    /// Library lists without the albums the owner dismissed.
    public func visible(_ albums: [AlbumItem]) -> [AlbumItem] { albums.filter { !acquisition.isHidden($0) } }

    /// Where the Back button on an album page goes: the screen the album was opened from (Albums by default).
    public private(set) var albumBack: Screen = .albums
    /// Where the Back button on an artist page goes: the screen the artist was opened from (Artists by default).
    public private(set) var artistBack: Screen = .artists

    public func open(album: AlbumItem) {
        if screen != .album && screen != .nowPlaying { albumBack = Self.listScreen(screen) }
        selectedAlbum = album; screen = .album
    }

    public func open(artist: ArtistItem) {
        if screen != .artist && screen != .nowPlaying { artistBack = Self.listScreen(screen) }
        selectedArtist = artist; selectedLetter = artist.letter; screen = .artist
    }

    /// Goes to a screen. Up Next in Cupertino opens the inspector over the current screen instead.
    public func go(_ s: Screen) {
        if s == .queue && themeID == .cupertino {
            queueOpen.toggle()
            if screen == .nowPlaying { screen = .albums }
        } else { screen = s }
    }

    /// Opens the album of the song playing now.
    public func openCurrentAlbum() {
        guard let c = player.current, !c.album.isEmpty else { return }
        if let known = (library.albums + library.recent).first(where: { c.albumID != nil && $0.remoteID == c.albumID }) { open(album: known); return }
        open(album: AlbumItem(id: 8000, title: c.album, artist: c.artist, year: 0, genre: "", format: "", owned: true,
                              hue: LibraryModel.hue(for: c.album), remoteID: c.albumID, coverArt: c.coverArt))
    }

    /// Opens the artist of the song playing now, when the library has them.
    public func openCurrentArtist() {
        guard let c = player.current else { return }
        openArtist(named: c.artist)
    }

    /// The Up Next view is the Albums grid with the inspector open, so going back from it lands on Albums.
    static func listScreen(_ s: Screen) -> Screen { s == .queue ? .albums : s }

    /// Name of a screen as the sidebar and Back buttons call it.
    public static func title(of screen: Screen) -> String {
        switch screen {
        case .home: "Home"
        case .album: "Album"
        case .nowPlaying: "Now Playing"
        case .queue: "Up Next"
        case .library: "Songs"
        case .artist: "Artist"
        case .settings: "Settings"
        case .albums: "Albums"
        case .downloads: "Downloads"
        case .discover: "New"
        case .equalizer: "Equalizer"
        case .gapRadar: "Gap Radar"
        case .smartPlaylists: "Smart Playlists"
        case .history: "History"
        case .artists: "Artists"
        case .recent: "Recently Added"
        }
    }

    /// True when the artist on screen is one the library does not hold (reached from a similar-artists row).
    public var selectedArtistIsUnowned: Bool { library.isLive && library.artist(named: selectedArtist.name) == nil }

    /// The albums the artist page lists: the library's own, or for an artist it lacks, the Librarian's list.
    public var shownArtistAlbums: [AlbumItem] {
        if selectedArtistIsUnowned { return related.artistAlbums }
        guard library.isLive else { return library.artistAlbums }
        // A partly owned artist: the library's albums, then every album the Librarian lists that the library lacks
        // (picks by the artist included), each once.
        var seen = Set(library.artistAlbums.map { Self.albumTitleKey($0.title) })
        let lacking = related.artistAlbums.filter { seen.insert(Self.albumTitleKey($0.title)).inserted }
        return library.artistAlbums + lacking
    }
    public var shownArtistOwnedCount: Int { library.isLive ? shownArtistAlbums.filter(\.owned).count : library.artistOwnedCount }
    public var shownArtistMissingCount: Int { library.isLive ? shownArtistAlbums.filter { !$0.owned }.count : library.artistMissingCount }

    /// Titles compared without case, punctuation or one trailing "(year)", as the server does.
    static func albumTitleKey(_ title: String) -> String {
        var t = title.lowercased()
        if let r = t.range(of: #"\s*[\(\[]\s*(19|20)\d{2}\s*[\)\]]\s*$"#, options: .regularExpression) { t.removeSubrange(r) }
        return String(t.filter { $0.isLetter || $0.isNumber })
    }

    /// Opens a similar artist: their library page when owned, otherwise a page built from the Librarian's data.
    public func open(similar a: SimilarArtistEntry) {
        if let own = library.artist(named: a.name) { open(artist: own); return }
        open(artist: ArtistItem(id: 100_000 + abs(a.name.lowercased().hashValue % 800_000), name: a.name, albumCount: 0))
    }

    /// Opens an artist by name when the library has them; otherwise nothing happens.
    public func openArtist(named name: String) {
        if let a = library.artist(named: name) { open(artist: a) }
        else if !library.isLive { open(artist: selectedArtist) }
    }
}

/// A mounter that does nothing: previews and screenshot tests.
struct NoMounter: ShareMounter {
    func mount(_ address: URL, credential: Credential?) async -> ShareMountOutcome { .failed(.unreachable) }
}

// MARK: Command palette

extension AppState {
    /// What the palette lists for what is typed, from the library as loaded now.
    func paletteResults() -> [PaletteCommand] {
        PaletteCatalog.results(query: palette.query, playing: player.isPlaying,
                               albums: visible(library.albums + library.recent + library.missing), artists: library.artists)
    }

    /// Runs one palette line and closes the palette.
    func perform(_ command: PaletteCommand) {
        palette.close()
        switch command.action {
        case .go(let s): go(s)
        case .playPause: player.togglePlayPause()
        case .next: player.next()
        case .previous: player.previous()
        case .toggleShuffle: player.toggleShuffle()
        case .cycleRepeat: player.cycleRepeat()
        case .openAlbum(let a): open(album: a)
        case .play(let a): actions.play(album: a)
        case .get(let a): actions.get(album: a)
        case .openArtist(let a): open(artist: a)
        }
    }
}
