import CryptoKit
import Foundation

/// The optional on-disk copy of played songs and cover art (macOS contract section 10: off by default, 2 GB, least recently
/// used goes first, a size readout and a clear button). One folder per Navidrome user. File names are a hash of the key, so a
/// key can never name a path. When it is off, nothing is read from it or written to it; what is already there stays until
/// cleared.
public final class MediaCache: @unchecked Sendable {
    public static let defaultLimit: Int64 = 2_000_000_000

    private let root: URL
    private let limit: Int64
    private let lock = NSLock()
    private var enabled = false
    private var folder: URL?

    public init(root: URL = MediaCache.defaultRoot, limit: Int64 = MediaCache.defaultLimit) {
        self.root = root
        self.limit = limit
    }

    public static var defaultRoot: URL {
        FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0].appending(path: "Discair/media")
    }

    public var isEnabled: Bool {
        get { lock.withLock { enabled } }
        set { lock.withLock { enabled = newValue } }
    }

    /// Points the cache at one server user (nil: none).
    public func setScope(_ scope: String?) {
        lock.withLock {
            folder = scope.map { root.appending(path: Self.hash($0)) }
        }
    }

    private static func hash(_ text: String) -> String {
        SHA256.hash(data: Data(text.utf8)).prefix(10).map { String(format: "%02x", $0) }.joined()
    }

    private func active() -> URL? { lock.withLock { enabled ? folder : nil } }

    private func path(_ dir: URL, _ key: String, _ ext: String) -> URL {
        let clean = String(ext.filter { $0.isLetter || $0.isNumber }.prefix(8))
        return dir.appending(path: Self.hash(key) + "." + (clean.isEmpty ? "bin" : clean))
    }

    /// The saved file for a key, marked as just used; nil when off or not saved.
    public func file(for key: String, ext: String) -> URL? {
        guard let dir = active() else { return nil }
        let f = path(dir, key, ext)
        guard FileManager.default.fileExists(atPath: f.path) else { return nil }
        try? FileManager.default.setAttributes([.modificationDate: Date()], ofItemAtPath: f.path)
        return f
    }

    public func data(for key: String, ext: String) -> Data? {
        file(for: key, ext: ext).flatMap { try? Data(contentsOf: $0) }
    }

    /// Saves a copy of `source` (a clone on APFS) and then evicts the least recently used files down to the limit.
    public func store(copyOf source: URL, key: String, ext: String) {
        guard let dir = active() else { return }
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let dest = path(dir, key, ext)
        try? FileManager.default.removeItem(at: dest)
        guard (try? FileManager.default.copyItem(at: source, to: dest)) != nil else { return }
        evict(in: dir, keeping: dest)
    }

    public func store(data: Data, key: String, ext: String) {
        guard let dir = active() else { return }
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let dest = path(dir, key, ext)
        guard (try? data.write(to: dest, options: .atomic)) != nil else { return }
        evict(in: dir, keeping: dest)
    }

    private func entries(in dir: URL) -> [(url: URL, date: Date, size: Int64)] {
        let keys: [URLResourceKey] = [.contentModificationDateKey, .fileSizeKey]
        let files = (try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: keys)) ?? []
        return files.compactMap { u in
            guard let v = try? u.resourceValues(forKeys: Set(keys)) else { return nil }
            return (u, v.contentModificationDate ?? .distantPast, Int64(v.fileSize ?? 0))
        }
    }

    private func evict(in dir: URL, keeping keep: URL) {
        var all = entries(in: dir).sorted { $0.date < $1.date }
        var total = all.reduce(Int64(0)) { $0 + $1.size }
        while total > limit, let oldest = all.first {
            all.removeFirst()
            if oldest.url == keep { continue }
            try? FileManager.default.removeItem(at: oldest.url)
            total -= oldest.size
        }
    }

    var usedFolderForTest: URL { lock.withLock { folder! } }

    /// Bytes on disk for every user (what the Settings readout shows).
    public func usedBytes() -> Int64 {
        guard let dirs = try? FileManager.default.contentsOfDirectory(at: root, includingPropertiesForKeys: nil) else { return 0 }
        return dirs.reduce(Int64(0)) { $0 + entries(in: $1).reduce(Int64(0)) { $0 + $1.size } }
    }

    /// Deletes every saved file (the Clear button, and sign-out).
    public func clear() { try? FileManager.default.removeItem(at: root) }
}

/// Plays from the cache when the song is there, else downloads it and keeps a copy. Playback always works on a private
/// temporary copy, because the player deletes its file when it is done with it.
public struct CachingFetcher: AudioFetcher {
    private let base: any AudioFetcher
    private let cache: MediaCache
    private let tempDirectory: URL

    public init(base: any AudioFetcher = URLSessionFetcher(), cache: MediaCache,
                tempDirectory: URL = FileManager.default.temporaryDirectory.appending(path: "discair-playback")) {
        self.base = base; self.cache = cache; self.tempDirectory = tempDirectory
    }

    /// The song and the way it is asked for. The login token and salt are not part of it.
    static func key(_ url: URL) -> String? {
        let items = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems ?? []
        func v(_ n: String) -> String { items.first { $0.name == n }?.value ?? "" }
        guard url.lastPathComponent == "stream", !v("id").isEmpty else { return nil }
        return "audio|\(v("id"))|\(v("maxBitRate"))|\(v("format"))"
    }

    public func fetch(_ url: URL, suffix: String?) async throws -> URL {
        let ext = suffix ?? "audio"
        guard let key = Self.key(url) else { return try await base.fetch(url, suffix: suffix) }
        if let hit = cache.file(for: key, ext: ext) {
            try FileManager.default.createDirectory(at: tempDirectory, withIntermediateDirectories: true)
            let copy = tempDirectory.appending(path: "\(UUID().uuidString).\(ext.filter { $0.isLetter || $0.isNumber })")
            if (try? FileManager.default.copyItem(at: hit, to: copy)) != nil { return copy }
        }
        let file = try await base.fetch(url, suffix: suffix)
        cache.store(copyOf: file, key: key, ext: ext)
        return file
    }

    /// Streams a song that is not cached yet; a cached song returns nil so it plays from the cache copy. The finished
    /// download is kept in the cache, as `fetch` does.
    public func beginGrowing(_ url: URL, suffix: String?) -> GrowingDownload? {
        let ext = suffix ?? "audio"
        guard let key = Self.key(url) else { return base.beginGrowing(url, suffix: suffix) }
        if cache.file(for: key, ext: ext) != nil { return nil }
        guard let download = base.beginGrowing(url, suffix: suffix) else { return nil }
        let cache = self.cache
        download.onComplete = { file in cache.store(copyOf: file, key: key, ext: ext) }
        return download
    }
}
