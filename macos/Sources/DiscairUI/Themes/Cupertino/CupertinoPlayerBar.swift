import SwiftUI

/// The player along the bottom of the window: one rectangle with the artwork, the song, a line in the middle (the synced lyric,
/// or a fact when there are no synced lyrics), the travel buttons, the time and the progress bar. Behind it sit the song's cover,
/// blurred like the album page's, and the song's sound graph as quiet bars from the floor. The buttons keep their size; the bar
/// gives them height.
struct CupertinoPlayerBar: View {
    let state: AppState
    static let height: CGFloat = 92
    @State private var tint: ArtworkTint?
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

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
            .task(id: "\(p.current?.coverArt ?? "")|\(state.artwork.generation)") {
                guard let id = p.current?.coverArt else { tint = nil; return }
                tint = await state.artwork.tint(coverArt: id)
            }
            // The lyrics of the playing song are read for the middle line, only while that line is switched on.
            .task(id: "\(p.current?.songID ?? "")|\(state.barOptions.showLyrics)|\(state.lyrics.state == .idle)") {
                guard state.barOptions.showLyrics, let c = p.current else { return }
                state.lyrics.show(songID: c.songID, title: c.title)
            }
            .task(id: "\(p.current?.songID ?? "")|\(state.barOptions.showFacts)|\(state.session?.navidrome != nil)") {
                guard state.barOptions.showFacts else { return }
                await state.facts.load(for: p.current, navidrome: state.session?.navidrome, librarian: state.session?.librarian)
            }
            .task(id: "\(p.current?.songID ?? "")|\(state.barOptions.showFacts)") {
                // One new line every 14 seconds while the song plays.
                guard state.barOptions.showFacts, !RenderMode.offscreenScreenshot else { return }
                while !Task.isCancelled {
                    try? await Task.sleep(for: .seconds(14))
                    if p.isPlaying { state.facts.advance() }
                }
            }
    }

    /// The width left of the player for the artwork square (or the connection text), in line with the sidebar.
    static let sidebarSlot: CGFloat = 236

    private var coverItem: AlbumItem? {
        guard let c = p.current, !(c.coverArt ?? "").isEmpty else { return nil }
        return AlbumItem(id: -1, title: c.album, artist: c.artist, year: 0, genre: "", format: "", owned: true, hue: 200, remoteID: c.albumID, coverArt: c.coverArt)
    }

    /// A painted rectangle, not glass: glass drops its tint when the window is not the active one. The cover's colour is the
    /// ground; the cover itself, blurred as on the album page, goes over it once it has loaded, with a dimming layer so the
    /// white text keeps its contrast.
    @ViewBuilder private var plate: some View {
        if let tint, !RenderMode.offscreenScreenshot {
            ZStack {
                LinearGradient(colors: [tint.color, ArtworkTint(hue: tint.hue, saturation: tint.saturation, brightness: max(0.2, tint.brightness - 0.1)).color],
                               startPoint: .top, endPoint: .bottom)
                if let cover = coverItem { BlurredArtwork(album: cover, radius: 24); Color.black.opacity(0.28) }
            }
            .clipShape(shape)
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
            nowPlayingButton
            middle
            if let q = p.current?.qualityLabel {
                Text(q).font(.system(size: 10, weight: .semibold, design: .monospaced)).foregroundStyle(secondary)
                    .padding(.horizontal, 6).padding(.vertical, 2)
                    .overlay(RoundedRectangle(cornerRadius: 4, style: .continuous).stroke(secondary.opacity(0.6), lineWidth: 1))
                    .fixedSize().accessibilityLabel("Quality \(q)")
            }
            if p.current != nil { lineSwitches }
            transport
            PlaybackClock(player: p) { Text("\(PlayerModel.clock($0)) / \(PlayerModel.clock(p.duration))").font(.system(size: 12)).monospacedDigit().foregroundStyle(secondary) }
                .padding(.leading, 6)
        }
        .padding(.horizontal, 16).frame(height: 68)
        .background {
            ZStack {
                plate
                if tint != nil, let peaks = p.waveform, !peaks.isEmpty { PlayerBarGraph(peaks: peaks, fraction: p.fraction).clipShape(shape) }
            }
        }
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

    private var nowPlayingButton: some View {
        Group {
            if let c = p.current {
                Button { state.screen = .nowPlaying } label: {
                    HStack(spacing: 14) {
                        CoverView(album: AlbumItem(id: -1, title: c.album, artist: c.artist, year: 0, genre: "", format: "", owned: true, hue: 200, remoteID: c.albumID, coverArt: c.coverArt))
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
        }
        .frame(minWidth: 150, idealWidth: 270, maxWidth: p.current == nil ? .infinity : 290, alignment: .leading)
        .layoutPriority(1)
    }

    // MARK: The line in the middle

    /// What the middle shows now: a synced lyric line, or (with no synced lyrics) a fact, or nothing.
    private enum Line: Equatable { case lyric(Int, String), fact(PlayerFact), none }

    private func line(at position: Double) -> Line {
        let options = state.barOptions
        guard p.current != nil else { return .none }
        if options.showLyrics, state.lyrics.state == .timed {
            // Timed lyrics own the middle: between lines it stays quiet rather than switching to a fact and back.
            if let i = state.lyrics.currentIndex(positionSeconds: position), state.lyrics.lines.indices.contains(i) {
                let text = state.lyrics.lines[i].text.trimmingCharacters(in: .whitespaces)
                if !text.isEmpty { return .lyric(i, text) }
            }
            return .none
        }
        if options.showFacts, let fact = state.facts.current, state.facts.songID == p.current?.songID { return .fact(fact) }
        return .none
    }

    private var middle: some View {
        PlaybackClock(player: p) { position in
            let now = line(at: position)
            ZStack {
                switch now {
                case .lyric(let i, let text):
                    MarqueeLine(reduceMotion: reduceMotion) { Text(text).font(.system(size: 13.5, weight: .semibold)) }
                        .id("l\(i)").transition(slide).accessibilityElement(children: .ignore).accessibilityLabel("Lyric: \(text)")
                case .fact(let fact):
                    MarqueeLine(reduceMotion: reduceMotion) { factText(fact) }.id(fact.id).transition(slide)
                case .none: Color.clear
                }
            }
            .lineLimit(1).truncationMode(.tail).multilineTextAlignment(.center)
            .frame(maxWidth: .infinity).frame(height: 22).clipped()
            .animation(reduceMotion || RenderMode.offscreenScreenshot ? nil : .easeInOut(duration: 0.45), value: now)
        }
        .frame(maxWidth: .infinity)
    }

    private var slide: AnyTransition {
        reduceMotion ? .identity : .asymmetric(insertion: .move(edge: .bottom).combined(with: .opacity), removal: .move(edge: .top).combined(with: .opacity))
    }

    @ViewBuilder private func factText(_ fact: PlayerFact) -> some View {
        let label = Text(fact.text).font(.system(size: 12.5)).foregroundStyle(ink.opacity(0.86))
        if let url = fact.sourceURL {
            Button { NSWorkspace.shared.open(url) } label: { label }.buttonStyle(.plain)
                .help("\(fact.source). Opens the page this comes from.").accessibilityLabel("Fact: \(fact.text). Source \(fact.source). Opens the page")
        } else {
            label.help("Source: \(fact.source)").accessibilityLabel("Fact: \(fact.text). Source \(fact.source)")
        }
    }

    // MARK: The two switches, right of the quality tag

    private var lineSwitches: some View {
        HStack(spacing: 4) {
            switchButton(on: state.barOptions.showLyrics, label: "Lyrics in the player bar") {
                QuoteMark().frame(width: 17, height: 17)
            } toggle: { state.barOptions.showLyrics.toggle() }
            switchButton(on: state.barOptions.showFacts, label: "Facts in the player bar") {
                Image(systemName: "info.circle").font(.system(size: 14, weight: .medium))
            } toggle: { state.barOptions.showFacts.toggle() }
        }
    }

    private func switchButton<Icon: View>(on: Bool, label: String, @ViewBuilder icon: () -> Icon, toggle: @escaping () -> Void) -> some View {
        Button(action: toggle) {
            icon().foregroundStyle(on ? ink : secondary.opacity(0.8))
                .frame(width: 26, height: 26)
                .background(RoundedRectangle(cornerRadius: 7, style: .continuous).fill(ink.opacity(on ? 0.22 : 0)))
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .help(on ? "\(label): on" : "\(label): off")
        .accessibilityLabel(label).accessibilityValue(on ? "On" : "Off").accessibilityAddTraits(.isToggle)
    }
}

/// The quote mark of the Android player's Lyrics tab (Material "format quote"), drawn from the same path so the two match.
struct QuoteMark: Shape {
    func path(in rect: CGRect) -> Path {
        let k = min(rect.width, rect.height) / 24
        func pt(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: rect.minX + x * k, y: rect.minY + y * k) }
        var p = Path()
        for dx: CGFloat in [0, 8] {       // two marks: M6,17 h3 l2,-4 V7 H5 v6 h3 z, then the same moved 8 right
            p.move(to: pt(6 + dx, 17)); p.addLine(to: pt(9 + dx, 17)); p.addLine(to: pt(11 + dx, 13)); p.addLine(to: pt(11 + dx, 7))
            p.addLine(to: pt(5 + dx, 7)); p.addLine(to: pt(5 + dx, 13)); p.addLine(to: pt(8 + dx, 13)); p.closeSubpath()
        }
        return p
    }
}

/// The song's sound graph behind the player bar: thin bars from the floor, played part a little brighter. Kept quiet (under a
/// quarter white, at most half the bar's height) so the text over it stays easy to read. The same 1000 peaks as the seek bar.
struct PlayerBarGraph: View {
    let peaks: [Float]
    let fraction: Double

    var body: some View {
        Canvas { ctx, size in
            let step: CGFloat = 3, width: CGFloat = 2
            let count = max(1, Int(size.width / step))
            let floorY = size.height - 4                      // above the 4 pt progress line
            let top = size.height * 0.5
            for i in 0..<count {
                let lo = i * peaks.count / count, hi = max(lo + 1, (i + 1) * peaks.count / count)
                let value = CGFloat(peaks[lo..<min(hi, peaks.count)].max() ?? 0)
                let h = max(1.5, value * top)
                let played = Double(i) / Double(count) <= fraction
                ctx.fill(Path(roundedRect: CGRect(x: CGFloat(i) * step, y: floorY - h, width: width, height: h), cornerRadius: 1),
                         with: .color(.white.opacity(played ? 0.22 : 0.11)))
            }
        }
        .allowsHitTesting(false).accessibilityHidden(true)
    }
}


/// One line that fits stays centred; one that does not fit scrolls from right to left, over and over with a gap between the
/// two passes, and is cut off cleanly at the left edge of its own frame, so it never runs under the song, artist and album text
/// beside it. With Reduce Motion it stays put and is cut with an ellipsis.
private struct MarqueeWidthKey: PreferenceKey {
    static let defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = max(value, nextValue()) }
}

private struct MarqueeLine<Content: View>: View {
    let reduceMotion: Bool
    @ViewBuilder var content: Content
    @State private var textWidth: CGFloat = 0
    @State private var start = Date()
    private let gap: CGFloat = 48
    private let speed: Double = 38
    private let pause: Double = 1.4

    var body: some View {
        GeometryReader { g in
            let overflow = textWidth > g.size.width + 0.5 && !reduceMotion
            Group {
                if overflow {
                    SwiftUI.TimelineView(.animation) { tl in
                        let cycle = Double(textWidth + gap)
                        let t = max(0, tl.date.timeIntervalSince(start) - pause)
                        HStack(spacing: gap) { content.fixedSize(); content.fixedSize() }
                            .offset(x: -CGFloat((t * speed).truncatingRemainder(dividingBy: cycle)))
                    }
                    .frame(width: g.size.width, height: g.size.height, alignment: .leading)
                } else {
                    content.lineLimit(1).truncationMode(.tail)
                        .frame(width: g.size.width, height: g.size.height, alignment: reduceMotion ? .leading : .center)
                }
            }
            .frame(width: g.size.width, height: g.size.height, alignment: .leading)
            .clipped()
        }
        .background(
            content.fixedSize().background(GeometryReader { Color.clear.preference(key: MarqueeWidthKey.self, value: $0.size.width) }).hidden()
        )
        .onPreferenceChange(MarqueeWidthKey.self) { textWidth = $0; start = Date() }
        .frame(height: 22)
    }
}
