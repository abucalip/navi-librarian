import DiscairLibrarian
import SwiftUI

/// Session and band pictures from the artist's albums (docs/artwork.md, idea 8). The pictures are chosen by type and comment words only
/// (`ArtworkPicture.qualifiesForCollage`); nothing here reads taste or play data. With too few pictures the model is empty and the
/// page keeps its usual hero: no placeholder, no empty frame.
@MainActor @Observable
final class ArtistCollageModel {
    private(set) var entries: [CollageEntry] = []
    private var loadedFor: String?
    /// The fewest pictures that count; the Cupertino hero takes any (one is a slideshow of one).
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

/// Where the pictures of the banner's mosaic sit, as fractions of the banner. Few pictures fill part of it (the blurred cover
/// shows through the rest); five or more fill all of it, in tiles of different sizes. Pure, so a test can drive it.
enum CollageLayout {
    static let maxSlots = 5

    static func slots(count: Int) -> [CGRect] {
        func r(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat) -> CGRect { CGRect(x: x, y: y, width: w, height: h) }
        switch min(count, maxSlots) {
        case ...0: return []
        case 1: return [r(0.40, 0, 0.60, 1)]
        case 2: return [r(0.34, 0, 0.36, 1), r(0.70, 0, 0.30, 1)]
        case 3: return [r(0, 0, 0.42, 1), r(0.42, 0, 0.58, 0.58), r(0.42, 0.58, 0.58, 0.42)]
        case 4: return [r(0, 0, 0.34, 1), r(0.34, 0, 0.33, 0.6), r(0.34, 0.6, 0.33, 0.4), r(0.67, 0, 0.33, 1)]
        default: return [r(0, 0, 0.30, 1), r(0.30, 0, 0.28, 0.6), r(0.30, 0.6, 0.28, 0.4), r(0.58, 0, 0.42, 0.38), r(0.58, 0.38, 0.42, 0.62)]
        }
    }

    /// The picture to show next in a slot: the first one, from the one after `current`, that no slot is showing. Nil when every
    /// picture is already on show.
    static func next(after current: Int, shown: [Int], count: Int) -> Int? {
        guard count > 0 else { return nil }
        for step in 1...count {
            let candidate = (current + step) % count
            if !shown.contains(candidate) { return candidate }
        }
        return nil
    }
}

/// How one tile drifts: a slow zoom toward a corner, each tile its own corner, size and pace.
private struct TileMotion {
    let scale: CGFloat, anchor: UnitPoint, seconds: Double
    static let all: [TileMotion] = [
        .init(scale: 1.16, anchor: .topLeading, seconds: 14), .init(scale: 1.12, anchor: .bottomTrailing, seconds: 18),
        .init(scale: 1.20, anchor: .center, seconds: 16), .init(scale: 1.14, anchor: .topTrailing, seconds: 12),
        .init(scale: 1.18, anchor: .bottomLeading, seconds: 20),
    ]
}

private struct CollageTile: View {
    let entry: CollageEntry
    let motion: TileMotion
    let still: Bool
    @State private var moved = false

    var body: some View {
        AlbumPictureView(picture: entry.picture, size: .display, fill: true)
            .scaleEffect(moved && !still ? motion.scale : 1, anchor: motion.anchor)
            .animation(.linear(duration: motion.seconds), value: moved)
            .onAppear { moved = true }
    }
}

/// Cupertino: the banner's slideshow of the artist's own photos, several at once. Up to five tiles of different sizes each drift
/// their own way, and one tile at a time hands its place to a picture not on show, so they change at different moments.
/// Holds still under Reduce Motion and in the offscreen screenshot. The caller puts the blurred cover under it and the scrim over it.
struct CollageHeroBackdrop: View {
    let entries: [CollageEntry]
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    /// The picture each slot shows, as an index into `entries`.
    @State private var shown: [Int] = []
    private var still: Bool { reduceMotion || RenderMode.offscreenScreenshot }
    private let seam: CGFloat = 3

    var body: some View {
        GeometryReader { g in
            let slots = CollageLayout.slots(count: entries.count)
            ZStack(alignment: .topLeading) {
                ForEach(Array(slots.enumerated()), id: \.offset) { i, f in
                    ZStack {
                        if shown.indices.contains(i), entries.indices.contains(shown[i]) {
                            CollageTile(entry: entries[shown[i]], motion: TileMotion.all[i % TileMotion.all.count], still: still)
                                .id(entries[shown[i]].id)
                                .transition(.opacity)
                        }
                    }
                    .frame(width: max(f.width * g.size.width - seam, 0), height: max(f.height * g.size.height - seam, 0))
                    .clipped()
                    .offset(x: f.minX * g.size.width + seam / 2, y: f.minY * g.size.height + seam / 2)
                }
            }
        }
        .allowsHitTesting(false).accessibilityHidden(true)
        .task(id: entries.map(\.id)) {
            shown = Array(0..<min(entries.count, CollageLayout.maxSlots))
            guard !still, entries.count > shown.count else { return }
            var changed = Array(repeating: 0, count: shown.count)    // when each slot last changed, as a tick number
            var tick = 0
            while !Task.isCancelled {
                try? await Task.sleep(for: .milliseconds(Int.random(in: 1800...3200)))
                guard !Task.isCancelled else { return }
                tick += 1
                guard let slot = changed.indices.min(by: { changed[$0] < changed[$1] }),
                      let pick = CollageLayout.next(after: shown[slot], shown: shown, count: entries.count) else { continue }
                changed[slot] = tick
                withAnimation(.easeInOut(duration: 1.4)) { shown[slot] = pick }
            }
        }
    }
}
