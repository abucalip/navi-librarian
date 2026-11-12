import SwiftUI

/// Album: artwork, bold sans title, red artist name, large Play capsule, zebra track table; the missing song is a
/// dashed row with its own Get. Mockup: `R.cupertino.album`.
/// The album's header sits on the blurred cover, edge to edge under the sidebar and toolbar like the artist page; only
/// the songs and the lists below it scroll.
struct CupertinoAlbumBanner: View {
    let state: AppState

    var body: some View {
        let a = state.selectedAlbum
        let tracks = state.library.tracks
        let owned = tracks.filter(\.owned).count
        let h = a.hue / 360
        ZStack(alignment: .topLeading) {
            CU.artwork(hue: h, saturation: 0.45, brightness: 0.45)
            RadialGradient(colors: [CU.artwork(hue: h, saturation: 0.6, brightness: 0.9).opacity(0.95), .clear],
                           center: UnitPoint(x: 0.2, y: 0.1), startRadius: 0, endRadius: 800)
            RadialGradient(colors: [CU.artwork(hue: (h + 0.1).truncatingRemainder(dividingBy: 1), saturation: 0.7, brightness: 0.6).opacity(0.9), .clear],
                           center: UnitPoint(x: 0.9, y: 0.9), startRadius: 0, endRadius: 700)
            if !(a.coverArt ?? "").isEmpty { BlurredArtwork(album: a, radius: 24); CU.shadowInk.opacity(0.12) }
            LinearGradient(colors: [CU.shadowInk.opacity(0.0), CU.shadowInk.opacity(0.4)], startPoint: .top, endPoint: .bottom)
        }
        .frame(height: CupertinoArtistLayout.bannerHeight)
        .frame(maxWidth: .infinity)
        .overlay(alignment: .topLeading) {
            VStack(alignment: .leading, spacing: 0) {
                BackButton(title: AppState.title(of: state.albumBack), onDark: true) { state.screen = state.albumBack }.padding(.bottom, 8)
                HStack(alignment: .top, spacing: 24) {
                    FlipCover(rgid: state.related.releaseGroupMBID, cornerRadius: 12, spineStrip: true, albumID: a.owned ? a.remoteID : nil) { CoverView(album: a).clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous)) }
                        .frame(width: 170, height: 170)
                        .shadow(color: CU.shadowInk.opacity(0.35), radius: 10, y: 5)
                    VStack(alignment: .leading, spacing: 0) {
                        Text(a.title).font(CU.title(34)).lineLimit(1).minimumScaleFactor(0.5)
                        Button { state.openArtist(named: a.artist) } label: { Text(a.artist).font(CU.Font.title2.weighted(.semibold)) }
                            .buttonStyle(.plain).padding(.top, 4).accessibilityLabel("Open artist \(a.artist)")
                        Text(a.line([a.genre, a.yearText, tracks.isEmpty ? "" : "\(tracks.count) songs" + (state.library.isLive ? "" : ", 41 minutes")]))
                            .opacity(0.85).padding(.top, 4)
                        HStack(spacing: 8) {
                            if let q = tracks.first(where: \.owned)?.format, !q.isEmpty {
                                Text(q).font(CU.Font.caption.weighted(.bold)).padding(.horizontal, 8).padding(.vertical, 0)
                                    .background(CU.onMedia.opacity(0.22), in: RoundedRectangle(cornerRadius: 4))
                            }
                            Text("\(owned) of \(tracks.count) owned").font(CU.Font.caption.weighted(.bold)).padding(.horizontal, 8).padding(.vertical, 0)
                                .background(CU.onMedia.opacity(0.22), in: RoundedRectangle(cornerRadius: 4))
                        }
                        .padding(.top, 8).padding(.bottom, 16)
                        HStack(spacing: 8) {
                            Button { state.actions.play(album: a) } label: { Label("Play", systemImage: "play.fill") }
                                .buttonStyle(CapsuleButtonStyle(primary: true))
                            Button { } label: { Label("Shuffle", systemImage: "shuffle") }
                                .buttonStyle(CapsuleButtonStyle(translucent: true))
                            BookletOpener(rgid: state.related.releaseGroupMBID) { open in
                                Button(action: open) { Label("Booklet", systemImage: "book") }
                                    .buttonStyle(CapsuleButtonStyle(translucent: true))
                                    .help("The album's booklet pages from the Cover Art Archive")
                            }
                            if state.canShowAlbumPaths {
                                Button { state.showAlbumPaths() } label: { Label("Paths", systemImage: "point.topleft.down.to.point.bottomright.curvepath") }
                                    .buttonStyle(CapsuleButtonStyle(translucent: true))
                                    .help("Albums in your library linked to this one by credits, works, years and sound")
                            }
                            if !a.owned {
                                Button { state.actions.get(album: a) } label: { Label(state.acquisition.buttonLabel(for: a) == "Get" ? "Get album" : state.acquisition.buttonLabel(for: a), systemImage: "plus") }
                                    .buttonStyle(CapsuleButtonStyle(translucent: true)).disabled(!state.acquisition.canGet(a))
                                    .help(state.acquisition.detail(for: a))
                            } else if let t = tracks.first(where: { !$0.owned }) {
                                Button { state.actions.getSong(album: a, title: t.title, trackNumber: t.id + 1) } label: {
                                    Label(state.acquisition.buttonLabel(for: a, song: t.title) == "Get" ? "Get missing song" : state.acquisition.buttonLabel(for: a, song: t.title), systemImage: "plus") }
                                    .buttonStyle(CapsuleButtonStyle(translucent: true)).disabled(!state.acquisition.canGet(a, song: t.title))
                                    .help(state.acquisition.detail(for: a, song: t.title))
                            }
                        }
                    }
                }
            }
            .foregroundStyle(CU.onMedia)
            .padding(.leading, 236 + CU.Space.xl).padding(.top, 76)
            .padding(.trailing, state.queueOpen ? CupertinoQueueInspector.width + CU.Space.xl : CU.Space.xl)
        }
        .accessibilityElement(children: .contain)
    }
}

