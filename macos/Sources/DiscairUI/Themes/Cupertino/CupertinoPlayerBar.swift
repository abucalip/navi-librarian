import DiscairLibrarian
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
    /// White ink is used on the song's tint, and on the dark plate a station has (mockup B1); a station never takes the song's tint.
    private var tinted: Bool { p.live != nil || tint != nil }
    private var ink: Color { tinted ? CU.onMedia : CU.text }
    private var secondary: Color { tinted ? CU.onMedia.opacity(0.72) : CU.textSecondary }
    private var shape: RoundedRectangle { RoundedRectangle(cornerRadius: 16, style: .continuous) }

    var body: some View {
        display
            .padding(.leading, Self.sidebarSlot).padding(.trailing, 16)
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
        if p.live != nil {
            LiveStationPlate.gradient.clipShape(shape).overlay(shape.stroke(CU.onMedia.opacity(0.12), lineWidth: 1))
        } else if let tint, !RenderMode.offscreenScreenshot {
            ZStack {
                LinearGradient(colors: [tint.color, ArtworkTint(hue: tint.hue, saturation: tint.saturation, brightness: max(0.2, tint.brightness - 0.1)).color],
                               startPoint: .top, endPoint: .bottom)
                if let cover = coverItem { BlurredArtwork(album: cover, radius: 24); CU.shadowInk.opacity(0.28) }
            }
            .clipShape(shape)
            .overlay(shape.stroke(CU.onMedia.opacity(0.12), lineWidth: 1))
        } else {
            Color.clear.glassEffect(CU.glass, in: shape)
        }
    }

    private var transport: some View {
        HStack(spacing: 8) {
            Button { p.toggleShuffle() } label: { Image(systemName: "shuffle").foregroundStyle(p.shuffle ? CU.accent : ink) }
                .accessibilityLabel(p.shuffle ? "Shuffle, on" : "Shuffle, off")
            Button { p.previous() } label: { Image(systemName: "backward.fill") }.accessibilityLabel("Previous")
            Button { p.togglePlayPause() } label: { Image(systemName: p.isPlaying ? "pause.fill" : "play.fill").font(CU.Icon.transport()) }
                .accessibilityLabel(p.isPlaying ? "Pause" : "Play").disabled(p.current == nil)
            Button { p.next() } label: { Image(systemName: "forward.fill") }.accessibilityLabel("Next").disabled(p.current == nil)
            Button { p.cycleRepeat() } label: {
                Image(systemName: p.repeatMode == .one ? "repeat.1" : "repeat").foregroundStyle(p.repeatMode == .off ? ink : CU.accent)
            }
            .accessibilityLabel("Repeat, \(p.repeatMode.rawValue)")
        }
        .buttonStyle(.plain).font(CU.Icon.row())
    }

    private var display: some View {
        Group { if let live = p.live { liveRow(live) } else { barRow } }
            // Anywhere on the bar that is not a control opens Now Playing; the controls and links keep their own clicks.
            .contentShape(Rectangle())
            .onTapGesture { if p.current != nil || p.live != nil { state.screen = p.live != nil ? .stations : .nowPlaying } }
            .accessibilityAction(named: p.live != nil ? "Open Radio" : "Open Now Playing") {
                if p.current != nil || p.live != nil { state.screen = p.live != nil ? .stations : .nowPlaying }
            }
    }

    // MARK: Live station (mockup B1; B2 was dropped, see macos/DESIGN.md)

    private var liveStation: RadioStation? { p.live.flatMap { live in state.stations.stations.first { $0.id == live.stationID } } }

    /// A station is playing: its logo, name, LIVE and the time since tuning in, then previous, stop and next station and the star,
    /// and a 3 pt hairline in place of the progress line. Shuffle, repeat, the lyric and fact line and their switches, the quality
    /// tag, the sound graph and the clock are not drawn: none of them applies to a stream (S2.6).
    private func liveRow(_ live: LiveSession) -> some View {
        HStack(spacing: 16) {
            HStack(spacing: 16) {
                if let station = liveStation { StationLogo(station: station, size: 50, radiusFraction: 0.16) }
                else { RoundedRectangle(cornerRadius: 8, style: .continuous).fill(CU.bgFill).frame(width: 50, height: 50) }
                VStack(alignment: .leading, spacing: 4) {
                    Text(live.name).font(CU.Font.body.weighted(.semibold)).lineLimit(1)
                    Text(live.phaseSentence ?? "On air").foregroundStyle(secondary).lineLimit(1)
                }
                .font(CU.Font.callout.weighted(.regular)).frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(minWidth: 150, idealWidth: 270, maxWidth: 380, alignment: .leading).layoutPriority(1)
            Spacer(minLength: 0)
            LiveBadge()
            SwiftUI.TimelineView(.periodic(from: .now, by: 1)) { tl in
                Text(live.elapsedText(at: tl.date)).font(CU.Font.callout.weighted(.regular)).monospacedDigit().foregroundStyle(secondary)
            }
            .accessibilityLabel("On air for \(live.elapsedText(at: Date()))")
            liveTransport(live)
        }
        .padding(.horizontal, 16).frame(height: 68)
        .background { plate }
        .overlay(alignment: .bottom) { Rectangle().fill(CU.onMedia.opacity(0.22)).frame(height: 3).accessibilityHidden(true) }
        .clipShape(shape)
        .accessibilityElement(children: .contain)
    }

    private func liveTransport(_ live: LiveSession) -> some View {
        HStack(spacing: 8) {
            Button { p.previous() } label: { Image(systemName: "backward.fill") }
                .accessibilityLabel("Previous station").disabled(state.stations.favourites.count < 2)
            Button { p.stopStation() } label: { Image(systemName: "stop.fill").font(CU.Icon.transport()) }
                .accessibilityLabel("Stop \(live.name)")
            Button { p.next() } label: { Image(systemName: "forward.fill") }
                .accessibilityLabel("Next station").disabled(state.stations.favourites.count < 2)
            if let station = liveStation {
                Button { Task { await state.stations.setFavourite(station, on: !station.favourite) } } label: {
                    Image(systemName: station.favourite ? "star.fill" : "star").foregroundStyle(station.favourite ? CU.accent : ink)
                }
                .accessibilityLabel(station.favourite ? "Favourite, on" : "Favourite, off")
            }
        }
        .buttonStyle(.plain).font(CU.Icon.row())
    }

    private var barRow: some View {
        HStack(spacing: 16) {
            nowPlayingButton
            middle
            if let q = p.current?.qualityLabel {
                Text(q).font(CU.Font.caption.weighted(.semibold)).foregroundStyle(secondary)
                    .padding(.horizontal, 8).padding(.vertical, 4)
                    .overlay(RoundedRectangle(cornerRadius: 4, style: .continuous).stroke(secondary.opacity(0.6), lineWidth: 1))
                    .fixedSize().accessibilityLabel("Quality \(q)")
            }
            if p.current != nil { lineSwitches }
            transport
            PlaybackClock(player: p) { Text("\(PlayerModel.clock($0)) / \(PlayerModel.clock(p.duration))").font(CU.Font.callout.weighted(.regular)).monospacedDigit().foregroundStyle(secondary) }
                .padding(.leading, 8)
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
                    Rectangle().fill(tint != nil ? CU.onAccent : CU.accent).frame(width: g.size.width * p.fraction)
                }
            }
            .frame(height: 4).clipShape(UnevenRoundedRectangle(bottomLeadingRadius: 16, bottomTrailingRadius: 16))
        }
        .clipShape(shape)
    }

    private var nowPlayingButton: some View {
        Group {
            if let c = p.current {
                HStack(spacing: 16) {
                    PlayerBarCover(artist: c.artist, album: c.album, disc: c.disc, spinning: p.isPlaying, side: 50, cornerRadius: 8, flipsAndOpensBooklet: false,
                                   fallback: { state.screen = .nowPlaying }) {
                        CoverView(album: AlbumItem(id: -1, title: c.album, artist: c.artist, year: 0, genre: "", format: "", owned: true, hue: 200, remoteID: c.albumID, coverArt: c.coverArt))
                    }
                    VStack(alignment: .leading, spacing: 4) {
                        Text(c.title).font(CU.Font.body.weighted(.semibold)).lineLimit(1)
                        if p.phase == .loading {
                            Text("Loading…").foregroundStyle(secondary).lineLimit(1)
                        } else {
                            // The artist and the album each open their own page; the rest of the bar opens Now Playing.
                            HStack(spacing: 0) {
                                Button { state.openCurrentArtist() } label: { Text(c.artist).lineLimit(1) }
                                    .buttonStyle(.plain).accessibilityLabel("Open artist \(c.artist)")
                                if !c.album.isEmpty {
                                    Text(" — ")
                                    Button { state.openCurrentAlbum() } label: { Text(c.album).lineLimit(1) }
                                        .buttonStyle(.plain).accessibilityLabel("Open album \(c.album)")
                                }
                            }
                            .foregroundStyle(secondary)
                        }
                        if case .failed(let m) = p.phase { CUErrorLine(message: m, onDark: tint != nil).lineLimit(1) }
                    }
                    .font(CU.Font.callout.weighted(.regular)).frame(maxWidth: .infinity, alignment: .leading)
                }
            } else {
                Text("Nothing playing").font(CU.Font.callout.weighted(.regular)).foregroundStyle(secondary).frame(maxWidth: .infinity, alignment: .leading)
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
                    MarqueeLine(reduceMotion: reduceMotion) { Text(text).font(CU.Font.body.weighted(.semibold)) }
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
        let label = Text(fact.text).font(CU.Font.callout.weighted(.regular)).foregroundStyle(ink.opacity(0.86))
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
                Image(systemName: "info.circle").font(CU.Icon.row(.medium))
            } toggle: { state.barOptions.showFacts.toggle() }
        }
    }

    private func switchButton<Icon: View>(on: Bool, label: String, @ViewBuilder icon: () -> Icon, toggle: @escaping () -> Void) -> some View {
        Button(action: toggle) {
            icon().foregroundStyle(on ? ink : secondary.opacity(0.8))
                .frame(width: 26, height: 26)
                .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(ink.opacity(on ? 0.22 : 0)))
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
                ctx.fill(Path(roundedRect: CGRect(x: CGFloat(i) * step, y: floorY - h, width: width, height: h), cornerRadius: 4),
                         with: .color(CU.onMedia.opacity(played ? 0.22 : 0.11)))
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
