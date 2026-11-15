import AppKit
import CoreImage
import DiscairLibrarian
import SwiftUI

/// The record that turns on Now Playing (docs/artwork.md, idea 3): the album's Medium image (vinyl label, CD face) cut to a disc with
/// a spindle hole. It turns only while `spinning`, and never under Reduce Motion. Draws nothing until the image arrives.
struct DiscView: View {
    let picture: ArtworkPicture
    let diameter: CGFloat
    let spinning: Bool
    /// Revolutions per minute: a slow turn, a label to look at rather than a toy.
    var rpm: Double = 10
    @Environment(\.artwork) private var store
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var image: NSImage?
    @State private var rendered: CGImage?

    private var running: Bool { spinning && !reduceMotion }

    /// The disc is drawn once into a bitmap and turned by a Core Animation layer, so the render server does the turning and the
    /// main thread does no work per frame (a 30 Hz `TimelineView` here starved the playback clock's tick).
    var body: some View {
        SpinningBitmap(image: rendered, spinning: running, rpm: rpm)
            .frame(width: diameter, height: diameter)
            .opacity(rendered == nil ? 0 : 1)
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("Disc: \(picture.label)")
            .accessibilityAddTraits(.isImage)
            .task(id: "\(picture.imageID)|\(store?.generation ?? 0)") {
                guard let store else { return }
                image = await store.albumImage(picture, size: .display)
                guard image != nil else { rendered = nil; return }
                let renderer = ImageRenderer(content: disc)
                renderer.scale = 2
                rendered = renderer.cgImage
            }
    }

    private var disc: some View {
        ZStack {
            Circle().fill(Color.black)
            if let image { Image(nsImage: image).resizable().scaledToFill().frame(width: diameter, height: diameter).clipShape(Circle()) }
            Circle().strokeBorder(Color.black.opacity(0.35), lineWidth: 1.5)
            Circle().fill(Color.black.opacity(0.85)).frame(width: diameter * 0.07, height: diameter * 0.07)
                .overlay { Circle().strokeBorder(Color.white.opacity(0.7), lineWidth: 1) }
        }
        .frame(width: diameter, height: diameter)
    }
}

/// Cupertino: the disc sits behind the sleeve and slides out to its right once it has loaded (a plain appearance under Reduce Motion).
/// Added as a background so the sleeve's own layout and shadow are unchanged.
struct DiscSleeve: ViewModifier {
    let picture: ArtworkPicture?
    let spinning: Bool
    @State private var out = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func body(content: Content) -> some View {
        content.background(alignment: .center) {
            GeometryReader { g in
                if let picture {
                    DiscView(picture: picture, diameter: g.size.width * 0.9, spinning: spinning)
                        .frame(width: g.size.width, height: g.size.height)
                        .offset(x: out ? g.size.width * 0.36 : 0)
                        .task(id: picture.imageID) {
                            out = false
                            try? await Task.sleep(for: .milliseconds(400))
                            if reduceMotion { out = true } else { withAnimation(.spring(duration: 0.9, bounce: 0.15)) { out = true } }
                        }
                }
            }
        }
    }
}

extension View {
    func discSleeve(_ picture: ArtworkPicture?, spinning: Bool) -> some View { modifier(DiscSleeve(picture: picture, spinning: spinning)) }
}

/// The session and booklet photos drifting, blurred, behind the lyrics (idea 4). Draws over the blurred cover, which stays visible
/// until the first photo has loaded. Each photo is held and then cross-faded into the next with a slow zoom and pan. The drift holds
/// still under Reduce Motion, in Low Power Mode and while paused; it never runs in the screenshot capture.
///
/// The motion is one looping Core Animation timeline (`SlideshowLayers`), paused in place when the drift stops, and each photo is
/// blurred and saturated once at the backdrop's size. A 20 Hz `TimelineView` here re-rendered the window's display list on the
/// main thread every frame (docs/DEVELOPMENT_WORKFLOW.md, macOS client motion and CPU rules). The offscreen screenshot, which cannot
/// draw an AppKit view, gets the first frame in SwiftUI.
struct SlideshowBackdrop: View {
    let slides: [ArtworkPicture]
    let playing: Bool
    @Environment(\.artwork) private var store
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var images: [Int: NSImage] = [:]
    @State private var lowPower = ProcessInfo.processInfo.isLowPowerModeEnabled

