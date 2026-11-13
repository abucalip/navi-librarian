import SwiftUI

/// The single window: picks the active theme and lets it compose everything.
public struct RootView: View {
    @Bindable var state: AppState
    public init(state: AppState) { self.state = state }

    /// The smallest window the screens are drawn for. The window cannot be resized below it, so the content never scrolls or bounces.
    static let designSize = CGSize(width: 1100, height: 700)

    public var body: some View {
        let theme = ThemeRegistry.theme(state.themeID)
        theme.window(state: state)
            .id(state.appearance.revision)
            .safeAreaInset(edge: .top, spacing: 0) {
                if let notice = state.offlineNotice { OfflineBanner(state: state, text: notice) }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Color(nsColor: .windowBackgroundColor))
        .ignoresSafeArea()
        .background(SpaceBarPlayPause { [state] in state.player.togglePlayPause() })
        .overlay { PipelineDockView(state: state) }
        .modifier(CommandPaletteOverlay(state: state))
        .sheet(item: $state.sonicPath) { SonicPathSheet(state: state, model: $0) }
        .sheet(item: $state.paths) { PathsSheet(state: state, model: $0) }
        .preferredColorScheme(state.appearance.mode == .night ? .dark : .light)
        .environment(\.artwork, state.artwork)
        .frame(minWidth: Self.designSize.width, minHeight: Self.designSize.height)
    }
}
