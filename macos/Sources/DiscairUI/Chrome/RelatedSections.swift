import DiscairLibrarian
import SwiftUI

/// Similar artists (the ones in the library first, then the rest under "Not in your library") and, on an album page,
/// similar albums the library lacks. All from the Librarian; a section with nothing is left out. Used by both themes.
struct RelatedSections: View {
    let state: AppState
    /// The album page also shows similar albums.
    var albums = false
    /// Artist page: one row with the artists you own and the ones you do not, the latter noted "Not in your library".
    var mixed = false

    private var zine: Bool { state.themeID == .zine }

    var body: some View {
        let r = state.related
        VStack(alignment: .leading, spacing: 0) {
            if mixed {
                if !r.artists.isEmpty { artistRow("Similar artists", r.artists, open: true) }
            } else {
                if !r.ownedArtists.isEmpty { artistRow("Similar artists in your library", r.ownedArtists, open: true) }
                if !r.otherArtists.isEmpty { artistRow("Not in your library", r.otherArtists, open: true) }
            }
            if albums && !r.albums.isEmpty { albumRow("Similar albums not in your library", r.albums) }
            if r.loading && r.artists.isEmpty && r.albums.isEmpty {
                Text("Looking for similar artists…").font(zine ? Z.mono(11) : .system(size: 12)).foregroundStyle(zine ? Z.ink.opacity(0.6) : CU.muted).padding(.top, 14)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func heading(_ title: String) -> some View {
        Group {
            if zine { ZineH2(title, size: 20) } else { Text(title).font(CU.title(20)) }
        }
        .padding(.top, 22).padding(.bottom, 10).accessibilityAddTraits(.isHeader)
    }

    private func artistRow(_ title: String, _ list: [SimilarArtistEntry], open: Bool) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            heading(title)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(alignment: .top, spacing: 16) {
                    ForEach(list) { a in
                        let tile = VStack(spacing: 6) {
                            ArtistPhoto(name: a.name, url: a.artworkURL, size: 76)
                            Text(a.name).font(zine ? Z.serif(12, bold: true) : .system(size: 12, weight: .medium)).lineLimit(2)
                                .multilineTextAlignment(.center).frame(width: 90)
                        }
                        if open {
                            Button { state.open(similar: a) } label: {
                                VStack(spacing: 2) {
                                    tile
                                    if !a.owned { Text("Not in your library").font(zine ? Z.mono(9) : .system(size: 10)).opacity(0.6) }
                                }
                                .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain).accessibilityLabel(a.owned ? "Open artist \(a.name)" : "Open artist \(a.name), not in your library")
                        } else {
                            VStack(spacing: 2) {
                                tile
                                Text("Not in your library").font(zine ? Z.mono(9) : .system(size: 10)).opacity(0.6)
                            }
                            .accessibilityElement(children: .combine).accessibilityLabel("\(a.name), not in your library")
                        }
                    }
                }
            }
        }
    }

    private func albumRow(_ title: String, _ list: [AlbumItem]) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            heading(title)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(alignment: .top, spacing: 16) {
                    ForEach(list) { a in
                        Button { state.open(album: a) } label: {
                            VStack(alignment: .leading, spacing: 5) {
                                Group {
                                    if zine { ZineCover(album: a, width: 110) }
                                    else { CoverView(album: a).frame(width: 110).clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous)).shadow(color: .black.opacity(0.2), radius: 6, y: 3) }
                                }
                                Text(a.title).font(zine ? Z.serif(12, bold: true) : .system(size: 12, weight: .semibold)).lineLimit(1)
                                Text(a.artist).font(zine ? Z.mono(10) : .system(size: 11)).opacity(0.7).lineLimit(1)
                            }
                            .frame(width: 110, alignment: .leading).contentShape(Rectangle())
                        }
                        .buttonStyle(.plain).accessibilityLabel("\(a.title) by \(a.artist), not in your library")
                    }
                }
            }
        }
    }
}
