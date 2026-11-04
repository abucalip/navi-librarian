import CryptoKit
import DiscairCore
import DiscairNavidrome
import Foundation
import Observation

/// One small file per song, kept per server and user, so another server never reads it. At most 300 songs or 5 MB, oldest
/// removed first; a "none" answer is trusted for 24 hours and a found one is refreshed at most daily. Lyrics are copyrighted
/// text: they live only here and are deleted at sign-out (`clear`).
struct LyricsCache {
    struct Entry: Codable, Equatable { var fetchedAt: Date; var lyrics: Lyrics? }
    static let maxFiles = 300
    static let maxBytes = 5_000_000
    let directory: URL
    var now: () -> Date = { .now }

    init(root: URL, scope: String, now: @escaping () -> Date = { .now }) {
        let hash = SHA256.hash(data: Data(scope.utf8)).prefix(8).map { String(format: "%02x", $0) }.joined()
        directory = root.appending(path: hash)
        self.now = now
    }

    private func file(_ id: String) -> URL { directory.appending(path: "\(id).json") }

    func get(_ id: String) -> Entry? {
        guard isValidSongID(id), let data = try? Data(contentsOf: file(id)) else { return nil }
        return try? JSONDecoder().decode(Entry.self, from: data)
    }

    /// A "none" entry older than a day counts as a miss; a found entry older than a day is stale but still usable.
    func isFresh(_ e: Entry) -> Bool { now().timeIntervalSince(e.fetchedAt) < 86_400 }

    func put(_ id: String, _ lyrics: Lyrics?) {
        guard isValidSongID(id), let data = try? JSONEncoder().encode(Entry(fetchedAt: now(), lyrics: lyrics)) else { return }
        try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try? data.write(to: file(id), options: .atomic)
        trim()
    }

    private func trim() {
        let keys: [URLResourceKey] = [.contentModificationDateKey, .fileSizeKey]
        guard let files = try? FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: keys) else { return }
        var info = files.compactMap { u -> (URL, Date, Int)? in
            guard let v = try? u.resourceValues(forKeys: Set(keys)) else { return nil }
            return (u, v.contentModificationDate ?? .distantPast, v.fileSize ?? 0)
        }.sorted { $0.1 < $1.1 }
        var total = info.reduce(0) { $0 + $1.2 }
        while (info.count > Self.maxFiles || total > Self.maxBytes), let oldest = info.first {
            try? FileManager.default.removeItem(at: oldest.0)
            total -= oldest.2
            info.removeFirst()
        }
    }

    /// Sign-out: removes every server's lyrics, not only this one's.
    func clear() { try? FileManager.default.removeItem(at: directory.deletingLastPathComponent()) }
}

/// The lyrics of the song that is playing, fetched only when a screen shows them, with the states of the Android contract
/// written out: loading, timed, plain, none, unsupported and failed. Prefetches the next song's.
@MainActor
@Observable
public final class LyricsModel {
    public enum State: Equatable, Sendable { case idle, loading, timed, plain, none, unsupported, failed(String) }

    public private(set) var state: State = .idle
    public private(set) var lines: [LyricLine] = []
    /// Shown instead of fresh lyrics when the server could not be reached.
    public private(set) var isSavedCopy = false

    @ObservationIgnored private var navidrome: NavidromeClient?
    @ObservationIgnored private var cache: LyricsCache?
    @ObservationIgnored private var supports: Bool?
    @ObservationIgnored private var songID: String?
    @ObservationIgnored private var generation = 0
    @ObservationIgnored private var inFlight: Task<Void, Never>?
    @ObservationIgnored private let language = Locale.current.language.languageCode?.identifier

    public init() {}

    static var defaultRoot: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appending(path: "Discair/lyrics")
    }

    func configure(navidrome: NavidromeClient?, scope: String, root: URL = LyricsModel.defaultRoot, now: @escaping () -> Date = { .now }) {
        self.navidrome = navidrome
        cache = navidrome == nil ? nil : LyricsCache(root: root, scope: scope, now: now)
        supports = nil; songID = nil; state = .idle; lines = []; isSavedCopy = false
        inFlight?.cancel()
    }

    /// Sign-out: forget everything and delete the saved lyrics.
    func clearAll() {
        cache?.clear()
        configure(navidrome: nil, scope: "")
    }

    public func currentIndex(positionSeconds: Double) -> Int? {
        guard state == .timed else { return nil }
        return LyricsTimeline.currentIndex(in: lines, positionMs: Int(positionSeconds * 1000))
    }

    /// Shows the lyrics of this song. Call when a screen that shows lyrics appears or the song changes.
    public func show(songID id: String?) {
        guard let id else { songID = nil; state = .idle; lines = []; return }
        guard id != songID || state == .idle || { if case .failed = state { true } else { false } }() else { return }
        generation += 1
        let mine = generation
        songID = id
        inFlight?.cancel()
        guard navidrome != nil, let cache else { return }
        // The cache answers at once; only a miss or a stale copy goes to the server.
        lines = []; isSavedCopy = false
        let cached = cache.get(id)
        if let cached { apply(cached.lyrics) } else { state = .loading }
        if let cached, cache.isFresh(cached) { return }
        inFlight = Task { [weak self] in await self?.load(id, mine, cached) }
    }

    /// Try again after a failure.
    public func retry() { let id = songID; state = .idle; show(songID: id) }

    private func apply(_ l: Lyrics?, savedCopy: Bool = false) {
        isSavedCopy = savedCopy
        if let l { lines = l.lines; state = l.timed ? .timed : .plain } else { lines = []; state = .none }
    }

    private func load(_ id: String, _ mine: Int, _ cached: LyricsCache.Entry?) async {
        guard let navidrome, let cache else { return }
        do {
            if supports == nil { supports = try await navidrome.supportsLyrics() }
            guard supports == true else { if mine == generation { state = .unsupported }; return }
            let fetched = try await navidrome.lyrics(songID: id, language: language)
            cache.put(id, fetched)
            guard mine == generation, !Task.isCancelled else { return }
            apply(fetched)
        } catch {
            guard mine == generation, !Task.isCancelled else { return }
            if let cached { apply(cached.lyrics, savedCopy: true); return }
            let e = error as? DiscairError
            state = .failed(e.map(AcquisitionModel.text) ?? ErrorMapping.map(error).summary)
        }
    }

    /// Fetches the next song's lyrics into the cache so they are ready at the song change. Only called while lyrics are showing.
    public func prefetch(songID id: String?) {
        guard let id, id != songID, let navidrome, let cache, supports == true else { return }
        if let c = cache.get(id), cache.isFresh(c) { return }
        Task { [language] in
            do { cache.put(id, try await navidrome.lyrics(songID: id, language: language)) } catch {}   // a failure is simply not cached
        }
    }
}
