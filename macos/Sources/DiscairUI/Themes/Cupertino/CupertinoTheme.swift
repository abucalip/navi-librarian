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

enum CU {
    static let accent = Color(red: 0.98, green: 0.176, blue: 0.282)      // #fa2d48
    static let muted = Color(red: 0.43, green: 0.43, blue: 0.45)         // #6e6e73
    static let ink = Color(red: 0.114, green: 0.114, blue: 0.122)        // #1d1d1f
    static let card = Color(red: 0.96, green: 0.96, blue: 0.97)          // #f5f5f7
    static let fill = Color(red: 0.925, green: 0.925, blue: 0.94)        // #ececf0
    /// Mockup glass: rgba(246,246,249,.74) over the blur. Bare `.regular` is too clear over the pastel backdrop.
    /// Offscreen screenshot renders blank when the tint is applied, so tests switch it off (`RenderMode`).
    static var glass: Glass {
        RenderMode.offscreenScreenshot ? .regular : .regular.tint(Color(red: 0.965, green: 0.965, blue: 0.976).opacity(0.74))
    }
    static let sidebarRadius: CGFloat = 20
    static let windowRadius: CGFloat = 26
    static func title(_ size: CGFloat) -> Font { .system(size: size, weight: .bold).width(.standard) }
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
        ("point.3.connected.trianglepath.dotted", "Connections", .connections), ("map", "Atlas", .atlas),
        ("calendar.day.timeline.left", "Timeline", .timeline), ("lightbulb", "Insights", .insights),
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
                            Text("Discover").font(.system(size: 11, weight: .bold))
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
                            HStack(spacing: 9) {
                                Image(systemName: "music.note.list").foregroundStyle(CU.accent).frame(width: 18)
                                Text(list.name).lineLimit(1)
                            }
                            .font(.system(size: 13.5)).padding(.horizontal, 10).padding(.vertical, 6)
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
        return Button { state.screen = screen } label: {
            HStack(spacing: 9) {
                Image(systemName: icon).foregroundStyle(CU.accent).frame(width: 18)
                Text(label).fontWeight(on ? .semibold : .regular)
                Spacer()
                if label == "Downloads", !state.library.isLive || state.acquisition.activeCount > 0 {
                    Text(state.library.isLive ? String(state.acquisition.activeCount) : "2").font(.system(size: 11, weight: .bold)).foregroundStyle(.white)
                        .padding(.horizontal, 7).background(CU.accent, in: Capsule())
                }
            }
            .font(.system(size: 13.5))
            .foregroundStyle(on ? CU.accent : CU.ink)
            .padding(.horizontal, 10).padding(.vertical, 6)
            .background(on ? CU.accent.opacity(0.13) : .clear, in: RoundedRectangle(cornerRadius: 9, style: .continuous))
            .contentShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(on ? .isSelected : [])
    }
}

/// Search and the Queue button, top right. The player itself is `CupertinoPlayerBar`, along the bottom.
struct CupertinoToolbar: View {
    let state: AppState
    var body: some View {
        HStack(spacing: 12) {
            Spacer(minLength: 0)
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
            Button { state.screen = .nowPlaying } label: {
                CoverView(album: AlbumItem(id: -1, title: c.album, artist: c.artist, year: 0, genre: "", format: "", owned: true, hue: 200, coverArt: c.coverArt), px: 600)
                    .frame(width: Self.side, height: Self.side)
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                    .shadow(color: .black.opacity(0.28), radius: 10, y: 4)
            }
            .buttonStyle(.plain).padding(.leading, 20).padding(.bottom, 10)
            .accessibilityLabel("Now playing artwork: \(c.album.isEmpty ? c.title : c.album). Opens Now Playing")
        } else {
            HStack(spacing: 5) {
                Circle().fill(state.connectionIsGood ? Color.green : CU.accent).frame(width: 7, height: 7)
                Text(state.connectionLabel).lineLimit(1).minimumScaleFactor(0.8)
            }
            .font(.system(size: 11)).foregroundStyle(CU.muted)
            .frame(width: Self.side, alignment: .leading).padding(.leading, 26).padding(.bottom, (CupertinoPlayerBar.height - 14) / 2)
            .accessibilityElement(children: .combine)
            .accessibilityLabel("Connection: \(state.connectionLabel)")
        }
    }
}
