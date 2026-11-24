import SwiftUI

/// The Library page: one search field for owned music, tabs for Artists, Albums and Songs, and an overview with the newest
/// albums as tiles and a pane of the 20 songs played last. On the overview the search shows a floating sheet of results; on
/// a tab it filters what that tab lists.
struct CupertinoLibraryHub: View {
    @Bindable var state: AppState
    @FocusState private var searchFocused: Bool
    @State private var matches: (query: String, tab: LibraryTab, rows: LibrarySearchResults)?
    @State private var songHits: (query: String, rows: [SongRow])?

    private var query: String { state.librarySearch }
    private func searchRequest(query: String, tab: LibraryTab) -> LibrarySearchRequest {
        guard !query.isEmpty else { return LibrarySearchRequest(query: query, tab: tab) }
        var snapshot = state.searchLibrarySnapshot()
        if tab == .albums, state.neverPlayedOnly {
            snapshot.albums = state.library.neverPlayedAlbums
            snapshot.recent = []
        }
        return LibrarySearchRequest(query: query, tab: tab, library: snapshot,
                                    songs: tab == .overview || tab == .songs ? state.library.songs : [],
                                    serverSongs: songHits?.query == query ? songHits?.rows ?? [] : [])
    }

    var body: some View {
        let text = query.trimmingCharacters(in: .whitespacesAndNewlines)
        let tab = state.libraryTab
        let request = searchRequest(query: text, tab: tab)
        let appliedQuery = !text.isEmpty && matches?.tab == tab ? matches?.query ?? "" : ""
        let filtered = text.isEmpty ? nil : (matches?.tab == tab ? matches?.rows ?? LibrarySearchResults() : LibrarySearchResults())
        let remoteQuery = tab == .overview ? text : ""
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .center, spacing: 16) {
                Text("Library").font(CU.title(34)).accessibilityAddTraits(.isHeader)
                CUSegmented(options: LibraryTab.allCases.map(\.rawValue), selection: Binding(
                    get: { state.libraryTab.rawValue },
                    set: { state.libraryTab = LibraryTab(rawValue: $0) ?? .overview }))
                Spacer(minLength: 0)
                searchField
            }
            .padding(.horizontal, CU.Space.xl).padding(.top, 4).padding(.bottom, 16)
            .zIndex(2)
            .overlay(alignment: .topTrailing) {
                if tab == .overview, !text.isEmpty {
                    sheet(results: appliedQuery == text ? filtered : nil, searching: appliedQuery != text)
                        .padding(.top, 52).padding(.trailing, CU.Space.xl)
                }
            }
            .zIndex(2)

