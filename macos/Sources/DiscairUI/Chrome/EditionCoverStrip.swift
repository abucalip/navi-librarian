import DiscairLibrarian
import SwiftUI

/// The covers of the release group a Downloads row is fetching (docs/artwork.md, idea 13): up to three Front images, each labelled
/// with its edition. Read-only; it does not change the download. The server does not record which pressing was matched, so the
/// caption says these are the album's editions. Nothing is drawn while loading, when the group has no Front image or when the
/// lookup fails.
struct EditionCoverStrip: View {
    let rgid: String
    @Environment(\.artwork) private var store
    @State private var pictures: [ArtworkPicture] = []

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            if !pictures.isEmpty {
                HStack(spacing: 6) {
                    ForEach(pictures) { picture in
                        AlbumPictureView(picture: picture, size: .thumb)
                            .frame(width: 44, height: 44)
                            .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
                            .accessibilityLabel(picture.label)
                    }
                }
                Text("Editions of this album. The pressing fetched is not recorded.")
                    .font(.system(size: 11)).foregroundStyle(.secondary)
            }
        }
        .accessibilityElement(children: .contain)
        .task(id: rgid) {
            guard let store else { return }
            guard case .ready(let index) = await store.artworkIndex(rgid: rgid, release: nil), !Task.isCancelled else {
                pictures = []; return
            }
            pictures = index.editionCovers
        }
    }
}
