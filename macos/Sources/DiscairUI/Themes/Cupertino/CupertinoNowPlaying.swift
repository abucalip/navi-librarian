import AppKit
import DiscairAudio
import DiscairLibrarian
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

    @Environment(\.artwork) private var artwork
    /// The playing album's images (disc and slideshow); nil until found, and when the album has none.
    @State private var albumArt: ArtworkIndex?

    private var slides: [ArtworkPicture] { albumArt?.slideshowImages ?? [] }
    private var slideshowOn: Bool { state.barOptions.showSlideshow && !slides.isEmpty }

    private var live: Bool { state.library.isLive || state.player.current != nil }

    /// The album whose cover and hue the screen uses: the playing song's, or the sample.
    private var nowAlbum: AlbumItem {
        guard live, let c = state.player.current else { return Fixtures.albums[0] }
        return AlbumItem(id: -1, title: c.album, artist: c.artist, year: 0, genre: "", format: "", owned: true,
                         hue: LibraryModel.hue(for: c.album.isEmpty ? c.title : c.album), remoteID: c.albumID, coverArt: c.coverArt)
    }

    /// A station that plays has its own Now Playing (mockup C1, `CupertinoNowPlayingLive.swift`); a library song has this one.
    var body: some View {
        if let station = state.player.live { CupertinoNowPlayingLive(state: state, live: station) } else { songBody }
    }

    @ViewBuilder private var songBody: some View {
        let a = nowAlbum
        ZStack(alignment: .topLeading) {
            NowPlayingCloseControls(state: state)

            HStack(spacing: 8) {
                if !slides.isEmpty {
                    Button { state.barOptions.showSlideshow.toggle() } label: {
                        chip("photo.on.rectangle.angled", state.barOptions.showSlideshow ? "Photos on" : "Photos off")
                    }
                    .buttonStyle(.plain).help("Session and booklet photos behind the lyrics")
                    .accessibilityLabel("Photos behind the lyrics").accessibilityValue(state.barOptions.showSlideshow ? "On" : "Off")
                    .accessibilityAddTraits(.isToggle)
                }
                if !live { chip("text.quote", "Lyrics") }
                Button { state.queueOpen = true; state.screen = .albums } label: { chip("list.bullet", "Up Next") }.buttonStyle(.plain)
            }
            .frame(maxWidth: .infinity, alignment: .trailing).padding(.trailing, 16).padding(.top, 16)

            (live ? AnyView(livePlayer(a)) : AnyView(player(a))).frame(width: 420).padding(.leading, 90).padding(.top, 90)

            (live ? AnyView(noLyrics) : AnyView(lyricColumn))
                .frame(height: 560).padding(.leading, 640).padding(.trailing, 60).padding(.top, 90)

            HStack(spacing: 8) {
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
        .foregroundStyle(CU.onMedia)
        .clipShape(RoundedRectangle(cornerRadius: CU.windowRadius, style: .continuous))
        .background(WindowConfigurator())
        .background(TwoFingerSwipeDown(maxX: 620) { state.closeNowPlaying() })
        .task(id: "\(state.player.current?.artist ?? "")|\(state.player.current?.album ?? "")|\(artwork?.generation ?? 0)") {
            albumArt = nil
            guard live, let c = state.player.current, let artwork else { return }
            albumArt = await artwork.nowPlayingIndex(artist: c.artist, album: c.album)
        }
    }

    /// Soft radial colour fields from the cover's hues; the real cover, blurred, is laid over them once it loads.
    private func backdrop(_ a: AlbumItem) -> some View {
        let h = a.hue / 360
        let warm = CU.artwork(hue: h, saturation: 0.6, brightness: 0.85)
        let deep = CU.artwork(hue: (h + 0.08).truncatingRemainder(dividingBy: 1), saturation: 0.75, brightness: 0.5)
        return ZStack {
            CU.playerGround
            RadialGradient(colors: [warm.opacity(0.9), .clear], center: UnitPoint(x: 0.1, y: 0.1), startRadius: 0, endRadius: 900)
            RadialGradient(colors: [deep.opacity(0.9), .clear], center: UnitPoint(x: 0.85, y: 0.95), startRadius: 0, endRadius: 800)
            if let id = a.coverArt, !id.isEmpty {
                BlurredArtwork(album: a)                                              // the real cover, blurred, over the colour fields
                if slideshowOn { SlideshowBackdrop(slides: slides, playing: state.player.isPlaying) }
                CU.shadowInk.opacity(slideshowOn ? 0.38 : 0.22)
            } else {
                CU.shadowInk.opacity(0.35)
            }
        }
        .accessibilityHidden(true)
    }

    private func player(_ a: AlbumItem) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            FlipCover(rgid: nil, cornerRadius: 16, albumID: a.owned ? a.remoteID : nil, index: albumArt, caption: true) { CoverView(album: a).clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous)) }
                .overlay(alignment: .bottomTrailing) { NowPlayingBookletBadge(index: albumArt) }
                .shadow(color: CU.shadowInk.opacity(0.5), radius: 35, y: 30)
            Text("After the Flood").font(CU.Font.title1.weighted(.bold)).padding(.top, 24)
            Text("Talk Talk — Laughing Stock").font(CU.Font.title2.weighted(.regular)).opacity(0.7)
            HStack(spacing: 8) {
                Text("3:12")
                Capsule().fill(CU.onMedia.opacity(0.3)).frame(height: 5)
                    .overlay(alignment: .leading) { GeometryReader { g in Capsule().fill(CU.onMedia).frame(width: g.size.width * 0.33) } }
                Text("-6:29")
            }
            .font(CU.Font.caption.weighted(.regular)).monospacedDigit().opacity(0.85).padding(.top, 16)
            HStack(spacing: 34) {
                transport("shuffle", CU.Icon.row(), "Shuffle")
                transport("backward.fill", CU.Icon.transport(), "Previous")
                transport("pause.fill", CU.Icon.hero(), "Pause")
                transport("forward.fill", CU.Icon.transport(), "Next")
                transport("repeat", CU.Icon.row(), "Repeat")
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
        return VStack(alignment: .leading, spacing: 8) {
            switch lyr.state {
            case .idle, .loading:
                HStack(spacing: 8) { ProgressView().controlSize(.small).tint(CU.onMedia); Text("Loading lyrics…") }.font(CU.Font.title2.weighted(.semibold)).opacity(0.7)
            case .none: Text("No lyrics for this song.").font(CU.Font.title2.weighted(.semibold)).opacity(0.7)
            case .unsupported: Text("Your Navidrome doesn't provide lyrics.").font(CU.Font.title2.weighted(.semibold)).opacity(0.7)
            case .failed(let m):
                Text(m).font(CU.Font.title2.weighted(.semibold)).opacity(0.8)
                Button("Try again") { lyr.retry() }.buttonStyle(CapsuleButtonStyle(small: true, translucent: true))
            case .timed, .plain:
                if lyr.isSavedCopy { Text("Saved copy").font(CU.Font.callout.weighted(.semibold)).opacity(0.7) }
                if lyr.state == .plain { Text("These lyrics are not timed.").font(CU.Font.body.weighted(.regular)).opacity(0.7) }
                ScrollViewReader { proxy in
                    ScrollView(showsIndicators: false) {
                        VStack(alignment: .leading, spacing: 24) {
                            ForEach(Array(lyr.lines.enumerated()), id: \.offset) { i, line in
                                Text(line.text.isEmpty ? " " : line.text).font((lyr.state == .timed ? CU.Font.largeTitle : CU.Font.title1).weighted(.bold)).tracking(-0.7).lineSpacing(2)
                                    .foregroundStyle(CU.onMedia.opacity(lyr.state == .plain || i == idx || idx == nil ? 1 : 0.38))
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
                .mask(LinearGradient(stops: [.init(color: .clear, location: 0), .init(color: CU.shadowInk, location: 0.12),
                                             .init(color: CU.shadowInk, location: 0.8), .init(color: .clear, location: 1)], startPoint: .top, endPoint: .bottom))
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
                .shadow(color: CU.shadowInk.opacity(0.5), radius: 35, y: 30)
                .discSleeve(albumArt?.discImage(disc: p.current?.disc), spinning: p.isPlaying)
            Text(p.current?.title ?? "Nothing playing").font(CU.Font.title1.weighted(.bold)).lineLimit(2).padding(.top, 24)
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
                .font(CU.Font.title2.weighted(.regular)).opacity(0.7).lineLimit(2)
            }
            if case .failed(let m) = p.phase { Text(m).font(CU.Font.body.weighted(.regular)).foregroundStyle(CU.onMedia).padding(.top, 4) }
            if let n = p.notice { Text(n).font(CU.Font.callout.weighted(.regular)).opacity(0.8).padding(.top, 4) }
            HStack(spacing: 8) {
                PlaybackClock(player: p) { Text(PlayerModel.clock($0)) }
                DragBar(value: p.fraction, peaks: p.waveform, label: "Position", valueText: { "\(PlayerModel.clock($0 * p.duration)) of \(PlayerModel.clock(p.duration))" }) { p.seek(toFraction: $0) }
                PlaybackClock(player: p) { Text("-" + PlayerModel.clock(max(0, p.duration - $0))) }
            }
            .font(CU.Font.caption.weighted(.regular)).monospacedDigit().opacity(0.85).padding(.top, 16)
            HStack(spacing: 34) {
                Button { p.toggleShuffle() } label: { Image(systemName: "shuffle").font(CU.Icon.row()).opacity(p.shuffle ? 1 : 0.5) }
                    .accessibilityLabel(p.shuffle ? "Shuffle, on" : "Shuffle, off")
                Button { p.previous() } label: { Image(systemName: "backward.fill").font(CU.Icon.transport()) }.accessibilityLabel("Previous")
                Button { p.togglePlayPause() } label: { Image(systemName: p.isPlaying ? "pause.fill" : "play.fill").font(CU.Icon.hero()) }
                    .accessibilityLabel(p.isPlaying ? "Pause" : "Play").disabled(p.current == nil)
                Button { p.next() } label: { Image(systemName: "forward.fill").font(CU.Icon.transport()) }.accessibilityLabel("Next").disabled(p.current == nil)
                Button { p.cycleRepeat() } label: { Image(systemName: p.repeatMode == .one ? "repeat.1" : "repeat").font(CU.Icon.row()).opacity(p.repeatMode == .off ? 0.5 : 1) }
                    .accessibilityLabel("Repeat, \(p.repeatMode.rawValue)")
            }
            .buttonStyle(.plain).frame(maxWidth: .infinity).padding(.top, 16)
            HStack(spacing: 8) {
                Image(systemName: "speaker.fill").font(CU.Icon.small()).accessibilityHidden(true)
                DragBar(value: Double(p.volume), label: "Volume") { p.volume = Float($0) }
                Image(systemName: "speaker.wave.3.fill").font(CU.Icon.small()).accessibilityHidden(true)
            }
            .opacity(0.85).padding(.top, 16)
        }
    }

    private func transport(_ symbol: String, _ font: Font, _ label: String) -> some View {
        Button { } label: { Image(systemName: symbol).font(font) }
            .buttonStyle(.plain).accessibilityLabel(label)
    }

    private var lyricColumn: some View {
        VStack(alignment: .leading, spacing: 24) {
            ForEach(Array(lyrics.enumerated()), id: \.offset) { i, line in
                Text(line).font(CU.Font.largeTitle.weighted(.bold)).tracking(-0.7).lineSpacing(2)
                    .foregroundStyle(CU.onMedia.opacity(i == 2 ? 1 : 0.38))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .mask(LinearGradient(stops: [.init(color: .clear, location: 0), .init(color: CU.shadowInk, location: 0.12),
                                     .init(color: CU.shadowInk, location: 0.8), .init(color: .clear, location: 1)],
                             startPoint: .top, endPoint: .bottom))
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Lyrics. Current line: \(lyrics[2])")
    }

    private func chip(_ symbol: String?, _ text: String, strong: Bool = false) -> some View {
        HStack(spacing: 8) {
            if let symbol { Image(systemName: symbol) }
            Text(text)
        }
        .font(CU.Font.body.weighted(.semibold)).lineLimit(1).fixedSize().padding(.horizontal, 16).frame(height: 32)
        .background(CU.shadowInk.opacity(0.3), in: Capsule())          // dimming layer under clear glass
        .glassEffect(.clear, in: Capsule())
        .overlay { if strong { Capsule().fill(CU.onMedia.opacity(0.18)) } }
    }
}


/// The traffic lights and the chevron that returns to where Now Playing was opened from.
struct NowPlayingCloseControls: View {
    let state: AppState

    var body: some View {
        HStack(spacing: 8) {
            TrafficLights()
            Button { state.closeNowPlaying() } label: {
                Image(systemName: "chevron.down").font(CU.Icon.row(.semibold))
            }
            .buttonStyle(.plain).accessibilityLabel("Close Now Playing").help("Back to \(AppState.title(of: state.nowPlayingReturn))").padding(.leading, 16)
        }
        .padding(16)
    }
}

/// A two-finger swipe down on the left part of the window (the artwork side, so the lyrics keep their own scrolling) calls `action`.
struct TwoFingerSwipeDown: NSViewRepresentable {
    let maxX: CGFloat
    let action: () -> Void

    func makeNSView(context: Context) -> NSView {
        let v = NSView()
        context.coordinator.install(maxX: maxX, action: action)
        return v
    }
    func updateNSView(_ v: NSView, context: Context) { context.coordinator.install(maxX: maxX, action: action) }
    static func dismantleNSView(_ v: NSView, coordinator: Coordinator) { coordinator.remove() }
    func makeCoordinator() -> Coordinator { Coordinator() }

    final class Coordinator {
        private var monitor: Any?
        private var travelled: CGFloat = 0
        private var fired = false

        func install(maxX: CGFloat, action: @escaping () -> Void) {
            remove()
            monitor = NSEvent.addLocalMonitorForEvents(matching: .scrollWheel) { [weak self] e in
                guard let self, e.hasPreciseScrollingDeltas, e.locationInWindow.x < maxX else { return e }
                if e.phase == .began { self.travelled = 0; self.fired = false }
                // Fingers moving down the trackpad give a positive delta with natural scrolling on.
                self.travelled += e.scrollingDeltaY
                if !self.fired, self.travelled > 90 { self.fired = true; DispatchQueue.main.async(execute: action) }
                return e
            }
        }
        func remove() { if let m = monitor { NSEvent.removeMonitor(m) }; monitor = nil }
        deinit { if let m = monitor { NSEvent.removeMonitor(m) } }
    }
}
