import SwiftUI

/// Library, Columns view (opt-in, contract section 6.3): Genre, Artist, Album and Tracks side by side, with an
/// inspector for the selected track. Each column filters the next; arrow keys move inside a column.
struct CupertinoMiller: View {
    let state: AppState
    @State private var genre: String?
    @State private var artist: String?
    @State private var album: String?
    @State private var track: Int?

    private var all: [SongRow] { state.library.songs }
    private var genres: [MillerColumns.Entry] { MillerColumns.genres(all) }
    private var genreChoice: String? { MillerColumns.valid(genre, in: genres) }
    private var artists: [MillerColumns.Entry] { MillerColumns.artists(all, genre: genreChoice) }
    private var artistChoice: String? { MillerColumns.valid(artist, in: artists) }
    private var albums: [MillerColumns.Entry] { MillerColumns.albums(all, genre: genreChoice, artist: artistChoice) }
    private var albumChoice: String? { MillerColumns.valid(album, in: albums) }
    private var tracks: [SongRow] { MillerColumns.tracks(all, genre: genreChoice, artist: artistChoice, album: albumChoice) }
    private var picked: SongRow? { tracks.first { $0.id == track } }

    var body: some View {
        let shownTracks = tracks
        HStack(spacing: 0) {
            column("Genre", genres, $genre)
            column("Artist", artists, $artist)
            column("Album", albums, $album)
            trackColumn(shownTracks)
            inspector(shownTracks)
        }
        .frame(minHeight: 360, maxHeight: .infinity)
        .background(Color.white, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).stroke(Color.black.opacity(0.08)))
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .onChange(of: genre) { artist = nil; album = nil; track = nil }
        .onChange(of: artist) { album = nil; track = nil }
        .onChange(of: album) { track = nil }
    }

    private func column(_ title: String, _ entries: [MillerColumns.Entry], _ selection: Binding<String?>) -> some View {
        VStack(spacing: 0) {
            heading(title)
            List(selection: selection) {
                ForEach(entries) { e in
                    HStack {
                        Text(e.name).lineLimit(1)
                        Spacer(minLength: 6)
                        Text(String(e.count)).foregroundStyle(CU.muted).monospacedDigit()
                    }
                    .font(.system(size: 13))
                    .tag(Optional(e.name))
                    .accessibilityLabel("\(e.name), \(e.count) songs")
                }
            }
            .listStyle(.plain)
        }
        .frame(minWidth: 150, maxWidth: .infinity)
        .overlay(alignment: .trailing) { Rectangle().fill(Color.black.opacity(0.08)).frame(width: 1) }
    }

    private func trackColumn(_ rows: [SongRow]) -> some View {
        VStack(spacing: 0) {
            heading("Tracks")
            List(selection: $track) {
                ForEach(Array(rows.enumerated()), id: \.element.id) { i, r in
                    HStack(spacing: 8) {
                        Text(r.track.map(String.init) ?? "").foregroundStyle(CU.muted).monospacedDigit().frame(width: 22, alignment: .trailing)
                        Text(r.title).lineLimit(1)
                    }
                    .font(.system(size: 13))
                    .tag(Optional(r.id))
                    .contentShape(Rectangle())
                    .onTapGesture(count: 2) { track = r.id; state.play(rows: rows, startAt: i) }
                }
            }
            .listStyle(.plain)
        }
        .frame(minWidth: 190, maxWidth: .infinity)
        .overlay(alignment: .trailing) { Rectangle().fill(Color.black.opacity(0.08)).frame(width: 1) }
    }

    private func inspector(_ rows: [SongRow]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            heading("Inspector").padding(.horizontal, -14)
            if let r = picked {
                CoverView(album: r.albumItem).frame(width: 120, height: 120).clipShape(RoundedRectangle(cornerRadius: 8))
                Text(r.title).font(.system(size: 15, weight: .bold)).lineLimit(2)
                Text(r.artist).foregroundStyle(CU.accent)
                Text(MillerColumns.albumName(r)).foregroundStyle(CU.muted).lineLimit(2)
                VStack(alignment: .leading, spacing: 3) {
                    fact("Genre", MillerColumns.genreName(r))
                    fact("Year", r.year > 0 ? String(r.year) : "")
                    fact("Format", r.format); fact("Bitrate", r.bitrate)
                    fact("Plays", String(r.plays)); fact("Last played", r.lastPlayed)
                    fact("Rating", SongTable.stars(r.rating))
                    fact("MusicBrainz", r.hasMBID ? "" : "Missing")
                }
                .font(.system(size: 12))
                HStack {
                    Button { if let i = rows.firstIndex(where: { $0.id == r.id }) { state.play(rows: rows, startAt: i) } } label: { Label("Play", systemImage: "play.fill") }
                        .buttonStyle(CapsuleButtonStyle(primary: true, small: true)).disabled(!state.library.isLive)
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
        .padding(.horizontal, 14)
        .frame(width: 230, alignment: .topLeading)
        .background(CU.card)
    }

    private func heading(_ t: String) -> some View {
        Text(t).font(.system(size: 12, weight: .medium)).foregroundStyle(CU.muted)
            .frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, 14).padding(.vertical, 7)
            .overlay(alignment: .bottom) { Rectangle().fill(Color.black.opacity(0.08)).frame(height: 1) }
    }

    @ViewBuilder private func fact(_ k: String, _ v: String) -> some View {
        if !v.isEmpty { HStack(alignment: .firstTextBaseline) { Text(k).foregroundStyle(CU.muted).frame(width: 78, alignment: .leading); Text(v) } }
    }
}