/// The space between the tab buttons and whatever the tab shows, the same for every tab.
enum AlbumTabGap { static let value: CGFloat = 28 }

enum AlbumTab: String, CaseIterable, Identifiable {
    case tracks = "Tracks", notes = "Liner Notes", booklet = "Booklet", credits = "Credits", reviews = "Reviews"
    var id: String { rawValue }
}

struct CupertinoAlbum: View {
    let state: AppState
    @State private var tab: AlbumTab = .tracks

    var body: some View {
        let a = state.selectedAlbum
        ScrollViewReader { proxy in
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                tabBar.frame(maxWidth: .infinity).padding(.top, 16)
                switch tab {
                case .tracks: tracksTab(a)
                case .notes: CupertinoAlbumSpread(state: state, part: .notes).padding(.top, AlbumTabGap.value)
                case .booklet: AlbumBookletTab(state: state).padding(.top, AlbumTabGap.value)
                case .credits: CupertinoAlbumSpread(state: state, part: .credits).padding(.top, AlbumTabGap.value)
                case .reviews: CupertinoAlbumSpread(state: state, part: .reviews).padding(.top, AlbumTabGap.value)
                }
            }
            .padding(.horizontal, CU.Space.xl).padding(.bottom, CU.Space.xl)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .task(id: a.id) { await state.loadSelectedAlbum() }
        .onChange(of: a.id) { _, _ in tab = .tracks }
        // A song opened from a Library search is marked and scrolled into view once the tracks arrive.
        .onChange(of: state.library.tracks) { _, tracks in
            if let t = tracks.first(where: { isHighlighted($0) }) { tab = .tracks; withAnimation { proxy.scrollTo(t.id, anchor: .center) } }
        }
        }
    }

    private var tabBar: some View {
        HStack(spacing: 8) {
            ForEach(AlbumTab.allCases) { t in
                Button { tab = t } label: {
                    Text(t.rawValue).font(CU.Font.body.weighted(.semibold))
                        .padding(.horizontal, 16).padding(.vertical, 8)
                        .background(tab == t ? CU.accent : CU.bgFill, in: Capsule())
                        .foregroundStyle(tab == t ? CU.onAccent : CU.text)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(t.rawValue).accessibilityAddTraits(tab == t ? [.isButton, .isSelected] : .isButton)
            }
        }
    }

    @ViewBuilder private func tracksTab(_ a: AlbumItem) -> some View {
        // One column as wide as the track table: the table, "More by" and the related lists share its edges, and each row of
        // covers or photos is centred in it.
        VStack(alignment: .center, spacing: 0) {
            trackTable.frame(maxWidth: .infinity)
            let more = state.library.more(by: a)
            if !more.isEmpty {
                VStack(alignment: .leading, spacing: 0) {
                    Text("More by \(a.artist)").font(CU.title(20)).padding(.top, 40).padding(.bottom, 16)
                        .accessibilityAddTraits(.isHeader)
                    HStack(alignment: .top, spacing: AlbumColumn.gap) {
                        ForEach(more) { m in
                            Button { state.open(album: m) } label: {
                                VStack(alignment: .leading, spacing: 8) {
                                    CoverView(album: m).frame(width: AlbumColumn.tile(5)).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                                        .shadow(color: CU.shadowInk.opacity(0.2), radius: 7, y: 4)
                                    Text(m.title).fontWeight(.semibold).lineLimit(1)
                                }
                                .font(CU.Font.body.weighted(.regular)).frame(width: AlbumColumn.tile(5), alignment: .leading)
                            }
                            .buttonStyle(.plain).accessibilityLabel("Open \(m.title)")
                        }
                    }
                }
            }
            AlbumRelatedGrids(state: state).padding(.top, 8)
        }
        .frame(maxWidth: AlbumColumn.width)
        .frame(maxWidth: .infinity)
        .padding(.top, AlbumTabGap.value)
    }

    private func isHighlighted(_ t: TrackItem) -> Bool {
        guard let h = state.highlightedSong else { return false }
        return LibrarySearch.fold(t.title) == LibrarySearch.fold(h)
    }

    private var trackTable: some View {
        VStack(spacing: 0) {
            row(["#", "Track", "Duration", "Quality", ""], header: true, shaded: false, playing: false, missing: false)
            ForEach(Array(state.library.tracks.enumerated()), id: \.element.id) { i, t in
                row(nil, track: t, index: i, shaded: i % 2 == 0)
                    .overlay { if isHighlighted(t) { RoundedRectangle(cornerRadius: 8, style: .continuous).stroke(CU.accent, lineWidth: 2) } }
                    .background { if isHighlighted(t) { RoundedRectangle(cornerRadius: 8, style: .continuous).fill(CU.accent.opacity(0.14)) } }
                    .id(t.id)
                    .contentShape(Rectangle())
                    .onTapGesture(count: 2) { if t.owned { state.playAlbum(state.selectedAlbum, startAt: i) } }
                    .help(t.owned ? "Double-click to play" : "")
            }
        }
        .accessibilityElement(children: .contain)
    }

    private let cols: [CGFloat?] = [44, nil, 84, 110, 96]

    private func row(_ header: [String]?, header isHeader: Bool = false, track: TrackItem? = nil, index: Int = 0,
                     shaded: Bool, playing: Bool = false, missing: Bool = false) -> some View {
        let on = track.map(state.isCurrent) ?? false
        let ms = track.map { !$0.owned } ?? false
        return HStack(spacing: 0) {
            cell(width: cols[0]) {
                if isHeader { Text("#") }
                else if on { PlayingBars(active: state.player.isPlaying) }
                else { Text("\(index + 1)").lineLimit(1).fixedSize() }
            }
            cell(width: cols[1]) { Text(isHeader ? "Track" : track!.title).lineLimit(1) }
            cell(width: cols[2]) { Text(isHeader ? "Duration" : track!.duration).lineLimit(1).fixedSize() }
            cell(width: cols[3]) {
                if isHeader { Text("Quality") }
                else if track!.owned {
                    Text(track!.format).font(CU.Font.caption.weighted(.bold))
                        .padding(.horizontal, 8).padding(.vertical, 0)
                        .background(on ? CU.onAccent.opacity(0.25) : CU.bgFill, in: RoundedRectangle(cornerRadius: 4))
                } else { Text("Not owned") }
            }
            cell(width: cols[4], trailing: true) {
                if !isHeader {
                    if track!.owned { Text("···") }
                    else {
                        Button(state.acquisition.buttonLabel(for: state.selectedAlbum, song: track!.title) == "Get" ? "Get song" : state.acquisition.buttonLabel(for: state.selectedAlbum, song: track!.title)) {
                            state.actions.getSong(album: state.selectedAlbum, title: track!.title, trackNumber: index + 1)
                        }
                        .buttonStyle(CapsuleButtonStyle(small: true))
                        .disabled(!state.acquisition.canGet(state.selectedAlbum, song: track!.title))
                        .help(state.acquisition.detail(for: state.selectedAlbum, song: track!.title))
                    }
                }
            }
        }
        .font(isHeader ? CU.Font.callout.weighted(.medium) : CU.Font.body.weighted(.regular))
        .monospacedDigit()
        .foregroundStyle(isHeader || ms ? CU.textSecondary : (on ? CU.onAccent : CU.text))
        .padding(.vertical, isHeader ? 8 : 4)
        .background {
            if on { RoundedRectangle(cornerRadius: 8, style: .continuous).fill(CU.accent) }
            else if shaded && !ms { Rectangle().fill(CU.bgPanel) }
        }
        .overlay(alignment: .bottom) {
            if isHeader { Rectangle().fill(CU.shadowInk.opacity(0.08)).frame(height: 1) }
            else if ms { Rectangle().stroke(CU.textTertiary, style: StrokeStyle(lineWidth: 1.5, dash: [4, 3])).frame(height: 1.5) }
        }
        .accessibilityElement(children: .combine)
    }

    /// A ZStack keeps the cell's width even when its content is empty (modifiers on an EmptyView vanish).
    private func cell<C: View>(width: CGFloat?, trailing: Bool = false, @ViewBuilder _ c: () -> C) -> some View {
        ZStack(alignment: trailing ? .trailing : .leading) { Color.clear.frame(height: 1); c() }
            .padding(.horizontal, 8)
            .frame(width: width)
            .frame(maxWidth: width == nil ? .infinity : nil, alignment: .leading)
    }
}
