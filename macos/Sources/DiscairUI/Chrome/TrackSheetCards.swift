import AppKit
import DiscairLibrarian
import SwiftUI

/// The Track images of the playing album (docs/artwork.md, idea 6): each a picture with its type and edition under it, drawn in the
/// queue while that album plays. The album's index is read here (the same lookup Now Playing uses, once per album). Nothing is drawn
/// when the album has no Track image, and a picture appears only once it has loaded. The caption is hidden from VoiceOver because the
/// picture carries the same label.
struct TrackSheetCards: View {
    let state: AppState
    @Environment(\.artwork) private var artwork
    @State private var albumArt: ArtworkIndex?
    @State private var images: [Int: NSImage] = [:]

    private var live: Bool { state.library.isLive || state.player.current != nil }

    var body: some View {
        let pictures = live ? (albumArt?.trackImages ?? []) : []
        VStack(alignment: .leading, spacing: 10) {
            ForEach(pictures) { picture in
                if let image = images[picture.imageID] {
                    VStack(alignment: .leading, spacing: 4) {
                        Image(nsImage: image)
                            .resizable()
                            .scaledToFit()
                            .frame(maxWidth: .infinity, maxHeight: 180)
                            .accessibilityLabel(picture.label)
                            .accessibilityAddTraits(.isImage)
                        Text(picture.label)
                            .font(.system(size: 11))
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                            .accessibilityHidden(true)
                    }
                }
            }
        }
        .task(id: "\(state.player.current?.artist ?? "")|\(state.player.current?.album ?? "")|\(artwork?.generation ?? 0)") {
            albumArt = nil
            guard live, let c = state.player.current, let artwork else { return }
            albumArt = await artwork.nowPlayingIndex(artist: c.artist, album: c.album)
        }
        .task(id: albumArt?.trackImages.map(\.imageID) ?? []) {
            images = [:]
            guard let store = artwork else { return }
            for picture in albumArt?.trackImages ?? [] {
                guard !Task.isCancelled else { return }
                if let image = await store.albumImage(picture, size: .display) { images[picture.imageID] = image }
            }
        }
    }
}
