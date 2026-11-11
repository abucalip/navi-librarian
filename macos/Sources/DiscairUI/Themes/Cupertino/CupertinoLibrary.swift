import SwiftUI

/// Library: Songs table with sortable columns and a selected row, a source segmented control, and a view switch with
/// Columns (opt-in, contract section 6). Mockup: `R.cupertino.library`. Zebra rows, selection in the accent colour.
struct CupertinoLibrary: View {
    let state: AppState
    /// Text from the Library search field; only matching songs show.
    var query = ""
    /// Inside the Library page: no heading or source switch of its own.
    var embedded = false
    @State private var sortKey: SongColumn = .title
    @State private var ascending = true
    @State private var selected = 1
    @State private var source = "Songs"
    @State private var viewMode = "Table"
    @State private var onlyMissingMBID = false
    /// The table shows 100 songs at a time: drawing the whole library at once froze the window.
    @State private var page = 0
    static let pageSize = 100

    private var rows: [SongRow] { SongTable.sorted(LibrarySearch.songs(state.library.songs, query: query).filter { state.tasteFilter?.matches($0) ?? true }, by: sortKey, ascending: ascending, onlyMissingMBID: onlyMissingMBID) }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                HStack(spacing: 16) {
                    if !embedded {
                        Text("Songs").font(CU.title(34))
                        CUSegmented(options: ["Songs", "Albums", "Artists", "Missing"], selection: $source)
                    }
                    Spacer()
                    Button { let shown = rows; if let i = shown.firstIndex(where: { $0.id == selected }) { state.play(rows: shown, startAt: i) } } label: { Label("Play", systemImage: "play.fill") }
                        .buttonStyle(CapsuleButtonStyle(primary: true, small: true)).disabled(!state.library.isLive)
                        .help("Play the selected song, then the rows below it")
                    Toggle("No MBID", isOn: $onlyMissingMBID).toggleStyle(.button).controlSize(.small)
                        .help("Show only songs without a MusicBrainz id")
                    CUSegmented(options: ["Table", "Grid", "Columns"], selection: $viewMode)
                }
                .padding(.top, 4).padding(.bottom, 16)
                if let f = state.tasteFilter {
                    Button { state.tasteFilter = nil } label: { Label("From your taste: \(f.label)", systemImage: "xmark.circle.fill") }
                        .buttonStyle(CapsuleButtonStyle(small: true, outlined: true)).padding(.bottom, 8)
                        .accessibilityLabel("Clear the \(f.label) filter from your taste")
                }

