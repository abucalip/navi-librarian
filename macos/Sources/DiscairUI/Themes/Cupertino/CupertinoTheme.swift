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
        ZStack(alignment: .topLeading) {
            LinearGradient(colors: [Color(red: 0.937, green: 0.914, blue: 0.969), Color(red: 0.969, green: 0.925, blue: 0.918), Color(red: 0.918, green: 0.945, blue: 0.969)], startPoint: .topLeading, endPoint: .bottomTrailing)

            // Opaque content; flows under the floating sidebar and toolbar (content is never glass).
            content
                .padding(.trailing, state.queueOpen && state.screen != .artist ? CupertinoQueueInspector.width : 0)
                .padding(.leading, 236)
                .padding(.top, state.screen == .artist ? CupertinoArtistLayout.bannerHeight : 66)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                .background(Color.white)
                .padding(.leading, 0)

            if state.screen == .artist { CupertinoArtistBanner(state: state) }   // under the sidebar and toolbar

            CupertinoSidebar(state: state)
            CupertinoToolbar(state: state)
                .padding(.leading, 238).padding(.trailing, state.queueOpen ? CupertinoQueueInspector.width + 16 : 16).padding(.top, 12)
            if state.queueOpen {
                CupertinoQueueInspector(state: state).frame(maxWidth: .infinity, alignment: .trailing)
            }
            // Top right under the search pill (owner decision), not at the bottom of the window or sidebar (HIG).
            HStack(spacing: 5) {
                Circle().fill(state.connectionIsGood ? Color.green : CU.accent).frame(width: 7, height: 7)
                Text(state.connectionLabel)
            }
            .font(.system(size: 11)).foregroundStyle(state.screen == .artist ? Color.white.opacity(0.9) : CU.muted)   // over the dark banner
            .accessibilityElement(children: .combine)
            .accessibilityLabel("Connection: \(state.connectionLabel)")
            .frame(maxWidth: .infinity, alignment: .trailing)
            .padding(.trailing, state.queueOpen ? CupertinoQueueInspector.width + 20 : 20).padding(.top, 52)
        }
        .overlay(alignment: .bottom) { CupertinoNotice(state: state).padding(.bottom, 22) }
        .foregroundStyle(CU.ink)
        .clipShape(RoundedRectangle(cornerRadius: CU.windowRadius, style: .continuous))
        .background(WindowConfigurator(canDragAt: { [state] p, size in !(state.queueOpen && p.x > size.width - CupertinoQueueInspector.width) }))
    }

    @ViewBuilder private var content: some View {
        switch state.screen {
        case .home: CupertinoHome(state: state)
        case .album: CupertinoAlbum(state: state)
        case .queue, .albums: CupertinoAlbumsGrid(state: state)
        case .library: CupertinoLibrary(state: state)
        case .artists: CupertinoArtistsIndex(state: state)
        case .recent: CupertinoAlbumsGrid(state: state, recent: true)
        case .artist: CupertinoArtist(state: state)
        case .settings: CupertinoSettings(state: state)
        case .downloads: CupertinoDownloads(state: state)
        case .discover: CupertinoDiscover(state: state)
        case .equalizer: CupertinoEQ(state: state)
        case .gapRadar: CupertinoGapRadar(state: state)
        case .smartPlaylists: CupertinoSmartPlaylists(state: state)
        case .history: CupertinoHistory(state: state)
        default: Text("\(state.screen.rawValue): not built yet").foregroundStyle(CU.muted).padding(28)
        }
    }
}

