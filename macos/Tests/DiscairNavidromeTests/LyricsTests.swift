import Foundation
import Testing
import DiscairCore
@testable import DiscairNavidrome

/// Placeholder text only: the real structure of the answer, never real lyrics.
@Suite("Lyrics") struct LyricsTests {
    func entry(synced: Bool, lang: String? = nil, offset: Int? = nil, _ lines: [(Int?, String)]) -> LyricsEntry {
        LyricsEntry(lang: lang, synced: synced, offset: offset, line: lines.map { .init(start: $0.0, value: $0.1) })
    }
    func client(_ body: String, status: Int = 200) throws -> (NavidromeClient, MockTransport) {
        let t = MockTransport { _ in (status, Data(body.utf8)) }
        return (try NavidromeClient(baseURL: URL(string: "https://navi.example.ts.net")!, credential: Credential(username: "o", password: "pw"), transport: t), t)
    }

    @Test func aPlaceholderIsNotLyrics() {
        #expect(LyricsChooser.choose([entry(synced: false, [(nil, "[Instrumental]")])]) == nil)
        #expect(LyricsChooser.choose([entry(synced: true, [(1000, "♪"), (5000, "♪")])]) == nil)
        #expect(LyricsChooser.choose([entry(synced: true, [(1000, "Instrumental")])]) == nil)
        #expect(LyricsChooser.choose([entry(synced: false, [(nil, "a line"), (nil, "[Instrumental]")])]) != nil)
    }

    @Test func aTitleThatSaysInstrumentalHasNoLyrics() {
        #expect(LyricsChooser.titleSaysInstrumental("Blue in Green (Instrumental)"))
        #expect(!LyricsChooser.titleSaysInstrumental("Blue in Green"))
        #expect(!LyricsChooser.titleSaysInstrumental(nil))
    }

    @Test func prefersTimedThenPlainAndTheLanguage() {
        let timed = entry(synced: true, lang: "xxx", [(1000, "a"), (2000, "b")])
        let plain = entry(synced: false, lang: "xxx", [(nil, "p")])
        #expect(LyricsChooser.choose([plain, timed])?.timed == true)
        #expect(LyricsChooser.choose([plain])?.timed == false)
        let en = entry(synced: true, lang: "en", [(5, "english")]), de = entry(synced: true, lang: "de", [(5, "deutsch")])
        #expect(LyricsChooser.choose([de, en], language: "en")?.lines.first?.text == "english")
        #expect(LyricsChooser.choose([de, en], language: "fr")?.lines.first?.text == "deutsch")   // none match: the first
        #expect(LyricsChooser.choose([]) == nil)
    }

    @Test func timedLinesAreSortedOffsetAndCleaned() {
        let e = entry(synced: true, offset: -500, [(3000, "c"), (1000, "a"), (nil, "no start"), (-5, "negative"), (2000, "b\u{7}\u{0}")])
        let l = LyricsChooser.choose([e])!
        #expect(l.timed && l.lines.map(\.text) == ["a", "b", "c"] && l.lines.map(\.startMs) == [500, 1500, 2500])
    }

    @Test func offsetNeverGoesBelowZero() {
        #expect(LyricsChooser.choose([entry(synced: true, offset: -5000, [(1000, "a"), (9000, "b")])])!.lines.first?.startMs == 0)
    }

    @Test func equalOrBackwardStartsFallBackToPlain() {
        #expect(LyricsChooser.choose([entry(synced: true, [(1000, "a"), (1000, "b"), (1000, "c")])])?.timed == false)
        #expect(LyricsChooser.choose([entry(synced: true, [(3000, "a"), (2000, "b"), (1000, "c")])])?.timed == false)
    }

    @Test func longLinesAndLongListsAreCut() {
        let long = String(repeating: "x", count: 900)
        #expect(LyricsChooser.choose([entry(synced: true, [(1, long)])])!.lines[0].text.count == 500)
        let many = (0..<2500).map { (Int?($0 * 10), "l\($0)") }
        #expect(LyricsChooser.choose([entry(synced: true, many)])!.lines.count == 2000)
    }

