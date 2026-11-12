import DiscairLibrarian
import SwiftUI

/// A fixed random pick: the same salt gives the same order, a new salt (each visit) a new one.
enum RandomPick {
    static func pick<T: Identifiable>(_ list: [T], _ count: Int, salt: UInt64) -> [T] {
        Array(list.sorted { rank("\($0.id)", salt) < rank("\($1.id)", salt) }.prefix(count))
    }

    /// FNV-1a over the id, mixed with the salt.
    private static func rank(_ id: String, _ salt: UInt64) -> UInt64 {
        var h: UInt64 = 0xcbf29ce484222325 ^ salt
        for b in id.utf8 { h = (h ^ UInt64(b)) &* 0x100000001b3 }
        return h
    }
}

/// Round artist photos with the name under them, Cupertino's look. Opens the artist's page.
struct SimilarArtistCircle: View {
    let state: AppState
    let artist: SimilarArtistEntry
    var size: CGFloat = 104

    var body: some View {
        Button { state.open(similar: artist) } label: {
            VStack(spacing: 6) {
                ArtistPhoto(name: artist.name, url: artist.artworkURL, size: size)
                Text(artist.name).font(.system(size: 12.5, weight: .medium)).lineLimit(2).multilineTextAlignment(.center).frame(width: size + 20)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(artist.owned ? "Open artist \(artist.name)" : "Open artist \(artist.name), not in your library")
    }
}

/// A square cover with title and artist, for an album the library lacks.
struct SimilarAlbumSquare: View {
    let state: AppState
    let album: AlbumItem
    var side: CGFloat = 110

    var body: some View {
        Button { state.open(album: album) } label: {
            VStack(alignment: .leading, spacing: 5) {
                CoverView(album: album).frame(width: side).clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    .shadow(color: .black.opacity(0.2), radius: 6, y: 3)
                Text(album.title).font(.system(size: 12, weight: .semibold)).lineLimit(1)
                Text(album.artist).font(.system(size: 11)).opacity(0.7).lineLimit(1)
            }
            .frame(width: side, alignment: .leading).contentShape(Rectangle())
        }
        .buttonStyle(.plain).accessibilityLabel("\(album.title) by \(album.artist), not in your library")
    }
}

/// The album page's related lists (Cupertino): similar artists in the library, six at random in two rows of three; then
/// "Not in your library" with two boxes side by side, six artists as circles and six albums as squares, each in two rows of three.
struct AlbumRelatedGrids: View {
    let state: AppState
    @State private var salt = UInt64.random(in: 0...UInt64.max)

    private func rows<V: View>(_ items: [V], spacing: CGFloat = 18) -> some View {
        let first = Array(items.prefix(3)), second = Array(items.dropFirst(3).prefix(3))
        return VStack(alignment: .leading, spacing: spacing) {
            HStack(alignment: .top, spacing: 18) { ForEach(first.indices, id: \.self) { first[$0] } }
            if !second.isEmpty { HStack(alignment: .top, spacing: 18) { ForEach(second.indices, id: \.self) { second[$0] } } }
        }
    }

    private func heading(_ title: String, size: CGFloat = 20) -> some View {
        Text(title).font(CU.title(size)).padding(.top, 40).padding(.bottom, 10).accessibilityAddTraits(.isHeader)
    }

    var body: some View {
        let r = state.related
        let owned = RandomPick.pick(r.ownedArtists, 6, salt: salt)
        let others = RandomPick.pick(r.otherArtists, 6, salt: salt)
        let albums = RandomPick.pick(r.albums, 6, salt: salt)
        VStack(alignment: .leading, spacing: 0) {
            if !owned.isEmpty {
                heading("Similar artists")
                rows(owned.map { SimilarArtistCircle(state: state, artist: $0, size: 112) })
            }
            if !others.isEmpty || !albums.isEmpty {
                heading("Not in your library")
                HStack(alignment: .top, spacing: 20) {
                    if !others.isEmpty { box("Similar artists") { rows(others.map { SimilarArtistCircle(state: state, artist: $0, size: 84) }) } }
                    if !albums.isEmpty { box("Albums") { rows(albums.map { SimilarAlbumSquare(state: state, album: $0, side: 96) }) } }
                }
            }
            if r.loading && r.artists.isEmpty && r.albums.isEmpty {
                Text("Looking for similar artists…").font(.system(size: 12)).foregroundStyle(CU.textSecondary).padding(.top, 14)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .onChange(of: state.selectedAlbum.id) { _, _ in salt = .random(in: 0...UInt64.max) }
    }

    private func box<C: View>(_ title: String, @ViewBuilder _ content: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title).font(.system(size: 12, weight: .semibold)).foregroundStyle(CU.textSecondary).textCase(.uppercase).accessibilityAddTraits(.isHeader)
            content()
        }
    }
}

/// The artist page's similar artists (Cupertino): as many round photos as fit one row of the album grid, picked at random each visit.
struct ArtistSimilarRow: View {
    let state: AppState
    @State private var salt = UInt64.random(in: 0...UInt64.max)

    var body: some View {
        let list = state.related.artists
        if !list.isEmpty {
            VStack(alignment: .leading, spacing: 0) {
                Text("Similar artists").font(CU.title(20)).padding(.top, ArtistSpacing.beforeHeading).padding(.bottom, ArtistSpacing.afterHeading)
                    .accessibilityAddTraits(.isHeader)
                // The same columns as the album grid, so the circles start and end where the albums do.
                GeometryReader { g in
                    let n = ArtistSpacing.columns, gap = ArtistSpacing.gap
                    let tile = (g.size.width - gap * CGFloat(n - 1)) / CGFloat(n)
                    HStack(alignment: .top, spacing: gap) {
                        ForEach(RandomPick.pick(list, n, salt: salt)) { a in
                            SimilarArtistCircle(state: state, artist: a, size: tile).frame(width: tile)
                        }
                        Spacer(minLength: 0)
                    }
                }
                .frame(height: 148 + 44)
            }
            .onChange(of: state.selectedArtist.id) { _, _ in salt = .random(in: 0...UInt64.max) }
        } else if state.related.loading {
            Text("Looking for similar artists…").font(.system(size: 12)).foregroundStyle(CU.textSecondary).padding(.top, 14)
        }
    }
}

/// The album page's Booklet tab: the booklet's pages as thumbnails; a click opens the dark reader. Nothing when the album has none.
struct AlbumBookletTab: View {
    let state: AppState
    @Environment(\.artwork) private var store
    @State private var booklet: BookletView?
    @State private var loaded = false
    @State private var showing = false

    var body: some View {
        Group {
            if let booklet {
                VStack(alignment: .center, spacing: 28) {
                    Button { showing = true } label: { Label("Open the booklet · \(booklet.badgeText)", systemImage: "book") }
                        .buttonStyle(CapsuleButtonStyle(primary: true))
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 120, maximum: 120), spacing: 14, alignment: .top)], alignment: .center, spacing: 14) {
                        ForEach(booklet.items.filter { !$0.isPDF }) { p in
                            Button { showing = true } label: {
                                AlbumPictureView(picture: p, size: .thumb).frame(width: 120, height: 120)
                                    .background(Color.black.opacity(0.06)).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                            }
                            .buttonStyle(.plain).accessibilityLabel(p.label)
                        }
                    }
                }
            } else {
                Text(loaded ? "This album has no booklet." : "Looking for the booklet…").foregroundStyle(CU.textSecondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .center)
        .sheet(isPresented: $showing) { if let booklet { BookletSheet(booklet: booklet) { showing = false } } }
        .task(id: "\(state.related.releaseGroupMBID ?? "")|\(store?.generation ?? 0)") {
            booklet = nil; loaded = false
            guard let rg = state.related.releaseGroupMBID, !rg.isEmpty, let store else { return }
            if case .ready(let index) = await store.artworkIndex(rgid: rg, release: nil), !Task.isCancelled { booklet = index.bookletView }
            loaded = true
        }
    }
}
