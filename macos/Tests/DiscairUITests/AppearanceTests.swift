import Foundation
import Testing
@testable import DiscairUI

/// Day and Night, the accent hue and the Appearance tab's model. The model tests pass their own `publish`, so they never
/// touch the shared palette that the screenshot and token tests read.
@MainActor
struct AppearanceTests {
    private func defaults() -> UserDefaults { UserDefaults(suiteName: "discair-appearance-\(UUID().uuidString)")! }

    private func ratio(_ pair: (name: String, text: CURGB, ground: CURGB)) -> Double { pair.text.contrast(with: pair.ground) }

    @Test func cupertinoIsTheOnlyTheme() {
        #expect(ThemeID.allCases == [.cupertino])
        #expect(ThemeRegistry.theme(.cupertino).name == "Cupertino")
    }

    @Test func dayIsTheShippedPaletteAndNightStartsOnCoral() {
        #expect(CUPalette.make(.day, accentHue: nil) == CUPalette.day)
        #expect(CUPalette.day.accent == CURGB(0xD61F4A) && CUPalette.day.content == CURGB(0xFFFFFF))
        #expect(CUPalette.night.content == CURGB(0x0B0B0D))
        #expect(CUPalette.night.accent == CURGB(0xFF7A8F))
        #expect(CUPalette.night.isNight && !CUPalette.day.isNight)
    }

    @Test func nightPairsReachAA() {
        for pair in CUPalette.night.contrastPairs {
            #expect(ratio(pair) >= 4.5, "night \(pair.name) is \(ratio(pair).formatted(.number.precision(.fractionLength(2)))):1")
        }
    }

    @Test(arguments: AppearanceMode.allCases)
    func everyHueOfTheSliderReachesAA(mode: AppearanceMode) {
        for degrees in stride(from: 0.0, through: 360.0, by: 5.0) {
            for pair in CUPalette.make(mode, accentHue: degrees).contrastPairs {
                #expect(ratio(pair) >= 4.5, "\(mode) hue \(degrees) \(pair.name) is \(ratio(pair).formatted(.number.precision(.fractionLength(2)))):1")
            }
        }
    }

    @Test func aHueChangesOnlyTheAccentAndTheHeatRamp() {
        let base = CUPalette.make(.night, accentHue: nil)
        var custom = CUPalette.make(.night, accentHue: 200)
        #expect(custom.accent != base.accent && custom.heat != base.heat)
        custom.accent = base.accent; custom.accentStrong = base.accentStrong; custom.accentTint = base.accentTint; custom.heat = base.heat
        #expect(custom == base)
    }

    @Test func hueRoundTripsThroughHSB() {
        for hue in stride(from: 0.0, to: 360.0, by: 15.0) {
            let c = CURGB(hue: hue, saturation: 0.8, brightness: 0.9)
            #expect(abs(c.hsb.hue - hue) < 1.5, "hue \(hue) came back as \(c.hsb.hue)")
        }
        #expect(CURGB(hue: 360, saturation: 1, brightness: 1) == CURGB(0xFF0000))
    }

    @Test func theSliderStartsAtTheDefaultHueOfTheMode() {
        var seen: [CUPalette] = []
        let m = AppearanceModel(defaults: defaults(), publish: { seen.append($0) })
        #expect(seen.isEmpty, "the shipped look publishes nothing")
        #expect(m.mode == .day && m.isDefaultAccent)
        #expect(abs(m.sliderHue - CURGB(0xD61F4A).hsb.hue) < 0.01)
        m.setMode(.night)
        #expect(abs(m.sliderHue - CURGB(0xFF7A8F).hsb.hue) < 0.01)
    }

    @Test func choicesArePublishedSavedAndRestored() {
        let d = defaults()
        var seen: [CUPalette] = []
        let m = AppearanceModel(defaults: d, publish: { seen.append($0) })
        m.setMode(.night)
        m.setAccentHue(200)
        #expect(seen.count == 2 && seen[0].isNight && seen[1].accent == CUPalette.make(.night, accentHue: 200).accent)
        #expect(m.revision == 2 && !m.isDefaultAccent)

        var restored: [CUPalette] = []
        let again = AppearanceModel(defaults: d, publish: { restored.append($0) })
        #expect(again.mode == .night && again.accentHue == 200 && restored.count == 1 && restored[0] == seen[1])
    }

    @Test func resetGoesBackToTheDefaultAccentOnly() {
        let d = defaults()
        let m = AppearanceModel(defaults: d, publish: { _ in })
        m.setMode(.night); m.setAccentHue(90)
        m.resetAccent()
        #expect(m.accentHue == nil && m.mode == .night && m.palette == CUPalette.night)
        #expect(d.object(forKey: AppearanceModel.hueKey) == nil)
        let rev = m.revision
        m.resetAccent()
        #expect(m.revision == rev, "resetting the default accent changes nothing")
    }

    @Test func hueWrapsAndRepeatsAreIgnored() {
        let m = AppearanceModel(defaults: defaults(), publish: { _ in })
        m.setAccentHue(370)
        #expect(m.accentHue == 10)
        let rev = m.revision
        m.setAccentHue(10); m.setMode(.day)
        #expect(m.revision == rev)
        m.setAccentHue(-20)
        #expect(m.accentHue == 340)
    }

    @Test func appStateOwnsTheModelAndPreviewsStartInDay() {
        let s = AppState(themeID: .cupertino, screen: .settings)
        #expect(s.appearance.mode == .day && s.appearance.isDefaultAccent)
    }
}
