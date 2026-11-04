import SwiftUI

/// Album: artwork, bold sans title, red artist name, large Play capsule, zebra track table; the missing song is a
/// dashed row with its own Get. Mockup: `R.cupertino.album`.
struct CupertinoAlbum: View {
    let state: AppState

    var body: some View {
        let a = state.selectedAlbum
        let tracks = state.library.tracks
        let owned = tracks.filter(\.owned).count
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                HStack(alignment: .top, spacing: 30) {
                    CoverView(album: a).frame(width: 250).clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                        .shadow(color: .black.opacity(0.2), radius: 7, y: 4)
                    VStack(alignment: .leading, spacing: 0) {
                        Text(a.title).font(CU.title(38))
                        Button { state.openArtist(named: a.artist) } label: { Text(a.artist).font(.system(size: 22)).foregroundStyle(CU.accent) }
                            .buttonStyle(.plain).padding(.top, 4).accessibilityLabel("Open artist \(a.artist)")
                        Text(a.line([a.genre, a.yearText, tracks.isEmpty ? "" : "\(tracks.count) songs" + (state.library.isLive ? "" : ", 41 minutes")]))
                            .foregroundStyle(CU.muted).padding(.top, 6)
                        HStack(spacing: 6) {
                            if let q = tracks.first(where: \.owned)?.format, !q.isEmpty {
                                Text(q).font(.system(size: 10.5, weight: .bold))
                                    .padding(.horizontal, 7).padding(.vertical, 1)
                                    .foregroundStyle(Color(red: 0.11, green: 0.54, blue: 0.23))
                                    .background(Color(red: 0.90, green: 0.965, blue: 0.918), in: RoundedRectangle(cornerRadius: 5))
                            }
                            Text("\(owned) of \(tracks.count) owned").font(.system(size: 10.5, weight: .bold))
                                .padding(.horizontal, 7).padding(.vertical, 1)
                                .foregroundStyle(Color(white: 0.27))
                                .background(CU.fill, in: RoundedRectangle(cornerRadius: 5))
                        }
                        .padding(.top, 8).padding(.bottom, 16)
                        HStack(spacing: 8) {
                            Button { state.actions.play(album: a) } label: { Label("Play", systemImage: "play.fill") }
                                .buttonStyle(CapsuleButtonStyle(primary: true, large: true))
                            Button { } label: { Label("Shuffle", systemImage: "shuffle") }
                                .buttonStyle(CapsuleButtonStyle(large: true))
                            if !a.owned {
                                Button { state.actions.get(album: a) } label: { Label(state.acquisition.buttonLabel(for: a) == "Get" ? "Get album" : state.acquisition.buttonLabel(for: a), systemImage: "plus") }
                                    .buttonStyle(CapsuleButtonStyle(outlined: true, large: true)).disabled(!state.acquisition.canGet(a))
                                    .help(state.acquisition.detail(for: a))
                            } else if let t = tracks.first(where: { !$0.owned }) {
                                Button { state.actions.getSong(album: a, title: t.title, trackNumber: t.id + 1) } label: {
                                    Label(state.acquisition.buttonLabel(for: a, song: t.title) == "Get" ? "Get missing song" : state.acquisition.buttonLabel(for: a, song: t.title), systemImage: "plus") }
                                    .buttonStyle(CapsuleButtonStyle(outlined: true, large: true)).disabled(!state.acquisition.canGet(a, song: t.title))
                                    .help(state.acquisition.detail(for: a, song: t.title))
                            }
                            Button(state.acquisition.isSaved(a) ? "Saved" : "Save") { state.actions.save(album: a) }
                                .buttonStyle(CapsuleButtonStyle(large: true)).disabled(state.acquisition.isSaved(a))
                        }
                    }
                    .padding(.top, 8)
                    Spacer(minLength: 0)
                }
                .padding(.top, 6)

                trackTable.padding(.top, 22)

                if !state.library.more(by: a).isEmpty {
                Text("More by \(a.artist)").font(CU.title(20)).padding(.top, 22).padding(.bottom, 10)
                    .accessibilityAddTraits(.isHeader)
                HStack(alignment: .top, spacing: 20) {
                    ForEach(state.library.more(by: a)) { m in
                        Button { state.open(album: m) } label: {
                        VStack(alignment: .leading, spacing: 8) {
                            CoverView(album: m).frame(width: 110).clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                                .shadow(color: .black.opacity(0.2), radius: 7, y: 4)
                            Text(m.title).fontWeight(.semibold).lineLimit(1)
                        }
                        .font(.system(size: 13)).frame(width: 110, alignment: .leading)
                        }
                        .buttonStyle(.plain).accessibilityLabel("Open \(m.title)")
                    }
                }
                }
            }
            .padding(.horizontal, 28).padding(.bottom, 28)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .task(id: a.id) { await state.loadSelectedAlbum() }
    }

    private var trackTable: some View {
        VStack(spacing: 0) {
            row(["#", "Song", "Time", "Quality", ""], header: true, shaded: false, playing: false, missing: false)
            ForEach(Array(state.library.tracks.enumerated()), id: \.element.id) { i, t in
                row(nil, track: t, index: i, shaded: i % 2 == 0)
            }
        }
        .accessibilityElement(children: .contain)
    }

    private let cols: [CGFloat?] = [52, nil, 80, 130, 110]

    private func row(_ header: [String]?, header isHeader: Bool = false, track: TrackItem? = nil, index: Int = 0,
                     shaded: Bool, playing: Bool = false, missing: Bool = false) -> some View {
        let on = track?.playing ?? false
        let ms = track.map { !$0.owned } ?? false
        return HStack(spacing: 0) {
            cell(width: cols[0]) {
                if isHeader { Text("#") }
                else if on { Image(systemName: "waveform").accessibilityLabel("Playing") }
                else { Text("\(index + 1)").lineLimit(1).fixedSize() }
            }
            cell(width: cols[1]) { Text(isHeader ? "Song" : track!.title).lineLimit(1) }
            cell(width: cols[2]) { Text(isHeader ? "Time" : track!.duration).lineLimit(1).fixedSize() }
            cell(width: cols[3]) {
                if isHeader { Text("Quality") }
                else if track!.owned {
                    Text(track!.format).font(.system(size: 10.5, weight: .bold))
                        .padding(.horizontal, 7).padding(.vertical, 1)
                        .background(on ? Color.white.opacity(0.25) : CU.fill, in: RoundedRectangle(cornerRadius: 5))
                } else { Text("Not owned") }
            }
            cell(width: cols[4], trailing: true) {
                if !isHeader {
                    if track!.owned { Text("···") }
                    else {
                        Button(state.acquisition.buttonLabel(for: state.selectedAlbum, song: track!.title) == "Get" ? "Get song" : state.acquisition.buttonLabel(for: state.selectedAlbum, song: track!.title)) {
                            state.actions.getSong(album: state.selectedAlbum, title: track!.title, trackNumber: index + 1)
                        }
                        .buttonStyle(CapsuleButtonStyle(primary: true, small: true))
                        .disabled(!state.acquisition.canGet(state.selectedAlbum, song: track!.title))
                        .help(state.acquisition.detail(for: state.selectedAlbum, song: track!.title))
                    }
                }
            }
        }
        .font(isHeader ? .system(size: 12, weight: .medium) : .system(size: 13))
        .monospacedDigit()
        .foregroundStyle(isHeader || ms ? CU.muted : (on ? Color.white : CU.ink))
        .padding(.vertical, isHeader ? 6 : 5)
        .background {
            if on { RoundedRectangle(cornerRadius: 7, style: .continuous).fill(CU.accent) }
            else if shaded && !ms { Rectangle().fill(Color(red: 0.965, green: 0.965, blue: 0.973)) }
        }
        .overlay(alignment: .bottom) {
            if isHeader { Rectangle().fill(Color.black.opacity(0.08)).frame(height: 1) }
            else if ms { Rectangle().stroke(Color(white: 0.73), style: StrokeStyle(lineWidth: 1.5, dash: [4, 3])).frame(height: 1.5) }
        }
        .accessibilityElement(children: .combine)
    }

    /// A ZStack keeps the cell's width even when its content is empty (modifiers on an EmptyView vanish).
    private func cell<C: View>(width: CGFloat?, trailing: Bool = false, @ViewBuilder _ c: () -> C) -> some View {
        ZStack(alignment: trailing ? .trailing : .leading) { Color.clear.frame(height: 1); c() }
            .padding(.horizontal, 10)
            .frame(width: width)
            .frame(maxWidth: width == nil ? .infinity : nil, alignment: .leading)
    }
}
