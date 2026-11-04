import SwiftUI

/// Placeholder artwork: a hue-derived gradient, same idea as the mockup's generated covers.
public struct CoverView: View {
    let album: AlbumItem
    var px = 300
    public init(album: AlbumItem) { self.album = album }
    init(album: AlbumItem, px: Int) { self.album = album; self.px = px }

    public var body: some View {
        let h = album.hue / 360
        LinearGradient(
            colors: [Color(hue: h, saturation: 0.55, brightness: 0.85), Color(hue: (h + 0.08).truncatingRemainder(dividingBy: 1), saturation: 0.7, brightness: 0.45)],
            startPoint: .topLeading, endPoint: .bottomTrailing
        )
        .overlay { ArtworkImage(album: album, px: px) }
        .aspectRatio(1, contentMode: .fit)
        .clipped()
        .accessibilityLabel("\(album.title) cover")
    }
}

/// The cover, enlarged and heavily blurred, as a backdrop. Sits over a colour fallback, so while the image loads (or when
/// there is none) the screen still has its gradient. Decorative: hidden from VoiceOver. Blur is skipped under
/// `RenderMode.offscreenScreenshot`, where it does not render.
struct BlurredArtwork: View {
    let album: AlbumItem
    var radius: CGFloat = 80
    var body: some View {
        GeometryReader { g in
            ArtworkImage(album: album, px: 300)
                .frame(width: g.size.width, height: g.size.height)
                .scaleEffect(1.4)                                   // pushes the blurred edges out of view
                .blur(radius: RenderMode.offscreenScreenshot ? 0 : radius)
                .saturation(1.3)
                .clipped()
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}
