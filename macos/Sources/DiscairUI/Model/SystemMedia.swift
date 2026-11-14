import AppKit
import DiscairAudio
import DiscairLibrarian
import Foundation
import MediaPlayer

/// The Mac's media keys, Control Centre and lock screen "Now Playing": reports the playing song and answers play, pause,
/// next, previous and seek from the system. The cover is fetched through the artwork store (memory, disk cache, then the
/// server) and added when it arrives; until then, and when there is none, the entry shows no picture.
@MainActor
final class SystemMedia {
    private let player: PlayerModel
    private let artwork: ArtworkStore?
    private var tokens: [(MPRemoteCommand, Any)] = []
    /// The cover id the picture below belongs to, and the picture once loaded.
    private var coverID: String?
    private var coverImage: NSImage?
    private var coverTask: Task<Void, Never>?
    /// The Notification Center widget gets the same song (nil in tests that don't ask for it).
    private let widget: WidgetPublisher?
    /// Station logos for the system picture while a station plays (S2-2 item 6); nil in tests that don't ask for it.
    private let logos: StationLogoStore?
    private var logoKey: String?
    private var logoImage: NSImage?
    private var logoTask: Task<Void, Never>?
    private let seekCommand: MPRemoteCommand
    /// Asked for at 600 px: Control Centre shows it at most a few hundred points wide.
    static let coverPixels = 600

    init(_ player: PlayerModel, artwork: ArtworkStore? = nil, widget: WidgetPublisher? = nil, logos: StationLogoStore? = nil) {
        self.player = player
        self.logos = logos
        self.widget = widget
        self.artwork = artwork
        let c = MPRemoteCommandCenter.shared()
        seekCommand = c.changePlaybackPositionCommand
        // A station cannot pause and keep its place: Pause stops it and Play starts the stopped one again (S2.2 item 6).
        add(c.playCommand) { p in if !p.isPlaying && p.live == nil { p.togglePlayPause() } }
        add(c.pauseCommand) { p in if p.isPlaying || p.live != nil { p.togglePlayPause() } }
        add(c.togglePlayPauseCommand) { p in p.togglePlayPause() }
        add(c.nextTrackCommand) { p in p.next() }
        add(c.previousTrackCommand) { p in p.previous() }
        let seek = c.changePlaybackPositionCommand
        seek.isEnabled = true
        let t = seek.addTarget { [weak self] event in
            guard let e = event as? MPChangePlaybackPositionCommandEvent else { return .commandFailed }
            MainActor.assumeIsolated { self?.player.seek(toSeconds: e.positionTime) }
            return .success
        }
        tokens.append((seek, t))
        player.onNowPlayingChange = { [weak self] in self?.update() }
    }

    private func add(_ command: MPRemoteCommand, _ action: @escaping @MainActor (PlayerModel) -> Void) {
        command.isEnabled = true
        let t = command.addTarget { [weak self] _ in
            guard let self else { return .commandFailed }
            MainActor.assumeIsolated { action(self.player) }
            return .success
        }
        tokens.append((command, t))
    }

    func update() {
        let center = MPNowPlayingInfoCenter.default()
        // Seeking is off while a station plays and on again when a library song does.
        seekCommand.isEnabled = player.live == nil
        if let live = player.live {
            loadLogoIfNeeded(for: player.stationByLive)
            center.nowPlayingInfo = Self.liveInfo(stationName: live.name, cover: logoImage)
            center.playbackState = .playing
            widget?.publishLive(stationName: live.name, stationID: live.stationID, logo: logoImage)
            return
        }
        logoTask?.cancel(); logoKey = nil; logoImage = nil
        guard let c = player.current, player.phase != .idle else {
            coverTask?.cancel(); coverID = nil; coverImage = nil
            center.nowPlayingInfo = nil
            center.playbackState = .stopped
            widget?.publish(item: nil, duration: 0, position: 0, playing: false, cover: nil)
            return
        }
        loadCoverIfNeeded(for: c)
        center.nowPlayingInfo = Self.info(for: c, duration: player.duration, position: player.position,
                                          playing: player.isPlaying, cover: coverImage)
        center.playbackState = player.isPlaying ? .playing : .paused
        widget?.publish(item: c, duration: player.duration, position: player.position, playing: player.isPlaying, cover: coverImage)
    }

