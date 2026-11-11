import SwiftUI

/// Cupertino (macOS, light). Spec: `docs/design/macos-m4/mockups.html`, `R.cupertino`.
/// Rules: glass only on controls (sidebar, toolbar pieces, centre display); opaque white content;
/// bold SF Pro Display titles (not serif); red-pink accent; Up Next as a trailing inspector.
struct CupertinoTheme: DiscairTheme {
    let id = ThemeID.cupertino
    let name = "Cupertino"
    let colorScheme = ColorScheme.light

    func window(state: AppState) -> AnyView {
        AnyView(CupertinoWindow(state: state))
    }
}

/// An sRGB colour kept as hex, so the contrast of every token can be measured in tests.
struct CURGB: Equatable, Sendable {
    let hex: UInt32
    init(_ hex: UInt32) { self.hex = hex }

    private func channel(_ shift: UInt32) -> Double { Double((hex >> shift) & 0xFF) / 255 }
    var color: Color { Color(red: channel(16), green: channel(8), blue: channel(0)) }

    /// WCAG 2 relative luminance.
    var luminance: Double {
        func linear(_ c: Double) -> Double { c <= 0.03928 ? c / 12.92 : pow((c + 0.055) / 1.055, 2.4) }
        return 0.2126 * linear(channel(16)) + 0.7152 * linear(channel(8)) + 0.0722 * linear(channel(0))
    }

    /// WCAG 2 contrast ratio against another colour, 1 to 21.
    func contrast(with other: CURGB) -> Double {
        let (hi, lo) = luminance >= other.luminance ? (luminance, other.luminance) : (other.luminance, luminance)
        return (hi + 0.05) / (lo + 0.05)
    }
}

/// Cupertino (macOS) tokens. Values are section 4.1 of `docs/redesign.md`; the stylesheet named there is the tie-breaker.
/// The old names (`accent`, `muted`, `ink`, `card`, `fill`) are kept as aliases of the new roles, so views that use them compile unchanged.
enum CU {
    // MARK: Colour roles

    static let contentRGB = CURGB(0xFFFFFF)          // content ground
    static let bgPanelRGB = CURGB(0xF5F5F7)          // grouped panels, inspector
    static let bgFillRGB = CURGB(0xECECF0)           // neutral buttons and tracks on white
    static let bgFillOnPanelRGB = CURGB(0xE6E6EB)    // neutral buttons and tracks on a panel
    static let textRGB = CURGB(0x1D1D1F)             // primary text
    static let textSecondaryRGB = CURGB(0x636368)    // secondary text
    static let textTertiaryRGB = CURGB(0x8E8E93)     // disabled and decorative only, never essential text
    static let separatorRGB = CURGB(0xE5E5EA)        // hairlines, gridlines
    static let separatorStrongRGB = CURGB(0xD1D1D6)  // field and outline-button borders
    static let accentRGB = CURGB(0xD61F4A)           // main action, selection, highlighted series
    static let accentStrongRGB = CURGB(0xC8163F)     // pressed; accent text on the tint
    static let accentTintRGB = CURGB(0xFCE8EC)       // selected row ground
    static let successRGB = CURGB(0x187A48)
    static let successTintRGB = CURGB(0xE6F4EC)
    static let warningRGB = CURGB(0x8A5200)
    static let warningTintRGB = CURGB(0xFFF4DC)
    static let dangerRGB = CURGB(0xB3261E)           // a brick hue, never the accent; always with an icon and a sentence
    static let dangerTintRGB = CURGB(0xFBEAE8)
    static let infoRGB = CURGB(0x0B5CAD)             // not loaded, paused
    static let infoTintRGB = CURGB(0xE8F1FB)
    static let chart2RGB = CURGB(0x8E8E93)           // comparison line, baseline dot (graphic, 3:1)
    static let chart3RGB = CURGB(0xC7C7CC)           // context bars
    static let chartGridRGB = CURGB(0xE5E5EA)
    static let chartBaseRGB = CURGB(0xC7C7CC)
    static let trackerTrackRGB = CURGB(0xDCDCE2)     // unfilled stage-tracker segments (the specimen sheet's value, a step darker than chart.ghost)
    static let heatRGB: [CURGB] = ([0xECECF0, 0xF6C5D0, 0xEE8FA5, 0xE2537A, 0xD61F4A] as [UInt32]).map { CURGB($0) }

