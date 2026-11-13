import Foundation
import Observation

/// Settings > Appearance: Day or Night, and the accent colour as a hue. Saved in UserDefaults. Cupertino reads the colours
/// from `CUPalette.current`; this model is the only writer, and it bumps `revision` so the window is rebuilt with the new ones.
@MainActor
@Observable
public final class AppearanceModel {
    public private(set) var mode: AppearanceMode
    /// The accent hue in degrees, or nil for the default of the mode (coral at night, the red-pink by day).
    public private(set) var accentHue: Double?
    /// Changes whenever the palette does. `RootView` uses it to rebuild the window.
    public private(set) var revision = 0

    @ObservationIgnored private let defaults: UserDefaults
    @ObservationIgnored private let publish: (CUPalette) -> Void
    static let modeKey = "discair.appearance.mode"
    static let hueKey = "discair.appearance.accentHue"

    /// `publish` receives each new palette; the app writes it to `CUPalette.current`, tests capture it instead.
    init(defaults: UserDefaults, publish: @escaping (CUPalette) -> Void = { CUPalette.current = $0 }) {
        self.defaults = defaults
        self.publish = publish
        mode = defaults.string(forKey: Self.modeKey).flatMap(AppearanceMode.init(rawValue:)) ?? .day
        accentHue = defaults.object(forKey: Self.hueKey) as? Double
        // The shipped look needs no write, so previews and tests that never set an appearance leave the shared palette alone.
        if mode != .day || accentHue != nil { publish(palette) }
    }

    var palette: CUPalette { CUPalette.make(mode, accentHue: accentHue) }
    /// Where the slider sits: the chosen hue, or the default hue of the mode.
    public var sliderHue: Double { accentHue ?? CUPalette.defaultHue(for: mode) }
    public var isDefaultAccent: Bool { accentHue == nil }

    public func setMode(_ new: AppearanceMode) {
        guard new != mode else { return }
        mode = new
        defaults.set(new.rawValue, forKey: Self.modeKey)
        apply()
    }

    /// Hue in degrees; values outside 0...360 wrap.
    public func setAccentHue(_ hue: Double) {
        let wrapped = (hue.truncatingRemainder(dividingBy: 360) + 360).truncatingRemainder(dividingBy: 360)
        guard accentHue != wrapped else { return }
        accentHue = wrapped
        defaults.set(wrapped, forKey: Self.hueKey)
        apply()
    }

    /// Back to the default accent of the mode.
    public func resetAccent() {
        guard accentHue != nil else { return }
        accentHue = nil
        defaults.removeObject(forKey: Self.hueKey)
        apply()
    }

    private func apply() {
        publish(palette)
        revision += 1
    }
}
