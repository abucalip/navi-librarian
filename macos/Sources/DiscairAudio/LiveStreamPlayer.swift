import AVFoundation
import Foundation
import MediaToolbox
import os

// Live radio playback (docs/RADIO_PLAYBACK_PROPOSAL.md S2.6; macOS stage 2, slice S2-2 item 2).
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
    /// Called on the main actor about 15 times a second while sound arrives: one RMS value, 0...1.
    var onLevel: ((Float) -> Void)? { get set }
    /// Called once when the first tap sample has arrived, and never when the stream gives no tappable track (the bar then shows B1).
    var hasTapSamples: Bool { get }
    var volume: Float { get set }
    func start(url: URL)
    func stop()
}

/// Collects squared samples from the audio thread and hands back one RMS value per call. Pure, so it is tested without audio.
public final class LevelAccumulator: @unchecked Sendable {
    private struct Sums { var squares: Double = 0; var count: Int = 0; var everHadSamples = false }
    private let lock = OSAllocatedUnfairLock(initialState: Sums())
    public init() {}

    /// Adds interleaved or planar float samples (any channel layout: the RMS covers them all).
    public func add(_ samples: UnsafeBufferPointer<Float>) {
        var sum: Double = 0
        for v in samples { sum += Double(v) * Double(v) }
        let n = samples.count
        let total = sum
        lock.withLock { $0.squares += total; $0.count += n; $0.everHadSamples = true }
    }

    /// RMS of everything added since the last call, clamped to 0...1; nil when nothing arrived.
    public func takeRMS() -> Float? {
        lock.withLock { sums in
            defer { sums.squares = 0; sums.count = 0 }
            guard sums.count > 0 else { return nil }
            return min(1, Float((sums.squares / Double(sums.count)).squareRoot()))
        }
    }

    public var hasEverHadSamples: Bool { lock.withLock { $0.everHadSamples } }
}

@MainActor
public final class LiveStreamPlayer: NSObject, LiveOutput {
    public var onState: ((LiveState) -> Void)?
    public var onLevel: ((Float) -> Void)?
    public var volume: Float = 1 { didSet { player?.volume = volume } }
    public var hasTapSamples: Bool { accumulator.hasEverHadSamples }

    private var player: AVPlayer?
    private var observers: [NSKeyValueObservation] = []
    private var endObserver: (any NSObjectProtocol)?
    private var meterTimer: Timer?
    private var accumulator = LevelAccumulator()
    private var state: LiveState = .connecting
    private var generation = 0

    public override init() { super.init() }

    public func start(url: URL) {
        stop()
        generation += 1
        let myGeneration = generation
        accumulator = LevelAccumulator()
        let item = AVPlayerItem(url: url)
        item.preferredForwardBufferDuration = 0
        let player = AVPlayer(playerItem: item)
        player.volume = volume
        player.automaticallyWaitsToMinimizeStalling = true
        self.player = player
        set(.connecting)

        observers.append(item.observe(\.status, options: [.new]) { [weak self] item, _ in
            let status = item.status
            Task { @MainActor in
                guard let self, self.generation == myGeneration else { return }
                switch status {
                case .failed: self.set(.failed)
                case .readyToPlay: self.attachTap(to: item, generation: myGeneration); self.player?.play()
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
        startMeterTimer(generation: myGeneration)
    }

    public func stop() {
        generation += 1
        meterTimer?.invalidate(); meterTimer = nil
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

    private func startMeterTimer(generation: Int) {
        // About 15 Hz. The tap writes on the audio thread; this reads on the main actor.
        meterTimer = Timer.scheduledTimer(withTimeInterval: 1.0 / 15.0, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self, self.generation == generation, let rms = self.accumulator.takeRMS() else { return }
                self.onLevel?(rms)
            }
        }
    }

    /// Puts an `MTAudioProcessingTap` on the item's audio track. An ICY or HLS address may expose no track: then nothing
    /// is attached, no level ever arrives and the bar falls back to B1 by design.
    private func attachTap(to item: AVPlayerItem, generation: Int) {
        // A live (ICY) asset reports no tracks through `loadTracks`, but the item lists its audio track once it is ready.
        guard self.generation == generation, player?.currentItem === item,
              let track = item.tracks.compactMap(\.assetTrack).first(where: { $0.mediaType == .audio }),
              let tap = Self.makeTap(accumulator: accumulator) else { return }
        defer { player?.play() }
        let params = AVMutableAudioMixInputParameters(track: track)
        params.audioTapProcessor = tap
        let mix = AVMutableAudioMix()
        mix.inputParameters = [params]
        item.audioMix = mix
    }

    private nonisolated static func makeTap(accumulator: LevelAccumulator) -> MTAudioProcessingTap? {
        var callbacks = MTAudioProcessingTapCallbacks(
            version: kMTAudioProcessingTapCallbacksVersion_0,
            clientInfo: Unmanaged.passRetained(accumulator).toOpaque(),
            init: { _, clientInfo, storageOut in storageOut.pointee = clientInfo },
            finalize: { tap in Unmanaged<LevelAccumulator>.fromOpaque(MTAudioProcessingTapGetStorage(tap)).release() },
            prepare: nil,
            unprepare: nil,
            process: { tap, frames, flags, bufferList, framesOut, flagsOut in
                guard MTAudioProcessingTapGetSourceAudio(tap, frames, bufferList, flagsOut, nil, framesOut) == noErr else { return }
                let acc = Unmanaged<LevelAccumulator>.fromOpaque(MTAudioProcessingTapGetStorage(tap)).takeUnretainedValue()
                for buffer in UnsafeMutableAudioBufferListPointer(bufferList) {
                    // The tap is asked for 32-bit float (the format AVFoundation hands to taps on macOS).
                    guard let data = buffer.mData else { continue }
                    let count = Int(buffer.mDataByteSize) / MemoryLayout<Float>.size
                    acc.add(UnsafeBufferPointer(start: data.assumingMemoryBound(to: Float.self), count: count))
                }
            })
        var tap: MTAudioProcessingTap?
        let status = MTAudioProcessingTapCreate(kCFAllocatorDefault, &callbacks, kMTAudioProcessingTapCreationFlag_PostEffects, &tap)
        guard status == noErr, let tap else {
            Unmanaged<LevelAccumulator>.fromOpaque(callbacks.clientInfo!).release()
            return nil
        }
        return tap
    }
}
