import AppKit
import DiscairAudio
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
    /// Asked for at 600 px: Control Centre shows it at most a few hundred points wide.
    static let coverPixels = 600

    init(_ player: PlayerModel, artwork: ArtworkStore? = nil, widget: WidgetPublisher? = nil) {
        self.player = player
        self.widget = widget
        self.artwork = artwork
        let c = MPRemoteCommandCenter.shared()
        add(c.playCommand) { p in if !p.isPlaying { p.togglePlayPause() } }
        add(c.pauseCommand) { p in if p.isPlaying { p.togglePlayPause() } }
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