struct CupertinoSidebar: View {
    let state: AppState
    private var selected: String {
        switch state.screen {
        case .home: "Home"
        case .queue, .library: "Songs"
        case .albums: "Albums"
        case .artist, .artists: "Artists"
        case .settings: "Settings"
        case .downloads: "Downloads"
        case .discover: "New"
        case .equalizer: "Settings"
        case .gapRadar: "Gap Radar"
        case .smartPlaylists: "Smart Playlists"
        case .history: "History"
        case .recent: "Recently Added"
        default: "Home"
        }
    }
    /// Where each row goes. Rows without a screen yet do nothing (they are still real buttons, so keyboard and
    /// VoiceOver treat them like the rest).
    private let target: [String: Screen] = ["Home": .home, "Songs": .library, "Albums": .albums, "Artists": .artists, "Recently Added": .recent, "New": .discover, "Gap Radar": .gapRadar, "Smart Playlists": .smartPlaylists, "History": .history, "Downloads": .downloads, "Settings": .settings]
    private let nav: [(String, String)] = [
        ("house", "Home"), ("sparkles", "New"), ("clock", "Recently Added"), ("music.mic", "Artists"),
        ("square.stack", "Albums"), ("music.note", "Songs"), ("dot.radiowaves.left.and.right", "Gap Radar"), ("wand.and.stars", "Smart Playlists"),
        ("clock.arrow.circlepath", "History"), ("arrow.down.circle", "Downloads"), ("gearshape", "Settings"),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            TrafficLights().padding(.leading, 6).padding(.bottom, 20)
            ForEach(nav, id: \.1) { icon, label in
                let on = label == selected
                Button {
                    if let t = target[label] { state.screen = t }
                } label: {
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
            Text("Playlists").font(.system(size: 11, weight: .bold)).foregroundStyle(CU.muted).padding(.leading, 10).padding(.top, 14)
            ForEach(state.smart.lists) { list in
                let p = list.name
                Button { state.smart.selectedID = list.id; state.screen = .smartPlaylists } label: {
                    HStack(spacing: 9) {
                        Image(systemName: "music.note.list").foregroundStyle(CU.accent).frame(width: 18)
                        Text(p).lineLimit(1)
                    }
                    .font(.system(size: 13.5)).padding(.horizontal, 10).padding(.vertical, 6)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
            }
            Spacer()
        }
        .padding(10).padding(.top, 6)
        .frame(width: 216)
        .glassEffect(CU.glass, in: RoundedRectangle(cornerRadius: CU.sidebarRadius, style: .continuous))
        .padding(10)
    }
}

struct CupertinoToolbar: View {
    let state: AppState
    var body: some View {
        HStack(spacing: 12) {
            HStack(spacing: 16) {
                let p = state.player
                Button { p.toggleShuffle() } label: { Image(systemName: "shuffle").foregroundStyle(p.shuffle ? CU.accent : CU.ink) }
                    .accessibilityLabel(p.shuffle ? "Shuffle, on" : "Shuffle, off")
                Button { p.previous() } label: { Image(systemName: "backward.fill") }.accessibilityLabel("Previous")
                Button { p.togglePlayPause() } label: { Image(systemName: p.isPlaying ? "pause.fill" : "play.fill") }
                    .accessibilityLabel(p.isPlaying ? "Pause" : "Play").disabled(p.current == nil)
                Button { p.next() } label: { Image(systemName: "forward.fill") }.accessibilityLabel("Next").disabled(p.current == nil)
                Button { p.cycleRepeat() } label: {
                    Image(systemName: p.repeatMode == .one ? "repeat.1" : "repeat").foregroundStyle(p.repeatMode == .off ? CU.ink : CU.accent)
                }
                .accessibilityLabel("Repeat, \(p.repeatMode.rawValue)")
            }
            .buttonStyle(.plain).font(.system(size: 15))
            .padding(.horizontal, 18).frame(height: 40)
            .glassEffect(CU.glass, in: Capsule())

            Button { state.screen = .nowPlaying } label: { nowPlayingDisplay }
                .buttonStyle(.plain).frame(maxWidth: 470)

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

            Button { state.queueOpen.toggle() } label: {
                Image(systemName: "list.bullet").font(.system(size: 15)).foregroundStyle(state.queueOpen ? CU.accent : CU.ink)
                    .frame(width: 40, height: 40).glassEffect(CU.glass, in: Circle())
            }
            .buttonStyle(.plain).accessibilityLabel(state.queueOpen ? "Close Up Next" : "Up Next")
        }
        .frame(height: 44)
    }

    @ViewBuilder private var nowPlayingDisplay: some View {
        if state.library.isLive || state.player.current != nil { liveDisplay } else { sampleDisplay }
    }

    private var liveDisplay: some View {
        let p = state.player
        return Group {
            if let c = p.current {
                HStack(spacing: 10) {
                    CoverView(album: AlbumItem(id: -1, title: c.album, artist: c.artist, year: 0, genre: "", format: "", owned: true, hue: 200, coverArt: c.coverArt))
                        .frame(width: 32).clipShape(RoundedRectangle(cornerRadius: 5)).accessibilityHidden(true)
                    VStack(spacing: 1) {
                        Text(c.title).fontWeight(.semibold).lineLimit(1)
                        Text(p.phase == .loading ? "Loading…" : (c.album.isEmpty ? c.artist : "\(c.artist) — \(c.album)")).foregroundStyle(CU.muted).lineLimit(1)
                        if case .failed(let m) = p.phase { Text(m).foregroundStyle(CU.accent).lineLimit(1) }
                    }
                    .font(.system(size: 12)).frame(maxWidth: .infinity)
                    Text(PlayerModel.clock(p.position)).font(.system(size: 11)).monospacedDigit().foregroundStyle(CU.muted)
                }
                .padding(.horizontal, 10).frame(height: 44)
                .overlay(alignment: .bottomLeading) {
                    GeometryReader { g in Rectangle().fill(CU.accent).frame(width: g.size.width * p.fraction, height: 3) }.frame(height: 3)
                }
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                .accessibilityElement(children: .combine)
                .accessibilityLabel("Now playing: \(c.title), \(c.artist), \(PlayerModel.clock(p.position)) of \(PlayerModel.clock(p.duration))")
            } else {
                Text("Nothing playing").font(.system(size: 12)).foregroundStyle(CU.muted).frame(maxWidth: .infinity).frame(height: 44)
            }
        }
        .glassEffect(CU.glass, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private var sampleDisplay: some View {
        let a = Fixtures.albums[0]
        return HStack(spacing: 10) {
            CoverView(album: a).frame(width: 32).clipShape(RoundedRectangle(cornerRadius: 5))
            VStack(spacing: 1) {
                Text("After the Flood").fontWeight(.semibold)
                Text("Talk Talk — Laughing Stock").foregroundStyle(CU.muted)
            }
            .font(.system(size: 12)).frame(maxWidth: .infinity)
            Text("3:12").font(.system(size: 11)).foregroundStyle(CU.muted)
        }
        .padding(.horizontal, 10).frame(height: 44)
        .overlay(alignment: .bottomLeading) {
            GeometryReader { g in Rectangle().fill(CU.accent).frame(width: g.size.width * 0.33, height: 3) }
                .frame(height: 3)
        }
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .glassEffect(CU.glass, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Now playing: After the Flood, Talk Talk, 3:12 of 9:41")
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