    static let content = contentRGB.color
    static let bgPanel = bgPanelRGB.color
    static let bgFill = bgFillRGB.color
    static let bgFillOnPanel = bgFillOnPanelRGB.color
    static let text = textRGB.color
    static let textSecondary = textSecondaryRGB.color
    static let textTertiary = textTertiaryRGB.color
    static let separator = separatorRGB.color
    static let separatorStrong = separatorStrongRGB.color
    static let accent = accentRGB.color
    static let accentStrong = accentStrongRGB.color
    static let accentTint = accentTintRGB.color
    static let success = successRGB.color
    static let successTint = successTintRGB.color
    static let warning = warningRGB.color
    static let warningTint = warningTintRGB.color
    static let danger = dangerRGB.color
    static let dangerTint = dangerTintRGB.color
    static let info = infoRGB.color
    static let infoTint = infoTintRGB.color
    static let chart1 = accent
    static let chart2 = chart2RGB.color
    static let chart3 = chart3RGB.color
    static let chartGhost = bgFill
    static let chartGrid = chartGridRGB.color
    static let chartBase = chartBaseRGB.color
    static let trackerTrack = trackerTrackRGB.color
    static let heat: [Color] = heatRGB.map(\.color)

    // Aliases for the names the views already use.
    static let muted = textSecondary
    static let ink = text
    static let card = bgPanel
    static let fill = bgFill

    // Roles added in M10b so that no view needs a colour literal.
    /// Label on the accent fill (the one primary action, a selected row).
    static let onAccent = contentRGB.color
    /// White marks and text over artwork or a dark gradient. Not a light-ground colour.
    static let onMedia = Color.white
    /// Source of shadows and dimming scrims; always used with an opacity.
    static let shadowInk = Color.black
    /// Ground of the full-screen Now Playing page, behind the artwork-derived washes.
    static let playerGround = CURGB(0x3A2A1C).color
    /// A colour derived from album artwork (hue, saturation, brightness). The one place a hue is built.
    static func artwork(hue: Double, saturation: Double, brightness: Double) -> Color {
        Color(hue: hue, saturation: saturation, brightness: brightness)
    }

    /// SF Symbols sizes: 16 in rows, 12 in small buttons (section 4.3).
    enum Icon {
        static func row(_ weight: SwiftUI.Font.Weight = .regular) -> SwiftUI.Font { .system(size: 16, weight: weight) }
        static func small(_ weight: SwiftUI.Font.Weight = .regular) -> SwiftUI.Font { .system(size: 12, weight: weight) }
        /// Transport controls in the player (previous, next).
        static func transport(_ weight: SwiftUI.Font.Weight = .regular) -> SwiftUI.Font { .system(size: 24, weight: weight) }
        /// The large play and pause symbol.
        static func hero(_ weight: SwiftUI.Font.Weight = .regular) -> SwiftUI.Font { .system(size: 34, weight: weight) }
        /// The service status symbol in an empty or summary state.
        static func status(_ weight: SwiftUI.Font.Weight = .regular) -> SwiftUI.Font { .system(size: 32, weight: weight) }
    }

    /// Mockup glass: rgba(246,246,249,.74) over the blur. Bare `.regular` is too clear over the pastel backdrop.
    /// Offscreen screenshot renders blank when the tint is applied, so tests switch it off (`RenderMode`).
    static var glass: Glass {
        RenderMode.offscreenScreenshot ? .regular : .regular.tint(Color(red: 0.965, green: 0.965, blue: 0.976).opacity(0.74))
    }
    static let sidebarRadius: CGFloat = 20
    static let windowRadius: CGFloat = 26
    static func title(_ size: CGFloat) -> SwiftUI.Font { .system(size: size, weight: .bold).width(.standard) }

