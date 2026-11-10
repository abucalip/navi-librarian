import DiscairLibrarian
import SwiftUI

/// Discover's covers peek (docs/artwork.md, idea 9): up to three covers of an album, the Back, the first booklet page and the
/// Medium. It opens while its row is hovered and stays open after a "Covers" click, which is the keyboard and VoiceOver route.
/// The index is read only once it is open, so the lists stay quick. Nothing is drawn while loading, when the album has none of
/// these pictures, or when the lookup fails; no album without a release group shows the control at all.
struct DiscoverPeek: View {
    let album: AlbumItem
    /// True while the pointer is over the row (the row sets this from the list model).
    let hovered: Bool
    @Environment(\.artwork) private var store
    @State private var pinned = false
    @State private var pictures: [ArtworkPicture] = []

    private var rgid: String? { album.releaseGroupMBID }
    private var showing: Bool { pinned || hovered }

    var body: some View {
        if rgid != nil {
            VStack(alignment: .leading, spacing: 6) {
                Button(pinned ? "Hide covers" : "Covers") { pinned.toggle() }
                    .buttonStyle(.plain)
                    .font(.system(size: 12, weight: .medium))
                    .accessibilityValue(pinned ? "Expanded" : "Collapsed")
                    .accessibilityHint("Shows up to three covers of \(album.title)")
                if showing, !pictures.isEmpty {
                    HStack(spacing: 6) {
                        ForEach(pictures) { picture in
                            AlbumPictureView(picture: picture, size: .thumb)
                                .frame(width: 56, height: 56)
                                .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
                                .accessibilityLabel(picture.label)
                        }
                    }
                    .accessibilityElement(children: .contain)
                }
            }
            .task(id: showing ? rgid : nil) {
                guard showing, let rgid, let store else { return }
                guard case .ready(let index) = await store.artworkIndex(rgid: rgid, release: nil), !Task.isCancelled else {
                    pictures = []; return
                }
                pictures = index.discoverPeek
            }
        }
    }
}
