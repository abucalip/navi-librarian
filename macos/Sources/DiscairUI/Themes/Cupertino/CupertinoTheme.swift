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
                .padding(.leading, 236)
                .padding(.top, 66)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                .background(Color.white)
                .padding(.leading, 0)

            CupertinoSidebar(state: state)
            CupertinoToolbar(state: state)
                .padding(.leading, 238).padding(.trailing, state.screen == .queue ? CupertinoQueueInspector.width + 16 : 16).padding(.top, 12)
            if state.screen == .queue {
                CupertinoQueueInspector(state: state).frame(maxWidth: .infinity, alignment: .trailing)
            }
            // Top right under the search pill (owner decision), not at the bottom of the window or sidebar (HIG).
            HStack(spacing: 5) {
                Circle().fill(Color.green).frame(width: 7, height: 7)
                Text(state.connectionLabel)
            }
            .font(.system(size: 11)).foregroundStyle(CU.muted)
            .accessibilityElement(children: .combine)
            .accessibilityLabel("Connection: \(state.connectionLabel)")
            .frame(maxWidth: .infinity, alignment: .trailing)
            .padding(.trailing, state.screen == .queue ? CupertinoQueueInspector.width + 20 : 20).padding(.top, 52)
        }
        .foregroundStyle(CU.ink)
        .clipShape(RoundedRectangle(cornerRadius: CU.windowRadius, style: .continuous))
        .background(WindowConfigurator())
    }

    @ViewBuilder private var content: some View {
        switch state.screen {
        case .home: CupertinoHome(state: state)
        case .album: CupertinoAlbum(state: state)
        case .queue: CupertinoAlbumsGrid()
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
        case .artist: "Artists"
        default: "Recently Added"
        }
    }
    private let nav: [(String, String)] = [
        ("house", "Home"), ("sparkles", "New"), ("clock", "Recently Added"), ("music.mic", "Artists"),
        ("square.stack", "Albums"), ("music.note", "Songs"), ("dot.radiowaves.left.and.right", "Gap Radar"),
        ("clock.arrow.circlepath", "History"), ("arrow.down.circle", "Downloads"),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            TrafficLights().padding(.leading, 6).padding(.bottom, 20)
            ForEach(nav, id: \.1) { icon, label in
                let on = label == selected
                HStack(spacing: 9) {
                    Image(systemName: icon).foregroundStyle(CU.accent).frame(width: 18)
                    Text(label).fontWeight(on ? .semibold : .regular)
                    Spacer()
                    if label == "Downloads" {
                        Text("2").font(.system(size: 11, weight: .bold)).foregroundStyle(.white)
                            .padding(.horizontal, 7).background(CU.accent, in: Capsule())
                    }
                }
                .font(.system(size: 13.5))
                .foregroundStyle(on ? CU.accent : CU.ink)
                .padding(.horizontal, 10).padding(.vertical, 6)
                .background(on ? CU.accent.opacity(0.13) : .clear, in: RoundedRectangle(cornerRadius: 9, style: .continuous))
                .accessibilityElement(children: .combine)
            }
            Text("Playlists").font(.system(size: 11, weight: .bold)).foregroundStyle(CU.muted).padding(.leading, 10).padding(.top, 14)
            ForEach(["Unplayed from artists I own", "1990s, rated 4+", "Late night"], id: \.self) { p in
                HStack(spacing: 9) {
                    Image(systemName: "music.note.list").foregroundStyle(CU.accent).frame(width: 18)
                    Text(p).lineLimit(1)
                }
                .font(.system(size: 13.5)).padding(.horizontal, 10).padding(.vertical, 6)
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
                ForEach(["shuffle", "backward.fill", "pause.fill", "forward.fill", "repeat"], id: \.self) { s in
                    Image(systemName: s).font(.system(size: 15)).accessibilityLabel(s)
                }
            }
            .padding(.horizontal, 18).frame(height: 40)
            .glassEffect(CU.glass, in: Capsule())

            Button { state.screen = .nowPlaying } label: { nowPlayingDisplay }
                .buttonStyle(.plain).frame(maxWidth: 470)

            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                Text("Search  ⌘K")
            }
            .foregroundStyle(CU.muted).padding(.horizontal, 14).frame(width: 210, height: 36)
            .glassEffect(CU.glass, in: Capsule())
        }
        .frame(height: 44)
    }

    private var nowPlayingDisplay: some View {
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