    /// Every text and accent pair that section 4.1 says must reach 4.5:1. `text.tertiary` is left out on purpose: it is 3.3:1 and decorative only.
    /// Accent text on the accent tint is also left out: it is 4.31:1, so the table uses `accent.strong` there instead.
    static let contrastPairs: [(name: String, text: CURGB, ground: CURGB)] = [
        ("text on content", textRGB, contentRGB),
        ("text on panel", textRGB, bgPanelRGB),
        ("text on fill", textRGB, bgFillRGB),
        ("text secondary on content", textSecondaryRGB, contentRGB),
        ("text secondary on panel", textSecondaryRGB, bgPanelRGB),
        ("text secondary on fill", textSecondaryRGB, bgFillRGB),
        ("white label on accent", contentRGB, accentRGB),
        ("accent on panel", accentRGB, bgPanelRGB),
        ("accent strong on accent tint", accentStrongRGB, accentTintRGB),
        ("success on panel", successRGB, bgPanelRGB),
        ("success on success tint", successRGB, successTintRGB),
        ("warning on warning tint", warningRGB, warningTintRGB),
        ("danger on danger tint", dangerRGB, dangerTintRGB),
        ("info on info tint", infoRGB, infoTintRGB),
    ]

    // MARK: Spacing (4, 8, 16, 24, 32 only)

    enum Space {
        static let xs: CGFloat = 4
        static let s: CGFloat = 8
        static let m: CGFloat = 16
        static let l: CGFloat = 24
        static let xl: CGFloat = 32
        static let scale: [CGFloat] = [xs, s, m, l, xl]
    }

    // MARK: Type roles (section 4.2)

    enum Font {
        struct Role: Equatable, Sendable {
            let size: CGFloat
            let lineHeight: CGFloat
            let weight: SwiftUI.Font.Weight
            /// Tracking in points. The eyebrow's +0.06em is stored as points at 11 pt.
            let tracking: CGFloat
            /// Set in capitals by the view; the role only records that the style is an eyebrow.
            let isCapitals: Bool

            var font: SwiftUI.Font { .system(size: size, weight: weight) }
            /// The same size with another weight, for the Semibold or Medium labels the mockups use at a role's size.
            func weighted(_ weight: SwiftUI.Font.Weight) -> SwiftUI.Font { .system(size: size, weight: weight) }
        }

        static let largeTitle = Role(size: 34, lineHeight: 40, weight: .bold, tracking: -0.4, isCapitals: false)
        static let heroMetric = Role(size: 44, lineHeight: 48, weight: .bold, tracking: -0.8, isCapitals: false)
        static let title1 = Role(size: 24, lineHeight: 32, weight: .bold, tracking: -0.3, isCapitals: false)
        static let title2 = Role(size: 20, lineHeight: 24, weight: .bold, tracking: -0.2, isCapitals: false)
        static let metric = Role(size: 24, lineHeight: 32, weight: .semibold, tracking: -0.3, isCapitals: false)
        static let title3 = Role(size: 17, lineHeight: 24, weight: .semibold, tracking: -0.1, isCapitals: false)
        static let headline = Role(size: 13, lineHeight: 20, weight: .semibold, tracking: 0, isCapitals: false)
        static let body = Role(size: 13, lineHeight: 20, weight: .regular, tracking: 0, isCapitals: false)
        static let callout = Role(size: 12, lineHeight: 18, weight: .regular, tracking: 0, isCapitals: false)
        static let caption = Role(size: 11, lineHeight: 16, weight: .regular, tracking: 0, isCapitals: false)
        static let eyebrow = Role(size: 11, lineHeight: 16, weight: .bold, tracking: 0.66, isCapitals: true)
    }
}

extension Text {
    /// Applies a `CU.Font.Role`'s size, weight and tracking. SwiftUI cannot set an exact line height on one `Text`;
    /// a block that needs one uses `lineSpacing(role.lineHeight - role.size)` where the view applies it.
    func cuRole(_ role: CU.Font.Role) -> Text { font(role.font).tracking(role.tracking) }
}

struct CupertinoWindow: View {
    let state: AppState

    var body: some View {
        if state.screen == .nowPlaying {
            CupertinoNowPlaying(state: state)
        } else {
            library
        }
    }

