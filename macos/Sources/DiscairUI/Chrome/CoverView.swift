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
