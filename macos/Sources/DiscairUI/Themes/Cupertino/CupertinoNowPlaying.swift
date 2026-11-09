import DiscairAudio
import SwiftUI

/// Now Playing: full-window blurred artwork, left-aligned bold lyrics beside the cover, EQ / crossfade / quality as
/// glass chips (the real settings). Mockup: `R.cupertino.now`. Dark over the artwork; chips use clear glass over
/// media with a dimming layer (HIG, Materials).
struct CupertinoNowPlaying: View {
    let state: AppState
    private let lyrics = [
        "A slow tide under the floorboards", "the lamp keeps counting what we left", "one long note, then the room agrees",
        "nobody here is in a hurry", "the water finds its level", "and the level finds us",
    ]

    private var live: Bool { state.library.isLive || state.player.current != nil }

    /// The album whose cover and hue the screen uses: the playing song's, or the sample.
    private var nowAlbum: AlbumItem {
        guard live, let c = state.player.current else { return Fixtures.albums[0] }
        return AlbumItem(id: -1, title: c.album, artist: c.artist, year: 0, genre: "", format: "", owned: true,
                         hue: LibraryModel.hue(for: c.album.isEmpty ? c.title : c.album), remoteID: c.albumID, coverArt: c.coverArt)
    }

    var body: some View {
        let a = nowAlbum
        ZStack(alignment: .topLeading) {
            HStack(spacing: 6) {
                TrafficLights()
                Button { state.screen = .home } label: {
                    Image(systemName: "chevron.backward").font(.system(size: 13, weight: .semibold))
                }
                .buttonStyle(.plain).accessibilityLabel("Back").padding(.leading, 14)
            }
            .padding(18)

            HStack(spacing: 10) {
                if !live { chip("text.quote", "Lyrics") }
                Button { state.queueOpen = true; state.screen = .albums } label: { chip("list.bullet", "Up Next") }.buttonStyle(.plain)
            }
            .frame(maxWidth: .infinity, alignment: .trailing).padding(.trailing, 20).padding(.top, 14)

            (live ? AnyView(livePlayer(a)) : AnyView(player(a))).frame(width: 420).padding(.leading, 90).padding(.top, 90)

            (live ? AnyView(noLyrics) : AnyView(lyricColumn))
                .frame(height: 560).padding(.leading, 640).padding(.trailing, 60).padding(.top, 90)

            HStack(spacing: 10) {
                if live {
                    Button { state.screen = .equalizer } label: { chip("slider.horizontal.3", "EQ · \(state.player.eq.enabled ? state.player.eq.presetLabel : "Off")") }
                        .buttonStyle(.plain)
                    chip(nil, state.player.crossfadeSeconds == 0 ? "Crossfade off" : "Crossfade \(state.player.crossfadeSeconds) s")
                    chip(nil, state.player.qualityCap.map { "Up to \($0) kbps" } ?? "Original quality")
                    if let sfx = state.player.current?.suffix, !sfx.isEmpty { chip(nil, sfx.uppercased(), strong: true) }
                } else {
                    chip("slider.horizontal.3", "EQ · Custom")
                    chip(nil, "Crossfade 6 s")
                    chip(nil, "Original quality")
                    chip(nil, "FLAC 16/44", strong: true)
                }
            }
            .padding(.leading, 640).frame(maxHeight: .infinity, alignment: .bottom).padding(.bottom, 34)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(alignment: .topLeading) { backdrop(a) }   // a background never changes the layout size
        .foregroundStyle(.white)
        .clipShape(RoundedRectangle(cornerRadius: CU.windowRadius, style: .continuous))
        .background(WindowConfigurator())
    }

    /// Soft radial colour fields from the cover's hues; the real cover, blurred, is laid over them once it loads.
    private func backdrop(_ a: AlbumItem) -> some View {
        let h = a.hue / 360
        let warm = Color(hue: h, saturation: 0.6, brightness: 0.85)
        let deep = Color(hue: (h + 0.08).truncatingRemainder(dividingBy: 1), saturation: 0.75, brightness: 0.5)
        return ZStack {
            Color(red: 0.227, green: 0.165, blue: 0.11)
            RadialGradient(colors: [warm.opacity(0.9), .clear], center: UnitPoint(x: 0.1, y: 0.1), startRadius: 0, endRadius: 900)
            RadialGradient(colors: [deep.opacity(0.9), .clear], center: UnitPoint(x: 0.85, y: 0.95), startRadius: 0, endRadius: 800)
            if let id = a.coverArt, !id.isEmpty {
                BlurredArtwork(album: a); Color.black.opacity(0.22)                 // the real cover, blurred, over the colour fields
            } else {
                Color(red: 0.08, green: 0.06, blue: 0.04).opacity(0.35)
            }
        }
        .accessibilityHidden(true)
    }

    private func player(_ a: AlbumItem) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            CoverView(album: a).clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                .shadow(color: .black.opacity(0.5), radius: 35, y: 30)
            Text("After the Flood").font(.system(size: 24, weight: .bold)).padding(.top, 22)
            Text("Talk Talk — Laughing Stock").font(.system(size: 18)).opacity(0.7)
            HStack(spacing: 10) {
                Text("3:12")
                Capsule().fill(.white.opacity(0.3)).frame(height: 5)
                    .overlay(alignment: .leading) { GeometryReader { g in Capsule().fill(.white).frame(width: g.size.width * 0.33) } }
                Text("-6:29")
            }
            .font(.system(size: 11)).monospacedDigit().opacity(0.85).padding(.top, 16)
            HStack(spacing: 34) {
                transport("shuffle", 17, "Shuffle")
                transport("backward.fill", 24, "Previous")
                transport("pause.fill", 34, "Pause")
                transport("forward.fill", 24, "Next")
                transport("repeat", 17, "Repeat")
            }
            .frame(maxWidth: .infinity).padding(.top, 16)
        }
    }

    @State private var following = true
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// Lyrics of the playing song with every state written out (ANDROID_LYRICS_CONTRACT.md section 7).
    private var noLyrics: some View {
        let lyr = state.lyrics
        let idx = lyr.currentIndex(positionSeconds: state.player.position)
        return VStack(alignment: .leading, spacing: 10) {
            switch lyr.state {
            case .idle, .loading:
                HStack(spacing: 8) { ProgressView().controlSize(.small).tint(.white); Text("Loading lyrics…") }.font(.system(size: 22, weight: .semibold)).opacity(0.7)
            case .none: Text("No lyrics for this song.").font(.system(size: 22, weight: .semibold)).opacity(0.7)
            case .unsupported: Text("Your Navidrome doesn't provide lyrics.").font(.system(size: 22, weight: .semibold)).opacity(0.7)
            case .failed(let m):
                Text(m).font(.system(size: 18, weight: .semibold)).opacity(0.8)
                Button("Try again") { lyr.retry() }.buttonStyle(CapsuleButtonStyle(small: true, translucent: true))
            case .timed, .plain:
                if lyr.isSavedCopy { Text("Saved copy").font(.system(size: 12, weight: .semibold)).opacity(0.7) }
                if lyr.state == .plain { Text("These lyrics are not timed.").font(.system(size: 13)).opacity(0.7) }
                ScrollViewReader { proxy in
                    ScrollView(showsIndicators: false) {
                        VStack(alignment: .leading, spacing: 22) {
                            ForEach(Array(lyr.lines.enumerated()), id: \.offset) { i, line in
                                Text(line.text.isEmpty ? " " : line.text).font(.system(size: lyr.state == .timed ? 36 : 28, weight: .bold)).tracking(-0.7).lineSpacing(2)
                                    .foregroundStyle(.white.opacity(lyr.state == .plain || i == idx || idx == nil ? 1 : 0.38))
                                    .fixedSize(horizontal: false, vertical: true)
                                    .id(i)
                                    .accessibilityAddTraits(i == idx ? .isSelected : [])
                                    .accessibilityHint(i == idx ? "Current line" : "")
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading).padding(.vertical, 120)
                    }
                    .onScrollPhaseChange { _, new in if new == .interacting { following = false } }   // reading by hand stops following
                    .onChange(of: idx) { _, new in
                        guard following, let new else { return }
                        if reduceMotion { proxy.scrollTo(new, anchor: .center) } else { withAnimation(.easeInOut(duration: 0.4)) { proxy.scrollTo(new, anchor: .center) } }
                    }
                    .overlay(alignment: .bottomTrailing) {
                        if !following && lyr.state == .timed {
                            Button("Back to the current line") {
                                following = true
                                if let idx { proxy.scrollTo(idx, anchor: .center) }
                            }
                            .buttonStyle(CapsuleButtonStyle(small: true, translucent: true))
                        }
                    }
                }
                .mask(LinearGradient(stops: [.init(color: .clear, location: 0), .init(color: .black, location: 0.12),
                                             .init(color: .black, location: 0.8), .init(color: .clear, location: 1)], startPoint: .top, endPoint: .bottom))
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .task(id: state.player.current?.songID) {
            following = true
            state.lyrics.show(songID: state.player.current?.songID, title: state.player.current?.title)
        }
        .onChange(of: lyr.state) { _, s in
            if s == .timed || s == .plain { state.lyrics.prefetch(songID: state.player.queue.peekNext?.songID) }
        }
    }

    private func livePlayer(_ a: AlbumItem) -> some View {
        let p = state.player
        return VStack(alignment: .leading, spacing: 0) {
            CoverView(album: a).clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                .shadow(color: .black.opacity(0.5), radius: 35, y: 30)
            Text(p.current?.title ?? "Nothing playing").font(.system(size: 24, weight: .bold)).lineLimit(2).padding(.top, 22)
            if let c = p.current {
                HStack(spacing: 0) {
                    Button { state.openCurrentArtist() } label: { Text(c.artist).underline(false) }
                        .buttonStyle(.plain).accessibilityLabel("Open artist \(c.artist)")
                    if !c.album.isEmpty {
                        Text(" — ")
                        Button { state.openCurrentAlbum() } label: { Text(c.album) }
                            .buttonStyle(.plain).accessibilityLabel("Open album \(c.album)")
                    }
                }
                .font(.system(size: 18)).opacity(0.7).lineLimit(2)
            }
            if case .failed(let m) = p.phase { Text(m).font(.system(size: 13)).foregroundStyle(.white).padding(.top, 4) }
            if let n = p.notice { Text(n).font(.system(size: 12)).opacity(0.8).padding(.top, 2) }
            HStack(spacing: 10) {
                PlaybackClock(player: p) { Text(PlayerModel.clock($0)) }
                DragBar(value: p.fraction, peaks: p.waveform, label: "Position", valueText: { "\(PlayerModel.clock($0 * p.duration)) of \(PlayerModel.clock(p.duration))" }) { p.seek(toFraction: $0) }
                PlaybackClock(player: p) { Text("-" + PlayerModel.clock(max(0, p.duration - $0))) }
            }
            .font(.system(size: 11)).monospacedDigit().opacity(0.85).padding(.top, 16)
            HStack(spacing: 34) {
                Button { p.toggleShuffle() } label: { Image(systemName: "shuffle").font(.system(size: 17)).opacity(p.shuffle ? 1 : 0.5) }
                    .accessibilityLabel(p.shuffle ? "Shuffle, on" : "Shuffle, off")
                Button { p.previous() } label: { Image(systemName: "backward.fill").font(.system(size: 24)) }.accessibilityLabel("Previous")
                Button { p.togglePlayPause() } label: { Image(systemName: p.isPlaying ? "pause.fill" : "play.fill").font(.system(size: 34)) }
                    .accessibilityLabel(p.isPlaying ? "Pause" : "Play").disabled(p.current == nil)
                Button { p.next() } label: { Image(systemName: "forward.fill").font(.system(size: 24)) }.accessibilityLabel("Next").disabled(p.current == nil)
                Button { p.cycleRepeat() } label: { Image(systemName: p.repeatMode == .one ? "repeat.1" : "repeat").font(.system(size: 17)).opacity(p.repeatMode == .off ? 0.5 : 1) }
                    .accessibilityLabel("Repeat, \(p.repeatMode.rawValue)")
            }
            .buttonStyle(.plain).frame(maxWidth: .infinity).padding(.top, 16)
            HStack(spacing: 8) {
                Image(systemName: "speaker.fill").font(.system(size: 11)).accessibilityHidden(true)
                DragBar(value: Double(p.volume), label: "Volume") { p.volume = Float($0) }
                Image(systemName: "speaker.wave.3.fill").font(.system(size: 11)).accessibilityHidden(true)
            }
            .opacity(0.85).padding(.top, 16)
        }
    }

    private func transport(_ symbol: String, _ size: CGFloat, _ label: String) -> some View {
        Button { } label: { Image(systemName: symbol).font(.system(size: size)) }
            .buttonStyle(.plain).accessibilityLabel(label)
    }

    private var lyricColumn: some View {
        VStack(alignment: .leading, spacing: 22) {
            ForEach(Array(lyrics.enumerated()), id: \.offset) { i, line in
                Text(line).font(.system(size: 36, weight: .bold)).tracking(-0.7).lineSpacing(2)
                    .foregroundStyle(.white.opacity(i == 2 ? 1 : 0.38))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .mask(LinearGradient(stops: [.init(color: .clear, location: 0), .init(color: .black, location: 0.12),
                                     .init(color: .black, location: 0.8), .init(color: .clear, location: 1)],
                             startPoint: .top, endPoint: .bottom))
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Lyrics. Current line: \(lyrics[2])")
    }

    private func chip(_ symbol: String?, _ text: String, strong: Bool = false) -> some View {
        HStack(spacing: 6) {
            if let symbol { Image(systemName: symbol) }
            Text(text)
        }
        .font(.system(size: 13, weight: .semibold)).lineLimit(1).fixedSize().padding(.horizontal, 14).frame(height: 32)
        .background(Color.black.opacity(0.3), in: Capsule())          // dimming layer under clear glass
        .glassEffect(.clear, in: Capsule())
        .overlay { if strong { Capsule().fill(.white.opacity(0.18)) } }
    }
}
