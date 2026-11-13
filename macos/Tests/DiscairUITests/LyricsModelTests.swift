import DiscairCore
import DiscairNavidrome
import Foundation
import Testing
@testable import DiscairUI

/// Placeholder text only.
private final class LyricsTransport: HTTPTransport, @unchecked Sendable {
    private let lock = NSLock()
    private var paths: [String] = []
    var lyricsBody: String
    var extensionsBody = #"{"subsonic-response":{"status":"ok","openSubsonicExtensions":[{"name":"songLyrics"}]}}"#
    var failLyrics = false
    init(lyrics: String) { lyricsBody = lyrics }
    var calls: [String] { lock.withLock { paths } }
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let p = request.url!.lastPathComponent
        lock.withLock { paths.append(p) }
        if failLyrics && p == "getLyricsBySongId" { throw URLError(.cannotConnectToHost) }
        let body = p == "getOpenSubsonicExtensions" ? extensionsBody : lyricsBody
        return (Data(body.utf8), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
    }
}

private let timedBody = #"{"subsonic-response":{"status":"ok","lyricsList":{"structuredLyrics":[{"lang":"xxx","synced":true,"line":[{"start":1000,"value":"one"},{"start":3000,"value":"two"}]}]}}}"#
private let plainBody = #"{"subsonic-response":{"status":"ok","lyricsList":{"structuredLyrics":[{"lang":"xxx","synced":false,"line":[{"value":"alpha"},{"value":"beta"}]}]}}}"#
private let noneBody = #"{"subsonic-response":{"status":"ok","lyricsList":{}}}"#

private func tempRoot() -> URL { FileManager.default.temporaryDirectory.appending(path: "lyrics-test-\(UUID().uuidString)") }

@MainActor
private func make(_ t: LyricsTransport, root: URL, now: @escaping () -> Date = { .now }) throws -> LyricsModel {
    let client = try NavidromeClient(baseURL: URL(string: "https://navi.example.ts.net")!, credential: Credential(username: "o", password: "pw"), transport: t)
    let m = LyricsModel()
    m.configure(navidrome: client, scope: "navi|o", root: root, now: now)
    return m
}

@MainActor
private func until(_ condition: () -> Bool) async {
    for _ in 0..<500 where !condition() { try? await Task.sleep(for: .milliseconds(10)) }
}

struct LyricsCacheTests {
    @Test func storesAndReturnsAnswersPerServerAndUser() {
        let root = tempRoot(); defer { try? FileManager.default.removeItem(at: root) }
        let a = LyricsCache(root: root, scope: "server-a|owner"), b = LyricsCache(root: root, scope: "server-b|owner")
        a.put("s1", Lyrics(timed: false, lines: [LyricLine(startMs: nil, text: "x")]))
        #expect(a.get("s1")?.lyrics?.lines.first?.text == "x")
        #expect(b.get("s1") == nil)                                   // another server never reads it
        a.put("s2", nil)
        #expect(a.get("s2") != nil && a.get("s2")?.lyrics == nil)     // "none" is remembered
        #expect(a.get("../x") == nil)
    }

    @Test func foundAnswersStayFreshAnHourAndNoneFiveMinutes() {
        let root = tempRoot(); defer { try? FileManager.default.removeItem(at: root) }
        var clock = Date(timeIntervalSince1970: 1_000_000)
        let c = LyricsCache(root: root, scope: "s", now: { clock })
        c.put("none", nil); c.put("found", Lyrics(timed: false, lines: [LyricLine(startMs: nil, text: "x")]))
        clock = clock.addingTimeInterval(200); #expect(c.isFresh(c.get("none")!))
        clock = clock.addingTimeInterval(200); #expect(!c.isFresh(c.get("none")!) && c.isFresh(c.get("found")!))
        clock = clock.addingTimeInterval(3_300); #expect(!c.isFresh(c.get("found")!))
    }