    private var running: Bool { playing && !reduceMotion && !lowPower && !RenderMode.offscreenScreenshot }

    var body: some View {
        GeometryReader { g in
            if RenderMode.offscreenScreenshot {
                if let f = slideshowFrame(elapsed: 0, count: slides.count) {
                    layer(f.index, progress: f.progress, size: g.size).saturation(1.2).clipped()
                }
            } else {
                BlurredSlides(slides: slides, images: images, size: g.size, running: running)
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
        .onReceive(NotificationCenter.default.publisher(for: .NSProcessInfoPowerStateDidChange)) { _ in
            lowPower = ProcessInfo.processInfo.isLowPowerModeEnabled
        }
        .task(id: "\(slides.map(\.imageID))|\(store?.generation ?? 0)") {
            images = [:]
            guard let store else { return }
            for slide in slides {
                guard let image = await store.albumImage(slide, size: .display), !Task.isCancelled else { continue }
                images[slide.imageID] = image
            }
        }
    }

    @ViewBuilder private func layer(_ i: Int, progress: Double, size: CGSize) -> some View {
        if slides.indices.contains(i), let image = images[slides[i].imageID] {
            Image(nsImage: image).resizable().scaledToFill()
                .frame(width: size.width, height: size.height)
                .scaleEffect(1.18 + 0.1 * progress)
                .offset(x: (progress - 0.5) * 30)
                .clipped()
        }
    }
}

/// Blurs each loaded photo once, at the backdrop's size (rounded to 64 points, so a window resize redoes it only now and then), and
/// hands the results to the layer timeline.
private struct BlurredSlides: View {
    let slides: [ArtworkPicture]
    let images: [Int: NSImage]
    let size: CGSize
    let running: Bool
    @State private var blurred: [Int: CGImage] = [:]

    private var bucket: CGSize {
        CGSize(width: max(64, (size.width / 64).rounded() * 64), height: max(64, (size.height / 64).rounded() * 64))
    }

    var body: some View {
        SlideshowLayers(ids: slides.map(\.imageID), images: slides.map { blurred[$0.imageID] }, running: running)
            .task(id: "\(images.keys.sorted())|\(bucket.width)x\(bucket.height)") {
                let target = bucket
                var done = blurred.filter { images[$0.key] != nil && blurredSize[$0.key] == target }
                for (id, image) in images where done[id] == nil {
                    guard let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
                    let out = await Task.detached(priority: .utility) { blurredFill(cg, size: target) }.value
                    guard !Task.isCancelled else { return }
                    if let out { done[id] = out; blurredSize[id] = target; blurred = done }
                }
                blurred = done
            }
    }

    @State private var blurredSize: [Int: CGSize] = [:]
}

/// The photo drawn to fill `size` (points, one pixel each: the blur hides the resolution), then blurred and saturated by 1.2, as
/// the SwiftUI version drew it. That one blurred by 36 after the zoom (1.18 to 1.28); this blurs before it, so by 36 / 1.23 to
/// look the same on screen (checked side by side). Edges are clamped so the blur does not darken them.
private func blurredFill(_ image: CGImage, size: CGSize) -> CGImage? {
    let source = CIImage(cgImage: image)
    let scale = max(size.width / source.extent.width, size.height / source.extent.height)
    let scaled = source.transformed(by: CGAffineTransform(scaleX: scale, y: scale))
    let crop = CGRect(x: (scaled.extent.width - size.width) / 2, y: (scaled.extent.height - size.height) / 2,
                      width: size.width, height: size.height)
    let blurred = scaled.clampedToExtent()
        .applyingGaussianBlur(sigma: 36 / 1.23)
        .applyingFilter("CIColorControls", parameters: [kCIInputSaturationKey: 1.2])
        .cropped(to: crop)
    // In sRGB, not Core Image's default linear light: that spread bright colours wider and brighter than SwiftUI's blur did
    // (checked side by side).
    let context = CIContext(options: [.cacheIntermediates: false, .workingColorSpace: CGColorSpace(name: CGColorSpace.sRGB)!])
    return context.createCGImage(blurred, from: crop)
}

/// The slideshow as Core Animation: one layer per photo, in order (a later photo above an earlier one), each with looping
/// keyframes for opacity, zoom and pan over the whole cycle, so the render server plays it and the main thread does nothing per
/// frame. Paused in place (`speed` 0) when `running` is false, as the turning disc is. Timing follows `slideshowFrame`: each photo
/// holds `hold` seconds, zooming 1.18 to 1.28 and panning 30 points, while the next fades in over the last `fade` seconds.
private struct SlideshowLayers: NSViewRepresentable {
    let ids: [Int]
    let images: [CGImage?]
    let running: Bool
    var hold: Double = 14
    var fade: Double = 3

    final class Host: NSView {
        let stage = CALayer()
        var ids: [Int]?
        override init(frame: NSRect) {
            super.init(frame: frame)
            wantsLayer = true
            layer?.masksToBounds = true
            layer?.addSublayer(stage)
        }
        required init?(coder: NSCoder) { nil }
        override func layout() {
            super.layout()
            CATransaction.begin()
            CATransaction.setDisableActions(true)
            stage.frame = bounds
            for slide in stage.sublayers ?? [] {
                slide.bounds = CGRect(origin: .zero, size: bounds.size)
                slide.position = CGPoint(x: bounds.midX, y: bounds.midY)
            }
            CATransaction.commit()
        }
    }

    func makeNSView(context: Context) -> Host { Host() }

    func updateNSView(_ view: Host, context: Context) {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        if view.ids != ids { rebuild(view) }
        for (slide, image) in zip(view.stage.sublayers ?? [], images) where slide.contents as AnyObject? !== image as AnyObject? {
            slide.contents = image
        }
        let stage = view.stage
        if running, stage.speed == 0 {
            let held = stage.timeOffset
            stage.timeOffset = 0
            stage.beginTime = 0
            stage.beginTime = stage.convertTime(CACurrentMediaTime(), from: nil) - held
            stage.speed = 1
        } else if !running, stage.speed != 0 {
            let local = stage.convertTime(CACurrentMediaTime(), from: nil)
            stage.speed = 0
            stage.timeOffset = local
        }
        CATransaction.commit()
    }

    /// New photos: fresh layers and a timeline starting at its beginning, paused until `updateNSView` starts it.
    private func rebuild(_ view: Host) {
        view.ids = ids
        let stage = view.stage
        stage.sublayers?.forEach { $0.removeFromSuperlayer() }
        stage.removeAllAnimations()
        stage.speed = 0
        stage.timeOffset = 0
        stage.beginTime = 0
        let n = ids.count
        guard n > 0 else { return }
        let cycle = Double(n) * hold
        for i in 0..<n {
            let slide = CALayer()
            slide.contentsGravity = .resizeAspectFill
            slide.bounds = CGRect(origin: .zero, size: view.bounds.size)
            slide.position = CGPoint(x: view.bounds.midX, y: view.bounds.midY)
            let frames = SlideshowKeyframes(index: i, count: n, hold: hold, fade: fade)
            slide.opacity = Float(frames.opacity.first?.1 ?? 1)
            slide.transform = CATransform3DMakeScale(1.18, 1.18, 1)
            if n > 1 { slide.add(Self.keyframes("opacity", frames.opacity, cycle: cycle), forKey: "opacity") }
            slide.add(Self.keyframes("transform.scale", frames.progress.map { ($0.0, 1.18 + 0.1 * $0.1) }, cycle: cycle), forKey: "zoom")
            slide.add(Self.keyframes("transform.translation.x", frames.progress.map { ($0.0, ($0.1 - 0.5) * 30) }, cycle: cycle), forKey: "pan")
            stage.addSublayer(slide)
        }
    }

    private static func keyframes(_ path: String, _ points: [(Double, Double)], cycle: Double) -> CAKeyframeAnimation {
        let a = CAKeyframeAnimation(keyPath: path)
        a.values = points.map(\.1)
        a.keyTimes = points.map { NSNumber(value: $0.0 / cycle) }
        a.duration = cycle
        a.repeatCount = .infinity
        a.calculationMode = .linear
        a.isRemovedOnCompletion = false
        return a
    }
}

/// One photo's keyframes over a cycle of `count * hold` seconds, as (time, value) pairs: its opacity, and its zoom-and-pan progress
/// (0 to 1). A photo fades in over the one before it (it is above it), shows while it drifts, then is hidden under the next. The
/// last photo is above the first, so at the end of the cycle the last fades out over the first instead, which looks the same.
/// Pure, so a test can check it against `slideshowFrame`.
struct SlideshowKeyframes {
    let opacity: [(Double, Double)]
    let progress: [(Double, Double)]

    init(index i: Int, count n: Int, hold h: Double, fade f: Double) {
        let cycle = Double(n) * h, start = Double(i) * h, end = start + h, e = 0.001
        if n <= 1 {
            opacity = [(0, 1), (cycle, 1)]
            progress = [(0, 0), (cycle, 1)]
        } else if i == 0 {
            opacity = [(0, 1), (h, 1), (h + e, 0), (cycle - f, 0), (cycle - f + e, 1), (cycle, 1)]
            progress = [(0, 0), (h, 1), (h + e, 0), (cycle, 0)]
        } else if i == n - 1 {
            opacity = [(0, 0), (start - f, 0), (start, 1), (cycle - f, 1), (cycle, 0)]
            progress = [(0, 0), (start, 0), (end, 1)]
        } else {
            opacity = [(0, 0), (start - f, 0), (start, 1), (end, 1), (end + e, 0), (cycle, 0)]
            progress = [(0, 0), (start, 0), (end, 1), (cycle, 1)]
        }
    }

    /// What the cycle shows at `t` seconds: (opacity, progress) by straight-line interpolation, for tests.
    func value(at t: Double) -> (opacity: Double, progress: Double) {
        func at(_ points: [(Double, Double)]) -> Double {
            guard let first = points.first else { return 0 }
            if t <= first.0 { return first.1 }
            for (a, b) in zip(points, points.dropFirst()) where t <= b.0 {
                return b.0 > a.0 ? a.1 + (b.1 - a.1) * (t - a.0) / (b.0 - a.0) : b.1
            }
            return points.last!.1
        }
        return (at(opacity), at(progress))
    }
}


/// A small badge on the Now Playing cover that opens the album's booklet (docs/artwork.md, idea 2). Shown only when the playing
/// album has booklet pages; nothing otherwise. The cover's click still flips it (idea 1); this badge is a separate control.
struct NowPlayingBookletBadge: View {
    let index: ArtworkIndex?
    var dark = true

    var body: some View {
        BookletOpener(rgid: nil, index: index) { open in
            if let text = index?.bookletView?.badgeText {
                Button(action: open) {
                    Label(text, systemImage: "book.closed.fill").font(.system(size: 11, weight: .semibold))
                        .padding(.horizontal, 8).padding(.vertical, 4)
                        .background(dark ? Color.black.opacity(0.62) : Color.white, in: Capsule())
                        .foregroundStyle(dark ? Color.white : Color.black)
                        .overlay(Capsule().strokeBorder(dark ? Color.white.opacity(0.25) : Color.black, lineWidth: dark ? 0.5 : 2))
                }
                .buttonStyle(.plain).padding(8)
                .help("Open the album's booklet")
                .accessibilityLabel("Open booklet, \(text)")
            }
        }
    }
}

/// The small cover in the player bar (docs/artwork.md, ideas 1, 3 and 5 on the bar). Hovering turns it to the album's Back; a click opens
/// the album's booklet when it has one and otherwise does what the bar's cover did before (`fallback`, Now Playing); the disc slides
/// out from behind it and turns while playing. The playing album's index comes by artist and title (`nowPlayingIndex`), so with no
/// index, no Back, no booklet or no Medium image it is the plain cover. The theme passes its cover and its edge treatment.
struct PlayerBarCover<Cover: View>: View {
    let artist: String
    let album: String
    let disc: Int?
    let spinning: Bool
    let side: CGFloat
    var cornerRadius: CGFloat = 0
    var border: Color?
    /// Hover turns the cover to its Back and a click opens the booklet. Off: the cover only shows the disc and a click is `fallback`.
    var flipsAndOpensBooklet = true
    /// The disc sliding out from behind the cover.
    var showsDisc = true
    let fallback: () -> Void
    @ViewBuilder let cover: () -> Cover

    @Environment(\.artwork) private var store
    @State private var index: ArtworkIndex?
    @State private var showing = false

    private var booklet: BookletView? { flipsAndOpensBooklet ? index?.bookletView : nil }
    private var discPicture: ArtworkPicture? { showsDisc ? index?.discImage(disc: disc) : nil }

    var body: some View {
        Button {
            if booklet != nil { showing = true } else { fallback() }
        } label: {
            Group {
                if flipsAndOpensBooklet { FlipCover(rgid: nil, cornerRadius: cornerRadius, index: index, hover: true) { cover() } }
                else { cover() }
            }
                .frame(width: side, height: side)
                .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
                .overlay { if let border { RoundedRectangle(cornerRadius: cornerRadius, style: .continuous).strokeBorder(border, lineWidth: 2) } }
                .discSleeve(discPicture, spinning: spinning)
                .padding(.trailing, discPicture == nil ? 0 : side * 0.36)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .help(booklet == nil ? "Open Now Playing" : "Open the booklet")
        .accessibilityLabel(booklet == nil ? "Open Now Playing" : "Open booklet, \(booklet?.badgeText ?? "")")
        .sheet(isPresented: $showing) { if let all = index?.bookletViews, !all.isEmpty { BookletSheet(booklets: all) { showing = false } } }
        .task(id: "\(artist)|\(album)|\(store?.generation ?? 0)") {
            index = nil
            guard let store else { return }
            index = await store.nowPlayingIndex(artist: artist, album: album)
        }
    }
}


/// A bitmap turned in place by a repeating Core Animation rotation (clockwise, `rpm`), paused where it is when `spinning` is
/// false. The turning layer is a child kept centred in the view, so the view itself (which SwiftUI moves, e.g. the disc sliding
/// out of the sleeve) is never what rotates.
private struct SpinningBitmap: NSViewRepresentable {
    let image: CGImage?
    let spinning: Bool
    let rpm: Double

    final class Host: NSView {
        let disc = CALayer()
        override init(frame: NSRect) {
            super.init(frame: frame)
            wantsLayer = true
            layer?.masksToBounds = false
            disc.contentsGravity = .resizeAspect
            disc.anchorPoint = CGPoint(x: 0.5, y: 0.5)
            disc.speed = 0
            let spin = CABasicAnimation(keyPath: "transform.rotation.z")
            spin.fromValue = 0
            spin.toValue = -2 * Double.pi
            spin.duration = 60 / 10
            spin.repeatCount = .infinity
            spin.timingFunction = CAMediaTimingFunction(name: .linear)
            disc.add(spin, forKey: "spin")
            layer?.addSublayer(disc)
        }
        required init?(coder: NSCoder) { nil }
        override func layout() {
            super.layout()
            CATransaction.begin()
            CATransaction.setDisableActions(true)
            let side = min(bounds.width, bounds.height)
            disc.bounds = CGRect(x: 0, y: 0, width: side, height: side)
            disc.position = CGPoint(x: bounds.midX, y: bounds.midY)
            CATransaction.commit()
        }
    }

    func makeNSView(context: Context) -> Host { Host() }

    func updateNSView(_ view: Host, context: Context) {
        let layer = view.disc
        if layer.contents as AnyObject? !== image as AnyObject? { layer.contents = image }
        if let spin = layer.animation(forKey: "spin"), spin.duration != 60 / rpm {
            layer.removeAnimation(forKey: "spin")
            let new = CABasicAnimation(keyPath: "transform.rotation.z")
            new.fromValue = 0; new.toValue = -2 * Double.pi; new.duration = 60 / rpm
            new.repeatCount = .infinity; new.timingFunction = CAMediaTimingFunction(name: .linear)
            layer.add(new, forKey: "spin")
        }
        if spinning, layer.speed == 0 {
            let held = layer.timeOffset
            layer.timeOffset = 0
            layer.beginTime = 0
            layer.beginTime = layer.convertTime(CACurrentMediaTime(), from: nil) - held
            layer.speed = 1
        } else if !spinning, layer.speed != 0 {
            let local = layer.convertTime(CACurrentMediaTime(), from: nil)
            layer.speed = 0
            layer.timeOffset = local
        }
    }
}
