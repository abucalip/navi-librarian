import SwiftUI

/// Library, Columns view (opt-in, contract section 6.3): Genre, Artist, Album and Tracks side by side, with an
/// inspector for the selected track. Each column filters the next; arrow keys move inside a column.
struct CupertinoMiller: View {
    let state: AppState
    @State private var genre: String?
    @State private var artist: String?
    @State private var album: String?
    @State private var track: Int?

    var body: some View {
        // Each column is worked out once per render, not once per column that reads it.
        let all = state.library.songs
        let gs = MillerColumns.genres(all)
        let gc = MillerColumns.valid(genre, in: gs)
        let ars = MillerColumns.artists(all, genre: gc)
        let ac = MillerColumns.valid(artist, in: ars)
        let als = MillerColumns.albums(all, genre: gc, artist: ac)
        let alc = MillerColumns.valid(album, in: als)
        let shownTracks = MillerColumns.tracks(all, genre: gc, artist: ac, album: alc)
        HStack(spacing: 0) {
            column("Genre", gs, selected: gc) { genre = $0 }
            column("Artist", ars, selected: ac) { artist = $0 }
            column("Album", als, selected: alc) { album = $0 }
            trackColumn(shownTracks)
            inspector(shownTracks)
        }
        .frame(minHeight: 360, maxHeight: .infinity)
        .background(CU.content, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 8, style: .continuous).stroke(CU.shadowInk.opacity(0.08)))
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .onChange(of: genre) { artist = nil; album = nil; track = nil }
        .onChange(of: artist) { album = nil; track = nil }
        .onChange(of: album) { track = nil }
    }

    /// Rows are plain buttons in a lazy stack (a `List` with a tap gesture on its rows swallowed single clicks). Clicking the
    /// chosen row again clears the choice.
    private func column(_ title: String, _ entries: [MillerColumns.Entry], selected: String?, pick: @escaping (String?) -> Void) -> some View {
        VStack(spacing: 0) {
            heading(title)
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(entries) { e in
                        let on = e.name == selected
                        Button { pick(on ? nil : e.name) } label: {
                            HStack {
                                Text(e.name).lineLimit(1)
                                Spacer(minLength: 6)
                                Text(String(e.count)).foregroundStyle(on ? CU.onAccent.opacity(0.85) : CU.muted).monospacedDigit()
                            }
                            .font(CU.Font.body.weighted(.regular))
                            .padding(.horizontal, 8).padding(.vertical, 4)
                            .foregroundStyle(on ? CU.onAccent : CU.ink)
                            .background(on ? CU.accent : .clear, in: RoundedRectangle(cornerRadius: 4, style: .continuous))
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("\(e.name), \(e.count) songs")
                        .accessibilityAddTraits(on ? .isSelected : [])
                    }
                }
                .padding(4)
            }
        }
        .frame(minWidth: 150, maxWidth: .infinity)
        .overlay(alignment: .trailing) { Rectangle().fill(CU.shadowInk.opacity(0.08)).frame(width: 1) }
    }

    private func trackColumn(_ rows: [SongRow]) -> some View {
        VStack(spacing: 0) {
            heading("Tracks")
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(Array(rows.enumerated()), id: \.element.id) { i, r in
                        let on = r.id == track
                        HStack(spacing: 8) {
                            Text(r.track.map(String.init) ?? "").foregroundStyle(on ? CU.onAccent.opacity(0.85) : CU.muted).monospacedDigit().frame(width: 22, alignment: .trailing)
                            Text(r.title).lineLimit(1)
                            Spacer(minLength: 0)
                        }
                        .font(CU.Font.body.weighted(.regular))
                        .padding(.horizontal, 8).padding(.vertical, 4)
                        .foregroundStyle(on ? CU.onAccent : CU.ink)
                        .background(on ? CU.accent : .clear, in: RoundedRectangle(cornerRadius: 4, style: .continuous))
                        .contentShape(Rectangle())
                        .onTapGesture(count: 2) { track = r.id; state.play(rows: rows, startAt: i) }
                        .onTapGesture { track = r.id }
                        .accessibilityElement(children: .combine)
                        .accessibilityAddTraits(on ? .isSelected : [])
                    }
                }
                .padding(4)
            }
        }
        .frame(minWidth: 190, maxWidth: .infinity)
        .overlay(alignment: .trailing) { Rectangle().fill(CU.shadowInk.opacity(0.08)).frame(width: 1) }
    }

    private func inspector(_ rows: [SongRow]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            heading("Inspector").padding(.horizontal, -16)
            if let r = rows.first(where: { $0.id == track }) {
                CoverView(album: r.albumItem).frame(width: 120, height: 120).clipShape(RoundedRectangle(cornerRadius: 8))
                Text(r.title).font(CU.Font.title3.weighted(.bold)).lineLimit(2)
                Text(r.artist).foregroundStyle(CU.accent)
                Text(MillerColumns.albumName(r)).foregroundStyle(CU.muted).lineLimit(2)
                VStack(alignment: .leading, spacing: 4) {
                    fact("Genre", MillerColumns.genreName(r))
                    fact("Year", r.year > 0 ? String(r.year) : "")
                    fact("Format", r.format); fact("Bitrate", r.bitrate)
                    fact("Plays", String(r.plays)); fact("Last played", r.lastPlayed)
                    fact("Rating", SongTable.stars(r.rating))
                    fact("MusicBrainz", r.hasMBID ? "" : "Missing")
                }
                .font(CU.Font.callout.weighted(.regular))
                HStack {
                    Button { if let i = rows.firstIndex(where: { $0.id == r.id }) { state.play(rows: rows, startAt: i) } } label: { Label("Play", systemImage: "play.fill") }
                        .buttonStyle(CapsuleButtonStyle(small: true)).disabled(!state.library.isLive)
                    if let item = PlayerModel.item(r) {
                        Button("Play Next") { state.player.playNext(item) }.buttonStyle(CapsuleButtonStyle(small: true))
                        Button("Add to Queue") { state.player.addToQueue(item) }.buttonStyle(CapsuleButtonStyle(small: true))
                    }
                }
            } else {
                Text("Pick a track to see its details.").foregroundStyle(CU.muted)
            }
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 16)
        .frame(width: 230, alignment: .topLeading)
        .background(CU.card)
    }

    private func heading(_ t: String) -> some View {
        Text(t).font(CU.Font.callout.weighted(.medium)).foregroundStyle(CU.muted)
            .frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, 16).padding(.vertical, 8)
            .overlay(alignment: .bottom) { Rectangle().fill(CU.shadowInk.opacity(0.08)).frame(height: 1) }
    }

    @ViewBuilder private func fact(_ k: String, _ v: String) -> some View {
        if !v.isEmpty { HStack(alignment: .firstTextBaseline) { Text(k).foregroundStyle(CU.muted).frame(width: 78, alignment: .leading); Text(v) } }
    }
}
