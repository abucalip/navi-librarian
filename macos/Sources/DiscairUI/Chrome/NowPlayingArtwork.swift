import AppKit
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
    @State private var base = 0.0
    @State private var since: Double?

    private var running: Bool { spinning && !reduceMotion }
    private static func now() -> Double { Date.timeIntervalSinceReferenceDate }

    var body: some View {
        SwiftUI.TimelineView(.animation(minimumInterval: 1.0 / 30, paused: !running)) { context in
            disc.rotationEffect(.degrees(discAngle(base: base, since: since, now: context.date.timeIntervalSinceReferenceDate, rpm: rpm)))
        }
        .frame(width: diameter, height: diameter)
        .opacity(image == nil ? 0 : 1)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Disc: \(picture.label)")
        .accessibilityAddTraits(.isImage)
        .onChange(of: running, initial: true) { _, on in
            let t = Self.now()
            if on { since = t } else { base = discAngle(base: base, since: since, now: t, rpm: rpm); since = nil }
        }
        .task(id: "\(picture.imageID)|\(store?.generation ?? 0)") {
            guard let store else { return }
            image = await store.albumImage(picture, size: .display)
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
struct SlideshowBackdrop: View {
    let slides: [ArtworkPicture]
    let playing: Bool
    @Environment(\.artwork) private var store
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var images: [Int: NSImage] = [:]
    @State private var lowPower = ProcessInfo.processInfo.isLowPowerModeEnabled
    @State private var base = 0.0
    @State private var since: Double?

    private var running: Bool { playing && !reduceMotion && !lowPower && !RenderMode.offscreenScreenshot }

    private func elapsed(at date: Date) -> Double { base + (since.map { max(0, date.timeIntervalSinceReferenceDate - $0) } ?? 0) }

    var body: some View {
        GeometryReader { g in
            SwiftUI.TimelineView(.animation(minimumInterval: 1.0 / 20, paused: !running)) { context in
                if let f = slideshowFrame(elapsed: elapsed(at: context.date), count: slides.count) {
                    ZStack {
                        layer(f.index, progress: f.progress, size: g.size)
                        if f.mix > 0 { layer(f.next, progress: 0, size: g.size).opacity(f.mix) }
                    }
                    .blur(radius: RenderMode.offscreenScreenshot ? 0 : 36)
                    .saturation(1.2)
                    .clipped()
                }
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
        .onChange(of: running, initial: true) { _, on in
            let t = Date.timeIntervalSinceReferenceDate
            if on { since = t } else { if let s = since { base += max(0, t - s) }; since = nil }
        }
        .onReceive(NotificationCenter.default.publisher(for: .NSProcessInfoPowerStateDidChange)) { _ in
            lowPower = ProcessInfo.processInfo.isLowPowerModeEnabled
        }
        .task(id: "\(slides.map(\.imageID))|\(store?.generation ?? 0)") {
            images = [:]; base = 0
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
