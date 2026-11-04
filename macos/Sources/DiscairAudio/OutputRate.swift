import CoreAudio
import Foundation

/// Picks the device rate for a song (contract 12.6). Pure.
public enum OutputRate {
    /// The file's own rate if the device offers it; else the smallest offered rate that is a whole multiple of it (44.1 kHz
    /// on a 96 kHz-only device is not, so it stays on the current rate and the engine resamples); else nil (leave it).
    public static func target(fileRate: Double, available: [Double]) -> Double? {
        guard fileRate > 0 else { return nil }
        if available.contains(where: { abs($0 - fileRate) < 0.5 }) { return fileRate }
        return available.filter { $0 > fileRate && abs($0 / fileRate - ($0 / fileRate).rounded()) < 0.001 }.min()
    }
}

/// The default output device's nominal rate.
@MainActor
public protocol OutputDeviceRate: AnyObject {
    var current: Double? { get }
    var available: [Double] { get }
    @discardableResult func set(_ rate: Double) -> Bool
}

/// Core Audio. Setting the nominal rate changes the system's output rate until it is set back, so `RateMatcher` restores it.
@MainActor
public final class SystemOutputDevice: OutputDeviceRate {
    public init() {}
    private func device() -> AudioDeviceID? {
        var id = AudioDeviceID(0), size = UInt32(MemoryLayout<AudioDeviceID>.size)
        var a = AudioObjectPropertyAddress(mSelector: kAudioHardwarePropertyDefaultOutputDevice, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
        return AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &a, 0, nil, &size, &id) == noErr && id != 0 ? id : nil
    }
    private var rateAddress: AudioObjectPropertyAddress {
        AudioObjectPropertyAddress(mSelector: kAudioDevicePropertyNominalSampleRate, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    }
    public var current: Double? {
        guard let id = device() else { return nil }
        var rate = Float64(0), size = UInt32(8), a = rateAddress
        return AudioObjectGetPropertyData(id, &a, 0, nil, &size, &rate) == noErr ? rate : nil
    }
    public var available: [Double] {
        guard let id = device() else { return [] }
        var a = AudioObjectPropertyAddress(mSelector: kAudioDevicePropertyAvailableNominalSampleRates, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
        var size = UInt32(0)
        guard AudioObjectGetPropertyDataSize(id, &a, 0, nil, &size) == noErr else { return [] }
        var ranges = [AudioValueRange](repeating: AudioValueRange(), count: Int(size) / MemoryLayout<AudioValueRange>.size)
        guard AudioObjectGetPropertyData(id, &a, 0, nil, &size, &ranges) == noErr else { return [] }
        return ranges.map(\.mMinimum)
    }
    public func set(_ rate: Double) -> Bool {
        guard let id = device() else { return false }
        var r = Float64(rate), a = rateAddress
        return AudioObjectSetPropertyData(id, &a, 0, nil, 8, &r) == noErr
    }
}

/// Moves the device to a song's rate and puts the first rate back on `restore`. Remembers the original only once, so
/// several songs in a row still restore to what the owner had.
@MainActor
public final class RateMatcher {
    private let device: OutputDeviceRate
    private var original: Double?
    public init(device: OutputDeviceRate) { self.device = device }

    /// True if the device rate was changed (the engine then needs a restart).
    @discardableResult
    public func match(fileRate: Double) -> Bool {
        guard let now = device.current, let target = OutputRate.target(fileRate: fileRate, available: device.available) ?? original,
              abs(target - now) > 0.5 else { return false }
        let base = original ?? now
        guard device.set(target) else { return false }
        original = base
        return true
    }

    public func restore() {
        guard let o = original else { return }
        original = nil
        if let now = device.current, abs(now - o) > 0.5 { device.set(o) }
    }
}
