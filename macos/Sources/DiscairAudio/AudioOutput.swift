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
    /// Plays a song that is still downloading: plays what is on disk and follows the file as it grows. `expectedDuration`
    /// is what `duration` reports while it grows.
    func openGrowing(_ download: GrowingDownload, expectedDuration: Double) throws
    /// True while a growing song is open. No preload is accepted then.
    var isGrowing: Bool { get }
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
    /// Switches the output device to each song's sample rate where it offers it (changes the system rate; off by default).
    func setMatchOutputRate(_ on: Bool)
    /// Puts the device rate back to what it was before matching. Called when matching is switched off and at quit.
    func restoreOutputRate()
}

public extension AudioOutput {
    func openGrowing(_ download: GrowingDownload, expectedDuration: Double) throws {
        throw AudioError("Playing while the song downloads is not available.")
    }
    var isGrowing: Bool { false }
    func setMatchOutputRate(_ on: Bool) {}
    func restoreOutputRate() {}
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
        /// `start` is the frame of `file` where the segment begins (0 except for the tail of a growing song).
        var segments: [(frames: AVAudioFrameCount, file: AVAudioFile, start: AVAudioFramePosition)] = []
        /// Frames that can really be decoded, when that is fewer than the file claims (a partial MP3 or FLAC reports the whole song).
        var limit: AVAudioFramePosition?
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
    /// A song still downloading. `scheduledFrames` is how far the file has been handed to the node; `stalled` means the node
    /// was stopped at the end of what was on disk and waits for more bytes.
    private struct Growth {
        let download: GrowingDownload
        let expectedDuration: Double
        var scheduledFrames: AVAudioFramePosition
        var nextCheck: Date
        var stalled: Bool
    }
    private var growth: Growth?
    /// How far ahead of the playhead (seconds) a growing song is kept scheduled, and how close to the playhead the node may
    /// run before it is stopped for lack of data.
    private static let growAhead = 4.0
    /// A stall is detected by the node running dry (`segmentEnded`), never by the ticker, which a busy main thread can delay.
    private static let stallBelow = 1.0
    private static let growCheckEvery: TimeInterval = 0.25
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

    /// During a crossfade the song on screen is still the old one until the fade ends, so these describe the old song.
    private var shown: Slot { fade?.from ?? cur }
    public var duration: Double { growth?.expectedDuration ?? duration(of: shown) }
    public var isGrowing: Bool { growth != nil }
    private func duration(of slot: Slot) -> Double { slot.file.map { Double($0.length) / $0.processingFormat.sampleRate } ?? 0 }
    public var isPlaying: Bool { cur.node.isPlaying }
    /// Test hook: the level of the playing node and of the other one (during a fade, the new and the old song).
    var levelsForTests: (current: Float, other: Float) { (cur.node.volume, other.node.volume) }

    public var position: Double { position(of: shown) }

    private func position(of slot: Slot) -> Double {
        guard let file = slot.file else { return 0 }
        if slot.paused { return slot.pausedAt }
        guard slot.node.isPlaying, let node = slot.node.lastRenderTime, let t = slot.node.playerTime(forNodeTime: node), t.sampleTime >= 0 else {
            return slot.startOffset
        }
        let played = Double(t.sampleTime - slot.baseSample) / file.processingFormat.sampleRate
        return min(max(slot.startOffset + played, 0), duration(of: slot))
    }

    // MARK: Opening

    public func open(file url: URL) throws {
        stop()
        let f: AVAudioFile
        do { f = try AVAudioFile(forReading: url) } catch { throw AudioError("This file could not be opened for playback.") }
        try attach(cur, file: f)
        cur.file = f
        cur.startOffset = 0; cur.baseSample = 0; cur.paused = false; cur.pausedAt = 0
        cur.limit = nil
        schedule(cur, from: 0)
    }

