import AppKit
import SwiftUI

/// Zine Spread (Neobrut, light). Spec: `docs/design/macos-m4/mockups.html`, `R.zine`.
/// A daily paper: masthead, ticker, reading-order pages and a black player strip at the bottom. No sidebar.
struct ZineTheme: DiscairTheme {
    let id = ThemeID.zine
    let name = "Zine Spread"
    let colorScheme = ColorScheme.light

    func window(state: AppState) -> AnyView { AnyView(ZineWindow(state: state)) }
}

struct ZineWindow: View {
    let state: AppState

    var body: some View {
        VStack(spacing: 0) {
            ZineMasthead(state: state)
            ZineTicker(live: state.library.isLive, text: state.acquisition.tickerText)
            ScrollView {
                page.padding(.horizontal, 22).padding(.vertical, 16)
                    .frame(maxWidth: .infinity, alignment: .topLeading)
            }
            .scrollEdgeEffectStyle(.hard, for: .top)
            ZinePlayerStrip(state: state)
        }
        .overlay(alignment: .bottom) { ZineNotice(state: state).padding(.bottom, 70) }
        .foregroundStyle(Z.ink)
        .background(Z.paper)
        .overlay { Rectangle().strokeBorder(Z.ink, lineWidth: 3).allowsHitTesting(false) }
        .background(WindowConfigurator(canDragAt: { [state] p, _ in !(state.screen == .queue && p.y > 100) }))
    }

    @ViewBuilder private var page: some View {
        switch state.screen {
        case .home: ZineHome(state: state)
        case .album: ZineAlbum(state: state)
        case .nowPlaying: ZineNowPlaying(state: state)
        case .queue, .albums: ZineQueue(state: state)
        case .library, .artists: ZineLibrary(state: state)
        case .artist: ZineArtist(state: state)
        case .settings: ZineSettings(state: state)
        case .downloads: ZineDownloads(state: state)
        case .discover: ZineDiscover(state: state)
        case .equalizer: ZineEQ(state: state)
        case .gapRadar: ZineGapRadar(state: state)
        case .connections: GraphExplorerView(state: state, style: .zine)
        case .atlas: AtlasView(state: state, style: .zine)
        case .timeline: TimelineView(state: state, style: .zine)
        case .smartPlaylists: ZineSmartPlaylists(state: state)
        case .history: ZineHistory(state: state)
        case .insights: ZineInsights(state: state)
        case .recent: ZineHome(state: state)
        }
    }
}

/// Which masthead section is lit for a screen (as drawn in the mockup).
private func activeSection(_ s: Screen) -> String {
    switch s {
    case .home, .nowPlaying, .queue: "Home"
    case .album, .library, .albums: "Library"
    case .artist, .artists: "Artists"
    case .settings: "Settings"
    case .downloads: "Downloads"
    case .discover, .insights: "Discover"
    case .equalizer: "Settings"
    case .gapRadar, .connections, .atlas, .timeline: "Artists"
    case .smartPlaylists: "Library"
    case .history, .recent: "Library"
    }
}

struct ZineMasthead: View {
    let state: AppState
    private let sections: [(String, Screen?)] = [
        ("Home", .home), ("Library", .library), ("Artists", .artists),
        ("Discover", .discover), ("Downloads", .downloads), ("Settings", .settings),
    ]

    var body: some View {
        VStack(spacing: 0) {
            VStack(spacing: 2) {
                // Dateline. The connection indicator and the unencrypted badge live here, at the top (owner decision).
                HStack {
                    Mono("Vol. 1 · No. 307")
                    Spacer()
                    HStack(spacing: 6) {
                        Mono(state.library.isLive ? Date.now.formatted(.dateTime.weekday(.wide).day().month(.wide).year()) + " ·" : "Tuesday 3 November 2026 ·")
                        Mono(state.connectionLabel)
                    }
                    .accessibilityElement(children: .combine)
                    .accessibilityLabel("Connection: \(state.connectionLabel)")
                    Spacer()
                    Mono(state.library.totalAlbumsText)
                }
                .padding(.trailing, 70).padding(.bottom, 4)
                .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 2) }
                Text("The Discair Daily")
                    .font(Z.an(80)).textCase(.uppercase).tracking(0.8).lineLimit(1).minimumScaleFactor(0.6)
                    .frame(maxWidth: .infinity)
                    .padding(.top, 2).padding(.bottom, 4)
                    .accessibilityAddTraits(.isHeader)
            }
            .padding(.horizontal, 22).padding(.top, 8)
            .overlay(alignment: .topTrailing) { ZineLights().padding(.trailing, 14).padding(.top, 8) }