    @Test func entriesFromAnOlderSchemaOrAnotherLanguageAreMisses() throws {
        let root = tempRoot(); defer { try? FileManager.default.removeItem(at: root) }
        let c = LyricsCache(root: root, scope: "s")
        c.put("s1", nil, language: "en")
        #expect(c.get("s1", language: "en") != nil)
        #expect(c.get("s1", language: "fr") == nil)
        // An entry written before schema numbers existed (no schema field) is dropped.
        try FileManager.default.createDirectory(at: c.directory, withIntermediateDirectories: true)
        try Data(#"{"fetchedAt":1000,"lyrics":null}"#.utf8).write(to: c.directory.appending(path: "old.json"))
        #expect(c.get("old") == nil)
    }

    @Test func keepsAtMost300SongsDroppingTheOldest() throws {
        let root = tempRoot(); defer { try? FileManager.default.removeItem(at: root) }
        let c = LyricsCache(root: root, scope: "s")
        for i in 0..<310 { c.put("song\(i)", nil) }
        let count = try FileManager.default.contentsOfDirectory(at: c.directory, includingPropertiesForKeys: nil).count
        #expect(count <= 300)
        #expect(c.get("song309") != nil)
    }

    @Test func clearRemovesEveryServersLyrics() {
        let root = tempRoot(); defer { try? FileManager.default.removeItem(at: root) }
        let a = LyricsCache(root: root, scope: "a"), b = LyricsCache(root: root, scope: "b")
        a.put("s1", nil); b.put("s1", nil)
        a.clear()
        #expect(a.get("s1") == nil && b.get("s1") == nil)
    }
}

@MainActor
struct LyricsModelTests {
    @Test func loadsTimedLyricsAndFindsTheCurrentLine() async throws {
        let root = tempRoot(); defer { try? FileManager.default.removeItem(at: root) }
        let m = try make(LyricsTransport(lyrics: timedBody), root: root)
        m.show(songID: "s1")
        #expect(m.state == .loading)
        await until { m.state == .timed }
        #expect(m.lines.map(\.text) == ["one", "two"])
        #expect(m.currentIndex(positionSeconds: 0.5) == nil && m.currentIndex(positionSeconds: 1.2) == 0 && m.currentIndex(positionSeconds: 3) == 1)
    }

    @Test func plainLyricsHaveNoCurrentLine() async throws {
        let root = tempRoot(); defer { try? FileManager.default.removeItem(at: root) }
        let m = try make(LyricsTransport(lyrics: plainBody), root: root)
        m.show(songID: "s1")
        await until { m.state == .plain }
        #expect(m.currentIndex(positionSeconds: 5) == nil)
    }

    @Test func noLyricsIsANormalAnswer() async throws {
        let root = tempRoot(); defer { try? FileManager.default.removeItem(at: root) }
        let m = try make(LyricsTransport(lyrics: noneBody), root: root)
        m.show(songID: "s1")
        await until { m.state == .none }
        #expect(m.state == .none && m.lines.isEmpty)
    }

    @Test func aServerWithoutTheExtensionSaysSoAndAsksForNoLyrics() async throws {
        let root = tempRoot(); defer { try? FileManager.default.removeItem(at: root) }
        let t = LyricsTransport(lyrics: timedBody)
        t.extensionsBody = #"{"subsonic-response":{"status":"ok","openSubsonicExtensions":[{"name":"transcoding"}]}}"#
        let m = try make(t, root: root)
        m.show(songID: "s1")
        await until { m.state == .unsupported }
        #expect(m.state == .unsupported && !t.calls.contains("getLyricsBySongId"))
    }

    @Test func aFreshCachedAnswerIsUsedWithoutAskingTheServerAgain() async throws {
        let root = tempRoot(); defer { try? FileManager.default.removeItem(at: root) }
        let t = LyricsTransport(lyrics: timedBody)
        let m = try make(t, root: root)
        m.show(songID: "s1")
        await until { m.state == .timed }
        let m2 = try make(t, root: root)
        m2.show(songID: "s1")
        #expect(m2.state == .timed)                                    // from the cache at once
        try await Task.sleep(for: .milliseconds(100))
        #expect(t.calls.filter { $0 == "getLyricsBySongId" }.count == 1)
    }

    @Test func offlineWithACachedCopyShowsItMarkedSavedAndWithoutOneFails() async throws {
        let root = tempRoot(); defer { try? FileManager.default.removeItem(at: root) }
        let t = LyricsTransport(lyrics: timedBody)
        var clock = Date(timeIntervalSince1970: 1_000_000)
        let m = try make(t, root: root, now: { clock })
        m.show(songID: "s1")
        await until { m.state == .timed }
        clock = clock.addingTimeInterval(200_000)                      // the copy is now stale, so the server is asked
        t.failLyrics = true
        let m2 = try make(t, root: root, now: { clock })
        m2.show(songID: "s1")
        await until { m2.isSavedCopy }
        #expect(m2.state == .timed && m2.isSavedCopy)
        m2.show(songID: "other")
        await until { if case .failed = m2.state { true } else { false } }
        if case .failed(let message) = m2.state { #expect(!message.isEmpty) } else { Issue.record("expected a failure") }
    }

    @Test func signOutDeletesTheSavedLyrics() async throws {
        let root = tempRoot(); defer { try? FileManager.default.removeItem(at: root) }
        let m = try make(LyricsTransport(lyrics: timedBody), root: root)
        m.show(songID: "s1")
        await until { m.state == .timed }
        m.clearAll()
        #expect(m.state == .idle && m.lines.isEmpty)
        #expect(!FileManager.default.fileExists(atPath: root.path))
    }
}