    public func openGrowing(_ download: GrowingDownload, expectedDuration: Double) throws {
        stop()
        let f: AVAudioFile
        do { f = try AVAudioFile(forReading: download.file) } catch { throw AudioError("This file could not be opened for playback.") }
        let readable = Self.readableFrames(f, download: download, known: 0)
        guard readable > 0 else { throw AudioError("This file could not be opened for playback.") }
        try attach(cur, file: f)
        cur.file = f
        cur.startOffset = 0; cur.baseSample = 0; cur.paused = false; cur.pausedAt = 0
        cur.limit = readable
        growth = Growth(download: download, expectedDuration: expectedDuration, scheduledFrames: readable, nextCheck: .distantPast, stalled: false)
        schedule(cur, from: 0)
    }

    private var matcher: RateMatcher?
    public func setMatchOutputRate(_ on: Bool) {
        if on { matcher = matcher ?? RateMatcher(device: SystemOutputDevice()) } else { matcher?.restore(); matcher = nil }
    }
    public func restoreOutputRate() { matcher?.restore() }

    private func attach(_ slot: Slot, file: AVAudioFile) throws {
        wireEQ()
        // Only between songs: `open` has just stopped the nodes. A device rate change needs the engine stopped first.
        if let matcher, !engine.isRunning || !slots.contains(where: { $0.node.isPlaying }) {
            let wasRunning = engine.isRunning
            if wasRunning { engine.stop() }
            let changed = matcher.match(fileRate: file.processingFormat.sampleRate)
            if changed { Thread.sleep(forTimeInterval: 0.15) }       // the device takes a moment to settle
        }
        if !slot.attached { engine.attach(slot.node); slot.attached = true }
        engine.disconnectNodeOutput(slot.node)
        engine.connect(slot.node, to: engine.mainMixerNode, format: file.processingFormat)
        engine.prepare()
        do { if !engine.isRunning { try engine.start() } } catch { throw AudioError("The audio output could not start.") }
    }

    /// Hands `file` (from `seconds`) to the node as the next segment.
    private func enqueue(_ slot: Slot, file: AVAudioFile, from seconds: Double) {
        let rate = file.processingFormat.sampleRate
        let start = AVAudioFramePosition(max(0, min(seconds, Double(slot.limit ?? file.length) / rate)) * rate)
        enqueueFrames(slot, file: file, startFrame: start)
    }