            HStack(spacing: 0) {
                ForEach(Array(sections.enumerated()), id: \.offset) { i, s in
                    let on = s.0 == activeSection(state.screen)
                    Button { if let t = s.1 { state.screen = t } } label: {
                        Text(s.0).font(Z.mono(12, bold: true)).textCase(.uppercase).tracking(0.96)
                            .foregroundStyle(on ? Z.yellow : Z.ink)
                            .frame(maxWidth: .infinity).padding(.vertical, 7)
                            .background(on ? Z.ink : .clear)
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityAddTraits(on ? .isSelected : [])
                    if i < sections.count - 1 { Rectangle().fill(Z.ink).frame(width: 3) }
                }
            }
            .fixedSize(horizontal: false, vertical: true)
            .overlay(alignment: .top) { Rectangle().fill(Z.ink).frame(height: 3) }
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }
            .padding(.bottom, 4)
        }
        .background(Z.paper)
    }
}

/// The theme's own window controls: square, 2 pt ink border, first one red. Same actions as the system buttons.
struct ZineLights: View {
    var body: some View {
        HStack(spacing: 6) {
            box(Z.red, "Close") { NSApp.keyWindow?.close() }
            box(Z.white, "Minimise") { NSApp.keyWindow?.miniaturize(nil) }
            box(Z.white, "Zoom") { NSApp.keyWindow?.zoom(nil) }
        }
    }
    private func box(_ c: Color, _ label: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) { Rectangle().fill(c).frame(width: 14, height: 14).zBorder(2) }
            .buttonStyle(.plain).accessibilityLabel(label)
    }
}

/// Pipeline as a ticker: acquisition progress while listening.
struct ZineTicker: View {
    /// A live library has no acquisition feed yet (Downloads is a later slice), so the ticker says so instead of showing sample items.
    var live = false
    var text = "Pipeline: no downloads in progress"
    var body: some View {
        Mono(live ? text : "▶ Downloading: Tago Mago 64%  ■  Queued: Zombie  ■  Imported: Heaven or Las Vegas  ■  Failed: none")
            .lineLimit(1).fixedSize()
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 22).padding(.vertical, 4)
            .background(Z.yellow)
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 3) }
            .clipped()
            .accessibilityLabel(live ? text : "Pipeline: downloading Tago Mago 64 percent, queued Zombie, imported Heaven or Las Vegas, failed none")
    }
}

