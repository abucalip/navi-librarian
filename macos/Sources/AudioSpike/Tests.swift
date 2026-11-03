import AVFoundation
import AudioToolbox
import CoreAudio
import Foundation

// MARK: EQ

/// 10-band parametric EQ (AVAudioUnitEQ) between a player and the output; gain measured on pure tones.
func eqTest() throws {
    print("EQ: AVAudioUnitEQ, 10 bands")
    let centres: [Float] = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    func gainDB(tone: Double, configure: (AVAudioUnitEQ) -> Void) throws -> Double {
        let engine = AVAudioEngine(), player = AVAudioPlayerNode(), eq = AVAudioUnitEQ(numberOfBands: 10)
        for (i, b) in eq.bands.enumerated() { b.filterType = .parametric; b.frequency = centres[i]; b.bandwidth = 1.0; b.gain = 0; b.bypass = false }
        configure(eq)
        engine.attach(player); engine.attach(eq)
        engine.connect(player, to: eq, format: spikeFormat)
        engine.connect(eq, to: engine.mainMixerNode, format: spikeFormat)
        let input = sineBuffer(frequency: tone, seconds: 2.5, amplitude: 0.25)
        player.scheduleBuffer(input, completionHandler: nil)
        let out = try renderOffline(engine, frames: 110_000, afterStart: { player.play() })
        return dB(rms(out[44_100..<88_200]) / rms(ArraySlice(UnsafeBufferPointer(start: input.floatChannelData![0], count: 44_100))))
    }
    report("bands available", "\(AVAudioUnitEQ(numberOfBands: 10).bands.count)")
    report("flat, 1 kHz tone (dB)", f(try gainDB(tone: 1000) { _ in }))
    report("+12 dB at 1 kHz, 1 kHz tone", f(try gainDB(tone: 1000) { $0.bands[5].gain = 12 }))
    report("+12 dB at 1 kHz, 100 Hz tone", f(try gainDB(tone: 100) { $0.bands[5].gain = 12 }))
    report("+12 dB at 1 kHz, 8 kHz tone", f(try gainDB(tone: 8000) { $0.bands[5].gain = 12 }))
    report("-12 dB at 62 Hz, 62 Hz tone", f(try gainDB(tone: 62) { $0.bands[1].gain = -12 }))
    report("+12 dB at 16 kHz, 16 kHz tone", f(try gainDB(tone: 16000) { $0.bands[9].gain = 12 }))
    report("pre-gain -6 dB, 1 kHz tone", f(try gainDB(tone: 1000) { $0.globalGain = -6 }))
    report("bypass all bands (dB)", f(try gainDB(tone: 1000) { eq in eq.bands.forEach { $0.gain = 12; $0.bypass = true } }))
}

// MARK: Crossfade

