import SwiftUI

/// Artists: every artist in the library, grouped by first letter. Opening one shows that artist's page, which has its
/// own Back button to this list.
struct CupertinoArtistsIndex: View {
    let state: AppState

    private var groups: [(letter: String, artists: [ArtistItem])] {
        let by = Dictionary(grouping: state.library.artists, by: \.letter)
        return by.keys.sorted { a, b in a == "#" ? false : (b == "#" ? true : a < b) }.map { k in
            (k, (by[k] ?? []).sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending })
        }
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                Text("Artists").font(CU.title(34)).padding(.top, 4).padding(.bottom, 6)
                if state.library.phase == .loading { Text("Loading your library…").foregroundStyle(CU.muted).padding(.bottom, 8) }
                if case .failed(let m) = state.library.phase { Text(m).foregroundStyle(CU.accent).padding(.bottom, 8) }
                ForEach(groups, id: \.letter) { g in
                    Text(g.letter).font(CU.title(20)).foregroundStyle(CU.accent).padding(.top, 18).padding(.bottom, 6)
                        .accessibilityAddTraits(.isHeader)
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 220), spacing: 12, alignment: .leading)], alignment: .leading, spacing: 2) {
                        ForEach(g.artists) { a in
                            Button { state.open(artist: a) } label: {
                                HStack(spacing: 8) {
                                    Text(a.name).lineLimit(1)
                                    Spacer(minLength: 4)
                                    Text("\(a.albumCount)").font(.system(size: 12)).monospacedDigit().foregroundStyle(CU.muted)
                                }
                                .padding(.horizontal, 10).padding(.vertical, 6)
                                .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)
                            .accessibilityLabel("\(a.name), \(a.albumCount) albums")
                        }
                    }
                }
            }
            .font(.system(size: 13.5))
            .padding(.horizontal, 28).padding(.bottom, 28)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
    }
}