/// Black strip at the bottom. Kept where drawn (owner decision); transport is also in the menu bar and media keys.
struct ZinePlayerStrip: View {
    let state: AppState
    var body: some View {
        let p = state.player
        let sample = !state.library.isLive && p.current == nil   // the mockup's sample strip
        let a = Fixtures.albums[0]
        let idle = !sample && p.current == nil
        HStack(spacing: 16) {
            if let c = p.current, !idle {
                    PlayerBarCover(artist: c.artist, album: c.album, disc: c.disc, spinning: p.isPlaying, side: 34, border: Z.paper,
                                   fallback: { state.screen = .nowPlaying }) {
                        CoverView(album: AlbumItem(id: -1, title: c.album, artist: c.artist, year: 0, genre: "", format: "", owned: true, hue: 200, remoteID: c.albumID, coverArt: c.coverArt))
                    }
            }
                HStack(spacing: 16) {
                    if idle {
                        Text("Nothing playing").font(Z.an(20)).textCase(.uppercase).foregroundStyle(Z.yellow)
                    } else if let c = p.current {
                        Text(c.title).font(Z.an(20)).textCase(.uppercase).foregroundStyle(Z.yellow).lineLimit(1)
                        HStack(spacing: 6) {
                            Button { state.openCurrentArtist() } label: { Mono(p.phase == .loading ? "Loading…" : c.artist).foregroundStyle(Z.paper) }
                                .buttonStyle(.plain).accessibilityLabel("Open artist \(c.artist)")
                            if !c.album.isEmpty, p.phase != .loading {
                                Mono("·").foregroundStyle(Z.paper)
                                Button { state.openCurrentAlbum() } label: { Mono(c.album).foregroundStyle(Z.paper) }
                                    .buttonStyle(.plain).accessibilityLabel("Open album \(c.album)")
                            }
                            PlaybackClock(player: p) { pos in Mono("· \(PlayerModel.clock(pos)) / \(PlayerModel.clock(p.duration))").foregroundStyle(Z.paper) }
                        }
                    } else {
                        CoverView(album: a).frame(width: 34).overlay { Rectangle().strokeBorder(Z.paper, lineWidth: 2) }
                        Text("After the Flood").font(Z.an(20)).textCase(.uppercase).foregroundStyle(Z.yellow)
                        Mono("Talk Talk · 3:12 / 9:41").foregroundStyle(Z.paper)
                    }
                }
                .accessibilityElement(children: .contain)

            if sample {
                ZStack(alignment: .leading) {
                    Rectangle().fill(Color(white: 0.267)).frame(height: 8)
                    GeometryReader { g in Rectangle().fill(Z.yellow).frame(width: g.size.width * 0.33, height: 8) }.frame(height: 8)
                }
                .frame(maxWidth: 360)
                .accessibilityElement().accessibilityLabel("Position").accessibilityValue("33 percent")
            } else {
                DragBar(value: p.fraction, height: 8, track: Color(white: 0.267), fill: Z.yellow, rounded: false, label: "Position",
                        valueText: { "\(PlayerModel.clock($0 * p.duration)) of \(PlayerModel.clock(p.duration))" }) { p.seek(toFraction: $0) }
                    .frame(maxWidth: 360)
            }

            Spacer(minLength: 0)
            HStack(spacing: 12) {
                Button { p.toggleShuffle() } label: { Image(systemName: "shuffle").foregroundStyle(p.shuffle ? Z.yellow : Z.paper) }
                    .accessibilityLabel(p.shuffle ? "Shuffle, on" : "Shuffle, off")
                Button { p.previous() } label: { Image(systemName: "backward.fill") }.accessibilityLabel("Previous")
                Button { p.togglePlayPause() } label: { Image(systemName: p.isPlaying || sample ? "pause.fill" : "play.fill") }
                    .accessibilityLabel(p.isPlaying ? "Pause" : "Play").disabled(p.current == nil && !sample)
                Button { p.next() } label: { Image(systemName: "forward.fill") }.accessibilityLabel("Next").disabled(p.current == nil)
                Button { p.cycleRepeat() } label: {
                    Image(systemName: p.repeatMode == .one ? "repeat.1" : "repeat").foregroundStyle(p.repeatMode == .off ? Z.paper : Z.yellow)
                }
                .accessibilityLabel("Repeat, \(p.repeatMode.rawValue)")
                Button { state.screen = .queue } label: { Image(systemName: "list.bullet") }.accessibilityLabel("Up Next")
                if sample { Mono("· FLAC 16/44") }
            }
            .buttonStyle(.plain)
            .font(.system(size: 14, weight: .bold)).foregroundStyle(Z.paper)
        }
        .padding(.horizontal, 22).frame(height: 54)
        .background(Z.ink)
        // Anywhere on the strip that is not a control opens Now Playing; the controls and links keep their own clicks.
        .contentShape(Rectangle())
        .onTapGesture { state.screen = .nowPlaying }
        .accessibilityAction(named: "Open Now Playing") { state.screen = .nowPlaying }
    }
}

/// Not for me waits a few seconds so it can be undone; failures show here until closed.
struct ZineNotice: View {
    let state: AppState
    var body: some View {
        let acq = state.acquisition
        if let p = acq.pending {
            HStack(spacing: 12) {
                Mono("Not for me: \(p.title)", bold: true).lineLimit(1)
                Button("Undo") { acq.undo() }.buttonStyle(ZineButtonStyle(small: true))
                Button("Never suggest \(p.artist)") { Task { await acq.neverSuggest() } }.buttonStyle(ZineButtonStyle(small: true))
            }
            .padding(.horizontal, 12).padding(.vertical, 8).background(Z.yellow).zBorder(3).zShadow(4)
            .accessibilityElement(children: .contain)
        } else if let n = acq.notice {
            HStack(spacing: 12) {
                Mono(n, bold: true).lineLimit(2)
                Button("Dismiss") { acq.clearNotice() }.buttonStyle(ZineButtonStyle(small: true))
            }
            .padding(.horizontal, 12).padding(.vertical, 8).background(Z.yellow).zBorder(3).zShadow(4)
        }
    }
}