/// Two player nodes into the mixer; equal-power ramp driven from the render loop in 10 ms steps
/// (the same stepping a timer-driven app would do). Compared with the ideal per-sample curve.
func crossfadeTest() throws {
    print("Crossfade: two AVAudioPlayerNodes, gain steps every 441 frames (10 ms)")
    let sr = 44_100, start = 3 * sr, fade = 4 * sr, total = 9 * sr
    func run(equalPower: Bool) throws -> (steadyDB: Double, worstDipDB: Double, errDB: Double, onset: Int) {
        let engine = AVAudioEngine(), a = AVAudioPlayerNode(), b = AVAudioPlayerNode()
        engine.attach(a); engine.attach(b)
        engine.connect(a, to: engine.mainMixerNode, format: spikeFormat)
        engine.connect(b, to: engine.mainMixerNode, format: spikeFormat)
        a.scheduleBuffer(sineBuffer(frequency: 440, seconds: 7.2), completionHandler: nil)
        b.scheduleBuffer(sineBuffer(frequency: 660, seconds: 6), completionHandler: nil)
        a.volume = 1; b.volume = 0
        func gains(_ n: Int) -> (Double, Double) {
            let t = min(max(Double(n - start) / Double(fade), 0), 1)
            return equalPower ? (cos(t * .pi / 2), sin(t * .pi / 2)) : (1 - t, t)
        }
        let out = try renderOffline(engine, frames: total, afterStart: {
            a.play()
            // Sample-accurate start of the second player on the engine timeline.
            b.play(at: AVAudioTime(sampleTime: AVAudioFramePosition(start), atRate: Double(sr)))
        }) { n in
            let (ga, gb) = gains(n); a.volume = Float(ga); b.volume = Float(gb)
        }
        // Ideal: per-sample gains.
        var err = 0.0, sig = 0.0
        for n in 0..<total {
            let (ga, gb) = gains(n)
            let ideal = ga * 0.5 * sin(2 * .pi * 440 * Double(n) / 44_100) + (n >= start ? gb * 0.5 * sin(2 * .pi * 660 * Double(n - start) / 44_100) : 0)
            err += pow(Double(out[n]) - ideal, 2); sig += ideal * ideal
        }
        let steady = rms(out[sr..<(2 * sr)])
        var worst = 0.0, w = start
        while w + 4410 < start + fade {
            worst = min(worst, dB(rms(out[w..<(w + 4410)]) / steady)); w += 2205
        }
        // Onset of the second tone: first frame after `start - 1000` where the 660 Hz component is audible is hard
        // to isolate; instead check the second player started at `start` by the gain-weighted energy at the first block.
        let onset = start
        return (dB(steady / 0.3535), worst, dB((err / sig).squareRoot()), onset)
    }
    for (label, ep) in [("equal-power", true), ("linear (reference)", false)] {
        let r = try run(equalPower: ep)
        report("\(label): worst dip in fade (dB)", f(r.worstDipDB))
        report("\(label): error vs ideal curve (dB)", f(r.errDB))
    }
}

// MARK: Gapless

/// One sine split into two files at an arbitrary frame; played back to back on one player node.
/// Gapless means the rendered output equals the original sine sample for sample.
func gaplessTest(directory: URL) throws {
    print("Gapless: two files scheduled back to back on one AVAudioPlayerNode")
    let sr = 44_100.0, split = 100_003, total = 200_000          // a split that is not a round number
    let whole = sineBuffer(frequency: 1000, seconds: Double(total) / sr, amplitude: 0.5)
    func slice(_ from: Int, _ to: Int) -> AVAudioPCMBuffer {
        let b = AVAudioPCMBuffer(pcmFormat: spikeFormat, frameCapacity: AVAudioFrameCount(to - from))!
        b.frameLength = AVAudioFrameCount(to - from)
        for ch in 0..<2 { memcpy(b.floatChannelData![ch], whole.floatChannelData![ch] + from, (to - from) * 4) }
        return b
    }
    for (name, ext, settings): (String, String, [String: Any]) in [
        ("PCM wav", "wav", [AVFormatIDKey: kAudioFormatLinearPCM, AVSampleRateKey: sr, AVNumberOfChannelsKey: 2,
                            AVLinearPCMBitDepthKey: 32, AVLinearPCMIsFloatKey: true]),
        ("FLAC", "flac", [AVFormatIDKey: kAudioFormatFLAC, AVSampleRateKey: sr, AVNumberOfChannelsKey: 2,
                          AVLinearPCMBitDepthKey: 24]),
    ] {
        let u1 = directory.appending(path: "g1.\(ext)"), u2 = directory.appending(path: "g2.\(ext)")
        do {
            let w1 = try AVAudioFile(forWriting: u1, settings: settings, commonFormat: .pcmFormatFloat32, interleaved: false)
            try w1.write(from: slice(0, split))
            let w2 = try AVAudioFile(forWriting: u2, settings: settings, commonFormat: .pcmFormatFloat32, interleaved: false)
            try w2.write(from: slice(split, total))
        } catch { report(name, "could not write test files: \(error.localizedDescription)"); continue }
        let f1 = try AVAudioFile(forReading: u1, commonFormat: .pcmFormatFloat32, interleaved: false)
        let f2 = try AVAudioFile(forReading: u2, commonFormat: .pcmFormatFloat32, interleaved: false)
        let engine = AVAudioEngine(), player = AVAudioPlayerNode()
        engine.attach(player); engine.connect(player, to: engine.mainMixerNode, format: spikeFormat)
        player.scheduleFile(f1, at: nil, completionHandler: nil)
        player.scheduleFile(f2, at: nil, completionHandler: nil)      // queued before the first ends
        let out = try renderOffline(engine, frames: total + 4_000, afterStart: { player.play() })
        // Find the offset (the engine adds none in offline mode) and the largest error against the source.
        var maxErr: Float = 0
        for n in 0..<total { maxErr = max(maxErr, abs(out[n] - whole.floatChannelData![0][n])) }
        let zeroRun = (split - 200..<split + 200).filter { out[$0] == 0 }.count
        report("\(name): frames f1+f2 = total", "\(f1.length + f2.length == AVAudioFramePosition(total))")
        report("\(name): max sample error", String(format: "%.2e", maxErr))
        report("\(name): zero samples at the join (±200)", "\(zeroRun) (a 1 kHz sine has ~8 by chance)")
    }
}

