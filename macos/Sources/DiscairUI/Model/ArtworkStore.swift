import AppKit
import DiscairAudio
import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import Observation
import SwiftUI

/// Fetches and caches cover art through the active Navidrome profile. One request per cover and size; redirects are
/// refused like every other call. Covers are kept in memory; with the optional media cache on they are also kept on disk,
/// so they still show offline.
@MainActor
@Observable
public final class ArtworkStore {
    private var builder: StreamURLBuilder?
    @ObservationIgnored private let cache = NSCache<NSString, NSImage>()
    @ObservationIgnored private var failed = Set<String>()
    @ObservationIgnored private let transport: any HTTPTransport

    @ObservationIgnored private let media: MediaCache?

    public init(transport: any HTTPTransport = URLSessionTransport(keepCookies: false), media: MediaCache? = nil) {
        self.transport = transport
        self.media = media
        cache.countLimit = 400
    }

    /// The Librarian finds covers for albums the library does not hold (recommendations, New, missing albums).
    @ObservationIgnored private var librarian: LibrarianClient?
    public func configure(librarian: LibrarianClient?) {
        self.librarian = librarian
        for k in failed where k.hasPrefix("lookup|") { failed.remove(k) }
    }

    /// The cover of an album that is not in the library, looked up by artist and title.
    public func image(artist: String, album: String, px: Int) async -> NSImage? {
        let key = "lookup|\(artist.lowercased())|\(album.lowercased())"
        if let hit = cache.object(forKey: key as NSString) { return hit }
        let diskKey = "cover|\(key)"
        if let data = media?.data(for: diskKey, ext: "img"), let image = NSImage(data: data) {
            cache.setObject(image, forKey: key as NSString); return image
        }
        guard !failed.contains(key), let librarian else { return nil }
        guard let url = try? await librarian.artworkURL(artist: artist, album: album) else { failed.insert(key); return nil }
        var request = URLRequest(url: url)
        request.setValue("image/*", forHTTPHeaderField: "Accept")
        guard let (data, http) = try? await transport.send(request), http.statusCode == 200, let image = NSImage(data: data) else {
            failed.insert(key); return nil
        }
        cache.setObject(image, forKey: key as NSString)
        media?.store(data: data, key: diskKey, ext: "img")
        return image
    }

    public func configure(_ builder: StreamURLBuilder?) {
        self.builder = builder
        cache.removeAllObjects()
        failed.removeAll()
    }

    public func image(coverArt: String, px: Int) async -> NSImage? {
        let key = "\(coverArt)@\(px)"
        if let hit = cache.object(forKey: key as NSString) { return hit }
        let diskKey = "cover|\(key)"
        if let data = media?.data(for: diskKey, ext: "img"), let image = NSImage(data: data) {
            cache.setObject(image, forKey: key as NSString); return image
        }
        guard !failed.contains(key), let builder, let url = try? builder.coverArtURL(coverArtID: coverArt, size: px) else { return nil }
        var request = URLRequest(url: url)
        request.setValue("image/*", forHTTPHeaderField: "Accept")
        guard let (data, http) = try? await transport.send(request), http.statusCode == 200, let image = NSImage(data: data) else {
            failed.insert(key); return nil
        }
        cache.setObject(image, forKey: key as NSString)
        media?.store(data: data, key: diskKey, ext: "img")
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
        // A real (clear) view carries the task: a bare `Group` that is empty until the image arrives never starts it when
        // the view stands alone, which left the blurred backdrops without their artwork.
        Color.clear
            .overlay { if let image { Image(nsImage: image).resizable().scaledToFill() } }
            .clipped()
            .task(id: "\(album.coverArt ?? "")@\(px)|\(album.owned ? "" : album.artist + "|" + album.title)") {
            image = nil
            guard let store else { return }
            if let id = album.coverArt { image = await store.image(coverArt: id, px: px) }
            else if !album.owned, album.id >= 0 { image = await store.image(artist: album.artist, album: album.title, px: px) }
        }
    }
}
