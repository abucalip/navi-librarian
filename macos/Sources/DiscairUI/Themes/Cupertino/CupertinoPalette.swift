import SwiftUI

/// Day or Night. Cupertino has one layout and two colour sets; the owner picks in Settings > Appearance.
public enum AppearanceMode: String, CaseIterable, Sendable {
    case day = "Day", night = "Night"
}

extension CURGB {
    init(hue: Double, saturation: Double, brightness: Double) {
        let h = (hue.truncatingRemainder(dividingBy: 360) + 360).truncatingRemainder(dividingBy: 360) / 60
        let s = min(max(saturation, 0), 1), v = min(max(brightness, 0), 1)
        let c = v * s, x = c * (1 - abs(h.truncatingRemainder(dividingBy: 2) - 1)), m = v - c
        let (r, g, b): (Double, Double, Double)
        switch Int(h) {
        case 0: (r, g, b) = (c, x, 0)
        case 1: (r, g, b) = (x, c, 0)
        case 2: (r, g, b) = (0, c, x)
        case 3: (r, g, b) = (0, x, c)
        case 4: (r, g, b) = (x, 0, c)
        default: (r, g, b) = (c, 0, x)
        }
        func byte(_ d: Double) -> UInt32 { UInt32((min(max(d + m, 0), 1) * 255).rounded()) }
        self.init(byte(r) << 16 | byte(g) << 8 | byte(b))
    }

    private var rgb: (r: Double, g: Double, b: Double) {
        (Double((hex >> 16) & 0xFF) / 255, Double((hex >> 8) & 0xFF) / 255, Double(hex & 0xFF) / 255)
    }

    /// Hue in degrees (0 to 360), saturation and brightness (0 to 1).
    var hsb: (hue: Double, saturation: Double, brightness: Double) {
        let (r, g, b) = rgb
        let hi = max(r, g, b), lo = min(r, g, b), d = hi - lo
        var h = 0.0
        if d > 0 {
            if hi == r { h = (g - b) / d } else if hi == g { h = 2 + (b - r) / d } else { h = 4 + (r - g) / d }
            h = (h * 60 + 360).truncatingRemainder(dividingBy: 360)
        }
        return (h, hi == 0 ? 0 : d / hi, hi)
    }

    /// `amount` of `other` over this colour.
    func mixed(with other: CURGB, _ amount: Double) -> CURGB {
        func ch(_ s: UInt32) -> UInt32 {
            let a = Double((hex >> s) & 0xFF), b = Double((other.hex >> s) & 0xFF)
            return UInt32((a + (b - a) * amount).rounded())
        }
        return CURGB(ch(16) << 16 | ch(8) << 8 | ch(0))
    }
}

/// Every colour role of the Cupertino theme for one mode and accent. `CU` reads `CUPalette.current`, so a screen never holds a
/// colour literal. The window is rebuilt when the palette changes (`CupertinoWindow`).
struct CUPalette: Equatable, Sendable {
    var content, panel, fill, fillOnPanel, text, textSecondary, textTertiary, separator, separatorStrong: CURGB
    var accent, accentStrong, accentTint, onAccent: CURGB
    var success, successTint, warning, warningTint, danger, dangerTint, info, infoTint: CURGB
    var chart2, chart3, chartGrid, chartBase, tracker: CURGB
    var heat: [CURGB]
    var backdrop: [CURGB]
    var glassTint: CURGB
    var glassOpacity: Double
    var isNight: Bool

    /// The shipped Cupertino colours (section 4.1 of `docs/redesign.md`).
    static let day = CUPalette(
        content: CURGB(0xFFFFFF), panel: CURGB(0xF5F5F7), fill: CURGB(0xECECF0), fillOnPanel: CURGB(0xE6E6EB),
        text: CURGB(0x1D1D1F), textSecondary: CURGB(0x636368), textTertiary: CURGB(0x8E8E93),
        separator: CURGB(0xE5E5EA), separatorStrong: CURGB(0xD1D1D6),
        accent: CURGB(0xD61F4A), accentStrong: CURGB(0xC8163F), accentTint: CURGB(0xFCE8EC), onAccent: CURGB(0xFFFFFF),
        success: CURGB(0x187A48), successTint: CURGB(0xE6F4EC), warning: CURGB(0x8A5200), warningTint: CURGB(0xFFF4DC),
        danger: CURGB(0xB3261E), dangerTint: CURGB(0xFBEAE8), info: CURGB(0x0B5CAD), infoTint: CURGB(0xE8F1FB),
        chart2: CURGB(0x8E8E93), chart3: CURGB(0xC7C7CC), chartGrid: CURGB(0xE5E5EA), chartBase: CURGB(0xC7C7CC), tracker: CURGB(0xDCDCE2),
        heat: [0xECECF0, 0xF6C5D0, 0xEE8FA5, 0xE2537A, 0xD61F4A].map { CURGB($0) },
        backdrop: [0xEFE9F7, 0xF7ECEA, 0xEAF1F7].map { CURGB($0) },
        glassTint: CURGB(0xF6F6F9), glassOpacity: 0.74, isNight: false)