    /// Fetches the logo of the playing station once, at 512; a late answer for another station is dropped.
    private func loadLogoIfNeeded(for station: RadioStation?) {
        guard let station else { return }
        guard station.id != logoKey else { return }
        logoTask?.cancel()
        logoKey = station.id; logoImage = nil
        guard let logos else { return }
        logoTask = Task { [weak self] in
            let image = await logos.logo(station: station.id, size: .large)
            guard !Task.isCancelled, let self, self.logoKey == station.id, let image else { return }
            self.logoImage = Self.squareCover(image) ?? image
            self.update()
        }
    }

    /// What the system is told while a station plays: the station's name as the title, a live stream (no duration, no position,
    /// no elapsed time) and the logo. The song joins it with S2-3. Pure, like `info`.
    nonisolated static func liveInfo(stationName: String, cover: NSImage?) -> [String: Any] {
        var info: [String: Any] = [
            MPMediaItemPropertyTitle: stationName,
            MPNowPlayingInfoPropertyIsLiveStream: true,
            MPNowPlayingInfoPropertyPlaybackRate: 1.0,
        ]
        if let cover {
            nonisolated(unsafe) let image = cover
            info[MPMediaItemPropertyArtwork] = MPMediaItemArtwork(boundsSize: cover.size) { _ in image }
        }
        return info
    }

    /// Fetches the cover of a new song once; a late answer for a song that is no longer playing is dropped.
    private func loadCoverIfNeeded(for item: QueueItem) {
        // The owner's chosen cover (docs/artwork.md, idea 7) is what the system shows, so a new pick is a new cover. One cover per song:
        // alternate sleeves per play are not built (open decision 2, off by default).
        let key = Self.coverKey(item, pick: item.albumID.flatMap { artwork?.choices[$0] })
        guard key != coverID else { return }
        coverTask?.cancel()
        coverID = key; coverImage = nil
        guard item.coverArt != nil || item.albumID != nil, let artwork else { return }
        coverTask = Task { [weak self] in
            let image = await artwork.libraryCover(albumID: item.albumID, coverArt: item.coverArt, px: Self.coverPixels)
            guard !Task.isCancelled, let self, self.coverID == key, let image else { return }
            self.coverImage = Self.squareCover(image) ?? image
            self.update()
        }
    }

    /// What identifies the cover being shown: the song's cover id, its album and the owner's pick.
    nonisolated static func coverKey(_ item: QueueItem, pick: Int?) -> String {
        "\(item.coverArt ?? "")|\(item.albumID ?? "")|\(pick ?? 0)"
    }

    /// The cover cut to the largest centred square. The server scales a cover without cropping it, so a wide or tall one reached
    /// Control Centre off-centre in its square tile. Nil when the image has no pixel data to cut (the caller keeps the original).
    nonisolated static func squareCover(_ image: NSImage) -> NSImage? {
        guard let rep = image.representations.first, rep.pixelsWide > 0, rep.pixelsHigh > 0,
              let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return nil }
        let w = cg.width, h = cg.height
        if w == h { return image }
        let side = min(w, h)
        guard let cut = cg.cropping(to: CGRect(x: (w - side) / 2, y: (h - side) / 2, width: side, height: side)) else { return nil }
        return NSImage(cgImage: cut, size: NSSize(width: side, height: side))
    }

    /// What the system is told about the playing song. Pure, so a test can check it without the system's shared center.
    nonisolated static func info(for c: QueueItem, duration: Double, position: Double, playing: Bool, cover: NSImage?) -> [String: Any] {
        var info: [String: Any] = [
            MPMediaItemPropertyTitle: c.title,
            MPMediaItemPropertyArtist: c.artist,
            MPMediaItemPropertyAlbumTitle: c.album,
            MPMediaItemPropertyPlaybackDuration: duration,
            MPNowPlayingInfoPropertyElapsedPlaybackTime: position,
            MPNowPlayingInfoPropertyPlaybackRate: playing ? 1.0 : 0.0,
        ]
        if let cover {
            // The system may call this on any thread and asks for any size; the image is immutable once loaded.
            nonisolated(unsafe) let image = cover
            info[MPMediaItemPropertyArtwork] = MPMediaItemArtwork(boundsSize: cover.size) { _ in image }
        }
        return info
    }

    // Lives as long as the app; the handlers are never removed.
}
