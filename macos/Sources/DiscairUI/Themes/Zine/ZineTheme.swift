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
            ZineTicker()
            ScrollView {
                page.padding(.horizontal, 22).padding(.vertical, 16)
                    .frame(maxWidth: .infinity, alignment: .topLeading)
            }
            .scrollEdgeEffectStyle(.hard, for: .top)
            ZinePlayerStrip(state: state)
        }
        .foregroundStyle(Z.ink)
        .background(Z.paper)
        .overlay { Rectangle().strokeBorder(Z.ink, lineWidth: 3).allowsHitTesting(false) }
        .background(WindowConfigurator())
    }

    @ViewBuilder private var page: some View {
        switch state.screen {
        case .home: ZineHome(state: state)
        case .album: ZineAlbum(state: state)
        case .nowPlaying: ZineNowPlaying(state: state)
        case .queue, .albums: ZineQueue(state: state)
        case .library: ZineLibrary(state: state)
        case .artist: ZineArtist(state: state)
        case .settings: ZineSettings(state: state)
        }
    }
}

/// Which masthead section is lit for a screen (as drawn in the mockup).
private func activeSection(_ s: Screen) -> String {
    switch s {
    case .home, .nowPlaying, .queue: "Home"
    case .album, .library, .albums: "Library"
    case .artist: "Artists"
    case .settings: "Settings"
    }
}

struct ZineMasthead: View {
    let state: AppState
    private let sections: [(String, Screen?)] = [
        ("Home", .home), ("Library", .library), ("Artists", .artist),
        ("Discover", nil), ("Downloads", nil), ("Settings", .settings),
    ]

    var body: some View {
        VStack(spacing: 0) {
            VStack(spacing: 2) {
                // Dateline. The connection indicator and the unencrypted badge live here, at the top (owner decision).
                HStack {
                    Mono("Vol. 1 · No. 307")
                    Spacer()
                    HStack(spacing: 6) {
                        Mono("Tuesday 3 November 2026 ·")
                        Mono(state.connectionLabel)
                    }
                    .accessibilityElement(children: .combine)
                    .accessibilityLabel("Tuesday 3 November 2026. Connection: \(state.connectionLabel)")
                    Spacer()
                    Mono("Library 4,812 albums")
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
    var body: some View {
        Mono("▶ Downloading: Tago Mago 64%  ■  Queued: Zombie  ■  Imported: Heaven or Las Vegas  ■  Failed: none")
            .lineLimit(1).fixedSize()
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 22).padding(.vertical, 4)
            .background(Z.yellow)
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 3) }
            .clipped()
            .accessibilityLabel("Pipeline: downloading Tago Mago 64 percent, queued Zombie, imported Heaven or Las Vegas, failed none")
    }
}

/// Black strip at the bottom. Kept where drawn (owner decision); transport is also in the menu bar and media keys.
struct ZinePlayerStrip: View {
    let state: AppState
    var body: some View {
        let a = Fixtures.albums[0]
        HStack(spacing: 16) {
            Button { state.screen = .nowPlaying } label: {
                HStack(spacing: 16) {
                    CoverView(album: a).frame(width: 34).overlay { Rectangle().strokeBorder(Z.paper, lineWidth: 2) }
                    Text("After the Flood").font(Z.an(20)).textCase(.uppercase).foregroundStyle(Z.yellow)
                    Mono("Talk Talk · 3:12 / 9:41").foregroundStyle(Z.paper)
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Now playing: After the Flood, Talk Talk, 3:12 of 9:41. Opens Now Playing")

            ZStack(alignment: .leading) {
                Rectangle().fill(Color(white: 0.267)).frame(height: 8)
                GeometryReader { g in Rectangle().fill(Z.yellow).frame(width: g.size.width * 0.33, height: 8) }.frame(height: 8)
            }
            .frame(maxWidth: 360)
            .accessibilityElement().accessibilityLabel("Position").accessibilityValue("33 percent")

            Spacer(minLength: 0)
            HStack(spacing: 12) {
                ForEach(["shuffle", "backward.fill", "pause.fill", "forward.fill"], id: \.self) { s in
                    Image(systemName: s).accessibilityLabel(s.replacingOccurrences(of: ".fill", with: ""))
                }
                Button { state.screen = .queue } label: { Image(systemName: "list.bullet") }
                    .buttonStyle(.plain).accessibilityLabel("Up Next")
                Mono("· FLAC 16/44")
            }
            .font(.system(size: 14, weight: .bold)).foregroundStyle(Z.paper)
        }
        .padding(.horizontal, 22).frame(height: 54)
        .background(Z.ink)
    }
}