    /// Near black with a cool lean. Accent and semantic colours are lifted so text on them keeps 4.5:1.
    static let night: CUPalette = {
        let content = CURGB(0x0B0B0D), panel = CURGB(0x151518), fill = CURGB(0x202025)
        let accent = nightAccent(hue: nil, panel: panel)
        return CUPalette(
            content: content, panel: panel, fill: fill, fillOnPanel: CURGB(0x26262B),
            text: CURGB(0xF2F2F4), textSecondary: CURGB(0x9E9EA7), textTertiary: CURGB(0x6E6E78),
            separator: CURGB(0x27272C), separatorStrong: CURGB(0x3A3A41),
            accent: accent.accent, accentStrong: accent.strong, accentTint: accent.tint, onAccent: content,
            success: CURGB(0x47C285), successTint: panel.mixed(with: CURGB(0x47C285), 0.16),
            warning: CURGB(0xF2B04A), warningTint: panel.mixed(with: CURGB(0xF2B04A), 0.16),
            danger: CURGB(0xFF7B72), dangerTint: panel.mixed(with: CURGB(0xFF7B72), 0.16),
            info: CURGB(0x6CB4FF), infoTint: panel.mixed(with: CURGB(0x6CB4FF), 0.16),
            chart2: CURGB(0x8E8E96), chart3: CURGB(0x3A3A41), chartGrid: CURGB(0x27272C), chartBase: CURGB(0x3A3A41), tracker: CURGB(0x2C2C32),
            heat: heatRamp(from: fill, to: accent.accent),
            backdrop: [0x16131D, 0x1B1416, 0x0F161B].map { CURGB($0) },
            glassTint: CURGB(0x18181C), glassOpacity: 0.72, isNight: true)
    }()

    // MARK: Accent

    /// Day keeps the current red-pink; Night starts on coral.
    static let dayAccentDefault = CURGB(0xD61F4A)
    static let nightAccentDefault = CURGB(0xFF7A8F)

    /// Where the Appearance slider sits when the accent is the default for the mode.
    static func defaultHue(for mode: AppearanceMode) -> Double {
        (mode == .night ? nightAccentDefault : dayAccentDefault).hsb.hue
    }

    private static func heatRamp(from low: CURGB, to high: CURGB) -> [CURGB] {
        [0, 0.28, 0.55, 0.78, 1].map { low.mixed(with: high, $0) }
    }

    /// Day accent for a hue: the shipped saturation and brightness, darkened until it reads as text on the panel.
    private static func dayAccent(hue: Double?, panel: CURGB, content: CURGB) -> (accent: CURGB, strong: CURGB, tint: CURGB) {
        guard let hue else { return (dayAccentDefault, CURGB(0xC8163F), CURGB(0xFCE8EC)) }
        let base = dayAccentDefault.hsb
        var b = base.brightness
        var accent = CURGB(hue: hue, saturation: base.saturation, brightness: b)
        while accent.contrast(with: panel) < 4.7, b > 0.25 { b -= 0.02; accent = CURGB(hue: hue, saturation: base.saturation, brightness: b) }
        let tint = content.mixed(with: accent, 0.10)
        var sb = b * 0.94
        var strong = CURGB(hue: hue, saturation: base.saturation, brightness: sb)
        while strong.contrast(with: tint) < 4.6, sb > 0.2 { sb -= 0.02; strong = CURGB(hue: hue, saturation: base.saturation, brightness: sb) }
        return (accent, strong, tint)
    }

    /// Night accent for a hue: full brightness, desaturated until it reads on the panel. `nil` is coral.
    private static func nightAccent(hue: Double?, panel: CURGB) -> (accent: CURGB, strong: CURGB, tint: CURGB) {
        let base = nightAccentDefault.hsb
        let h = hue ?? base.hue
        var s = base.saturation
        var accent = hue == nil ? nightAccentDefault : CURGB(hue: h, saturation: s, brightness: 1)
        while accent.contrast(with: panel) < 4.8, s > 0.05 { s -= 0.02; accent = CURGB(hue: h, saturation: s, brightness: 1) }
        let tint = panel.mixed(with: accent, 0.20)
        var ss = s * 0.9
        var strong = CURGB(hue: h, saturation: ss, brightness: 1)
        while strong.contrast(with: tint) < 4.6, ss > 0.02 { ss -= 0.02; strong = CURGB(hue: h, saturation: ss, brightness: 1) }
        return (accent, strong, tint)
    }

    /// The palette for a mode with an optional accent hue (degrees). `nil` is the default accent of the mode.
    static func make(_ mode: AppearanceMode, accentHue: Double?) -> CUPalette {
        var p = mode == .night ? night : day
        guard let hue = accentHue else { return p }
        let a = mode == .night ? nightAccent(hue: hue, panel: p.panel) : dayAccent(hue: hue, panel: p.panel, content: p.content)
        p.accent = a.accent; p.accentStrong = a.strong; p.accentTint = a.tint
        p.heat = heatRamp(from: p.fill, to: a.accent)
        return p
    }

    /// Every text and accent pair that must reach 4.5:1. `textTertiary` is left out on purpose: decorative only.
    var contrastPairs: [(name: String, text: CURGB, ground: CURGB)] {
        [
            ("text on content", text, content), ("text on panel", text, panel), ("text on fill", text, fill),
            ("text secondary on content", textSecondary, content), ("text secondary on panel", textSecondary, panel),
            ("text secondary on fill", textSecondary, fill),
            ("label on accent", onAccent, accent), ("accent on panel", accent, panel),
            ("accent strong on accent tint", accentStrong, accentTint),
            ("success on panel", success, panel), ("success on success tint", success, successTint),
            ("warning on warning tint", warning, warningTint), ("danger on danger tint", danger, dangerTint),
            ("info on info tint", info, infoTint),
        ]
    }

    /// Read on the main actor by every view; written only by `AppearanceModel`.
    nonisolated(unsafe) static var current = CUPalette.day
}
