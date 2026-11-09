import SwiftUI

/// The single window: picks the active theme and lets it compose everything.
public struct RootView: View {
    @Bindable var state: AppState
    public init(state: AppState) { self.state = state }

    /// The smallest size the screens are drawn for. A window smaller than this scrolls instead of squeezing the layout.
    static let designSize = CGSize(width: 1100, height: 700)

    public var body: some View {
        let theme = ThemeRegistry.theme(state.themeID)
        GeometryReader { g in
            ScrollView([.horizontal, .vertical]) {
                theme.window(state: state)
                    .safeAreaInset(edge: .top, spacing: 0) {
                        if let notice = state.offlineNotice { OfflineBanner(state: state, text: notice) }
                    }
                    .frame(width: max(g.size.width, Self.designSize.width), height: max(g.size.height, Self.designSize.height))
            }
            .scrollBounceBehavior(.basedOnSize)
        }
        .ignoresSafeArea()
        .background(SpaceBarPlayPause { [state] in state.player.togglePlayPause() })
        .overlay { PipelineDockView(state: state) }
        .modifier(CommandPaletteOverlay(state: state))
        .sheet(item: $state.sonicPath) { SonicPathSheet(state: state, model: $0) }
        .sheet(item: $state.paths) { PathsSheet(state: state, model: $0) }
        .preferredColorScheme(theme.colorScheme)
        .environment(\.artwork, state.artwork)
        .frame(minWidth: 480, minHeight: 360)
    }
}
