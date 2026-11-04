import SwiftUI

/// Library: Songs table with sortable columns and a selected row, a source segmented control, and a view switch with
/// Columns (opt-in, contract section 6). Mockup: `R.cupertino.library`. Zebra rows, selection in the accent colour.
struct CupertinoLibrary: View {
    let state: AppState
    private enum Key: String { case title = "Title", artist = "Artist", year = "Year", genre = "Genre", format = "Format", plays = "Plays" }
    @State private var sortKey: Key = .title
    @State private var ascending = true
    @State private var selected = 1
    @State private var source = "Songs"
    @State private var viewMode = "Table"

    private var rows: [SongRow] {
        let r = state.library.songs.sorted { a, b in
            switch sortKey {
            case .title: a.title.localizedCaseInsensitiveCompare(b.title) == .orderedAscending
            case .artist: a.artist.localizedCaseInsensitiveCompare(b.artist) == .orderedAscending
            case .year: a.year < b.year
            case .genre: a.genre.localizedCaseInsensitiveCompare(b.genre) == .orderedAscending
            case .format: a.format < b.format
            case .plays: a.plays < b.plays
            }
        }
        return ascending ? r : r.reversed()
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                HStack(spacing: 14) {
                    Text("Songs").font(CU.title(34))
                    CUSegmented(options: ["Songs", "Albums", "Artists", "Missing"], selection: $source)
                    Spacer()
                    Button { let shown = rows; if let i = shown.firstIndex(where: { $0.id == selected }) { state.play(rows: shown, startAt: i) } } label: { Label("Play", systemImage: "play.fill") }
                        .buttonStyle(CapsuleButtonStyle(primary: true, small: true)).disabled(!state.library.isLive)
                        .help("Play the selected song, then the rows below it")
                    CUSegmented(options: ["Table", "Grid", "Columns"], selection: $viewMode)
                }
                .padding(.top, 4).padding(.bottom, 12)

                header
                let shown = rows
                ForEach(Array(shown.enumerated()), id: \.element.id) { i, r in
                    row(r, shaded: i % 2 == 0, on: r.id == selected)
                        .onTapGesture(count: 2) { selected = r.id; state.play(rows: shown, startAt: i) }
                        .onTapGesture { selected = r.id }
                        .contextMenu {
                            Button("Play") { state.play(rows: shown, startAt: i) }
                            if let item = PlayerModel.item(r) {
                                Button("Play Next") { state.player.playNext(item) }
                                Button("Add to Queue") { state.player.addToQueue(item) }
                            }
                        }
                }
                footer
            }
            .padding(.horizontal, 28).padding(.bottom, 28)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .task(id: state.library.isLive) { await state.loadSongs() }
    }

    /// Loading, failure and paging. Sorting only reorders the songs already loaded, and the footer says so.
    @ViewBuilder private var footer: some View {
        let lib = state.library
        if lib.isLive {
            VStack(alignment: .leading, spacing: 8) {
                if lib.songsLoading { HStack(spacing: 8) { ProgressView().controlSize(.small); Text("Loading songs…") }.foregroundStyle(CU.muted) }
                if let e = lib.songsError {
                    Text(e).foregroundStyle(CU.muted)
                    Button("Try again") { Task { await state.loadSongs(more: !lib.songs.isEmpty && lib.songsHaveMore) } }
                        .buttonStyle(CapsuleButtonStyle(primary: true, small: true))
                } else if lib.songsHaveMore && !lib.songsLoading {
                    Button("Load more songs") { Task { await state.loadSongs(more: true) } }.buttonStyle(CapsuleButtonStyle(small: true))
                }
                if !lib.songs.isEmpty {
                    Text("\(lib.songs.count) songs loaded" + (lib.songsHaveMore ? ". Sorting reorders only these." : "."))
                        .font(.system(size: 12)).foregroundStyle(CU.muted)
                }
                if lib.songs.isEmpty && !lib.songsLoading && lib.songsError == nil { Text("No songs in the library yet.").foregroundStyle(CU.muted) }
            }
            .padding(.top, 14)
        }
    }

    private let w: [CGFloat?] = [36, nil, 150, 52, 92, 108, 74, 52, 92, 70]

    private var header: some View {
        HStack(spacing: 0) {
            cell(w[0]) { Text("") }
            headCell("Title", .title, w[1]); headCell("Artist", .artist, w[2]); headCell("Year", .year, w[3])
            headCell("Genre", .genre, w[4]); headCell("Format", .format, w[5])
            cell(w[6]) { Text("Bitrate") }; headCell("Plays", .plays, w[7])
            cell(w[8]) { Text("Last played") }; cell(w[9]) { Text("Added") }
        }
        .font(.system(size: 12, weight: .medium)).foregroundStyle(CU.muted).padding(.vertical, 6)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.black.opacity(0.08)).frame(height: 1) }
    }

    private func headCell(_ t: String, _ k: Key, _ width: CGFloat?) -> some View {
        Button {
            if sortKey == k { ascending.toggle() } else { sortKey = k; ascending = true }
        } label: {
            cell(width) { Text(sortKey == k ? "\(t) \(ascending ? "▴" : "▾")" : t) }
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Sort by \(t)")
        .accessibilityAddTraits(sortKey == k ? .isSelected : [])
    }

    private func row(_ r: SongRow, shaded: Bool, on: Bool) -> some View {
        HStack(spacing: 0) {
            cell(w[0]) { CoverView(album: r.albumItem).frame(width: 24).clipShape(RoundedRectangle(cornerRadius: 4)) }
            cell(w[1]) { Text(r.title).lineLimit(1) }
            cell(w[2]) { Text(r.artist).lineLimit(1) }
            cell(w[3]) { Text(String(r.year)) }
            cell(w[4]) { Text(r.genre).lineLimit(1) }
            cell(w[5]) {
                Text(r.format).font(.system(size: 10.5, weight: .bold)).padding(.horizontal, 7).padding(.vertical, 1)
                    .background(on ? Color.white.opacity(0.25) : CU.fill, in: RoundedRectangle(cornerRadius: 5))
            }
            cell(w[6]) { Text(r.bitrate) }; cell(w[7]) { Text(String(r.plays)) }
            cell(w[8]) { Text(r.lastPlayed) }; cell(w[9]) { Text(r.added) }
        }
        .font(.system(size: 13)).monospacedDigit()
        .foregroundStyle(on ? Color.white : CU.ink)
        .padding(.vertical, 4)
        .background {
            if on { RoundedRectangle(cornerRadius: 7, style: .continuous).fill(CU.accent) }
            else if shaded { Rectangle().fill(Color(red: 0.965, green: 0.965, blue: 0.973)) }
        }
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(on ? .isSelected : [])
    }

    private func cell<C: View>(_ width: CGFloat?, @ViewBuilder _ c: () -> C) -> some View {
        ZStack(alignment: .leading) { Color.clear.frame(height: 1); c() }
            .padding(.horizontal, 8)
            .frame(width: width)
            .frame(maxWidth: width == nil ? .infinity : nil, alignment: .leading)
    }
}

/// Capsule segmented control used by the library and the queue inspector (selected segment is a white capsule).
struct CUSegmented: View {
    let options: [String]
    @Binding var selection: String

    var body: some View {
        HStack(spacing: 0) {
            ForEach(options, id: \.self) { o in
                let on = o == selection
                Button { selection = o } label: {
                    Text(o).font(.system(size: 13, weight: on ? .semibold : .medium)).lineLimit(1).fixedSize()
                        .padding(.horizontal, 14).padding(.vertical, 3)
                        .background(on ? Color.white : .clear, in: Capsule())
                        .shadow(color: .black.opacity(on ? 0.15 : 0), radius: 1.5, y: 1)
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(on ? .isSelected : [])
            }
        }
        .padding(3).background(Color(red: 0.47, green: 0.47, blue: 0.5).opacity(0.14), in: Capsule())
    }
}
