import SwiftUI

/// The single window: picks the active theme and lets it compose everything.
public struct RootView: View {
    @Bindable var state: AppState
    public init(state: AppState) { self.state = state }

    public var body: some View {
        let theme = ThemeRegistry.theme(state.themeID)
        theme.window(state: state)
            .preferredColorScheme(theme.colorScheme)
            .environment(\.artwork, state.artwork)
            .frame(minWidth: 1100, minHeight: 700)
    }
}
