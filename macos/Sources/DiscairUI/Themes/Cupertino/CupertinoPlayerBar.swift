import SwiftUI

/// The player along the bottom of the window: one rectangle with the artwork, the song, the travel buttons, the time and the
/// progress bar. It takes the tint of the playing song's cover. The buttons keep their size; the bar gives them height.
struct CupertinoPlayerBar: View {
    let state: AppState
    static let height: CGFloat = 92
    @State private var tint: ArtworkTint?

    private var p: PlayerModel { state.player }
    /// White on a tint (tints are kept dark); the usual ink and glass when nothing is playing.
    private var ink: Color { tint != nil ? .white : CU.ink }
    private var secondary: Color { tint != nil ? .white.opacity(0.72) : CU.muted }
    private var shape: RoundedRectangle { RoundedRectangle(cornerRadius: 16, style: .continuous) }

    var body: some View {
        display
            .padding(.leading, Self.sidebarSlot).padding(.trailing, 18)
            .frame(height: Self.height)
            .foregroundStyle(ink)
            .animation(RenderMode.offscreenScreenshot ? nil : .easeInOut(duration: 0.5), value: tint)
            .task(id: p.current?.coverArt) {
                guard let id = p.current?.coverArt else { tint = nil; return }
                tint = await state.artwork.tint(coverArt: id)
            }
    }

    /// The width left of the player for the artwork square (or the connection text), in line with the sidebar.
    static let sidebarSlot: CGFloat = 236

    /// A tinted rectangle is painted, not glass: glass drops its tint when the window is not the active one.
    @ViewBuilder private var plate: some View {
        if let tint, !RenderMode.offscreenScreenshot {
            shape.fill(LinearGradient(colors: [tint.color, ArtworkTint(hue: tint.hue, saturation: tint.saturation, brightness: max(0.2, tint.brightness - 0.1)).color],
                                      startPoint: .top, endPoint: .bottom))
                .overlay(shape.stroke(.white.opacity(0.12), lineWidth: 1))
        } else {
            Color.clear.glassEffect(CU.glass, in: shape)
        }
    }

    private var transport: some View {
        HStack(spacing: 10) {
            Button { p.toggleShuffle() } label: { Image(systemName: "shuffle").foregroundStyle(p.shuffle ? CU.accent : ink) }
                .accessibilityLabel(p.shuffle ? "Shuffle, on" : "Shuffle, off")
            Button { p.previous() } label: { Image(systemName: "backward.fill") }.accessibilityLabel("Previous")
            Button { p.togglePlayPause() } label: { Image(systemName: p.isPlaying ? "pause.fill" : "play.fill").font(.system(size: 22)) }
                .accessibilityLabel(p.isPlaying ? "Pause" : "Play").disabled(p.current == nil)
            Button { p.next() } label: { Image(systemName: "forward.fill") }.accessibilityLabel("Next").disabled(p.current == nil)
            Button { p.cycleRepeat() } label: {
                Image(systemName: p.repeatMode == .one ? "repeat.1" : "repeat").foregroundStyle(p.repeatMode == .off ? ink : CU.accent)
            }
            .accessibilityLabel("Repeat, \(p.repeatMode.rawValue)")
        }
        .buttonStyle(.plain).font(.system(size: 15))
    }

    private var display: some View {
        HStack(spacing: 14) {
            if let c = p.current {
                Button { state.screen = .nowPlaying } label: {
                    HStack(spacing: 14) {
                        CoverView(album: AlbumItem(id: -1, title: c.album, artist: c.artist, year: 0, genre: "", format: "", owned: true, hue: 200, coverArt: c.coverArt))
                            .frame(width: 50).clipShape(RoundedRectangle(cornerRadius: 7, style: .continuous)).accessibilityHidden(true)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(c.title).font(.system(size: 14, weight: .semibold)).lineLimit(1)
                            Text(p.phase == .loading ? "Loading…" : (c.album.isEmpty ? c.artist : "\(c.artist) — \(c.album)")).foregroundStyle(secondary).lineLimit(1)
                            if case .failed(let m) = p.phase { Text(m).foregroundStyle(CU.accent).lineLimit(1) }
                        }
                        .font(.system(size: 12.5)).frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Now playing: \(c.title), \(c.artist). Opens Now Playing")
            } else {
                Text("Nothing playing").font(.system(size: 12.5)).foregroundStyle(secondary).frame(maxWidth: .infinity, alignment: .leading)
            }
            transport
            PlaybackClock(player: p) { Text("\(PlayerModel.clock($0)) / \(PlayerModel.clock(p.duration))").font(.system(size: 12)).monospacedDigit().foregroundStyle(secondary) }
                .padding(.leading, 6)
        }
        .padding(.horizontal, 16).frame(height: 68)
        .background { plate }
        .overlay(alignment: .bottomLeading) {
            GeometryReader { g in
                ZStack(alignment: .leading) {
                    Rectangle().fill(ink.opacity(0.18))
                    Rectangle().fill(tint != nil ? Color.white : CU.accent).frame(width: g.size.width * p.fraction)
                }
            }
            .frame(height: 4).clipShape(UnevenRoundedRectangle(bottomLeadingRadius: 16, bottomTrailingRadius: 16))
        }
        .clipShape(shape)
    }
}
