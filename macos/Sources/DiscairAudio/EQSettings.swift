import Foundation

/// A built-in curve. Numbers are the Android ones (`ANDROID_EQ_CONTRACT.md` 5.3, `EqEditor.kt`), in dB, one per band.
public struct EQPreset: Equatable, Sendable, Identifiable {
    public let id: String
    public let label: String
    public let gains: [Double]
}

public let eqBandHz: [Int] = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
public let eqMaxGainDB = 12.0
public let eqStepDB = 0.5

public let eqPresets: [EQPreset] = [
    EQPreset(id: "flat", label: "Flat", gains: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    EQPreset(id: "bass_boost", label: "Bass boost", gains: [6, 5, 4, 2, 0, 0, 0, 0, 0, 0]),
    EQPreset(id: "bass_reduce", label: "Bass reduce", gains: [-6, -5, -4, -2, 0, 0, 0, 0, 0, 0]),
    EQPreset(id: "treble_boost", label: "Treble boost", gains: [0, 0, 0, 0, 0, 1, 2, 4, 5, 6]),
    EQPreset(id: "vocal", label: "Vocal", gains: [-2, -2, -1, 1, 3, 3.5, 3, 1, 0, -1]),
    EQPreset(id: "rock", label: "Rock", gains: [4, 3, 2, 1, -1, -1, 1, 3, 4, 4.5]),
    EQPreset(id: "classical", label: "Classical", gains: [4, 3, 2, 2, -1, -1, 0, 2, 3, 4]),
    EQPreset(id: "electronic", label: "Electronic", gains: [5, 4, 1, 0, -2, 2, 1, 2, 4, 5]),
    // Gentle low and high cut for low listening levels.
    EQPreset(id: "late_night", label: "Late night", gains: [-4, -3, -2, 0, 0, 0, 0, -1, -2, -3]),
]

/// The equalizer as the owner left it: a switch, a preset or the Custom curve, ten band gains and the pre-gain.
/// Moving a band switches the selection to Custom (which keeps the last hand-made curve); presets are never changed.
public struct EQSettings: Equatable, Codable, Sendable {
    public static let customID = "custom"

    public var enabled = false
    public var presetID = "flat"
    public private(set) var gains: [Double] = Array(repeating: 0, count: 10)
    /// The last hand-made curve, kept while a preset is chosen.
    public private(set) var custom: [Double] = Array(repeating: 0, count: 10)
    public var preGainAuto = true
    public var preGainManual = 0.0

    public init() {}

    private enum CodingKeys: String, CodingKey { case enabled, presetID, gains, custom, preGainAuto, preGainManual }

    /// Tolerant: a missing, short or out-of-range value falls back to Flat and off instead of failing.
    public init(from decoder: any Decoder) throws {
        self.init()
        guard let c = try? decoder.container(keyedBy: CodingKeys.self) else { return }
        enabled = (try? c.decode(Bool.self, forKey: .enabled)) ?? false
        let id = (try? c.decode(String.self, forKey: .presetID)) ?? "flat"
        presetID = (id == Self.customID || eqPresets.contains { $0.id == id }) ? id : "flat"
        gains = Self.fix((try? c.decode([Double].self, forKey: .gains)) ?? [])
        custom = Self.fix((try? c.decode([Double].self, forKey: .custom)) ?? [])
        preGainAuto = (try? c.decode(Bool.self, forKey: .preGainAuto)) ?? true
        preGainManual = min(max(Self.step((try? c.decode(Double.self, forKey: .preGainManual)) ?? 0), -eqMaxGainDB), 0)
        if presetID != Self.customID, let p = eqPresets.first(where: { $0.id == presetID }) { gains = p.gains }
    }

    static func step(_ v: Double) -> Double { (v / eqStepDB).rounded() * eqStepDB }
    static func fix(_ v: [Double]) -> [Double] {
        (0..<10).map { i in i < v.count && v[i].isFinite ? min(max(step(v[i]), -eqMaxGainDB), eqMaxGainDB) : 0 }
    }

    public var presetLabel: String { presetID == Self.customID ? "Custom" : (eqPresets.first { $0.id == presetID }?.label ?? "Flat") }

    public mutating func choose(preset id: String) {
        if id == Self.customID { presetID = id; gains = custom; return }
        guard let p = eqPresets.first(where: { $0.id == id }) else { return }
        presetID = id; gains = p.gains
    }

    public mutating func nudge(band: Int, steps: Int) { set(band: band, db: gains[band] + Double(steps) * eqStepDB) }

    public mutating func set(band: Int, db: Double) {
        guard gains.indices.contains(band) else { return }
        gains[band] = min(max(Self.step(db), -eqMaxGainDB), eqMaxGainDB)
        custom = gains
        presetID = Self.customID
    }

    /// Flat, and the Custom slot cleared.
    public mutating func reset() { presetID = "flat"; gains = Array(repeating: 0, count: 10); custom = gains; preGainAuto = true; preGainManual = 0 }

    /// Applied before the filters: automatic is minus the largest boost, so a +6 dB band lowers the signal 6 dB first.
    public var preGainDB: Double { preGainAuto ? -max(0, gains.max() ?? 0) : preGainManual }

    /// What the engine uses: all zero and 0 dB when the equalizer is off (a true bypass).
    public var effective: (gains: [Double], preGain: Double) { enabled ? (gains, preGainDB) : (Array(repeating: 0, count: 10), 0) }
}
