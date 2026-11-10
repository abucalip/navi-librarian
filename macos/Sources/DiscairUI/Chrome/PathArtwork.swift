import DiscairLibrarian
import SwiftUI

/// A path row's cover that cycles through the album's alternate covers while the pointer is over the row's thumbnail
/// (docs/artwork.md, idea 10). The index is read only on the first hover, from the release group the Librarian's album page names;
/// an album with fewer than two covers, or one that cannot be looked up, keeps its usual cover. Under Reduce Motion nothing cycles:
/// hovering shows the first alternate cover and holds it. Chosen by type only; nothing is said about the album.
struct PathRowThumb<Usual: View>: View {
    let step: PathStep
    let size: CGFloat
    @ViewBuilder let usual: () -> Usual
    @Environment(\.artwork) private var store
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var hovering = false
    @State private var faces: [ArtworkPicture] = []
    @State private var current = 0

    var body: some View {
        ZStack {
            if hovering, !faces.isEmpty {
                AlbumPictureView(picture: faces[current % faces.count], size: .thumb)
                    .frame(width: size, height: size)
                    .clipShape(RoundedRectangle(cornerRadius: size / 7, style: .continuous))
                    .accessibilityHidden(true)
            } else {
                usual()
            }
        }
        .frame(width: size, height: size)
        .onHover { hovering = $0; if !$0 { current = 0 } }
        .task(id: hovering ? step.id : -1) {
            guard hovering, let cover = step.cover, let store else { return }
            if faces.isEmpty {
                guard let index = await store.nowPlayingIndex(artist: cover.artist, album: cover.title), !Task.isCancelled else { return }
                faces = index.pathCoverFaces
            }
            guard faces.count >= 2, !reduceMotion else { current = faces.isEmpty ? 0 : 1; return }
            current = 1
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(1.2))
                if Task.isCancelled { return }
                current = nextPathCover(after: current, count: faces.count)
            }
        }
    }
}

/// Same Room (idea 10): the two albums' session photos side by side, each under its album's name. Drawn only when at least one of
/// them has a photo; an album with none says so, and nothing is compared or inferred beyond what the pictures are.
struct SameRoomPhotos: View {
    let startTitle: String, startArtist: String, otherTitle: String, otherArtist: String
    @Environment(\.artwork) private var store
    @State private var start: [ArtworkPicture] = []
    @State private var other: [ArtworkPicture] = []

    var body: some View {
        Group {
            if hasRoomPhotos(start, other) {
                HStack(alignment: .top, spacing: 10) {
                    column(startTitle, start)
                    column(otherTitle, other)
                }
                .accessibilityElement(children: .contain)
            }
        }
        .task(id: "\(startArtist)|\(startTitle)|\(otherArtist)|\(otherTitle)") {
            guard let store else { return }
            let a = await store.nowPlayingIndex(artist: startArtist, album: startTitle)?.roomPhotos ?? []
            let b = await store.nowPlayingIndex(artist: otherArtist, album: otherTitle)?.roomPhotos ?? []
            if !Task.isCancelled { start = a; other = b }
        }
    }

    private func column(_ title: String, _ photos: [ArtworkPicture]) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.caption.weight(.semibold)).lineLimit(1).truncationMode(.tail)
            if photos.isEmpty { Text("No session photos").font(.caption).foregroundStyle(.secondary) }
            ForEach(photos) { photo in
                AlbumPictureView(picture: photo, size: .display)
                    .frame(maxWidth: .infinity).aspectRatio(1.5, contentMode: .fit)
                    .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
                    .accessibilityLabel(photo.label)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
