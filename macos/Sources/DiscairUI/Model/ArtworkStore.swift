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
    /// Counts connections made. A cover asked for before the connection existed (a restored queue at launch) got nothing and is
    /// never asked again by itself, so views include this in their task id and ask again once it changes.
    public private(set) var generation = 0
    @ObservationIgnored private let transport: any HTTPTransport

    @ObservationIgnored private let media: MediaCache?

    /// Album images from the Librarian's artwork routes (docs/artwork.md, slice 2). Own memory cache, so a long booklet
    /// never pushes the covers out; a request for the same image already under way is joined, not repeated.
    @ObservationIgnored private let albumCache: NSCache<NSString, NSImage> = {
        let c = NSCache<NSString, NSImage>(); c.countLimit = 120; c.totalCostLimit = 96 * 1024 * 1024; return c
    }()
    @ObservationIgnored private var albumLoads: [String: AlbumLoad] = [:]
    @ObservationIgnored private var indexes: [String: ArtworkIndex] = [:]
    /// The owner's cover picks (docs/artwork.md, idea 7), library album id to artwork image id. Views read it, so a new pick redraws.
    public private(set) var choices: [String: Int] = [:]
    /// Release group of an album by artist and title, found once per album (Now Playing has no album page to read it from).
    @ObservationIgnored private var releaseGroups: [String: String] = [:]

    private final class AlbumLoad: @unchecked Sendable {
        let task: Task<NSImage?, Never>
        var waiters = 0
        init(task: Task<NSImage?, Never>) { self.task = task }
    }

    public init(transport: any HTTPTransport = URLSessionTransport(keepCookies: false), media: MediaCache? = nil) {
        self.transport = transport
        self.media = media
        cache.countLimit = 400
    }

    /// The Librarian finds covers for albums the library does not hold (recommendations, New, missing albums).
    @ObservationIgnored private var librarian: LibrarianClient?
    public func configure(librarian: LibrarianClient?) {
        self.librarian = librarian
        albumCache.removeAllObjects()
        indexes.removeAll()
        releaseGroups.removeAll()
        for k in failed where k.hasPrefix("lookup|") || k.hasPrefix("owned|") { failed.remove(k) }
        choices = [:]
        generation += 1
        if let librarian { let connection = generation; Task { [weak self] in await self?.loadChoices(librarian, connection: connection) } }
    }

    /// `connection` is the generation this was asked for; an answer that arrives after a newer connection is dropped.
    private func loadChoices(_ client: LibrarianClient, connection: Int) async {
        guard let found = try? await client.artworkChoices(), connection == generation else { return }
        choices = found
    }

    /// Stores the owner's pick for an owned album; the server then serves it on every screen. False when the server refused or
    /// could not be reached: nothing changes then.
    public func setChoice(albumID: String, rgid: String, imageID: Int) async -> Bool {
        guard let librarian else { return false }
        do { try await librarian.setArtworkChoice(albumID: albumID, rgid: rgid, imageID: imageID) } catch { return false }
        choices[albumID] = imageID
        return true
    }

    /// Removes the pick: the automatic cover is used again.
    public func clearChoice(albumID: String) async -> Bool {
        guard let librarian else { return false }
        do { try await librarian.clearArtworkChoice(albumID: albumID) } catch { return false }
        choices.removeValue(forKey: albumID)
        return true
    }

    /// An owned album's cover as the Librarian resolves it: the owner's pick, or the best front when the library has no cover or a
    /// small one. nil when the server has nothing better (404) or cannot be reached.
    public func ownedCover(albumID: String, px: Int) async -> NSImage? {
        let key = "owned|\(albumID)|\(choices[albumID] ?? 0)|\(px)"
        if let hit = cache.object(forKey: key as NSString) { return hit }
        guard !failed.contains(key), let librarian else { return nil }
        do {
            let got = try await librarian.ownedCover(albumID: albumID, px: px)
            guard !got.isPDF, let image = NSImage(data: got.data) else { failed.insert(key); return nil }
            cache.setObject(image, forKey: key as NSString)
            return image
        } catch DiscairError.server(let status, _) where status == 404 {
            failed.insert(key); return nil
        } catch { return nil }
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

    /// An artist photo, from the address the server gave or else looked up by name.
    public func image(artistName: String, url: URL?) async -> NSImage? {
        let key = "artist|\(artistName.lowercased())"
        if let hit = cache.object(forKey: key as NSString) { return hit }
        let diskKey = "cover|\(key)"
        if let data = media?.data(for: diskKey, ext: "img"), let image = NSImage(data: data) {
            cache.setObject(image, forKey: key as NSString); return image
        }
        guard !failed.contains(key) else { return nil }
        var source = url
        if source == nil, let librarian { source = try? await librarian.artistImageURL(name: artistName) }
        guard let source else { failed.insert(key); return nil }
        var request = URLRequest(url: source)
        request.setValue("image/*", forHTTPHeaderField: "Accept")
        guard let (data, http) = try? await transport.send(request), http.statusCode == 200, let image = NSImage(data: data) else {
            failed.insert(key); return nil
        }
        cache.setObject(image, forKey: key as NSString)
        media?.store(data: data, key: diskKey, ext: "img")
        return image
    }

    // MARK: Album images (artwork index)

    /// An album's images by MusicBrainz release group. Asks again while the server builds the index (`not_loaded`); a failure or
    /// a build that does not finish is `unavailable`, never `empty`. A built index is kept for the session. Nothing is shown
    /// for `empty` or `unavailable`: the caller draws nothing extra.
    public func artworkIndex(rgid: String, release: String?) async -> ArtworkIndexResult {
        if let hit = indexes[rgid] { return .ready(hit) }
        guard let librarian else { return .unavailable }
        let result = await ArtworkIndexResult.load { try await librarian.artworkIndex(rgid: rgid, release: release) }
        if case .ready(let index) = result { indexes[rgid] = index }
        return result
    }

    /// The artist collage (docs/artwork.md, idea 8): the session and band pictures of up to `collageAlbumLimit` of the artist's albums.
    /// Indexes are asked one at a time (the server paces its own provider calls). An album whose index is empty, unavailable or still
    /// building after the usual waits adds nothing. Empty when there are too few pictures, so the page keeps its usual hero.
    public func artistCollage(_ sources: [CollageSource], minimum: Int = collageMinimum) async -> [CollageEntry] {
        var found: [(title: String, rgid: String, index: ArtworkIndex)] = []
        for source in sources.prefix(Self.collageAlbumLimit) {
            guard !Task.isCancelled else { return [] }
            if case .ready(let index) = await artworkIndex(rgid: source.rgid, release: nil) { found.append((source.title, source.rgid, index)) }
        }
        return DiscairLibrarian.artistCollage(from: found, minimum: minimum)
    }
    static let collageAlbumLimit = 8

    /// The artwork index of the album playing now. The release group comes from the Librarian's album page (once per album; a failed
    /// ask is not remembered). nil when the album has no title, the group is unknown or the index is empty, unavailable or still
    /// building: Now Playing then shows nothing extra.
    public func nowPlayingIndex(artist: String, album: String) async -> ArtworkIndex? {
        guard !album.isEmpty, let librarian else { return nil }
        let key = "\(artist.lowercased())|\(album.lowercased())"
        var rgid = releaseGroups[key]
        if rgid == nil {
            guard let page = try? await librarian.albumPage(artist: artist, album: album), let found = page.releaseGroupMBID, !found.isEmpty,
                  !Task.isCancelled else { return nil }
            releaseGroups[key] = found
            rgid = found
        }
        guard let rgid, case .ready(let index) = await artworkIndex(rgid: rgid, release: nil), !Task.isCancelled else { return nil }
        return index
    }

    /// An owned album's cover as every screen shows it: the owner's pick (docs/artwork.md, idea 7), else the library cover (the song's
    /// own cover id, then the album's), with the server's best front when the library has none or only a small one.
    public func libraryCover(albumID: String?, coverArt: String?, px: Int) async -> NSImage? {
        var image: NSImage?
        let id = albumID.flatMap { $0.isEmpty ? nil : $0 }
        if let id, choices[id] != nil {
            image = await ownedCover(albumID: id, px: px)
            if image != nil { return image }
        }
        if let coverArt {
            image = await self.image(coverArt: coverArt, px: px)
            // A song's own cover id that Navidrome no longer serves: its album's cover stands in.
            if image == nil, let id, coverArt != "al-\(id)" { image = await self.image(coverArt: "al-\(id)", px: px) }
        }
        if let id, image == nil || (px >= 300 && Self.isSmall(image)) {
            if let better = await ownedCover(albumID: id, px: px) { image = better }
        }
        return image
    }

    /// A library cover whose longer side is under 300 px (the server uses the same limit).
    static func isSmall(_ image: NSImage?) -> Bool {
        guard let rep = image?.representations.first, rep.pixelsWide > 0 else { return false }
        return max(rep.pixelsWide, rep.pixelsHigh) < 300
    }

    /// One album image as a bitmap. A PDF original (`size == .full`) is not a bitmap and gives nil: the PDF viewer fetches it whole.
    /// A 404 is remembered for the session; a 503 or a network error is not, so the next ask tries again. Cancelling the caller
    /// cancels the download once nobody else is waiting for it.
    public func albumImage(_ image: ArtworkPicture, size: ArtworkSize) async -> NSImage? {
        if image.isPDF && size == .full { return nil }
        let key = "album|\(image.imageID)|\(size.rawValue)"
        if let hit = albumCache.object(forKey: key as NSString) { return hit }
        let diskKey = "cover|\(key)"
        if let data = media?.data(for: diskKey, ext: "img"), let decoded = NSImage(data: data) {
            albumCache.setObject(decoded, forKey: key as NSString, cost: data.count); return decoded
        }
        guard !failed.contains(key), let librarian else { return nil }
        let load: AlbumLoad
        if let running = albumLoads[key] { load = running } else {
            let task = Task<NSImage?, Never> { [weak self] in
                do {
                    let got = try await librarian.artworkImage(id: image.imageID, size: size)
                    guard !got.isPDF, let decoded = NSImage(data: got.data) else { await self?.markFailed(key); return nil }
                    await self?.keep(decoded, data: got.data, key: key, diskKey: diskKey)
                    return decoded
                } catch DiscairError.server(let status, _) where status == 404 {
                    await self?.markFailed(key); return nil
                } catch {
                    return nil
                }
            }
            load = AlbumLoad(task: task)
            albumLoads[key] = load
        }
        load.waiters += 1
        let value = await withTaskCancellationHandler {
            await load.task.value
        } onCancel: {
            Task { @MainActor in
                load.waiters -= 1
                if load.waiters <= 0 { load.task.cancel() }
            }
        }
        if !Task.isCancelled { load.waiters -= 1 }
        if load.waiters <= 0, albumLoads[key] === load { albumLoads[key] = nil }
        return value
    }

    /// A PDF booklet's bytes (`size=full`), whole: it can be tens of MB, so only the last one is kept in memory (the media cache, when
    /// on, keeps it on disk). nil on any failure; cancelling the caller cancels the download. Never a bitmap: the PDF viewer reads it.
    public func albumPDF(_ image: ArtworkPicture) async -> Data? {
        let diskKey = "cover|album|\(image.imageID)|pdf"
        if let hit = lastPDF, hit.id == image.imageID { return hit.data }
        if let data = media?.data(for: diskKey, ext: "pdf") { lastPDF = (image.imageID, data); return data }
        guard let librarian, let got = try? await librarian.artworkImage(id: image.imageID, size: .full), got.isPDF, !Task.isCancelled else { return nil }
        lastPDF = (image.imageID, got.data)
        media?.store(data: got.data, key: diskKey, ext: "pdf")
        return got.data
    }
    @ObservationIgnored private var lastPDF: (id: Int, data: Data)?

    private func markFailed(_ key: String) { failed.insert(key) }
    private func keep(_ image: NSImage, data: Data, key: String, diskKey: String) {
        albumCache.setObject(image, forKey: key as NSString, cost: data.count)
        media?.store(data: data, key: diskKey, ext: "img")
    }

    public func configure(_ builder: StreamURLBuilder?) {
        self.builder = builder
        cache.removeAllObjects()
        albumCache.removeAllObjects()
        indexes.removeAll()
        failed.removeAll()
        generation += 1
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

    private var pick: Int? { album.remoteID.flatMap { store?.choices[$0] } }

    var body: some View {
        // A real (clear) view carries the task: a bare `Group` that is empty until the image arrives never starts it when
        // the view stands alone, which left the blurred backdrops without their artwork.
        Color.clear
            .overlay { if let image { Image(nsImage: image).resizable().scaledToFill() } }
            .clipped()
            .task(id: "\(album.coverArt ?? "")@\(px)|\(album.owned ? "" : album.artist + "|" + album.title)|\(store?.generation ?? 0)|\(pick ?? 0)") {
            image = nil
            guard let store else { return }
            if album.owned {
                // The owner's pick wins on every screen, and a missing or small cover falls back to the best front (never an artist photo).
                image = await store.libraryCover(albumID: album.remoteID, coverArt: album.coverArt, px: px)
            } else if let id = album.coverArt {
                image = await store.image(coverArt: id, px: px)
            } else if album.id >= 0 {
                image = await store.image(artist: album.artist, album: album.title, px: px)
            }
        }
    }
}

/// A round artist photo with the first letter under it until (or unless) the photo arrives.
struct ArtistPhoto: View {
    let name: String
    var url: URL?
    var size: CGFloat = 72
    @Environment(\.artwork) private var store
    @State private var image: NSImage?

    var body: some View {
        ZStack {
            Circle().fill(Color(hue: LibraryModel.hue(for: name) / 360, saturation: 0.35, brightness: 0.8))
            Text(String(name.first.map(String.init) ?? "?")).font(.system(size: size * 0.4, weight: .bold)).foregroundStyle(.white.opacity(0.9))
            if let image { Image(nsImage: image).resizable().scaledToFill() }
        }
        .frame(width: size, height: size)
        .clipShape(Circle())
        .task(id: "\(name)|\(store?.generation ?? 0)") {
            image = nil
            guard let store else { return }
            image = await store.image(artistName: name, url: url)
        }
        .accessibilityHidden(true)
    }
}
