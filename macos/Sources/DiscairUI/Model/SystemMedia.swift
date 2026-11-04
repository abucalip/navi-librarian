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
    /// Asked for at 600 px: Control Centre shows it at most a few hundred points wide.
    static let coverPixels = 600

    init(_ player: PlayerModel, artwork: ArtworkStore? = nil) {
        self.player = player
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
            return
        }
        loadCoverIfNeeded(for: c)
        center.nowPlayingInfo = Self.info(for: c, duration: player.duration, position: player.position,
                                          playing: player.isPlaying, cover: coverImage)
        center.playbackState = player.isPlaying ? .playing : .paused
    }

    /// Fetches the cover of a new song once; a late answer for a song that is no longer playing is dropped.
    private func loadCoverIfNeeded(for item: QueueItem) {
        guard item.coverArt != coverID else { return }
        coverTask?.cancel()
        coverID = item.coverArt; coverImage = nil
        guard let id = item.coverArt, let artwork else { return }
        coverTask = Task { [weak self] in
            let image = await artwork.image(coverArt: id, px: Self.coverPixels)
            guard !Task.isCancelled, let self, self.coverID == id, let image else { return }
            self.coverImage = image
            self.update()
        }
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
