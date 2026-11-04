import AVFoundation
import Foundation

/// What the player needs from an audio back end. The real one is `EngineOutput`; tests use a fake that plays nothing.
@MainActor
public protocol AudioOutput: AnyObject {
    /// Called on the main actor when the opened file has played to its end (not after `stop`, `seek` or a new `open`).
    var onFinished: (() -> Void)? { get set }
    var isPlaying: Bool { get }
    /// Seconds into the opened file.
    var position: Double { get }
    /// Seconds in the opened file; 0 when nothing is open.
    var duration: Double { get }
    /// Opens a local file ready to play from the start. Replaces whatever was open.
    func open(file: URL) throws
    func play()
    func pause()
    func stop()
    func seek(to seconds: Double)

    /// Hands over the next song so it can follow without a gap. The file is already on disk.
    func preload(file: URL, transition: Transition) throws
    /// Forgets the preloaded song (the queue changed).
    func cancelPreload()
    /// Called when the engine has started the preloaded song: at the join for `gapless`, at the start of the fade for
    /// `crossfade`. After it, `position`, `duration` and `onFinished` refer to the new song.
    var onAdvanced: (() -> Void)? { get set }

    /// Output level 0...1 of the app's own mixer (the system volume is separate).
    var volume: Float { get set }
    /// Applies the equalizer: ten band gains in dB and a pre-gain in dB. All zero is a true bypass.
    func applyEQ(gains: [Double], preGain: Double)
}

public enum Transition: Equatable, Sendable {
    /// The next song starts the moment this one ends, with no inserted or dropped frames.
    case gapless
    /// An equal-power fade of this many seconds, ending as the current song ends.
    case crossfade(Double)
}

public struct AudioError: Error, Equatable, Sendable, CustomStringConvertible {
    public let description: String
    public init(_ description: String) { self.description = description }
}

/// `AVAudioEngine` with two player nodes (contract section 12).
///
/// Gapless: when the next file has the same format, it is scheduled on the same node right behind the current one, which
/// the spike measured as sample-exact. Otherwise (or for a crossfade) the next file starts on the other node, and for a
/// crossfade the two levels follow an equal-power curve (cos and sin), stepped every 20 ms. A format change without a
/// fade starts the other node about 30 ms before the end, so that join is close but not sample-exact.
/// A generation number marks which `open`, `seek` or segment a completion belongs to, so a stopped or replaced file
/// never reports "finished".
@MainActor
public final class EngineOutput: AudioOutput {
    @MainActor private final class Slot {
        let node = AVAudioPlayerNode()
        var file: AVAudioFile?
        var attached = false
        /// Seconds into the file where the first segment on this node began.
        var startOffset: Double = 0
        /// Frames of earlier segments on the node (the node's sample time keeps counting across segments).
        var baseSample: Int64 = 0
        var generation = 0
        var paused = false
        var pausedAt: Double = 0
        /// Segments handed to the node and not yet finished, oldest first: (frames, file).
        var segments: [(frames: AVAudioFrameCount, file: AVAudioFile)] = []
    }

    private let engine = AVAudioEngine()
    /// Ten peaking bands after the mixer, so files of different formats share one filter chain (measured in the M2 spike).
    private let eq = AVAudioUnitEQ(numberOfBands: 10)
    private var eqWired = false
    private let slots = [Slot(), Slot()]
    private var active = 0
    private var cur: Slot { slots[active] }
    private var other: Slot { slots[1 - active] }

    private struct Pending { let file: AVAudioFile; let transition: Transition; var queuedOnNode: Bool }
    private var pending: Pending?
    private struct Fade { let from: Slot; let to: Slot; var elapsed: Double; let length: Double }
    private var fade: Fade?
    private var ticker: Task<Void, Never>?
    private static let tick = 0.02

    public var onFinished: (() -> Void)?
    public var onAdvanced: (() -> Void)?

    public init() {
        for (i, band) in eq.bands.enumerated() {
            band.filterType = .parametric
            band.frequency = Float(eqBandHz[i])
            band.bandwidth = 1.0                      // one octave
            band.gain = 0
            band.bypass = false
        }
    }

    public var volume: Float {
        get { engine.mainMixerNode.outputVolume }
        set { engine.mainMixerNode.outputVolume = min(max(newValue, 0), 1) }
    }

    private var eqGains = [Double](repeating: 0, count: 10)
    private var eqPreGain = 0.0

