import SwiftUI

/// Placeholder artwork: a hue-derived gradient, same idea as the mockup's generated covers.
public struct CoverView: View {
    let album: AlbumItem
    public init(album: AlbumItem) { self.album = album }

    public var body: some View {
        let h = album.hue / 360
        LinearGradient(
            colors: [Color(hue: h, saturation: 0.55, brightness: 0.85), Color(hue: (h + 0.08).truncatingRemainder(dividingBy: 1), saturation: 0.7, brightness: 0.45)],
            startPoint: .topLeading, endPoint: .bottomTrailing
        )
        .aspectRatio(1, contentMode: .fit)
        .accessibilityLabel("\(album.title) cover")
    }
}
