import AppKit
import DiscairCore
import DiscairNavidrome
import Observation
import SwiftUI

/// Fetches and caches cover art through the active Navidrome profile. One request per cover and size; redirects are
/// refused like every other call. Covers are in memory only (the optional disk cache is a later slice).
@MainActor
@Observable
public final class ArtworkStore {
    private var builder: StreamURLBuilder?
    @ObservationIgnored private let cache = NSCache<NSString, NSImage>()
    @ObservationIgnored private var failed = Set<String>()
    @ObservationIgnored private let transport: any HTTPTransport

    public init(transport: any HTTPTransport = URLSessionTransport(keepCookies: false)) {
        self.transport = transport
        cache.countLimit = 400
    }

    public func configure(_ builder: StreamURLBuilder?) {
        self.builder = builder
        cache.removeAllObjects()
        failed.removeAll()
    }

    public func image(coverArt: String, px: Int) async -> NSImage? {
        let key = "\(coverArt)@\(px)"
        if let hit = cache.object(forKey: key as NSString) { return hit }
        guard !failed.contains(key), let builder, let url = try? builder.coverArtURL(coverArtID: coverArt, size: px) else { return nil }
        var request = URLRequest(url: url)
        request.setValue("image/*", forHTTPHeaderField: "Accept")
        guard let (data, http) = try? await transport.send(request), http.statusCode == 200, let image = NSImage(data: data) else {
            failed.insert(key); return nil
        }
        cache.setObject(image, forKey: key as NSString)
        return image
    }
}

private struct ArtworkKey: EnvironmentKey { static let defaultValue: ArtworkStore? = nil }
extension EnvironmentValues {
    var artwork: ArtworkStore? {
        get { self[ArtworkKey.self] }
        set { self[ArtworkKey.self] = newValue }
    }
}

/// The album's cover art, loaded on demand; nothing is drawn until it arrives (the caller shows its placeholder under it).
struct ArtworkImage: View {
    let album: AlbumItem
    var px = 300
    @Environment(\.artwork) private var store
    @State private var image: NSImage?

    var body: some View {
        Group {
            if let image { Image(nsImage: image).resizable().scaledToFill() }
        }
        .task(id: "\(album.coverArt ?? "")@\(px)") {
            image = nil
            guard let id = album.coverArt, let store else { return }
            image = await store.image(coverArt: id, px: px)
        }
    }
}