    private func enqueueFrames(_ slot: Slot, file: AVAudioFile, startFrame start: AVAudioFramePosition) {
        let frames = AVAudioFrameCount(max(0, (slot.limit ?? file.length) - start))
        let mine = slot.generation
        slot.segments.append((frames, file, start))
        guard frames > 0 else { return }          // the node refuses an empty segment; the caller ends the song
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
        slot.startOffset = max(0, min(seconds, Double(slot.limit ?? file.length) / rate))
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
            slot.startOffset = Double(next.start) / next.file.processingFormat.sampleRate
            slot.baseSample += Int64(done.frames)
            pending = nil
            onAdvanced?()
        } else if let p = pending, !p.queuedOnNode {
            beginFade(into: p, length: 0)          // the ticker was late: join now rather than report the end
        } else if var g = growth, !(g.download.isComplete || g.download.failure != nil) || g.scheduledFrames < Self.readableNow(g.download, known: g.scheduledFrames) {
            // The node ran dry at the end of what was on disk. This is decided here, from the completion callback, not on the
            // ticker, so a starved main thread cannot turn a stall into the end of the song. The ticker resumes it.
            slot.node.stop()
            slot.startOffset = Double(done.start + AVAudioFramePosition(done.frames)) / done.file.processingFormat.sampleRate
            slot.baseSample = 0
            g.stalled = true
            g.nextCheck = .distantPast
            growth = g
        } else {
            slot.paused = false
            growth = nil                 // a growing song is over once its last segment has played
            onFinished?()
        }
    }

    // MARK: Growing song

    /// Keeps a growing song scheduled `growAhead` seconds past the playhead. Runs on the ticker, at most every 0.25 s.
    /// Each new tail is appended to the same node as a gapless join. When the download is behind the playhead, the node
    /// runs dry at the end of what is on disk (see `segmentEnded`) and is restarted from that point once more bytes arrive.
    private func feedGrowth() {
        guard var g = growth, let file = cur.file, fade == nil else { return }
        let now = Date()
        guard now >= g.nextCheck else { return }
        let rate = file.processingFormat.sampleRate
        let remaining = Double(g.scheduledFrames) / rate - position(of: cur)
        g.nextCheck = now.addingTimeInterval(Self.growCheckEvery)
        guard remaining < Self.growAhead else { growth = g; return }
        let ended = g.download.isComplete || g.download.failure != nil      // read before the file is opened
        let fresh = try? AVAudioFile(forReading: g.download.file)
        let readable = fresh.map { Self.readableFrames($0, download: g.download, known: g.scheduledFrames) } ?? 0
        if let fresh, readable > g.scheduledFrames {
            cur.limit = readable
            if g.stalled {
                resumeGrowth(fresh, readable, &g)
            } else {
                enqueueFrames(cur, file: fresh, startFrame: g.scheduledFrames)
                g.scheduledFrames = readable
            }
        } else if ended {
            // Nothing more is coming. A stopped node plays out what it has, so it is restarted for the last part.
            if g.stalled { resumeGrowth(file, g.scheduledFrames, &g) }
            growth = nil
            return
        }
        growth = g
    }

    /// Frames of `file` that decode now. A partial MP3 or FLAC reports the length of the whole song from its header, and
    /// scheduling that many frames makes the node read past the data. So the end is found by test reads (a read past the
    /// data throws; `known` frames are known to be good). A finished download, and Ogg Opus (its length comes from the pages
    /// on disk, and seeking a partial Opus file raises an Objective-C exception that Swift cannot catch), are taken as they are.
    static func readableFrames(_ file: AVAudioFile, download: GrowingDownload, known: AVAudioFramePosition) -> AVAudioFramePosition {
        if download.isComplete { return file.length }
        let ext = download.file.pathExtension.lowercased()
        if ext == "opus" || ext == "ogg" { return file.length }
        guard let buffer = AVAudioPCMBuffer(pcmFormat: file.processingFormat, frameCapacity: 1) else { return known }
        func decodes(_ frame: AVAudioFramePosition) -> Bool {
            file.framePosition = frame - 1
            buffer.frameLength = 0
            return (try? file.read(into: buffer, frameCount: 1)) != nil && buffer.frameLength > 0
        }
        var hi = file.length
        if hi <= known || decodes(hi) { return hi }
        var lo = known
        let step = AVAudioFramePosition(file.processingFormat.sampleRate / 10)
        while hi - lo > step {
            let mid = (lo + hi) / 2
            if decodes(mid) { lo = mid } else { hi = mid }
        }
        return lo
    }

    static func readableNow(_ download: GrowingDownload, known: AVAudioFramePosition) -> AVAudioFramePosition {
        guard let f = try? AVAudioFile(forReading: download.file) else { return known }
        return readableFrames(f, download: download, known: known)
    }

    /// Restarts a stalled node from where it stopped, on a file that now has more frames.
    private func resumeGrowth(_ file: AVAudioFile, _ readable: AVAudioFramePosition, _ g: inout Growth) {
        let at = cur.startOffset
        cur.file = file
        cur.limit = readable
        schedule(cur, from: at)
        g.scheduledFrames = readable
        g.stalled = false
        if !cur.paused { cur.node.play() }
    }

    /// Seeks inside a growing song. A target past what is on disk is pulled back to just before its end.
    private func seekGrowing(to seconds: Double) {
        guard var g = growth, let old = cur.file else { return }
        let fresh = (try? AVAudioFile(forReading: g.download.file)) ?? old
        let readable = max(g.scheduledFrames, Self.readableFrames(fresh, download: g.download, known: g.scheduledFrames))
        let rate = fresh.processingFormat.sampleRate
        let at = min(max(0, seconds), max(0, Double(readable) / rate - Self.stallBelow))
        let wasPlaying = !cur.paused
        cur.node.stop()
        cur.file = fresh
        cur.limit = readable
        schedule(cur, from: at)
        g.scheduledFrames = readable
        g.stalled = false
        cur.pausedAt = cur.startOffset
        cur.paused = !wasPlaying
        if wasPlaying { cur.node.play() }
        growth = g
    }

    // MARK: Transport

    public func play() {
        guard cur.file != nil else { return }
        if !engine.isRunning { try? engine.start() }
        cur.paused = false
        // A stalled node has nothing scheduled: it starts again when more of the file is on disk (`resumeGrowth`).
        if growth?.stalled != true { cur.node.play() }
        if let f = fade { f.to.node.play(); f.to.paused = false; f.from.node.play(); f.from.paused = false }
        startTicker()
    }

    public func pause() {
        if growth?.stalled == true, !cur.paused {
            // The node is stopped at the end of what was on disk, so there is nothing to pause; remember the wish so the
            // song stays paused when the rest of the file arrives.
            cur.pausedAt = cur.startOffset
            cur.paused = true
            return
        }
        guard cur.node.isPlaying else { return }
        cur.pausedAt = position(of: cur)
        cur.node.pause(); cur.paused = true
        if let f = fade { f.from.pausedAt = position(of: f.from); f.from.node.pause(); f.from.paused = true }
    }

    public func stop() {
        for s in slots { s.generation += 1; s.node.stop(); s.node.volume = 1; s.file = nil; s.segments = []; s.paused = false; s.pausedAt = 0; s.startOffset = 0; s.baseSample = 0 }
        pending = nil; fade = nil; growth = nil
        for s in slots { s.limit = nil }
        ticker?.cancel(); ticker = nil
        active = 0
    }

    public func seek(to seconds: Double) {
        guard cur.file != nil else { return }
        if growth != nil { seekGrowing(to: seconds); return }
        if fade != nil { endFade(); return }      // the bar belongs to the old song, which is now over: the new one carries on
        let wasPlaying = cur.node.isPlaying
        cur.node.stop()
        schedule(cur, from: seconds)
        cur.pausedAt = cur.startOffset
        if let p = pending, p.queuedOnNode { enqueue(cur, file: p.file, from: 0) }   // seeking dropped the queued follower
        if wasPlaying { cur.node.play(); cur.paused = false } else { cur.paused = true }
    }

    // MARK: Preload, gapless and crossfade

    public func preload(file url: URL, transition: Transition) throws {
        guard !isGrowing else { throw AudioError("The next song waits until this one has downloaded.") }
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
        if growth != nil { feedGrowth(); return }
        if var f = fade {
            guard cur.node.isPlaying else { return }
            // The audio clock decides how far the fade is, not the count of ticks: a busy main thread delays ticks, and a
            // fade that lags the audio would leave the old song to end before its level reached zero.
            f.elapsed = max(f.elapsed + Self.tick, position(of: f.to))
            let t = min(f.elapsed / max(f.length, 0.001), 1)
            f.from.node.volume = Float(cos(t * .pi / 2))
            f.to.node.volume = Float(sin(t * .pi / 2))
            if t >= 1 { fade = nil; finish(old: f.from); onAdvanced?() } else { fade = f }
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
        if length > 0 { fade = Fade(from: old, to: new, elapsed: 0, length: length) } else { finish(old: old); onAdvanced?() }
    }

    private func finish(old: Slot) {
        old.node.stop(); old.node.volume = 1; old.file = nil; old.segments = []
    }

    private func endFade() {
        guard let f = fade else { return }
        fade = nil
        f.to.node.volume = 1
        finish(old: f.from)
        onAdvanced?()
    }
}
