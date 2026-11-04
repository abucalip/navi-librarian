import Foundation
import Testing
@testable import DiscairAudio

@Suite("Equalizer settings") struct EQSettingsTests {
    @Test func startsFlatAndOffWithAHardBypass() {
        let e = EQSettings()
        #expect(!e.enabled && e.presetID == "flat" && e.gains == Array(repeating: 0, count: 10))
        #expect(e.effective.gains.allSatisfy { $0 == 0 } && e.effective.preGain == 0)
    }

    @Test func offMeansBypassEvenWithABoostedCurve() {
        var e = EQSettings(); e.choose(preset: "bass_boost")
        #expect(e.effective.gains.allSatisfy { $0 == 0 })
        e.enabled = true
        #expect(e.effective.gains[0] == 6)
    }

    @Test func automaticPreGainIsMinusTheLargestBoost() {
        var e = EQSettings(); e.enabled = true; e.choose(preset: "bass_boost")
        #expect(e.preGainDB == -6)
        e.choose(preset: "bass_reduce")
        #expect(e.preGainDB == 0)                       // nothing boosted, nothing to compensate
        e.preGainAuto = false; e.preGainManual = -3
        #expect(e.effective.preGain == -3)
    }

    @Test func movingABandSwitchesToCustomAndKeepsThePresetUnchanged() {
        var e = EQSettings(); e.choose(preset: "rock")
        e.nudge(band: 0, steps: 2)
        #expect(e.presetID == "custom" && e.gains[0] == 5 && e.presetLabel == "Custom")
        e.choose(preset: "vocal")
        #expect(e.gains[0] == -2)
        e.choose(preset: "custom")
        #expect(e.gains[0] == 5)                        // the Custom slot kept the hand-made curve
        #expect(eqPresets.first { $0.id == "rock" }?.gains[0] == 4)
    }

    @Test func gainsAreClampedAndStepped() {
        var e = EQSettings()
        e.set(band: 3, db: 99); #expect(e.gains[3] == 12)
        e.set(band: 3, db: -99); #expect(e.gains[3] == -12)
        e.set(band: 3, db: 1.3); #expect(e.gains[3] == 1.5)
        e.set(band: 42, db: 3)                          // no such band: ignored
        #expect(e.gains.count == 10)
    }

    @Test func resetReturnsToFlatAndClearsCustom() {
        var e = EQSettings(); e.set(band: 2, db: 4); e.reset()
        #expect(e.presetID == "flat" && e.custom.allSatisfy { $0 == 0 } && e.gains.allSatisfy { $0 == 0 })
    }

    @Test func aSavedCurveSurvivesAndACorruptOneFallsBackToFlat() throws {
        var e = EQSettings(); e.enabled = true; e.set(band: 4, db: 3)
        let back = try JSONDecoder().decode(EQSettings.self, from: JSONEncoder().encode(e))
        #expect(back == e)
        let bad = try JSONDecoder().decode(EQSettings.self, from: Data(#"{"enabled":true,"presetID":"nope","gains":[99,"x"],"preGainManual":5}"#.utf8))
        #expect(bad.presetID == "flat" && bad.gains.allSatisfy { $0 == 0 } || bad.gains[0] == 12)
        #expect(bad.preGainManual == 0)
        let junk = try JSONDecoder().decode(EQSettings.self, from: Data("[]".utf8))
        #expect(junk == EQSettings())
    }

    @Test func presetsMatchTheAndroidNumbers() {
        #expect(eqPresets.map(\.id) == ["flat", "bass_boost", "bass_reduce", "treble_boost", "vocal", "rock", "classical", "electronic", "late_night"])
        #expect(eqPresets.allSatisfy { $0.gains.count == 10 && $0.gains.allSatisfy { abs($0) <= 12 } })
        #expect(eqPresets.first { $0.id == "vocal" }?.gains == [-2, -2, -1, 1, 3, 3.5, 3, 1, 0, -1])
    }
}