    private var library: some View {
        VStack(spacing: 0) {
            ZStack(alignment: .topLeading) {
                // Opaque content; flows under the floating sidebar and toolbar (content is never glass).
                content
                    .padding(.trailing, state.queueOpen && state.screen != .artist && state.screen != .album ? CupertinoQueueInspector.width : 0)
                    .padding(.leading, 236)
                    .padding(.top, state.screen == .artist || state.screen == .album ? CupertinoArtistLayout.bannerHeight : 66)
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                    .background(Color.white)

                if state.screen == .artist { CupertinoArtistBanner(state: state) }
                if state.screen == .album { CupertinoAlbumBanner(state: state) }   // under the sidebar and toolbar

                CupertinoSidebar(state: state)
                    .padding(.bottom, state.player.current != nil ? CupertinoArtworkSlot.side + 20 - CupertinoPlayerBar.height : 0)
                CupertinoToolbar(state: state)
                    .padding(.leading, 238).padding(.trailing, state.queueOpen ? CupertinoQueueInspector.width + 16 : 16).padding(.top, 12)
                if state.queueOpen {
                    CupertinoQueueInspector(state: state).frame(maxWidth: .infinity, alignment: .trailing)
                }
            }
            .overlay(alignment: .bottom) { CupertinoNotice(state: state).padding(.bottom, 22) }
            // The player runs along the bottom of the window (owner decision; Apple's guidance puts it at the top).
            CupertinoPlayerBar(state: state)
        }
        // Left of the player, under the sidebar: the playing cover as a large square, or the connection when nothing plays.
        .overlay(alignment: .bottomLeading) { CupertinoArtworkSlot(state: state) }
        .background(LinearGradient(colors: [Color(red: 0.937, green: 0.914, blue: 0.969), Color(red: 0.969, green: 0.925, blue: 0.918), Color(red: 0.918, green: 0.945, blue: 0.969)], startPoint: .topLeading, endPoint: .bottomTrailing))
        .foregroundStyle(CU.ink)
        .clipShape(RoundedRectangle(cornerRadius: CU.windowRadius, style: .continuous))
        .background(WindowConfigurator(canDragAt: { [state] p, size in !(state.queueOpen && p.x > size.width - CupertinoQueueInspector.width && p.y < size.height - CupertinoPlayerBar.height) }))
    }

    @ViewBuilder private var content: some View {
        switch state.screen {
        case .home: CupertinoHome(state: state)
        case .album: CupertinoAlbum(state: state)
        case .queue, .albums, .library, .artists, .recent: CupertinoLibraryHub(state: state)
        case .artist: CupertinoArtist(state: state)
        case .settings: CupertinoSettings(state: state)
        case .downloads: CupertinoDownloads(state: state)
        case .discover: CupertinoDiscover(state: state)
        case .equalizer: CupertinoEQ(state: state)
        case .gapRadar: CupertinoGapRadar(state: state)
        case .connections: GraphExplorerView(state: state, style: .cupertino)
        case .atlas: AtlasView(state: state, style: .cupertino)
        case .timeline: TimelineView(state: state, style: .cupertino)
        case .smartPlaylists: CupertinoSmartPlaylists(state: state)
        case .history: CupertinoHistory(state: state)
        case .insights: CupertinoInsights(state: state)
        default: Text("\(state.screen.rawValue): not built yet").foregroundStyle(CU.muted).padding(28)
        }
    }
}

