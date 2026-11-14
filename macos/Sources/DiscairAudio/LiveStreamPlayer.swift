import AVFoundation
import Foundation

// Live radio playback (docs/RADIO_PLAYBACK_PROPOSAL.md S2.6; macOS stage 2, slice S2-2 item 2).
// No level tap: AVFoundation gives a tap no samples on live streams (macos/DESIGN.md, S2-2 item 1), so the bar is B1 everywhere.
// The station's address is only ever passed to AVPlayer: it is never logged, shown or put in an error (contract principle 6).

/// What a live stream is doing. `stalled` is the player waiting for data; the reconnect rules of S2-4 build on it.
public enum LiveState: Equatable, Sendable {
    case connecting, playing, stalled, failed
}

/// What the model needs from a live back end. The real one is `LiveStreamPlayer`; tests use `FakeLiveOutput`, which plays nothing.
@MainActor
public protocol LiveOutput: AnyObject {
    /// Called on the main actor whenever the state changes.
    var onState: ((LiveState) -> Void)? { get set }
    var volume: Float { get set }
    func start(url: URL)
    func stop()
}

@MainActor
public final class LiveStreamPlayer: NSObject, LiveOutput {
    public var onState: ((LiveState) -> Void)?
    public var volume: Float = 1 { didSet { player?.volume = volume } }

    private var player: AVPlayer?
    private var observers: [NSKeyValueObservation] = []
    private var endObserver: (any NSObjectProtocol)?
    private var state: LiveState = .connecting
    private var generation = 0

    public override init() { super.init() }

    public func start(url: URL) {
        stop()
        generation += 1
        let myGeneration = generation
        let item = AVPlayerItem(url: url)
        item.preferredForwardBufferDuration = 0
        let player = AVPlayer(playerItem: item)
        player.volume = volume
        player.automaticallyWaitsToMinimizeStalling = true
        self.player = player
        set(.connecting)
        player.play()

        observers.append(item.observe(\.status, options: [.new]) { [weak self] item, _ in
            let status = item.status
            Task { @MainActor in
                guard let self, self.generation == myGeneration else { return }
                switch status {
                case .failed: self.set(.failed)
                case .readyToPlay: break
                default: break
                }
            }
        })
        observers.append(player.observe(\.timeControlStatus, options: [.new]) { [weak self] player, _ in
            let status = player.timeControlStatus
            Task { @MainActor in
                guard let self, self.generation == myGeneration else { return }
                switch status {
                case .playing: self.set(.playing)
                case .waitingToPlayAtSpecifiedRate: if self.state == .playing { self.set(.stalled) }
                case .paused: break
                @unknown default: break
                }
            }
        })
        // A live stream that ends (server closed it) is a drop, not a finish.
        endObserver = NotificationCenter.default.addObserver(forName: AVPlayerItem.didPlayToEndTimeNotification, object: item, queue: .main) { [weak self] _ in
            Task { @MainActor in
                guard let self, self.generation == myGeneration else { return }
                self.set(.failed)
            }
        }
    }

    public func stop() {
        generation += 1
        observers.removeAll()
        if let endObserver { NotificationCenter.default.removeObserver(endObserver) }
        endObserver = nil
        player?.pause()
        player?.replaceCurrentItem(with: nil)
        player = nil
    }

    private func set(_ new: LiveState) {
        guard new != state || new == .connecting else { return }
        state = new
        onState?(new)
    }
}
