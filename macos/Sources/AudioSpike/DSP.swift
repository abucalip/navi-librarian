import AVFoundation
import Foundation

/// Helpers for the offline (manual rendering) measurements. Offline rendering is deterministic and silent:
/// nothing is played through the speakers.

let spikeFormat = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: 44_100, channels: 2, interleaved: false)!

func sineBuffer(frequency: Double, seconds: Double, amplitude: Float = 0.5, format: AVAudioFormat = spikeFormat,
                startFrame: Int = 0) -> AVAudioPCMBuffer {
    let frames = AVAudioFrameCount(seconds * format.sampleRate)
    let buf = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames)!
    buf.frameLength = frames
    for ch in 0..<Int(format.channelCount) {
        let p = buf.floatChannelData![ch]
        for i in 0..<Int(frames) {
            p[i] = amplitude * Float(sin(2 * .pi * frequency * Double(startFrame + i) / format.sampleRate))
        }
    }
    return buf
}

func rms(_ x: ArraySlice<Float>) -> Double {
    guard !x.isEmpty else { return 0 }
    return (x.reduce(0.0) { $0 + Double($1) * Double($1) } / Double(x.count)).squareRoot()
}

func dB(_ ratio: Double) -> Double { 20 * log10(max(ratio, 1e-12)) }

/// Runs the engine in offline mode for `frames` frames and returns the left channel. `perBlock` is called before
/// each block with the frame position, and may start players or change gains.
func renderOffline(_ engine: AVAudioEngine, frames: Int, block: Int = 441,
                   afterStart: () -> Void = {}, perBlock: ((Int) -> Void)? = nil) throws -> [Float] {
    try engine.enableManualRenderingMode(.offline, format: spikeFormat, maximumFrameCount: 4096)
    try engine.start()
    defer { engine.stop() }
    afterStart()   // players can only be started once the engine runs
    let out = AVAudioPCMBuffer(pcmFormat: spikeFormat, frameCapacity: AVAudioFrameCount(block))!
    var left: [Float] = []; left.reserveCapacity(frames)
    var done = 0
    while done < frames {
        perBlock?(done)
        let n = AVAudioFrameCount(min(block, frames - done))
        let status = try engine.renderOffline(n, to: out)
        guard status == .success else { throw SpikeError("offline render status \(status.rawValue)") }
        left += UnsafeBufferPointer(start: out.floatChannelData![0], count: Int(out.frameLength))
        done += Int(out.frameLength)
    }
    return left
}

struct SpikeError: Error, CustomStringConvertible { let description: String; init(_ d: String) { description = d } }

func report(_ name: String, _ value: String) { print("  \(name.padding(toLength: 46, withPad: " ", startingAt: 0)) \(value)") }
func f(_ v: Double, _ digits: Int = 2) -> String { String(format: "%.\(digits)f", v) }
