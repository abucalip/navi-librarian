import AppKit
import DiscairLibrarian
import SwiftUI

/// Session and band pictures from the artist's albums (docs/archive/completed/artwork.md, idea 8). The pictures are chosen by type and comment words only
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
    static let tileOverlap: CGFloat = 1

    /// Pixel-align a collage tile and extend each shared edge by half an overlap so neighbouring tiles cannot expose a seam.
    static func tileFrame(for slot: CGRect, in size: CGSize, scale: CGFloat, overlap: CGFloat = tileOverlap) -> CGRect {
        let pixels = max(scale, 1)
        let x = (slot.minX * size.width * pixels).rounded() / pixels
        let y = (slot.minY * size.height * pixels).rounded() / pixels
        let width = (slot.width * size.width * pixels).rounded() / pixels
        let height = (slot.height * size.height * pixels).rounded() / pixels
        return CGRect(x: x - overlap / 2, y: y - overlap / 2, width: width + overlap, height: height + overlap)
    }

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

/// The still SwiftUI tile, for the offscreen screenshot only (it cannot draw the AppKit layer of `CollageSlot`).
private struct CollageTile: View {
    let entry: CollageEntry

    var body: some View {
        AlbumPictureView(picture: entry.picture, size: .display, fill: true)
    }
}

/// One slot of the mosaic in the window: it loads its picture, then hands it to a Core Animation layer that zooms it slowly
/// toward its corner and cross-fades it over the picture before. A SwiftUI zoom and cross-fade here re-rendered the window's
/// display list on the main thread every frame while the banner moved (docs/DEVELOPMENT_WORKFLOW.md, macOS client motion and CPU
/// rules). The old picture stays until the new one has loaded.
private struct CollageSlot: View {
    let entry: CollageEntry
    let motion: TileMotion
    let still: Bool
    @Environment(\.artwork) private var store
    @State private var loaded: (id: Int, image: NSImage)?

    var body: some View {
        CollageSlotLayer(loaded: loaded, motion: motion, still: still)
            .task(id: "\(entry.picture.imageID)|\(store?.generation ?? 0)") {
                guard let store, let image = await store.albumImage(entry.picture, size: .display), !Task.isCancelled else { return }
                loaded = (entry.id, image)
            }
    }
}

private struct CollageSlotLayer: NSViewRepresentable {
    let loaded: (id: Int, image: NSImage)?
    let motion: TileMotion
    let still: Bool
    static let fade = 1.4

    final class Host: NSView {
        var shownID: Int?
        override init(frame: NSRect) {
            super.init(frame: frame)
            wantsLayer = true
            layer?.masksToBounds = true
        }
        required init?(coder: NSCoder) { nil }
        override func layout() {
            super.layout()
            CATransaction.begin()
            CATransaction.setDisableActions(true)
            for tile in layer?.sublayers ?? [] { place(tile) }
            CATransaction.commit()
        }
        /// Bounds and position, not frame: the tile carries a zoom transform, and its anchor is the corner it zooms toward.
        func place(_ tile: CALayer) {
            tile.bounds = CGRect(origin: .zero, size: bounds.size)
            tile.position = CGPoint(x: tile.anchorPoint.x * bounds.width, y: tile.anchorPoint.y * bounds.height)
        }
    }

    func makeNSView(context: Context) -> Host { Host() }

    func updateNSView(_ view: Host, context: Context) {
        guard let loaded, loaded.id != view.shownID, let root = view.layer else { return }
        let first = view.shownID == nil
        view.shownID = loaded.id
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        let tile = CALayer()
        tile.contents = loaded.image
        tile.contentsGravity = .resizeAspectFill
        // SwiftUI's unit point counts y from the top; this layer's y runs from the bottom.
        tile.anchorPoint = CGPoint(x: motion.anchor.x, y: 1 - motion.anchor.y)
        view.place(tile)
        root.addSublayer(tile)
        if !still {
            tile.transform = CATransform3DMakeScale(motion.scale, motion.scale, 1)
            let zoom = CABasicAnimation(keyPath: "transform.scale")
            zoom.fromValue = 1
            zoom.toValue = motion.scale
            zoom.duration = motion.seconds
            zoom.timingFunction = CAMediaTimingFunction(name: .linear)
            tile.add(zoom, forKey: "zoom")
        }
        let older = (root.sublayers ?? []).filter { $0 !== tile }
        if first || still {
            older.forEach { $0.removeFromSuperlayer() }
        } else {
            let fadeIn = CABasicAnimation(keyPath: "opacity")
            fadeIn.fromValue = 0
            fadeIn.toValue = 1
            fadeIn.duration = Self.fade
            fadeIn.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
            tile.add(fadeIn, forKey: "fade")
            DispatchQueue.main.asyncAfter(deadline: .now() + Self.fade + 0.1) { older.forEach { $0.removeFromSuperlayer() } }
        }
        CATransaction.commit()
    }
}

/// Cupertino: the banner's slideshow of the artist's own photos, several at once. Up to five tiles of different sizes each drift
/// their own way, and one tile at a time hands its place to a picture not on show, so they change at different moments.
/// Holds still under Reduce Motion and in the offscreen screenshot. The caller puts the blurred cover under it and the scrim over it.
struct CollageHeroBackdrop: View {
    let entries: [CollageEntry]
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.displayScale) private var displayScale
    /// The picture each slot shows, as an index into `entries`.
    @State private var shown: [Int] = []
    private var still: Bool { reduceMotion || RenderMode.offscreenScreenshot }

    var body: some View {
        GeometryReader { g in
            let slots = CollageLayout.slots(count: entries.count)
            ZStack(alignment: .topLeading) {
                ForEach(Array(slots.enumerated()), id: \.offset) { i, f in
                    let frame = CollageLayout.tileFrame(for: f, in: g.size, scale: displayScale)
                    ZStack {
                        if shown.indices.contains(i), entries.indices.contains(shown[i]) {
                            if RenderMode.offscreenScreenshot {
                                CollageTile(entry: entries[shown[i]])
                            } else {
                                CollageSlot(entry: entries[shown[i]], motion: TileMotion.all[i % TileMotion.all.count], still: still)
                            }
                        }
                    }
                    .frame(width: frame.width, height: frame.height)
                    .clipped()
                    .offset(x: frame.minX, y: frame.minY)
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
                shown[slot] = pick    // the slot's layer cross-fades it (Core Animation, not a SwiftUI animation)
            }
        }
    }
}