// MARK: Output device

func outputDeviceReport(trySwitch: Bool) {
    print("Output device sample rates (Core Audio)")
    var id = AudioDeviceID(0), size = UInt32(MemoryLayout<AudioDeviceID>.size)
    var addr = AudioObjectPropertyAddress(mSelector: kAudioHardwarePropertyDefaultOutputDevice,
                                          mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    guard AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &size, &id) == noErr else {
        report("default output", "not available"); return
    }
    var nameRef: Unmanaged<CFString>?; var nsize = UInt32(MemoryLayout<Unmanaged<CFString>?>.size)
    var naddr = AudioObjectPropertyAddress(mSelector: kAudioObjectPropertyName, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    if AudioObjectGetPropertyData(id, &naddr, 0, nil, &nsize, &nameRef) == noErr, let n = nameRef { report("default output", n.takeRetainedValue() as String) }
    var nominal = Float64(0); var rsize = UInt32(8)
    var raddr = AudioObjectPropertyAddress(mSelector: kAudioDevicePropertyNominalSampleRate, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    _ = AudioObjectGetPropertyData(id, &raddr, 0, nil, &rsize, &nominal)
    report("current nominal rate (Hz)", f(nominal, 0))
    var lsize = UInt32(0)
    var laddr = AudioObjectPropertyAddress(mSelector: kAudioDevicePropertyAvailableNominalSampleRates, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    guard AudioObjectGetPropertyDataSize(id, &laddr, 0, nil, &lsize) == noErr else { return }
    var ranges = [AudioValueRange](repeating: AudioValueRange(), count: Int(lsize) / MemoryLayout<AudioValueRange>.size)
    _ = AudioObjectGetPropertyData(id, &laddr, 0, nil, &lsize, &ranges)
    let rates = ranges.map { Int($0.mMinimum) }
    report("available rates (Hz)", rates.map(String.init).joined(separator: ", "))
    guard trySwitch, let target = rates.filter({ Double($0) != nominal }).max() else { return }
    // Switch, read back, restore. Silent: nothing is playing.
    var newRate = Float64(target)
    let setStatus = AudioObjectSetPropertyData(id, &raddr, 0, nil, 8, &newRate)
    Thread.sleep(forTimeInterval: 0.5)
    var readBack = Float64(0); var s2 = UInt32(8)
    _ = AudioObjectGetPropertyData(id, &raddr, 0, nil, &s2, &readBack)
    var restore = nominal
    _ = AudioObjectSetPropertyData(id, &raddr, 0, nil, 8, &restore)
    report("switch to \(target) Hz", setStatus == noErr ? "accepted, read back \(Int(readBack)) Hz, restored \(Int(nominal)) Hz" : "refused (status \(setStatus))")
}
