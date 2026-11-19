import SwiftUI

/// The single window: picks the active theme and lets it compose everything.
public struct RootView: View {
    @Bindable var state: AppState
    /// The Pipeline card's own height, measured in the overlay; 0 until it is laid out.
    @State private var pipelineCardHeight: CGFloat = 0
    public init(state: AppState) { self.state = state }

    /// The smallest window the screens are drawn for. The window cannot be resized below it, so the content never scrolls or bounces.
    static let designSize = CGSize(width: 1100, height: 700)

    /// Room the pages leave above the player bar while the Pipeline card shows (D3.1); 0 when it is hidden.
    private var pipelineDockClearance: CGFloat {
        let content = state.acquisition.dock
        guard PipelineDockPlacement.shows(screen: state.screen, content: content) else { return 0 }
        return PipelineDockPlacement.bottomClearance(cardHeight: pipelineCardHeight)
    }

    public var body: some View {
        let theme = ThemeRegistry.theme(state.themeID)
        theme.window(state: state)
            .environment(\.pipelineDockClearance, pipelineDockClearance)
            .id(state.appearance.revision)
            .safeAreaInset(edge: .top, spacing: 0) {
                if let notice = state.offlineNotice { OfflineBanner(state: state, text: notice) }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Color(nsColor: .windowBackgroundColor))
        .ignoresSafeArea()
        .background(SpaceBarPlayPause { [state] in state.player.togglePlayPause() })
        .overlay { PipelineDockView(state: state) { pipelineCardHeight = $0 } }
        .modifier(CommandPaletteOverlay(state: state))
        .sheet(item: $state.sonicPath) { SonicPathSheet(state: state, model: $0) }
        .sheet(item: $state.paths) { PathsSheet(state: state, model: $0) }
        .preferredColorScheme(state.appearance.mode == .night ? .dark : .light)
        .environment(\.artwork, state.artwork)
        .environment(\.stationLogos, state.stationLogos)
        .frame(minWidth: Self.designSize.width, minHeight: Self.designSize.height)
    }
}
