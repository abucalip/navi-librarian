import SwiftUI

/// Library: Songs table with sortable columns and a selected row, a source segmented control, and a view switch with
/// Columns (opt-in, contract section 6). Mockup: `R.cupertino.library`. Zebra rows, selection in the accent colour.
struct CupertinoLibrary: View {
    let state: AppState
    @State private var sortKey: SongColumn = .title
    @State private var ascending = true
    @State private var selected = 1
    @State private var source = "Songs"
    @State private var viewMode = "Table"
    @State private var onlyMissingMBID = false
    /// The table shows 100 songs at a time: drawing the whole library at once froze the window.
    @State private var page = 0
    static let pageSize = 100

    private var rows: [SongRow] { SongTable.sorted(state.library.songs, by: sortKey, ascending: ascending, onlyMissingMBID: onlyMissingMBID) }

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
                    Toggle("No MBID", isOn: $onlyMissingMBID).toggleStyle(.button).controlSize(.small)
                        .help("Show only songs without a MusicBrainz id")
                    CUSegmented(options: ["Table", "Grid", "Columns"], selection: $viewMode)
                }
                .padding(.top, 4).padding(.bottom, 12)

                if viewMode == "Columns" {
                    CupertinoMiller(state: state).frame(height: 460)
                    footer
                } else {
                header
                let all = rows
                let pages = Self.pageCount(all.count)
                let current = min(page, pages - 1)
                let first = current * Self.pageSize
                ForEach(Array(all[first..<min(all.count, first + Self.pageSize)].enumerated()), id: \.element.id) { n, r in
                    let i = first + n   // position in the whole sorted list: the queue is the table in the order shown
                    row(r, shaded: n % 2 == 0, on: r.id == selected)
                        .onTapGesture(count: 2) { selected = r.id; state.play(rows: all, startAt: i) }
                        .onTapGesture { selected = r.id }
                        .contextMenu {
                            Button("Play") { state.play(rows: all, startAt: i) }
                            if let item = PlayerModel.item(r) {
                                Button("Play Next") { state.player.playNext(item) }
                                Button("Add to Queue") { state.player.addToQueue(item) }
                            }
                        }
                }
                pager(total: all.count, pages: pages, current: current)
                footer
                }
            }
            .padding(.horizontal, 28).padding(.bottom, 28)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .onChange(of: sortKey) { _, _ in page = 0 }
        .onChange(of: ascending) { _, _ in page = 0 }
        .onChange(of: onlyMissingMBID) { _, _ in page = 0 }
        .task(id: state.library.isLive) { await state.loadAllSongs() }
    }

    static func pageCount(_ rows: Int) -> Int { max(1, (rows + pageSize - 1) / pageSize) }

    private func pager(total: Int, pages: Int, current: Int) -> some View {
        HStack(spacing: 10) {
            Button { page = max(0, current - 1) } label: { Image(systemName: "chevron.left") }
                .buttonStyle(CapsuleButtonStyle(small: true)).disabled(current == 0).accessibilityLabel("Previous page")
            Text(total == 0 ? "No songs" : "Songs \(current * Self.pageSize + 1)–\(min(total, (current + 1) * Self.pageSize)) of \(total) · Page \(current + 1) of \(pages)")
                .font(.system(size: 12)).monospacedDigit().foregroundStyle(CU.muted)
            Button { page = min(pages - 1, current + 1) } label: { Image(systemName: "chevron.right") }
                .buttonStyle(CapsuleButtonStyle(small: true)).disabled(current >= pages - 1).accessibilityLabel("Next page")
        }
        .padding(.top, 12)
    }

    /// Loading, failure and paging. Sorting only reorders the songs already loaded, and the footer says so.
    @ViewBuilder private var footer: some View {
        let lib = state.library
        if lib.isLive {
            VStack(alignment: .leading, spacing: 8) {
                if lib.songsLoading { HStack(spacing: 8) { ProgressView().controlSize(.small); Text("Loading songs… \(lib.songs.count) so far") }.foregroundStyle(CU.muted) }
                if let e = lib.songsError {
                    Text(e).foregroundStyle(CU.muted)
                    Button("Try again") { Task { await state.loadAllSongs() } }
                        .buttonStyle(CapsuleButtonStyle(primary: true, small: true))
                } else if lib.songsHaveMore && !lib.songsLoading {
                    Button("Load more songs") { Task { await state.loadAllSongs() } }.buttonStyle(CapsuleButtonStyle(small: true))
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

    private let w: [CGFloat?] = [36, nil, 150, 52, 92, 108, 74, 74, 52, 92, 70, 64]

    private var header: some View {
        HStack(spacing: 0) {
            cell(w[0]) { Text("") }
            headCell(.title, w[1]); headCell(.artist, w[2]); headCell(.year, w[3]); headCell(.genre, w[4])
            headCell(.format, w[5]); headCell(.bitrate, w[6]); headCell(.rating, w[7]); headCell(.plays, w[8])
            headCell(.lastPlayed, w[9]); headCell(.added, w[10]); headCell(.mbid, w[11])
        }
        .font(.system(size: 12, weight: .medium)).foregroundStyle(CU.muted).padding(.vertical, 6)
        .overlay(alignment: .bottom) { Rectangle().fill(Color.black.opacity(0.08)).frame(height: 1) }
    }

    private func headCell(_ k: SongColumn, _ width: CGFloat?) -> some View {
        Button {
            if sortKey == k { ascending.toggle() } else { sortKey = k; ascending = k.startsAscending }
        } label: {
            cell(width) { Text(sortKey == k ? "\(k.rawValue) \(ascending ? "▴" : "▾")" : k.rawValue).lineLimit(1) }
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Sort by \(k.rawValue)")
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
            cell(w[6]) { Text(r.bitrate) }
            cell(w[7]) { Text(SongTable.stars(r.rating)).font(.system(size: 11)).accessibilityLabel(r.rating > 0 ? "\(r.rating) stars" : "Not rated") }
            cell(w[8]) { Text(String(r.plays)) }
            cell(w[9]) { Text(r.lastPlayed) }; cell(w[10]) { Text(r.added) }
            cell(w[11]) { if !r.hasMBID { Text("Missing").font(.system(size: 11, weight: .semibold)).foregroundStyle(on ? Color.white : CU.accent) } }
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
