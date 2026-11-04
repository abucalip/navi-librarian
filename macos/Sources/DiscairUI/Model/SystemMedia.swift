import DiscairAudio
import Foundation
import MediaPlayer

/// The Mac's media keys, Control Centre and lock screen "Now Playing": reports the playing song and answers play, pause,
/// next, previous and seek from the system. Artwork is not sent yet.
@MainActor
final class SystemMedia {
    private let player: PlayerModel
    private var tokens: [(MPRemoteCommand, Any)] = []

    init(_ player: PlayerModel) {
        self.player = player
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
            center.nowPlayingInfo = nil
            center.playbackState = .stopped
            return
        }
        center.nowPlayingInfo = [
            MPMediaItemPropertyTitle: c.title,
            MPMediaItemPropertyArtist: c.artist,
            MPMediaItemPropertyAlbumTitle: c.album,
            MPMediaItemPropertyPlaybackDuration: player.duration,
            MPNowPlayingInfoPropertyElapsedPlaybackTime: player.position,
            MPNowPlayingInfoPropertyPlaybackRate: player.isPlaying ? 1.0 : 0.0,
        ]
        center.playbackState = player.isPlaying ? .playing : .paused
    }

    // Lives as long as the app; the handlers are never removed.
}
