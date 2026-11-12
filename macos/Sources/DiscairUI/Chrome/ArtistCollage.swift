import DiscairLibrarian
import SwiftUI

/// Session and band pictures from the artist's albums (docs/artwork.md, idea 8). The pictures are chosen by type and comment words only
/// (`ArtworkPicture.qualifiesForCollage`); nothing here reads taste or play data. With too few pictures the model is empty and the
/// page keeps its usual hero: no placeholder, no empty frame.
@MainActor @Observable
final class ArtistCollageModel {
    private(set) var entries: [CollageEntry] = []
    private var loadedFor: String?
    /// The fewest pictures that count; the Cupertino hero takes any (one is a slideshow of one), the Zine sheet keeps the default.
    var minimum = collageMinimum

    func load(sources: [CollageSource], store: ArtworkStore?) async {
        let key = sources.map(\.rgid).joined(separator: ",")
        guard !sources.isEmpty, let store else { entries = []; loadedFor = nil; return }
        if loadedFor == key { return }
        let found = await store.artistCollage(sources, minimum: minimum)
        guard !Task.isCancelled else { return }
        entries = found; loadedFor = key
    }
}

/// Zine: a contact sheet, one framed frame per picture with the album under it in mono type.
struct ZineContactSheet: View {
    let entries: [CollageEntry]

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Mono("Contact sheet")
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 120, maximum: 150), spacing: 10, alignment: .top)], alignment: .leading, spacing: 10) {
                ForEach(entries) { e in
                    VStack(alignment: .leading, spacing: 3) {
                        AlbumPictureView(picture: e.picture, size: .thumb)
                            .frame(maxWidth: .infinity).frame(height: 96)
                            .background(Z.white).clipped().zBorder(3)
                        Mono(e.albumTitle).lineLimit(1)
                    }
                    .accessibilityElement(children: .ignore).accessibilityLabel(e.label)
                }
            }
        }
        .padding(.vertical, 8)
    }
}

/// Cupertino: the banner's moving slideshow of the artist's own photos, sharp, each drifting slowly and cross-fading into the next.
/// Holds on the first picture under Reduce Motion and in the offscreen screenshot. The caller adds the scrim for the text.
struct CollageHeroBackdrop: View {
    let entries: [CollageEntry]
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var index = 0
    @State private var drift = false
    private let hold: Duration = .seconds(8)
    private var still: Bool { reduceMotion || RenderMode.offscreenScreenshot }

    var body: some View {
        ZStack {
            if entries.indices.contains(index) {
                AlbumPictureView(picture: entries[index].picture, size: .display)
                    .id(entries[index].id)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .scaleEffect(drift && !still ? 1.12 : 1.0)
                    .offset(x: drift && !still ? -14 : 0)
                    .animation(.linear(duration: 9), value: drift)
                    .clipped()
                    .transition(.opacity)
            }
        }
        .allowsHitTesting(false).accessibilityHidden(true)
        .task(id: entries.map(\.id)) {
            index = 0; drift = false
            guard !entries.isEmpty, !still else { return }
            drift = true
            guard entries.count > 1 else { return }
            while !Task.isCancelled {
                try? await Task.sleep(for: hold)
                guard !Task.isCancelled else { return }
                drift = false
                withAnimation(.easeInOut(duration: 1.4)) { index = (index + 1) % entries.count }
                try? await Task.sleep(for: .milliseconds(50))
                drift = true
            }
        }
    }
}