    public func applyEQ(gains: [Double], preGain: Double) {
        eqGains = gains; eqPreGain = preGain
        for (i, band) in eq.bands.enumerated() where gains.indices.contains(i) {
            band.gain = Float(gains[i])
            band.bypass = gains[i] == 0
        }
        eq.globalGain = Float(preGain)
        eq.bypass = preGain == 0 && gains.allSatisfy { $0 == 0 }     // off is a true bypass
    }

    /// mixer -> EQ -> output, wired once.
    private func wireEQ() {
        guard !eqWired else { return }
        engine.attach(eq)
        engine.disconnectNodeOutput(engine.mainMixerNode)
        engine.connect(engine.mainMixerNode, to: eq, format: nil)
        engine.connect(eq, to: engine.outputNode, format: nil)
        eqWired = true
        applyEQ(gains: eqGains, preGain: eqPreGain)
    }

    // MARK: State

    public var duration: Double { cur.file.map { Double($0.length) / $0.processingFormat.sampleRate } ?? 0 }
    public var isPlaying: Bool { cur.node.isPlaying }

    public var position: Double {
        let slot = cur
        guard let file = slot.file else { return 0 }
        if slot.paused { return slot.pausedAt }
        guard slot.node.isPlaying, let node = slot.node.lastRenderTime, let t = slot.node.playerTime(forNodeTime: node), t.sampleTime >= 0 else {
            return slot.startOffset
        }
        let played = Double(t.sampleTime - slot.baseSample) / file.processingFormat.sampleRate
        return min(max(slot.startOffset + played, 0), duration)
    }

    // MARK: Opening

    public func open(file url: URL) throws {
        stop()
        let f: AVAudioFile
        do { f = try AVAudioFile(forReading: url) } catch { throw AudioError("This file could not be opened for playback.") }
        try attach(cur, file: f)
        cur.file = f
        cur.startOffset = 0; cur.baseSample = 0; cur.paused = false; cur.pausedAt = 0
        schedule(cur, from: 0)
    }

    private func attach(_ slot: Slot, file: AVAudioFile) throws {
        wireEQ()
        if !slot.attached { engine.attach(slot.node); slot.attached = true }
        engine.disconnectNodeOutput(slot.node)
        engine.connect(slot.node, to: engine.mainMixerNode, format: file.processingFormat)
        engine.prepare()
        do { if !engine.isRunning { try engine.start() } } catch { throw AudioError("The audio output could not start.") }
    }

    /// Hands `file` (from `seconds`) to the node as the next segment.
    private func enqueue(_ slot: Slot, file: AVAudioFile, from seconds: Double) {
        let rate = file.processingFormat.sampleRate
        let start = AVAudioFramePosition(max(0, min(seconds, Double(file.length) / rate)) * rate)
        let frames = AVAudioFrameCount(max(0, file.length - start))
        let mine = slot.generation
        slot.segments.append((frames, file))
        slot.node.scheduleSegment(file, startingFrame: start, frameCount: frames, at: nil, completionCallbackType: .dataPlayedBack) { [weak self, weak slot] _ in
            DispatchQueue.main.async {
                MainActor.assumeIsolated {
                    guard let self, let slot, slot.generation == mine else { return }
                    self.segmentEnded(slot)
                }
            }
        }
    }

    private func schedule(_ slot: Slot, from seconds: Double) {
        slot.generation += 1
        slot.segments = []
        guard let file = slot.file else { return }
        let rate = file.processingFormat.sampleRate
        slot.startOffset = max(0, min(seconds, Double(file.length) / rate))
        slot.baseSample = 0
        enqueue(slot, file: file, from: slot.startOffset)
        if slot.segments.first?.frames == 0 { segmentEndedSoon(slot) }
    }

    private func segmentEndedSoon(_ slot: Slot) {
        let mine = slot.generation
        DispatchQueue.main.async { MainActor.assumeIsolated { if slot.generation == mine { self.segmentEnded(slot) } } }
    }

    /// The oldest segment on `slot` has been heard. A queued follower means a gapless join; otherwise the song is over.
    private func segmentEnded(_ slot: Slot) {
        guard slot === cur, !slot.segments.isEmpty else { return }
        let done = slot.segments.removeFirst()
        if let next = slot.segments.first {
            slot.file = next.file
            slot.startOffset = 0
            slot.baseSample += Int64(done.frames)
            pending = nil
            onAdvanced?()
        } else if let p = pending, !p.queuedOnNode {
            beginFade(into: p, length: 0)          // the ticker was late: join now rather than report the end
        } else {
            slot.paused = false
            onFinished?()
        }
    }