                if viewMode == "Columns" {
                    CupertinoMiller(state: state).frame(height: 460)
                    footer
                } else {
                let all = rows
                let pages = Self.pageCount(all.count)
                let current = min(page, pages - 1)
                let first = current * Self.pageSize
                if viewMode == "Grid" {
                    // Covers, one tile per song (the table is the list view); double-click plays from that song.
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 128, maximum: 128), spacing: 16, alignment: .top)], alignment: .leading, spacing: 16) {
                        ForEach(Array(all[first..<min(all.count, first + Self.pageSize)].enumerated()), id: \.element.id) { n, r in
                            let i = first + n
                            VStack(alignment: .leading, spacing: 0) {
                                CoverView(album: r.albumItem).frame(width: 128).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                                    .overlay { if r.id == selected { RoundedRectangle(cornerRadius: 8, style: .continuous).stroke(CU.accent, lineWidth: 3) } }
                                    .shadow(color: CU.shadowInk.opacity(0.2), radius: 7, y: 4).padding(.bottom, 8)
                                Text(r.title).fontWeight(.semibold).lineLimit(1)
                                Text(r.artist).foregroundStyle(CU.muted).lineLimit(1)
                            }
                            .font(CU.Font.body.weighted(.regular)).frame(width: 128, alignment: .leading).contentShape(Rectangle())
                            .onTapGesture(count: 2) { selected = r.id; state.play(rows: all, startAt: i) }
                            .onTapGesture { selected = r.id }
                            .contextMenu {
                                Button("Play") { state.play(rows: all, startAt: i) }
                                if let item = PlayerModel.item(r) {
                                    Button("Play Next") { state.player.playNext(item) }
                                    Button("Add to Queue") { state.player.addToQueue(item) }
                    if state.radio.sonicAvailable {
                        Button("Songs That Sound Like This") { state.startSonicRadio(seed: item) }
                        Button("Sonic Path from Playing Song") { state.showSonicPath(to: item) }
                    }
                                }
                            }
                            .accessibilityElement(children: .combine)
                            .accessibilityLabel("\(r.title), \(r.artist)")
                        }
                    }
                } else {
                header
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
                    if state.radio.sonicAvailable {
                        Button("Songs That Sound Like This") { state.startSonicRadio(seed: item) }
                        Button("Sonic Path from Playing Song") { state.showSonicPath(to: item) }
                    }
                            }
                        }
                }
                }
                pager(total: all.count, pages: pages, current: current)
                footer
                }
            }
            .padding(.horizontal, CU.Space.xl).padding(.bottom, CU.Space.xl)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .onChange(of: sortKey) { _, _ in page = 0 }
        .onChange(of: ascending) { _, _ in page = 0 }
        .onChange(of: onlyMissingMBID) { _, _ in page = 0 }
        .onChange(of: query) { _, _ in page = 0 }
        .onChange(of: viewMode) { _, _ in page = 0 }
        .task(id: state.library.isLive) { await state.loadAllSongs() }
    }

    static func pageCount(_ rows: Int) -> Int { max(1, (rows + pageSize - 1) / pageSize) }

    private func pager(total: Int, pages: Int, current: Int) -> some View {
        HStack(spacing: 8) {
            Button { page = max(0, current - 1) } label: { Image(systemName: "chevron.left") }
                .buttonStyle(CapsuleButtonStyle(small: true)).disabled(current == 0).accessibilityLabel("Previous page")
            Text(total == 0 ? "No songs" : "Songs \(current * Self.pageSize + 1)–\(min(total, (current + 1) * Self.pageSize)) of \(total) · Page \(current + 1) of \(pages)")
                .font(CU.Font.callout.weighted(.regular)).monospacedDigit().foregroundStyle(CU.muted)
            Button { page = min(pages - 1, current + 1) } label: { Image(systemName: "chevron.right") }
                .buttonStyle(CapsuleButtonStyle(small: true)).disabled(current >= pages - 1).accessibilityLabel("Next page")
        }
        .padding(.top, 16)
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
                        .buttonStyle(CapsuleButtonStyle(small: true))
                } else if lib.songsHaveMore && !lib.songsLoading {
                    Button("Load more songs") { Task { await state.loadAllSongs() } }.buttonStyle(CapsuleButtonStyle(small: true))
                }
                if !lib.songs.isEmpty {
                    Text("\(lib.songs.count) songs loaded" + (lib.songsHaveMore ? ". Sorting reorders only these." : "."))
                        .font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.muted)
                }
                if lib.songs.isEmpty && !lib.songsLoading && lib.songsError == nil { Text("No songs in the library yet.").foregroundStyle(CU.muted) }
            }
            .padding(.top, 16)
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
        .font(CU.Font.callout.weighted(.medium)).foregroundStyle(CU.muted).padding(.vertical, 8)
        .overlay(alignment: .bottom) { Rectangle().fill(CU.shadowInk.opacity(0.08)).frame(height: 1) }
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
                Text(r.format).font(CU.Font.caption.weighted(.bold)).padding(.horizontal, 8).padding(.vertical, 0)
                    .background(on ? CU.onAccent.opacity(0.25) : CU.fill, in: RoundedRectangle(cornerRadius: 4))
            }
            cell(w[6]) { Text(r.bitrate) }
            cell(w[7]) { Text(SongTable.stars(r.rating)).font(CU.Font.caption.weighted(.regular)).accessibilityLabel(r.rating > 0 ? "\(r.rating) stars" : "Not rated") }
            cell(w[8]) { Text(String(r.plays)) }
            cell(w[9]) { Text(r.lastPlayed) }; cell(w[10]) { Text(r.added) }
            cell(w[11]) { if !r.hasMBID { Text("Missing").font(CU.Font.caption.weighted(.semibold)).foregroundStyle(on ? CU.onAccent : CU.accent) } }
        }
        .font(CU.Font.body.weighted(.regular)).monospacedDigit()
        .foregroundStyle(on ? CU.onAccent : CU.ink)
        .padding(.vertical, 4)
        .background {
            if on { RoundedRectangle(cornerRadius: 8, style: .continuous).fill(CU.accent) }
            else if shaded { Rectangle().fill(CU.bgPanel) }
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