/// Owned music first (Home, Library), then the Discover group, then the tools. Playlists stay below.
struct CupertinoSidebar: View {
    let state: AppState
    private var selected: String {
        switch state.screen {
        case .home: "Home"
        case .queue, .library, .albums, .artists, .recent, .artist, .album: "Library"
        case .settings, .equalizer: "Settings"
        case .downloads: "Downloads"
        case .discover: "New"
        case .gapRadar: "Gap Radar"
        case .connections: "Connections"
        case .atlas: "Atlas"
        case .timeline: "Timeline"
        case .smartPlaylists: "Smart Playlists"
        case .history: "Library"
        case .insights: "Insights"
        default: "Home"
        }
    }
    private let discover: [(String, String, Screen)] = [
        ("sparkles", "New", .discover), ("dot.radiowaves.left.and.right", "Gap Radar", .gapRadar),
        ("point.3.connected.trianglepath.dotted", "Connections", .connections), ("calendar.day.timeline.left", "Timeline", .timeline),
        ("map", "Atlas", .atlas), ("lightbulb", "Insights", .insights),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            TrafficLights().padding(.leading, 6).padding(.bottom, 20)
            ScrollView {
                VStack(alignment: .leading, spacing: 2) {
                    row("house", "Home", .home)
                    row("books.vertical", "Library", .library)
                    Color.clear.frame(height: 12)
                    Button { state.discoverOpen.toggle() } label: {
                        HStack(spacing: 6) {
                            Image(systemName: state.discoverOpen ? "chevron.down" : "chevron.right").font(.system(size: 10, weight: .bold)).frame(width: 18)
                            Text("Discover").font(CU.Font.headline.font)
                            Spacer()
                        }
                        .foregroundStyle(CU.muted).padding(.horizontal, 10).padding(.top, 2).padding(.bottom, 2)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Discover").accessibilityValue(state.discoverOpen ? "expanded" : "collapsed")
                    .accessibilityHint("Shows or hides the discovery pages")
                    if state.discoverOpen {
                        ForEach(discover, id: \.1) { icon, label, screen in row(icon, label, screen).padding(.leading, 16) }
                    }
                    Color.clear.frame(height: 12)
                    row("wand.and.stars", "Smart Playlists", .smartPlaylists)
                    row("arrow.down.circle", "Downloads", .downloads)
                    row("gearshape", "Settings", .settings)
                    Text("Playlists").font(.system(size: 11, weight: .bold)).foregroundStyle(CU.muted).padding(.leading, 10).padding(.top, 14)
                    ForEach(state.smart.lists) { list in
                        Button { state.smart.selectedID = list.id; state.screen = .smartPlaylists } label: {
                            HStack(spacing: CU.Space.s) {
                                Image(systemName: "music.note.list").foregroundStyle(CU.textSecondary).frame(width: 18)
                                Text(list.name).lineLimit(1)
                            }
                            .font(CU.Font.body.weighted(.regular)).foregroundStyle(CU.text)
                            .padding(.horizontal, CU.Space.s).frame(height: 32, alignment: .leading)
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
            .scrollIndicators(.hidden)
        }
        .padding(10).padding(.top, 6)
        .frame(width: 216)
        .glassEffect(CU.glass, in: RoundedRectangle(cornerRadius: CU.sidebarRadius, style: .continuous))
        .padding(10)
    }

    private func row(_ icon: String, _ label: String, _ screen: Screen) -> some View {
        let on = label == selected
        // Mockup: 32 high, radius 12, 8 horizontal padding. Icons are secondary text; only the selected row takes the accent,
        // as an accent-tint ground, accent-strong text and an accent icon.
        return Button { state.screen = screen } label: {
            HStack(spacing: CU.Space.s) {
                Image(systemName: icon).foregroundStyle(on ? CU.accent : CU.textSecondary).frame(width: 18)
                Text(label).fontWeight(on ? .semibold : .regular)
                Spacer()
                if label == "Downloads", !state.library.isLive || state.acquisition.activeCount > 0 {
                    Text(state.library.isLive ? String(state.acquisition.activeCount) : "2").font(.system(size: 11, weight: .bold)).foregroundStyle(.white)
                        .padding(.horizontal, 7).background(CU.accent, in: Capsule())
                }
            }
            .font(CU.Font.body.weighted(.regular))
            .foregroundStyle(on ? CU.accentStrong : CU.text)
            .padding(.horizontal, CU.Space.s).frame(height: 32)
            .background(on ? CU.accentTint : .clear, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
            .contentShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(on ? .isSelected : [])
    }
}

/// The services status button (M9), Search and the Queue button, top right. The player itself is `CupertinoPlayerBar`, along the bottom.
struct CupertinoToolbar: View {
    let state: AppState
    var body: some View {
        HStack(spacing: 12) {
            Spacer(minLength: 0)
            CupertinoStatusButton(state: state)
            Button { state.palette.open() } label: {
                HStack(spacing: 8) {
                    Image(systemName: "magnifyingglass")
                    Text("Search  ⌘K")
                    Spacer(minLength: 0)
                }
                .foregroundStyle(CU.muted).padding(.horizontal, 14).frame(width: 210, height: 36)
                .contentShape(Capsule())
                .glassEffect(CU.glass, in: Capsule())
            }
            .buttonStyle(.plain).accessibilityLabel("Search and commands").accessibilityHint("Opens the command palette, shortcut command K")

            // The whole circle is the button, not just the icon.
            Button { state.queueOpen.toggle() } label: {
                Image(systemName: "list.bullet").font(.system(size: 15)).foregroundStyle(state.queueOpen ? CU.accent : CU.ink)
                    .frame(width: 40, height: 40).contentShape(Circle()).glassEffect(CU.glass, in: Circle())
            }
            .buttonStyle(.plain).contentShape(Circle()).accessibilityLabel(state.queueOpen ? "Close Queue" : "Queue")
        }
        .frame(height: 44)
    }
}

/// Not for me waits a few seconds so it can be undone; failures of Save or a dismissal show here until closed.
struct CupertinoNotice: View {
    let state: AppState
    var body: some View {
        let acq = state.acquisition
        if let p = acq.pending {
            HStack(spacing: 12) {
                Text("Not for me: \(p.title)").fontWeight(.semibold).lineLimit(1)
                Button("Undo") { acq.undo() }.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
                Button("Never suggest \(p.artist)") { Task { await acq.neverSuggest() } }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
            }
            .font(.system(size: 13)).padding(.horizontal, 16).padding(.vertical, 10)
            .glassEffect(CU.glass, in: Capsule())
            .accessibilityElement(children: .contain)
        } else if let n = acq.notice {
            HStack(spacing: 12) {
                Text(n).lineLimit(2)
                Button("Dismiss") { acq.clearNotice() }.buttonStyle(CapsuleButtonStyle(small: true))
            }
            .font(.system(size: 13)).padding(.horizontal, 16).padding(.vertical, 10)
            .glassEffect(CU.glass, in: Capsule())
        }
    }
}

/// Bottom left of the window, in the space the travel buttons used to take: the large cover of the song playing (it covers the
/// connection text), or that text when nothing is playing.
struct CupertinoArtworkSlot: View {
    let state: AppState
    static let side: CGFloat = 216

    var body: some View {
        if let c = state.player.current {
            // The large cover turns over on hover and opens the album's booklet on click (Now Playing when it has none).
            PlayerBarCover(artist: c.artist, album: c.album, disc: c.disc, spinning: false, side: Self.side, cornerRadius: CU.sidebarRadius,
                           showsDisc: false, fallback: { state.screen = .nowPlaying }) {
                CoverView(album: AlbumItem(id: -1, title: c.album, artist: c.artist, year: 0, genre: "", format: "", owned: true, hue: 200, remoteID: c.albumID, coverArt: c.coverArt), px: 600)
            }
            .shadow(color: .black.opacity(0.28), radius: 10, y: 4)
            // The sidebar's glass starts 10 points in and is 216 wide: the cover takes the same column.
            .padding(.leading, 10).padding(.bottom, 10)
        } else {
            HStack(spacing: 5) {
                // A bad connection is danger with its own icon and the label's words; never the accent.
                Image(systemName: state.connectionIsGood ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                    .foregroundStyle(state.connectionIsGood ? CU.success : CU.danger).accessibilityHidden(true)
                Text(state.connectionLabel).lineLimit(1).minimumScaleFactor(0.8)
            }
            .font(CU.Font.caption.weighted(.regular)).foregroundStyle(CU.muted)
            .frame(width: Self.side, alignment: .leading).padding(.leading, 26).padding(.bottom, (CupertinoPlayerBar.height - 14) / 2)
            .accessibilityElement(children: .combine)
            .accessibilityLabel("Connection: \(state.connectionLabel)")
        }
    }
}