    // MARK: Transport

    public func play() {
        guard cur.file != nil else { return }
        if !engine.isRunning { try? engine.start() }
        cur.node.play()
        cur.paused = false
        if let f = fade { f.to.node.play(); f.to.paused = false; f.from.node.play() }
        startTicker()
    }

    public func pause() {
        guard cur.node.isPlaying else { return }
        cur.pausedAt = position
        cur.node.pause(); cur.paused = true
        if let f = fade { f.from.node.pause() }
    }

    public func stop() {
        for s in slots { s.generation += 1; s.node.stop(); s.node.volume = 1; s.file = nil; s.segments = []; s.paused = false; s.pausedAt = 0; s.startOffset = 0; s.baseSample = 0 }
        pending = nil; fade = nil
        ticker?.cancel(); ticker = nil
        active = 0
    }

    public func seek(to seconds: Double) {
        guard cur.file != nil else { return }
        endFade()
        let wasPlaying = cur.node.isPlaying
        cur.node.stop()
        schedule(cur, from: seconds)
        cur.pausedAt = cur.startOffset
        if let p = pending, p.queuedOnNode { enqueue(cur, file: p.file, from: 0) }   // seeking dropped the queued follower
        if wasPlaying { cur.node.play(); cur.paused = false } else { cur.paused = true }
    }

    // MARK: Preload, gapless and crossfade

    public func preload(file url: URL, transition: Transition) throws {
        guard let now = cur.file else { return }
        let next: AVAudioFile
        do { next = try AVAudioFile(forReading: url) } catch { throw AudioError("The next song could not be opened.") }
        cancelPreload()
        let sameFormat = next.processingFormat.sampleRate == now.processingFormat.sampleRate
            && next.processingFormat.channelCount == now.processingFormat.channelCount
        if transition == .gapless, sameFormat {
            enqueue(cur, file: next, from: 0)
            pending = Pending(file: next, transition: transition, queuedOnNode: true)
        } else {
            pending = Pending(file: next, transition: transition, queuedOnNode: false)
            startTicker()
        }
    }

    public func cancelPreload() {
        guard let p = pending else { return }
        pending = nil
        if p.queuedOnNode, cur.file != nil {
            // The node cannot drop one queued segment, so the current song is rescheduled from where it is.
            let at = position, wasPlaying = cur.node.isPlaying
            cur.node.stop()
            schedule(cur, from: at)
            if wasPlaying { cur.node.play() }
        }
    }

    private func startTicker() {
        guard ticker == nil else { return }
        ticker = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(Self.tick))
                self?.step()
            }
        }
    }

    private func step() {
        if var f = fade {
            guard cur.node.isPlaying else { return }
            f.elapsed += Self.tick
            let t = min(f.elapsed / max(f.length, 0.001), 1)
            f.from.node.volume = Float(cos(t * .pi / 2))
            f.to.node.volume = Float(sin(t * .pi / 2))
            if t >= 1 { fade = nil; finish(old: f.from) } else { fade = f }
            return
        }
        guard let p = pending, !p.queuedOnNode, cur.node.isPlaying, cur.file != nil else { return }
        let remaining = duration - position
        let length: Double
        switch p.transition {
        case .crossfade(let s): length = max(0, min(s, remaining, Double(p.file.length) / p.file.processingFormat.sampleRate))
        case .gapless: length = 0
        }
        guard remaining <= max(length, 0.03) else { return }
        beginFade(into: p, length: length)
    }

    /// Starts the preloaded file on the other node; the old node keeps playing and is faded out.
    private func beginFade(into p: Pending, length: Double) {
        let old = cur, new = other
        do { try attach(new, file: p.file) } catch { pending = nil; return }
        new.generation += 1
        new.file = p.file; new.startOffset = 0; new.baseSample = 0; new.paused = false; new.pausedAt = 0
        new.segments = []
        new.node.volume = length > 0 ? 0 : 1
        enqueue(new, file: p.file, from: 0)
        new.node.play()
        old.generation += 1                       // the old node's end must not report "finished"
        active = 1 - active
        pending = nil
        if length > 0 { fade = Fade(from: old, to: new, elapsed: 0, length: length) } else { finish(old: old) }
        onAdvanced?()
    }

    private func finish(old: Slot) {
        old.node.stop(); old.node.volume = 1; old.file = nil; old.segments = []
    }

    private func endFade() {
        guard let f = fade else { return }
        fade = nil
        f.to.node.volume = 1
        finish(old: f.from)
    }
}
