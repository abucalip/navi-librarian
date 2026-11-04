import DiscairAudio
import SwiftUI

/// Now Playing: a centre spread. Halftone cover on the left page, synced lyrics set as article columns on the
/// right. Mockup: `R.zine.now`.
struct ZineNowPlaying: View {
    let state: AppState

    private var live: Bool { state.library.isLive || state.player.current != nil }

    var body: some View {
        if live { liveBody } else { sampleBody }
    }

    private var liveBody: some View {
        let p = state.player
        let c = p.current
        let a = AlbumItem(id: -1, title: c?.album ?? "", artist: c?.artist ?? "", year: 0, genre: "", format: "", owned: true,
                          hue: LibraryModel.hue(for: (c?.album.isEmpty ?? true) ? (c?.title ?? "") : c!.album), coverArt: c?.coverArt)
        return HStack(alignment: .top, spacing: 26) {
            VStack(alignment: .leading, spacing: 0) {
                Mono("Centre spread · Now playing").padding(.bottom, 6)
                ZineCover(album: a, width: 350).overlay { Halftone().padding(3) }
                Text(c?.title ?? "Nothing playing").font(Z.an(54)).textCase(.uppercase).tracking(0.5).lineLimit(1).minimumScaleFactor(0.5)
                    .padding(.top, 16).accessibilityAddTraits(.isHeader)
                if let c { Mono([c.artist, c.album, c.suffix?.uppercased() ?? ""].filter { !$0.isEmpty }.joined(separator: " · ")) }
                if case .failed(let m) = p.phase { Text(m).font(Z.serif(14)).padding(.top, 4) }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            Rectangle().fill(Z.ink).frame(width: 6)
            VStack(alignment: .leading, spacing: 12) {
                Mono(state.lyrics.state == .timed ? "Lyrics · synced" : "Lyrics").padding(.bottom, 2)
                lyricsView
                HStack(spacing: 10) {
                    Mono("Position", bold: true)
                    DragBar(value: p.fraction, height: 12, track: Z.white, fill: Z.yellow, rounded: false, label: "Position",
                            valueText: { "\(PlayerModel.clock($0 * p.duration)) of \(PlayerModel.clock(p.duration))" }) { p.seek(toFraction: $0) }
                        .overlay { Rectangle().strokeBorder(Z.ink, lineWidth: 2).frame(height: 12).allowsHitTesting(false) }
                    Mono("\(PlayerModel.clock(p.position)) / \(PlayerModel.clock(p.duration))")
                }
                HStack(spacing: 10) {
                    Mono("Volume", bold: true)
                    DragBar(value: Double(p.volume), height: 12, track: Z.white, fill: Z.ink, rounded: false, label: "Volume") { p.volume = Float($0) }
                        .overlay { Rectangle().strokeBorder(Z.ink, lineWidth: 2).frame(height: 12).allowsHitTesting(false) }
                        .frame(maxWidth: 260)
                }
                HStack(spacing: 10) {
                    Button("EQ · \(p.eq.enabled ? p.eq.presetLabel : "Off")") { state.screen = .equalizer }.buttonStyle(ZineButtonStyle())
                    Mono(p.crossfadeSeconds == 0 ? "Crossfade off" : "Crossfade \(p.crossfadeSeconds) s", bold: true)
                    Button("Queue") { state.screen = .queue }.buttonStyle(ZineButtonStyle(kind: .yellow))
                }
                .padding(.top, 4)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    @State private var following = true
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// Lyrics of the playing song as an article column; the current line is highlighted. Every state is written out.
    private var lyricsView: some View {
        let lyr = state.lyrics
        let idx = lyr.currentIndex(positionSeconds: state.player.position)
        return VStack(alignment: .leading, spacing: 8) {
            switch lyr.state {
            case .idle, .loading: Mono("Loading lyrics…")
            case .none: Text("No lyrics for this song.").font(Z.serif(22, italic: true)).opacity(0.7)
            case .unsupported: Text("Your Navidrome doesn't provide lyrics.").font(Z.serif(22, italic: true)).opacity(0.7)
            case .failed(let m):
                Text(m).font(Z.serif(18))
                Button("Try again") { lyr.retry() }.buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
            case .timed, .plain:
                if lyr.isSavedCopy { Mono("Saved copy", size: 10) }
                if lyr.state == .plain { Mono("These lyrics are not timed.", size: 10) }
                ScrollViewReader { proxy in
                    ScrollView(showsIndicators: false) {
                        VStack(alignment: .leading, spacing: 8) {
                            ForEach(Array(lyr.lines.enumerated()), id: \.offset) { i, line in
                                let now = i == idx
                                Text(line.text.isEmpty ? " " : line.text).font(Z.serif(22, italic: true)).lineSpacing(2)
                                    .padding(.horizontal, now ? 4 : 0).background(now ? Z.yellow : .clear)
                                    .opacity(lyr.state == .plain || now || idx == nil ? 1 : 0.45)
                                    .id(i)
                                    .accessibilityAddTraits(now ? .isSelected : [])
                                    .accessibilityHint(now ? "Current line" : "")
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading).padding(.vertical, 40)
                    }
                    .onScrollPhaseChange { _, new in if new == .interacting { following = false } }
                    .onChange(of: idx) { _, new in
                        guard following, let new else { return }
                        if reduceMotion { proxy.scrollTo(new, anchor: .center) } else { withAnimation(.easeInOut(duration: 0.3)) { proxy.scrollTo(new, anchor: .center) } }
                    }
                    .overlay(alignment: .bottomTrailing) {
                        if !following && lyr.state == .timed {
                            Button("Back to the current line") { following = true; if let idx { proxy.scrollTo(idx, anchor: .center) } }
                                .buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
                        }
                    }
                }
                .frame(height: 300)
            }
        }
        .task(id: state.player.current?.songID) {
            following = true
            state.lyrics.show(songID: state.player.current?.songID)
        }
        .onChange(of: lyr.state) { _, s in
            if s == .timed || s == .plain { state.lyrics.prefetch(songID: state.player.queue.peekNext?.songID) }
        }
    }

    private var sampleBody: some View {
        let a = Fixtures.albums[0]
        let lyr = ZineFixtures.lyrics
        return HStack(alignment: .top, spacing: 26) {
            VStack(alignment: .leading, spacing: 0) {
                Mono("Centre spread · Now playing").padding(.bottom, 6)
                ZineCover(album: a, width: 350)
                    .overlay { Halftone().padding(3) }
                Text("After the Flood").font(Z.an(54)).textCase(.uppercase).tracking(0.5).lineLimit(1).minimumScaleFactor(0.5)
                    .padding(.top, 16).accessibilityAddTraits(.isHeader)
                Mono("Talk Talk · Laughing Stock · 3 of 6 · FLAC 16/44")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            Rectangle().fill(Z.ink).frame(width: 6)
            VStack(alignment: .leading, spacing: 0) {
                Mono("Lyrics · synced").padding(.bottom, 6)
                HStack(alignment: .top, spacing: 20) {
                    column([0, 1, 2], lyr)
                    Rectangle().fill(Z.ink).frame(width: 2)
                    column([3, 4], lyr)
                }
                .fixedSize(horizontal: false, vertical: true)
                HStack(spacing: 10) {
                    Button("EQ · Custom") { }.buttonStyle(ZineButtonStyle())
                    Button("Crossfade 6 s") { }.buttonStyle(ZineButtonStyle())
                    Button("Quality · Original") { }.buttonStyle(ZineButtonStyle())
                    Button("Queue") { state.screen = .queue }.buttonStyle(ZineButtonStyle(kind: .yellow))
                }
                .padding(.top, 14)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    /// One text column; line 2 is the current line (yellow highlight), the rest are dimmed.
    private func column(_ idx: [Int], _ lyr: [String]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            ForEach(idx, id: \.self) { i in
                let now = i == 2
                Text(lyr[i]).font(Z.serif(24, italic: true)).lineSpacing(2)
                    .padding(.horizontal, now ? 4 : 0).background(now ? Z.yellow : .clear)
                    .opacity(now ? 1 : 0.45)
                    .accessibilityAddTraits(now ? .isSelected : [])
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
