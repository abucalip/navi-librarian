import SwiftUI

public enum ThemeID: String, CaseIterable, Sendable, Identifiable {
    case cupertino
    public var id: String { rawValue }
}

/// A theme owns its screens and window composition (contract section 2, D-022 spirit). Adding a theme means adding
/// one conforming type and one registry line; no screen or model code changes.
@MainActor
public protocol DiscairTheme {
    var id: ThemeID { get }
    var name: String { get }
    /// Each theme fixes its own light or dark.
    var colorScheme: ColorScheme { get }
    /// The whole window content, including sidebar/masthead, toolbar and player, for the current `state.screen`.
    func window(state: AppState) -> AnyView
}

@MainActor
public enum ThemeRegistry {
    public static func theme(_ id: ThemeID) -> DiscairTheme {
        switch id {
        case .cupertino: CupertinoTheme()
        }
    }
}

/// Stands in for a theme whose screens are not built yet, so the switcher and tests exercise the registry.
struct PlaceholderTheme: DiscairTheme {
    let id: ThemeID
    let name: String
    let scheme: ColorScheme
    var colorScheme: ColorScheme { scheme }
    func window(state: AppState) -> AnyView {
        AnyView(Text("\(name): not built yet").frame(maxWidth: .infinity, maxHeight: .infinity))
    }
}
