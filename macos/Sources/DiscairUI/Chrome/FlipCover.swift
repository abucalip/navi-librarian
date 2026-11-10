import AppKit
import DiscairLibrarian
import SwiftUI

/// One image of an album from the Librarian, loaded at `size` through the artwork store. Draws nothing until it arrives (and
/// nothing at all when it never does): the caller's background shows, never a placeholder that claims there is an image.
struct AlbumPictureView: View {
    let picture: ArtworkPicture
    var size: ArtworkSize = .display
    @Environment(\.artwork) private var store
    @State private var image: NSImage?

    var body: some View {
        ZStack {
            if let image { Image(nsImage: image).resizable().scaledToFit() }
        }
        .task(id: "\(picture.imageID)|\(size.rawValue)|\(store?.generation ?? 0)") {
            guard let store else { return }
            image = await store.albumImage(picture, size: size)
        }
    }
}

/// The turning card: draws the face nearer the viewer for the angle, so the face changes at the edge-on moment of the flip.
/// An odd number of half turns would show a face mirrored, so it is turned back.
private struct FlipCard<Front: View, Back: View>: View, @preconcurrency Animatable {
    var angle: Double
    let faces: Int
    let front: Front
    let back: (Int) -> Back
    var animatableData: Double { get { angle } set { angle = newValue } }

    var body: some View {
        let half = Int((angle / 180).rounded())
        let face = coverFace(afterSteps: half, backs: faces - 1)
        let odd = ((half % 2) + 2) % 2 == 1
        Group {
            if face == 0 { front } else { back(face - 1) }
        }
        .rotation3DEffect(.degrees(odd ? 180 : 0), axis: (x: 0, y: 1, z: 0))
        .rotation3DEffect(.degrees(angle), axis: (x: 0, y: 1, z: 0), perspective: 0.45)
    }
}

/// The album cover as a card that a click turns over to its Back image, then Tray and Spine when the album has them
/// (docs/artwork.md, idea 1). The index is asked for once the album's release group is known; with no Back image, or while
/// the lookup is pending, empty or failed, this is just `front`: no gesture, no hint, nothing claimed about the album.
/// Reduced motion cross-fades the faces instead of turning the card.
struct FlipCover<Front: View>: View {
    let rgid: String?
    var cornerRadius: CGFloat = 0
    /// A theme dresses the back faces like its own cover (Zine's border and shadow); the default leaves them plain.
    var dressBack: (AnyView) -> AnyView = { $0 }
    /// Draws the album's Spine image as a thin strip on the cover's left edge, when it has one (Cupertino and Zine headers).
    var spineStrip = false
    let front: () -> Front

    @Environment(\.artwork) private var store
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var backs: [ArtworkPicture] = []
    @State private var spine: ArtworkPicture?
    @State private var steps = 0
    @State private var angle = 0.0

    var body: some View {
        Group {
            if backs.isEmpty {
                front()
            } else {
                card
            }
        }
        .overlay(alignment: .leading) {
            if spineStrip, let spine { SpineStrip(picture: spine).offset(x: -SpineStrip.width) }
        }
        .task(id: "\(rgid ?? "")|\(store?.generation ?? 0)") { await loadFaces() }
    }

    private var face: Int { coverFace(afterSteps: steps, backs: backs.count) }
    private var label: String { face == 0 ? "Front cover" : backs[face - 1].label }

    private var card: some View {
        Group {
            if reduceMotion {
                ZStack { faceView(face) }.id(face).transition(.opacity)
            } else {
                FlipCard(angle: angle, faces: backs.count + 1, front: front(), back: { faceView($0 + 1) })
            }
        }
        .contentShape(Rectangle())
        .onTapGesture { flip() }
        .help("Click to flip the cover")
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(label)
        .accessibilityHint("Flips the cover")
        .accessibilityAddTraits(.isButton)
        .accessibilityAction { flip() }
    }

    @ViewBuilder private func faceView(_ i: Int) -> some View {
        if i == 0 { front() } else {
            dressBack(AnyView(
                AlbumPictureView(picture: backs[i - 1])
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color.black.opacity(0.08))
                    .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
            ))
        }
    }

    private func flip() {
        if reduceMotion {
            withAnimation(.easeInOut(duration: 0.3)) { steps += 1 }
        } else {
            steps += 1
            withAnimation(.easeInOut(duration: 0.45)) { angle = Double(steps) * 180 }
        }
    }

    private func loadFaces() async {
        steps = 0; angle = 0; backs = []; spine = nil
        guard let rgid, !rgid.isEmpty, let store else { return }
        guard case .ready(let index) = await store.artworkIndex(rgid: rgid, release: nil), !Task.isCancelled else { return }
        let faces = index.coverBackFaces
        backs = faces
        spine = index.slotImage("Spine")
        // Warm the display size so the first flip shows the image, not an empty card.
        for picture in faces { _ = await store.albumImage(picture, size: .display) }
    }
}

/// The Spine image as a thin strip standing against the cover's edge. A spine scan is usually wider than tall, so it is turned
/// to read up the strip. Decorative to VoiceOver apart from its label; the flip cover carries the real controls.
struct SpineStrip: View {
    static let width: CGFloat = 12
    let picture: ArtworkPicture
    @Environment(\.artwork) private var store
    @State private var image: NSImage?

    var body: some View {
        GeometryReader { g in
            ZStack {
                if let image {
                    let wide = image.size.width > image.size.height
                    Image(nsImage: image).resizable().scaledToFill()
                        .frame(width: wide ? g.size.height : Self.width, height: wide ? Self.width : g.size.height)
                        .rotationEffect(.degrees(wide ? -90 : 0))
                        .frame(width: Self.width, height: g.size.height)
                        .clipped()
                }
            }
        }
        .frame(width: Self.width)
        .accessibilityLabel(picture.label)
        .task(id: "\(picture.imageID)|\(store?.generation ?? 0)") {
            guard let store else { return }
            image = await store.albumImage(picture, size: .display)
        }
    }
}
