import Foundation
import Testing
@testable import DiscairAudio

private func temp() -> URL { FileManager.default.temporaryDirectory.appending(path: "discair-media-\(UUID().uuidString)") }

private func source(_ bytes: Int) throws -> URL {
    let u = FileManager.default.temporaryDirectory.appending(path: "src-\(UUID().uuidString).flac")
    try Data(repeating: 7, count: bytes).write(to: u)
    return u
}

private final class CountingFetcher: AudioFetcher, @unchecked Sendable {
    private let lock = NSLock(); private var n = 0
    var count: Int { lock.withLock { n } }
    func fetch(_ url: URL, suffix: String?) async throws -> URL {
        lock.withLock { n += 1 }
        return try source(100)
    }
}

struct MediaCacheTests {
    private func make(limit: Int64 = 1000, enabled: Bool = true) -> MediaCache {
        let c = MediaCache(root: temp(), limit: limit); c.setScope("u"); c.isEnabled = enabled; return c
    }

    @Test func offByDefaultAndThenNothingIsReadOrWritten() throws {
        let c = MediaCache(root: temp()); c.setScope("u")
        #expect(!c.isEnabled)
        c.store(data: Data([1]), key: "k", ext: "jpg")
        #expect(c.data(for: "k", ext: "jpg") == nil && c.usedBytes() == 0)
    }

    @Test func storesAndReadsBack() throws {
        let c = make()
        c.store(data: Data([1, 2, 3]), key: "cover|al-1|300", ext: "img")
        #expect(c.data(for: "cover|al-1|300", ext: "img") == Data([1, 2, 3]))
        #expect(c.usedBytes() == 3)
    }

    @Test func leastRecentlyUsedGoesFirstAndReadingRefreshesIt() throws {
        let c = make(limit: 250)
        c.store(data: Data(repeating: 1, count: 100), key: "a", ext: "bin")
        Thread.sleep(forTimeInterval: 0.02)
        c.store(data: Data(repeating: 2, count: 100), key: "b", ext: "bin")
        Thread.sleep(forTimeInterval: 0.02)
        _ = c.file(for: "a", ext: "bin")                          // a is now newer than b
        Thread.sleep(forTimeInterval: 0.02)
        c.store(data: Data(repeating: 3, count: 100), key: "c", ext: "bin")   // 300 > 250: b goes
        #expect(c.file(for: "b", ext: "bin") == nil)
        #expect(c.file(for: "a", ext: "bin") != nil && c.file(for: "c", ext: "bin") != nil)
        #expect(c.usedBytes() <= 250)
    }

    @Test func clearRemovesEverythingAndKeysCannotEscape() throws {
        let c = make()
        c.store(data: Data([1]), key: "../../evil", ext: "../x")
        let names = (try? FileManager.default.contentsOfDirectory(atPath: c.usedFolderForTest.path)) ?? []
        #expect(names.count == 1 && !names[0].contains(".."))
        c.clear()
        #expect(c.usedBytes() == 0)
    }

    @Test func anotherUserNeverReadsIt() throws {
        let root = temp()
        let a = MediaCache(root: root); a.setScope("a"); a.isEnabled = true
        a.store(data: Data([1]), key: "k", ext: "bin")
        let b = MediaCache(root: root); b.setScope("b"); b.isEnabled = true
        #expect(b.data(for: "k", ext: "bin") == nil && a.data(for: "k", ext: "bin") != nil)
    }
}

struct CachingFetcherTests {
    private func url(_ id: String, cap: Int? = nil, token: String = "t1") -> URL {
        var s = "https://navi.example.ts.net/rest/stream?u=o&t=\(token)&s=salt&v=1.16.1&c=discair&id=\(id)"
        if let cap { s += "&maxBitRate=\(cap)" }
        return URL(string: s)!
    }

    @Test func theSecondPlayComesFromTheCacheEvenWithADifferentToken() async throws {
        let cache = MediaCache(root: temp()); cache.setScope("u"); cache.isEnabled = true
        let base = CountingFetcher()
        let f = CachingFetcher(base: base, cache: cache, tempDirectory: temp())
        let first = try await f.fetch(url("s1"), suffix: "flac")
        let second = try await f.fetch(url("s1", token: "t2"), suffix: "flac")
        #expect(base.count == 1)
        #expect(first != second && FileManager.default.fileExists(atPath: second.path))
        try FileManager.default.removeItem(at: second)               // the player deletes its copy
        let third = try await f.fetch(url("s1"), suffix: "flac")
        #expect(base.count == 1 && FileManager.default.fileExists(atPath: third.path))
    }

    @Test func aDifferentQualityIsADifferentEntry() async throws {
        let cache = MediaCache(root: temp()); cache.setScope("u"); cache.isEnabled = true
        let base = CountingFetcher()
        let f = CachingFetcher(base: base, cache: cache, tempDirectory: temp())
        _ = try await f.fetch(url("s1"), suffix: "flac")
        _ = try await f.fetch(url("s1", cap: 128), suffix: "mp3")
        #expect(base.count == 2)
    }

    @Test func whenOffEveryPlayDownloads() async throws {
        let cache = MediaCache(root: temp()); cache.setScope("u")
        let base = CountingFetcher()
        let f = CachingFetcher(base: base, cache: cache, tempDirectory: temp())
        _ = try await f.fetch(url("s1"), suffix: "flac"); _ = try await f.fetch(url("s1"), suffix: "flac")
        #expect(base.count == 2 && cache.usedBytes() == 0)
    }
}