            Group {
                switch tab {
                case .overview: overview
                case .artists: CupertinoArtistsIndex(state: state, showHeader: false, filtered: filtered?.artists)
                case .albums: CupertinoAlbumsGrid(state: state, query: appliedQuery, showHeader: false, filtered: filtered?.albums)
                case .songs: CupertinoLibrary(state: state, query: appliedQuery, embedded: true, filtered: filtered?.songs)
                }
            }
            .zIndex(1)
        }
        .onAppear(perform: syncTab)
        .onChange(of: state.screen) { _, _ in syncTab() }
        .task(id: state.library.isLive) { await state.loadAllSongs() }
        .task(id: request) {
            guard !text.isEmpty else { matches = nil; return }
            let rows = await request.results()
            guard !Task.isCancelled, state.libraryTab == tab,
                  state.librarySearch.trimmingCharacters(in: .whitespacesAndNewlines) == text else { return }
            matches = (text, tab, rows)
        }
        .task(id: remoteQuery) {
            songHits = nil
            guard !remoteQuery.isEmpty else { return }
            let rows = await state.searchSongHits(remoteQuery)
            guard !Task.isCancelled, state.libraryTab == .overview,
                  state.librarySearch.trimmingCharacters(in: .whitespacesAndNewlines) == remoteQuery else { return }
            songHits = (remoteQuery, rows)
        }
    }

    /// The old screens (Albums, Artists, Recently Added) are tabs of this page now.
    private func syncTab() {
        switch state.screen {
        case .albums: state.libraryTab = .albums; state.screen = .library
        case .artists: state.libraryTab = .artists; state.screen = .library
        case .recent: state.libraryTab = .overview; state.screen = .library
        case .queue: state.screen = .library
        default: break
        }
    }

    private var searchField: some View {
        HStack(spacing: 8) {
            Image(systemName: "magnifyingglass").foregroundStyle(CU.textSecondary).accessibilityHidden(true)
            TextField(state.libraryTab == .overview ? "Search your library" : "Filter \(state.libraryTab.rawValue.lowercased())", text: $state.librarySearch)
                .textFieldStyle(.plain).focused($searchFocused)
                .accessibilityLabel(state.libraryTab == .overview ? "Search your library" : "Filter \(state.libraryTab.rawValue)")
                .onExitCommand { state.librarySearch = "" }
            if !query.isEmpty {
                Button { state.librarySearch = "" } label: { Image(systemName: "xmark.circle.fill").foregroundStyle(CU.textSecondary) }
                    .buttonStyle(.plain).accessibilityLabel("Clear search")
            }
        }
        .font(CU.Font.body.weighted(.regular))
        .padding(.horizontal, 16).frame(width: 300, height: 34)
        .background(CU.bgFill, in: Capsule())
    }

    // MARK: Overview

    private var overview: some View {
        HStack(alignment: .top, spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    Text("Recently Added").font(CU.title(20)).padding(.bottom, 16).accessibilityAddTraits(.isHeader)
                    if state.library.phase == .loading { Text("Loading your library…").foregroundStyle(CU.textSecondary).padding(.bottom, 8) }
                    if case .failed(let m) = state.library.phase { CUErrorLine(message: m).padding(.bottom, 8) }
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 128, maximum: 128), spacing: 16, alignment: .top)], alignment: .leading, spacing: 16) {
                        ForEach(state.visible(state.library.recent)) { a in AlbumTile(state: state, album: a) }
                    }
                }
                .padding(.leading, CU.Space.xl).padding(.trailing, 16)
            }
            .scrollEdgeEffectStyle(.hard, for: .top)
            LibraryRecentlyPlayed(state: state)
        }
    }

    // MARK: Search sheet

    private func sheet(results: LibrarySearchResults?, searching: Bool) -> some View {
        let r = results ?? LibrarySearchResults()
        return ScrollView {
            VStack(alignment: .leading, spacing: 4) {
                if r.isEmpty {
                    Text(searching ? "Searching…" : "Nothing in your library matches.").foregroundStyle(CU.textSecondary).padding(8)
                }
                if !r.artists.isEmpty {
                    sectionTitle("Artists")
                    ForEach(r.artists) { a in
                        resultRow(icon: "music.mic", title: a.name, detail: "\(a.albumCount) albums") { close(); state.open(artist: a) }
                    }
                }
                if !r.albums.isEmpty {
                    sectionTitle("Albums")
                    ForEach(r.albums) { a in
                        resultRow(cover: a, title: a.title, detail: a.artist) { close(); state.open(album: a) }
                    }
                }
                if !r.songs.isEmpty {
                    sectionTitle("Songs")
                    ForEach(r.songs) { s in
                        resultRow(cover: s.albumItem, title: s.title, detail: "\(s.artist) — \(s.albumItem.title)") {
                            close(); state.open(album: s.albumItem, highlighting: s.title)
                        }
                    }
                }
            }
            .padding(8)
        }
        .font(CU.Font.body.weighted(.regular))
        .frame(width: 420).frame(maxHeight: 420).fixedSize(horizontal: false, vertical: true)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 16, style: .continuous).stroke(CU.text.opacity(0.08), lineWidth: 1))
        .shadow(color: CU.shadowInk.opacity(0.18), radius: 16, y: 6)
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Search results")
    }

    private func close() { state.librarySearch = "" }

    private func sectionTitle(_ t: String) -> some View {
        Text(t).font(CU.Font.caption.weighted(.bold)).foregroundStyle(CU.textSecondary).padding(.horizontal, 8).padding(.top, 8)
            .accessibilityAddTraits(.isHeader)
    }

    private func resultRow(icon: String? = nil, cover: AlbumItem? = nil, title: String, detail: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if let cover { CoverView(album: cover).frame(width: 32).clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous)).accessibilityHidden(true) }
                else if let icon { Image(systemName: icon).foregroundStyle(CU.accent).frame(width: 32).accessibilityHidden(true) }
                VStack(alignment: .leading, spacing: 0) {
                    Text(title).fontWeight(.semibold).lineLimit(1)
                    Text(detail).font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary).lineLimit(1)
                }
                Spacer(minLength: 0)
            }
            .padding(.horizontal, 8).padding(.vertical, 4).contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(title), \(detail)")
    }
}

private struct LibraryRecentlyPlayed: View {
    let state: AppState

    var body: some View {
        let songs = state.recentlyPlayed
        return VStack(alignment: .leading, spacing: 8) {
            Text("Recently played").font(CU.title(20)).padding(.bottom, 8).accessibilityAddTraits(.isHeader)
            if songs.isEmpty {
                Text(state.library.songsLoading ? "Reading your songs…" : "Nothing played yet.").foregroundStyle(CU.textSecondary)
            }
            ScrollView {
                VStack(spacing: 0) {
                    ForEach(songs) { s in
                        Button { state.open(album: s.albumItem, highlighting: s.title) } label: {
                            HStack(spacing: 8) {
                                CoverView(album: s.albumItem).frame(width: 36).clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous)).accessibilityHidden(true)
                                VStack(alignment: .leading, spacing: 0) {
                                    Text(s.title).fontWeight(.semibold).lineLimit(1)
                                    Text(s.artist).font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary).lineLimit(1)
                                }
                                Spacer(minLength: 0)
                            }
                            .padding(.vertical, 4).contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("\(s.title), \(s.artist)")
                    }
                }
            }
        }
        .font(CU.Font.body.weighted(.regular))
        .padding(.leading, 16).padding(.trailing, 24).padding(.bottom, 16)
        .frame(width: 270)
        .overlay(alignment: .leading) { Rectangle().fill(CU.text.opacity(0.08)).frame(width: 1) }
    }
}

/// One album as a cover tile; opens the album page.
struct AlbumTile: View {
    let state: AppState
    let album: AlbumItem
    var body: some View {
        Button { state.open(album: album) } label: {
            VStack(alignment: .leading, spacing: 0) {
                CoverView(album: album).frame(width: 128).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .shadow(color: CU.shadowInk.opacity(0.2), radius: 7, y: 4).padding(.bottom, 8)
                Text(album.title).fontWeight(.semibold).lineLimit(1)
                Text(album.artist).foregroundStyle(CU.textSecondary).lineLimit(1)
            }
            .font(CU.Font.body.weighted(.regular)).frame(width: 128, alignment: .leading)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(album.title), \(album.artist)")
    }
}
