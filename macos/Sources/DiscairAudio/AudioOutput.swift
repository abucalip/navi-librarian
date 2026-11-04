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
}

public struct AudioError: Error, Equatable, Sendable, CustomStringConvertible {
    public let description: String
    public init(_ description: String) { self.description = description }
}

/// `AVAudioEngine` with one player node. Whole file, no crossfade or EQ yet (later slices: contract section 12).
/// A generation number marks which `open` or `seek` a completion belongs to, so a stopped or replaced file never
/// reports "finished".
@MainActor
public final class EngineOutput: AudioOutput {
    private let engine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private var file: AVAudioFile?
    private var generation = 0
    /// Seconds into the file where the current schedule began.
    private var startOffset: Double = 0
    private var paused = false
    private var attached = false

    public var onFinished: (() -> Void)?

    public init() {}

    public var duration: Double {
        guard let file else { return 0 }
        return Double(file.length) / file.processingFormat.sampleRate
    }

    public var isPlaying: Bool { player.isPlaying }

    public var position: Double {
        guard let file else { return 0 }
        guard player.isPlaying || paused, let node = player.lastRenderTime, let t = player.playerTime(forNodeTime: node), t.sampleTime >= 0 else {
            return paused ? pausedAt : startOffset
        }
        let played = Double(t.sampleTime) / file.processingFormat.sampleRate
        return min(startOffset + played, duration)
    }
    private var pausedAt: Double = 0

    public func open(file url: URL) throws {
        stop()
        let f: AVAudioFile
        do { f = try AVAudioFile(forReading: url) } catch { throw AudioError("This file could not be opened for playback.") }
        file = f
        if !attached { engine.attach(player); attached = true }
        engine.disconnectNodeOutput(player)
        engine.connect(player, to: engine.mainMixerNode, format: f.processingFormat)
        engine.prepare()
        do { if !engine.isRunning { try engine.start() } } catch { throw AudioError("The audio output could not start.") }
        startOffset = 0; pausedAt = 0; paused = false
        schedule(from: 0)
    }

    private func schedule(from seconds: Double) {
        guard let file else { return }
        generation += 1
        let mine = generation
        let rate = file.processingFormat.sampleRate
        let start = AVAudioFramePosition(max(0, min(seconds, duration)) * rate)
        let frames = AVAudioFrameCount(max(0, file.length - start))
        startOffset = Double(start) / rate
        guard frames > 0 else { DispatchQueue.main.async { MainActor.assumeIsolated { if self.generation == mine { self.onFinished?() } } }; return }
        player.scheduleSegment(file, startingFrame: start, frameCount: frames, at: nil, completionCallbackType: .dataPlayedBack) { [weak self] _ in
            DispatchQueue.main.async {
                MainActor.assumeIsolated {
                    guard let self, self.generation == mine else { return }
                    self.paused = false
                    self.onFinished?()
                }
            }
        }
    }

    public func play() {
        guard file != nil else { return }
        if !engine.isRunning { try? engine.start() }
        player.play()
        paused = false
    }

    public func pause() {
        guard player.isPlaying else { return }
        pausedAt = position
        player.pause()
        paused = true
    }

    public func stop() {
        generation += 1                      // the cancelled schedule must not report a finish
        player.stop()
        file = nil
        paused = false; pausedAt = 0; startOffset = 0
    }

    public func seek(to seconds: Double) {
        guard file != nil else { return }
        let wasPlaying = player.isPlaying
        player.stop()
        schedule(from: seconds)
        pausedAt = startOffset
        if wasPlaying { player.play(); paused = false } else { paused = true }
    }
}
