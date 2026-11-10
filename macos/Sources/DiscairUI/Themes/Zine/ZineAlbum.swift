import SwiftUI

/// Album: an article. Giant headline, byline, a contents box where the missing song is a dashed coupon with its
/// own Get. Mockup: `R.zine.album`.
struct ZineAlbum: View {
    let state: AppState

    var body: some View {
        let a = state.selectedAlbum
        VStack(alignment: .leading, spacing: 0) {
            BackButton(title: AppState.title(of: state.albumBack), zine: true) { state.screen = state.albumBack }.padding(.bottom, 8)
            Text(a.title).font(Z.an(118)).textCase(.uppercase).tracking(1.2).lineLimit(1).minimumScaleFactor(0.4)
                .padding(.bottom, 4).accessibilityAddTraits(.isHeader)
            Rectangle().fill(Z.ink).frame(height: 4)
            byline(a)
            HStack(alignment: .top, spacing: 22) {
                VStack(alignment: .leading, spacing: 0) {
                    FlipCover(rgid: state.related.releaseGroupMBID, dressBack: { AnyView($0.zBorder(3).zShadow(6)) }, spineStrip: true, albumID: a.owned ? a.remoteID : nil) { ZineCover(album: a, width: 260) }
                        .frame(width: 260, height: 260)
                    if !state.library.isLive {
                        Rectangle().fill(Z.ink).frame(height: 4).padding(.top, 20)
                        Text(ZineFixtures.albumPull).font(Z.serif(19, italic: true)).padding(.top, 6)
                    }
                }
                .frame(width: 260)
                VStack(alignment: .leading, spacing: 8) {
                    if state.library.isLive {
                        if let r = a.reason { Text(r) } else { Mono("No article for this album yet") }
                    } else {
                        (Text(ZineFixtures.albumLede).bold() + Text(ZineFixtures.albumBody1))
                        Text(ZineFixtures.albumBody2)
                    }
                }
                .font(Z.serif(14.5)).frame(maxWidth: .infinity, alignment: .topLeading)
                contents(a).frame(maxWidth: .infinity)
            }
            RelatedSections(state: state, albums: true)
            ZineAlbumSpread(state: state)
        }
        .task(id: a.id) { await state.loadSelectedAlbum() }
    }

    private var summary: String {
        let n = state.library.tracks.count
        guard state.library.isLive else { return "6 songs · 41 min" }
        let a = state.selectedAlbum
        let minutes = a.durationSeconds.map { " · \($0 / 60) min" } ?? ""
        return "\(a.songCount ?? n) songs" + minutes
    }

    private func byline(_ a: AlbumItem) -> some View {
        HStack(spacing: 26) {
            Button { state.openArtist(named: a.artist) } label: { Mono("By \(a.artist)") }.buttonStyle(.plain)
                .accessibilityLabel("Open artist \(a.artist)")
            if a.year > 0 { Mono("\(a.year)") }
            if !a.genre.isEmpty { Mono(a.genre) }
            Mono(summary)
            ZineBadge(!a.owned ? "Not owned" : (state.library.tracks.first(where: \.owned)?.format ?? "").isEmpty ? "In library" : state.library.tracks.first(where: \.owned)!.format)
            Spacer()
            HStack(spacing: 10) {
                Button { state.actions.play(album: a) } label: { Label("Play", systemImage: "play.fill") }
                    .buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
                BookletOpener(rgid: state.related.releaseGroupMBID) { open in
                    Button(action: open) { Label("Booklet", systemImage: "book") }
                        .buttonStyle(ZineButtonStyle(small: true))
                }
                if state.canShowAlbumPaths {
                    Button { state.showAlbumPaths() } label: { Label("Paths", systemImage: "point.topleft.down.to.point.bottomright.curvepath") }
                        .buttonStyle(ZineButtonStyle(small: true))
                        .help("Albums in your library linked to this one by credits, works, years and sound")
                }
                Button(state.acquisition.isSaved(a) ? "Saved" : "Save") { state.actions.save(album: a) }
                    .buttonStyle(ZineButtonStyle(small: true)).disabled(state.acquisition.isSaved(a))
                if !a.owned || !state.library.isLive {
                    Button(state.acquisition.buttonLabel(for: a) == "Get" ? "Get album" : state.acquisition.buttonLabel(for: a)) { state.actions.get(album: a) }
                        .buttonStyle(ZineButtonStyle(small: true)).disabled(!state.acquisition.canGet(a))
                        .help(state.acquisition.detail(for: a))
                }
            }
        }
        .padding(.vertical, 6)
        .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 2) }
        .padding(.bottom, 14)
    }

    private func contents(_ a: AlbumItem) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            ZineH2("Contents", size: 20)
            ForEach(Array(state.library.tracks.enumerated()), id: \.element.id) { i, t in
                if t.owned {
                    DotRow {
                        HStack(spacing: 6) {
                            if state.isCurrent(t) { PlayingBars(active: state.player.isPlaying) } else { Text("\(i + 1)").font(Z.an(15)) }
                            Text(t.title).font(Z.serif(14))
                        }
                    } right: { Text(t.duration).font(Z.serif(14)) }
                    .padding(.vertical, 3)
                    .contentShape(Rectangle())
                    .onTapGesture(count: 2) { state.playAlbum(a, startAt: i) }
                    .help("Double-click to play")
                    .accessibilityElement(children: .combine)
                } else {
                    HStack {
                        Mono("\(i + 1) \(t.title) · not owned")
                        Spacer(minLength: 6)
                        Button(state.acquisition.buttonLabel(for: a, song: t.title) == "Get" ? "Get song" : state.acquisition.buttonLabel(for: a, song: t.title)) {
                            state.actions.getSong(album: a, title: t.title, trackNumber: i + 1)
                        }
                        .buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
                        .disabled(!state.acquisition.canGet(a, song: t.title)).help(state.acquisition.detail(for: a, song: t.title))
                    }
                    .padding(.horizontal, 10).padding(.vertical, 6)
                    .background(Z.yellow).zBorder(3, dashed: true)
                    .padding(.vertical, 4)
                }
            }
            if state.library.tracksLoading { Mono("Loading songs…").padding(.top, 6) }
            if let p = state.library.tracks.firstIndex(where: { $0.playing }) {
                Mono("▶ Now playing: \(p + 1) \(state.library.tracks[p].title)").padding(.top, 6)
            }
        }
        .padding(.horizontal, 12).padding(.vertical, 10)
        .background(Z.white).zBorder(3)
    }
}