    @Test func emptyLinesAreKeptAsPausesAndAllEmptyIsNone() {
        let l = LyricsChooser.choose([entry(synced: true, [(1000, "a"), (2000, ""), (3000, "b")])])!
        #expect(l.lines.map(\.text) == ["a", "", "b"])
        #expect(LyricsChooser.choose([entry(synced: false, [(nil, ""), (nil, "")])]) == nil)
    }

    @Test func theCurrentLineIsTheLastOneThatStarted() {
        let lines = [LyricLine(startMs: 1000, text: "a"), LyricLine(startMs: 2000, text: "b"), LyricLine(startMs: 4000, text: "c")]
        #expect(LyricsTimeline.currentIndex(in: lines, positionMs: 500) == nil)       // before the first line
        #expect(LyricsTimeline.currentIndex(in: lines, positionMs: 1000) == 0)         // exactly on a start
        #expect(LyricsTimeline.currentIndex(in: lines, positionMs: 3999) == 1)
        #expect(LyricsTimeline.currentIndex(in: lines, positionMs: 99_000) == 2)       // after the last
        #expect(LyricsTimeline.currentIndex(in: lines, positionMs: 1500) == 0)         // a seek back lands correctly
        #expect(LyricsTimeline.currentIndex(in: [], positionMs: 5) == nil)
    }

    @Test func theClientAsksByIdAndDecodesTheAnswer() async throws {
        let body = #"{"subsonic-response":{"status":"ok","version":"1.16.1","lyricsList":{"structuredLyrics":[{"displayArtist":"A","displayTitle":"T","lang":"xxx","synced":true,"line":[{"start":1000,"value":"placeholder one"},{"start":2500,"value":"placeholder two"}]}]}}}"#
        let (c, t) = try client(body)
        let l = try await c.lyrics(songID: "s1")
        #expect(l?.timed == true && l?.lines.count == 2)
        #expect(t.sent[0].url!.path.hasSuffix("rest/getLyricsBySongId") && queryValue(t.sent[0], "id") == "s1")
        #expect(t.sent[0].timeoutInterval == 45)
    }

    @Test func noLyricsAndAnUnknownSongAreBothNone() async throws {
        let (a, _) = try client(#"{"subsonic-response":{"status":"ok","version":"1.16.1","lyricsList":{}}}"#)
        #expect(try await a.lyrics(songID: "s1") == nil)
        let (b, _) = try client(#"{"subsonic-response":{"status":"failed","version":"1.16.1","error":{"code":70,"message":"Song not found"}}}"#)
        #expect(try await b.lyrics(songID: "nope") == nil)
    }

    @Test func aBadSongIDMakesNoRequestAndALoginFailureIsReported() async throws {
        let (c, t) = try client(#"{"subsonic-response":{"status":"failed","version":"1.16.1","error":{"code":40,"message":"Wrong username or password"}}}"#)
        await #expect(throws: DiscairError.self) { _ = try await c.lyrics(songID: "../etc") }
        #expect(t.sent.isEmpty)
        do { _ = try await c.lyrics(songID: "s1"); Issue.record("should have thrown") }
        catch DiscairError.unauthorised { }
    }

    @Test func extensionCheck() async throws {
        let yes = #"{"subsonic-response":{"status":"ok","version":"1.16.1","openSubsonicExtensions":[{"name":"transcoding","versions":[1]},{"name":"songLyrics","versions":[1]}]}}"#
        #expect(try await client(yes).0.supportsLyrics())
        let no = #"{"subsonic-response":{"status":"ok","version":"1.16.1","openSubsonicExtensions":[{"name":"transcoding","versions":[1]}]}}"#
        #expect(try await client(no).0.supportsLyrics() == false)
    }
}
