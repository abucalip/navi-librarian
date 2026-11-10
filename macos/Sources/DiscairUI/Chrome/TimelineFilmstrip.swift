import DiscairLibrarian
import SwiftUI

/// A Timeline entry's filmstrip (docs/artwork.md, idea 11): the album's pictures in one row of thumbnails, opened by the
/// "Pictures" button on the selected card. The index is read only once it is open. Nothing is drawn while loading, when the album
/// has fewer than two pictures, or when the lookup fails; the animation is a plain appearance under Reduce Motion.
struct TimelineFilmstrip: View {
    let rgid: String
    let title: String
    @Environment(\.artwork) private var store
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var open = false
    @State private var pictures: [ArtworkPicture] = []
    @State private var checked = false

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Button(open ? "Hide pictures" : "Pictures") { withAnimation(reduceMotion ? nil : .easeOut(duration: 0.2)) { open.toggle() } }
                .buttonStyle(.plain).font(.system(size: 12, weight: .medium)).underline()
                .accessibilityValue(open ? "Expanded" : "Collapsed")
                .accessibilityHint("Shows the pictures of \(title) as a strip")
            if open, checked, pictures.isEmpty { Text("No pictures for this album.").font(.system(size: 11)).opacity(0.6) }
            if open, !pictures.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(pictures) { picture in
                            AlbumPictureView(picture: picture, size: .thumb)
                                .frame(width: 84, height: 84)
                                .background(Color.black.opacity(0.06))
                                .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
                                .accessibilityLabel(picture.label)
                        }
                    }
                }
                .frame(height: 84)
                .accessibilityElement(children: .contain)
                .accessibilityLabel("Pictures of \(title)")
            }
        }
        .task(id: open ? rgid : nil) {
            guard open, let store else { return }
            guard case .ready(let index) = await store.artworkIndex(rgid: rgid, release: nil), !Task.isCancelled else { checked = true; return }
            pictures = index.filmstrip; checked = true
        }
    }
}

/// An Atlas disc node (docs/artwork.md, idea 11): the album's Medium image cut to a small record, shown next to an album in the
/// place inspector. It never turns. Draws nothing when the album has no Medium image or the lookup fails.
struct AlbumDisc: View {
    let rgid: String
    let diameter: CGFloat
    @Environment(\.artwork) private var store
    @State private var picture: ArtworkPicture?

    var body: some View {
        ZStack { if let picture { DiscView(picture: picture, diameter: diameter, spinning: false) } }
            .frame(width: picture == nil ? 0 : diameter, height: picture == nil ? 0 : diameter)
            .task(id: rgid) {
                guard let store else { return }
                guard case .ready(let index) = await store.artworkIndex(rgid: rgid, release: nil), !Task.isCancelled else { return }
                picture = index.discImage(disc: nil)
            }
    }
}
