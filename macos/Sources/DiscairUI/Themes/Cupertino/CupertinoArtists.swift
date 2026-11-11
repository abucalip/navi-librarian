import SwiftUI

/// Artists: every artist in the library, grouped by first letter. Opening one shows that artist's page, which has its
/// own Back button to this list.
struct CupertinoArtistsIndex: View {
    let state: AppState
    /// Text from the Library search field; only matching artists show.
    var query = ""
    var showHeader = true

    private var groups: [(letter: String, artists: [ArtistItem])] {
        let by = Dictionary(grouping: LibrarySearch.artists(state.library.artists, query: query), by: \.letter)
        return by.keys.sorted { a, b in a == "#" ? false : (b == "#" ? true : a < b) }.map { k in
            (k, (by[k] ?? []).sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending })
        }
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                if showHeader { Text("Artists").font(CU.title(34)).padding(.top, 4).padding(.bottom, 8) }
                if state.library.phase == .loading { Text("Loading your library…").foregroundStyle(CU.muted).padding(.bottom, 8) }
                if case .failed(let m) = state.library.phase { CUErrorLine(message: m).padding(.bottom, 8) }
                ForEach(groups, id: \.letter) { g in
                    Text(g.letter).font(CU.title(20)).foregroundStyle(CU.accent).padding(.top, 16).padding(.bottom, 8)
                        .accessibilityAddTraits(.isHeader)
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 220), spacing: 8, alignment: .leading)], alignment: .leading, spacing: 4) {
                        ForEach(g.artists) { a in
                            Button { state.open(artist: a) } label: {
                                HStack(spacing: 8) {
                                    Text(a.name).lineLimit(1)
                                    Spacer(minLength: 4)
                                    Text("\(a.albumCount)").font(CU.Font.callout.weighted(.regular)).monospacedDigit().foregroundStyle(CU.muted)
                                }
                                .padding(.horizontal, 8).padding(.vertical, 8)
                                .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)
                            .accessibilityLabel("\(a.name), \(a.albumCount) albums")
                        }
                    }
                }
            }
            .font(CU.Font.body.weighted(.regular))
            .padding(.horizontal, CU.Space.xl).padding(.bottom, CU.Space.xl)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
    }
}
