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
    /// The connection graph around an artist (Server V2 Phase 7 client gate; mockup `docs/design/macos-graph/index.html`).
    case connections
    /// A map of the places recordings were made, with stated coordinates only (Server V2 Phase 7 client gate; mockup `docs/design/macos-graph/index.html`).
    case atlas
    /// One artist's albums and events by stated date (Server V2 Phase 7 client gate).
    case timeline
    /// Rule-built playlists, saved to Navidrome (M6 slice 8; contract section 6.7).
    case smartPlaylists
    /// Days and a heatmap of when songs were last played (M6 slice 9; contract section 6.6).
    case history
    /// Server V2 Phase 3 insight cards, one section per lens (client gate; the mockups are `docs/design/macos-insights/mockups.html`).
    case insights
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
    public var screen: Screen {
        didSet {
            // Now Playing remembers where it was opened from, so its chevron goes back there.
            if screen == .nowPlaying && oldValue != .nowPlaying { nowPlayingReturn = oldValue }
        }
    }
    /// The screen the chevron on Now Playing returns to.
    public let albumCredits = AlbumCreditsModel()
    public private(set) var nowPlayingReturn: Screen = .home
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
    /// Songs the server found for the text being searched (the palette and the Library search), whole library.
    public private(set) var songHits: [SongRow] = []
    public let lyrics = LyricsModel()
    /// Facts about the playing song, album and artist for the player bar, and the two switches that show them.
    public let facts = FactsModel()
    public let barOptions: PlayerBarOptions
    /// Playback: the queue, the audio engine and the controls.
    public let player: PlayerModel
    /// Saved skip events; nil without a session (previews and tests).
    @ObservationIgnored private var feedback: FeedbackOutbox?
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
    public let insights = InsightsModel()
    /// "Your taste" cards inside Insights; refreshed once per launch from the connected session.
    public let taste = TasteModel()
    /// Settings > ListenBrainz: the server-side account taste and popularity read.
    public let listenBrainz = ListenBrainzModel()
    public let graph = GraphExplorerModel()
    public let atlas = AtlasModel()
    public let timeline = TimelineModel()
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
    /// The Library page's tab, and the text in its search field (it stays when the tab changes).
    public var libraryTab: LibraryTab = .overview
    public var librarySearch = ""
    /// A genre or decade a taste card asked the Songs tab to show (slice 7); the owner clears it with the chip on the tab.
    public var tasteFilter: TasteAction?
    /// The song to mark on the album page after a Library search result opened it (matched by title).
    public var highlightedSong: String?
    /// The Discover group of the Cupertino sidebar is folded or open.
    public var discoverOpen = true

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
        self.barOptions = PlayerBarOptions(defaults: defaults)
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
        // Skip events wait in a file until the Librarian takes them. Previews and tests have no session, so they record none.
        if let session {
            let outbox = FeedbackOutbox(fileURL: FeedbackOutbox.defaultURL, send: { [weak session] events in
                guard let librarian = await MainActor.run(body: { session?.librarian }) else { throw FeedbackUnavailable() }
                return try await librarian.reportFeedback(events)
            })
            player.configureFeedback(outbox)
            insights.configureFeedback(outbox)
            feedback = outbox
        }
        player.onUpNextLow = { [weak self] in if self?.radio.autoplay == true { self?.startRadio() } }
        player.waveformFetch = { [weak session] songID in
            guard let librarian = await MainActor.run(body: { session?.librarian }) else { return .unavailable }
            return (try? await librarian.songPeaks(id: songID)) ?? .unavailable
        }
        session?.onConnected = { [weak self] in
            self?.share.startIfNeeded()
            // The refresh can take about a minute on a long history, so it never holds up the library load.
            Task { [weak self] in await self?.refreshTaste() }
            await self?.refreshLibrary()
        }
        session?.onNavidromeSignOut = { [weak self] in self?.lyrics.clearAll(); self?.facts.reset(); self?.library.clearSavedPages(); self?.cache.media.clear(); self?.player.waveformCache.clear() }
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
        // Skips saved while the Librarian was unreachable go out now that it is connected (in the background).
        Task { await feedback?.flush() }
        lyrics.configure(navidrome: navidrome, scope: "\(session.activeProfile?.navidromeURL.absoluteString ?? "")|\(session.navidromeUsername ?? "")")
        if let librarian = session.librarian {
            radio.setSonicAvailable(await librarian.sonicAvailable())
            pathsAvailable = await librarian.pathsAvailable()
        }
        await library.load(navidrome: navidrome, librarian: session.librarian)
        await library.loadSongs(navidrome: navidrome)
        Task { await library.loadAllAlbums(navidrome: navidrome) }
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
        guard let c = player.current else { return false }
        // The song id tells two versions of one title on an album apart; sample and suggested tracks have none.
        if let id = track.songID { return c.songID == id }
        guard c.title == track.title else { return false }
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

    /// Sounds like this: adds songs that sound like `seed` (default the song playing) after what is queued. A seed that is not
    /// the playing song is played first when nothing is queued. Needs the Librarian and `sonic_available`.
    public func startSonicRadio(seed: QueueItem? = nil) {
        guard radio.sonicAvailable, let librarian = session?.librarian, let seed = seed ?? player.current else { return }
        let queued = Set(player.queue.items.map(\.songID))
        Task {
            let songs = await radio.sonicSongs(like: seed, queued: queued) { id, count in try await librarian.sonicSimilar(songID: id, count: count) }
            if player.current == nil || player.queue.isEmpty { player.play([seed] + songs) } else { player.addToQueue(songs) }
        }
    }

    /// Whether the server reports the paths feature (`features.paths`); the album Paths button shows whenever it does.
    public private(set) var pathsAvailable = false

    /// The album Paths sheet, when one is open.
    public var paths: PathsSheetModel?

    /// The server builds album paths from an album in the library, by its Navidrome id, so an album outside it has none.
    public var canShowAlbumPaths: Bool { pathsAvailable && library.isLive && selectedAlbum.owned && selectedAlbum.remoteID != nil }

    /// Opens the Paths sheet for the album on screen and reads its first tab.
    public func showAlbumPaths() {
        guard canShowAlbumPaths, let id = selectedAlbum.remoteID else { return }
        let a = selectedAlbum
        let model = PathsSheetModel(albumTitle: a.title, artist: a.artist, albumID: id, sonicAvailable: radio.sonicAvailable)
        paths = model
        let librarian = session?.librarian
        Task { await model.load(librarian: librarian) }
    }

    /// The artist's Paths button: the server builds artist paths by MusicBrainz id, which Navidrome holds on the artist record.
    public var canShowArtistPaths: Bool { pathsAvailable && library.isLive && selectedArtist.remoteID != nil }

    /// Opens the Paths sheet for the artist on screen and reads its first tab.
    public func showArtistPaths() {
        guard canShowArtistPaths, let id = selectedArtist.remoteID, let navidrome = session?.navidrome else { return }
        let model = PathsSheetModel(artistName: selectedArtist.name) { try await navidrome.artist(id: id).artist.musicBrainzId }
        model.subjectID = id
        paths = model
        let librarian = session?.librarian
        Task { await model.load(librarian: librarian) }
    }

    /// Reads the chosen tab of the open Paths sheet (once; `retry` asks again after a failure).
    public func loadPathsTab(retry: Bool = false) {
        guard let model = paths else { return }
        let librarian = session?.librarian
        Task { await model.load(librarian: librarian, retry: retry) }
    }

    /// The sonic path sheet, when one is open.
    public var sonicPath: SonicPathModel?

    /// Opens the sonic path from the playing song to `target`. Needs the Librarian, `sonic_available` and a different playing song.
    public func showSonicPath(to target: QueueItem) {
        guard radio.sonicAvailable, let librarian = session?.librarian, let start = player.current, start.songID != target.songID else { return }
        let model = SonicPathModel(start: start, target: target)
        sonicPath = model
        Task { await model.load { s, e, n in try await librarian.sonicPath(start: s, end: e, count: n) } }
    }

    /// Adds the path's steps after the queue (the start song is already playing), or plays the whole path now.
    public func useSonicPath(_ steps: [QueueItem], playNow: Bool) {
        if playNow { player.play(steps) } else { player.addToQueue(Array(steps.dropFirst())) }
        sonicPath = nil
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
        await albumCredits.load(rgid: related.releaseGroupMBID, librarian: session?.librarian)
    }

    public func retrySpreadReviews() async { await spread.loadReviews(album: selectedAlbum, librarian: session?.librarian) }

    public func loadSelectedArtist() async {
        async let relatedLoad: Void = related.loadArtist(name: selectedArtist.name, remoteID: selectedArtist.remoteID, librarian: session?.librarian)
        await library.loadArtist(selectedArtist, navidrome: session?.navidrome)
        await relatedLoad
    }

    public func loadInsights() async { await insights.load(librarian: session?.librarian) }
    /// Taste card action: starts a smart playlist from a listed genre or decade and opens it for editing. Nothing is saved to
    /// Navidrome until the owner saves it, and no ranking is touched.
    public func makeSmartPlaylist(from action: TasteAction) {
        smart.add(action.playlist)
        screen = .smartPlaylists
    }
    /// Taste card action: opens the Library's Songs tab showing only that genre or decade.
    public func openLibrary(filteredBy action: TasteAction) {
        librarySearch = ""; tasteFilter = action; libraryTab = .songs; screen = .library
    }
    public func refreshTaste() async { await taste.refreshOnLaunch(librarian: session?.librarian) }
    /// Saves the ListenBrainz account on the server, then reloads taste so "connect ListenBrainz" clears without a relaunch.
    public func connectListenBrainz() async {
        let librarian = session?.librarian
        let accepted = await listenBrainz.connect(librarian: librarian) { [taste] in
            await taste.refreshNow(librarian: librarian)
        }
        // Kept with the other logins so every launch sends it to the server again.
        if let accepted, let id = session?.activeProfile?.id { try? session?.setListenBrainzUsername(accepted.username, forProfile: id) }
        if let accepted { try? session?.saveLogin(.listenbrainz, username: accepted.username, password: accepted.token) }
    }

    /// Starts the connection explorer from the artist the owner picked in its search field.
    public func loadConnections(for a: ArtistItem) async {
        await graph.start(artistRemoteID: library.isLive ? a.remoteID : nil, name: a.name, navidrome: session?.navidrome, librarian: session?.librarian)
    }

    /// Reads the timeline of the artist the owner picked in its search field.
    public func loadTimeline(for a: ArtistItem) async {
        await timeline.start(artistRemoteID: library.isLive ? a.remoteID : nil, name: a.name, navidrome: session?.navidrome, librarian: session?.librarian)
    }

    public func loadAtlas() async { await atlas.load(librarian: session?.librarian) }

    public func loadGapRadar() async { await library.loadGapRadar(navidrome: session?.navidrome) }

    /// Reads every song so rules see the whole library, then the playlists already on Navidrome.
    public func loadSmartPlaylists() async {
        let nav = session?.navidrome
        await library.loadAllSongs(navidrome: nav)
        await smart.loadRemote(navidrome: nav)
        await smart.sync(librarian: session?.librarian)
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

    /// The 20 songs played most recently, from what Navidrome keeps per song.
    public var recentlyPlayed: [SongRow] { LibrarySearch.recentlyPlayed(library.songs) }

    /// Opens an album and marks one of its songs (a Library search result for a song).
    public func open(album: AlbumItem, highlighting song: String) {
        open(album: album)
        highlightedSong = song
    }

    public func open(album: AlbumItem) {
        highlightedSong = nil
        if screen != .album && screen != .nowPlaying { albumBack = Self.listScreen(screen) }
        // The previous album's songs, notes and similar lists are cleared at once, so the page never shows them under the new title.
        if album.id != selectedAlbum.id || album.remoteID != selectedAlbum.remoteID || album.title != selectedAlbum.title {
            library.showTracks([]); related.clear(); spread.startNewAlbum(); albumCredits.forget()
        }
        selectedAlbum = album; screen = .album
    }

    /// Leaves Now Playing for the screen it was opened from.
    public func closeNowPlaying() {
        screen = nowPlayingReturn == .nowPlaying ? .home : nowPlayingReturn
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
        case .queue: "Queue"
        case .library: "Library"
        case .artist: "Artist"
        case .settings: "Settings"
        case .albums: "Albums"
        case .downloads: "Downloads"
        case .discover: "New"
        case .equalizer: "Equalizer"
        case .gapRadar: "Gap Radar"
        case .connections: "Connections"
        case .atlas: "Atlas"
        case .timeline: "Timeline"
        case .smartPlaylists: "Smart Playlists"
        case .history: "History"
        case .insights: "Insights"
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
                               albums: visible(library.searchableAlbums + library.missing), artists: library.artists, songs: songHits)
    }

    /// Asks the server for songs matching `query` after a short pause; a newer query cancels this one (call it from `.task(id:)`).
    func searchSongHits(_ query: String) async {
        let q = LibrarySearch.fold(query)
        guard q.count >= 2, library.isLive, let nav = session?.navidrome else { songHits = []; return }
        try? await Task.sleep(for: .milliseconds(250))
        guard !Task.isCancelled else { return }
        if let found = try? await nav.searchSongs(q, count: 8), !Task.isCancelled {
            songHits = found.enumerated().map { LibraryModel.row($0.element, id: 2_000_000 + $0.offset) }
        }
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
        case .openSong(let s): open(album: s.albumItem, highlighting: s.title)
        case .playSong(let s): play(rows: [s], startAt: 0)
        }
    }
}
