import Testing
import Foundation
import DiscairCore
@testable import DiscairNavidrome

@Suite("Subsonic token and salt") struct SubsonicAuthTests {
    @Test func tokenMatchesTheSubsonicDocumentationVector() {
        // From the Subsonic API docs: password "sesame", salt "c19b2d".
        #expect(SubsonicAuth.token(password: "sesame", salt: "c19b2d") == "26719a1196d2a940705a59634eb18eab")
    }
    @Test func freshSaltEveryRequest() {
        let auth = SubsonicAuth(credential: Credential(username: "owner", password: "pw"))
        let salts = (0..<50).map { _ in auth.queryItems().first { $0.name == "s" }!.value! }
        #expect(Set(salts).count == 50)
        #expect(salts.allSatisfy { $0.count == 16 && $0.allSatisfy(\.isHexDigit) })
    }
    @Test func tokenIsBoundToTheSaltAndPasswordIsNeverSent() {
        let secret = "correct horse battery staple"
        let auth = SubsonicAuth(credential: Credential(username: "owner", password: secret), makeSalt: { "abc123" })
        let items = auth.queryItems()
        let dict = Dictionary(uniqueKeysWithValues: items.map { ($0.name, $0.value!) })
        #expect(dict["t"] == SubsonicAuth.token(password: secret, salt: "abc123"))
        #expect(dict["s"] == "abc123" && dict["u"] == "owner" && dict["v"] == "1.16.1" && dict["c"] == "discair" && dict["f"] == "json")
        #expect(dict["p"] == nil && dict["password"] == nil)
        #expect(!items.contains { $0.value?.contains(secret) == true })
    }
    @Test func jsonFormatIsOptional() {
        let auth = SubsonicAuth(credential: Credential(username: "o", password: "p"))
        #expect(!auth.queryItems(json: false).contains { $0.name == "f" })
    }
}

@Suite("Stream URL builder") struct StreamURLTests {
    func builder(_ base: String = "https://navi.example.ts.net", pw: String = "pw") throws -> StreamURLBuilder {
        try StreamURLBuilder(baseURL: try AddressPolicy.validate(base),
                             auth: SubsonicAuth(credential: Credential(username: "owner", password: pw), makeSalt: { "salty" }))
    }

    @Test func originalHasOnlyIDAndAuth() throws {
        let url = try builder().streamURL(songID: "1aF3pKQJpLQmSVb50IlxsP")
        #expect(url.path == "/rest/stream")
        let names = Set(URLComponents(url: url, resolvingAgainstBaseURL: false)!.queryItems!.map(\.name))
        #expect(names == ["u", "t", "s", "v", "c", "id"])
        #expect(queryValue(url, "id") == "1aF3pKQJpLQmSVb50IlxsP")
    }
    @Test func bitRateAndFormatFromTheAllowlistOnly() throws {
        let b = try builder()
        for rate in [64, 96, 128, 192, 256, 320] {
            #expect(queryValue(try b.streamURL(songID: "x1", maxBitRate: rate), "maxBitRate") == String(rate))
        }
        for rate in [0, 1, 63, 100, 321, 1000, -128] {
            #expect(throws: StreamURLBuilder.BuildError.unsupportedBitRate) { try b.streamURL(songID: "x1", maxBitRate: rate) }
        }
        #expect(queryValue(try b.streamURL(songID: "x1", format: .opus), "format") == "opus")
        #expect(queryValue(try b.streamURL(songID: "x1", format: .mp3), "format") == "mp3")
        #expect(TranscodeFormat.allCases.map(\.rawValue).sorted() == ["mp3", "opus"])   // no "raw", no "flac"
        #expect(queryValue(try b.streamURL(songID: "x1"), "format") == nil)
        #expect(queryValue(try b.streamURL(songID: "x1"), "maxBitRate") == nil)
    }
    @Test func songIDsAreRestricted() throws {
        let b = try builder()
        for bad in ["", "a b", "a/b", "../x", "a&maxBitRate=1", "a?b", "é", String(repeating: "a", count: 129), "a\nb", "a%20b"] {
            #expect(throws: StreamURLBuilder.BuildError.invalidID, "\(bad.debugDescription)") { try b.streamURL(songID: bad) }
        }
        for good in ["abc", "A-b_9", String(repeating: "a", count: 128)] { _ = try b.streamURL(songID: good) }
    }
    @Test func passwordNeverAppearsAndSaltIsFresh() throws {
        let secret = "pa$$word-with-chars"
        let urls = try builder(pw: secret).streamURL(songID: "x1").absoluteString
        #expect(!urls.contains(secret) && !urls.contains("password"))
        var n = 0
        let b = try StreamURLBuilder(baseURL: try AddressPolicy.validate("https://h.example"),
                                     auth: SubsonicAuth(credential: Credential(username: "o", password: "p")))
        let salts = try (0..<20).map { _ in queryValue(try b.streamURL(songID: "x1"), "s")! }
        n = Set(salts).count
        #expect(n == 20)
    }
    @Test func transportRulesApplyToTheBase() throws {
        _ = try builder("http://192.168.1.87:4533")
        #expect(throws: DiscairError.insecureOrInvalidAddress(reason: .publicHTTP)) { try builder("http://music.example.com") }
        #expect(try builder("https://h.example/navidrome/").streamURL(songID: "x1").path == "/navidrome/rest/stream")
    }
    @Test func coverArtURL() throws {
        let url = try builder().coverArtURL(coverArtID: "al-7y8UEyluchKVjyUsqNJQRQ_a83305b4cffa73be", size: 300)
        #expect(url.path == "/rest/getCoverArt" && queryValue(url, "size") == "300")
        #expect(queryValue(try builder().coverArtURL(coverArtID: "mf-1", size: 99999), "size") == nil)
        #expect(throws: StreamURLBuilder.BuildError.invalidID) { try builder().coverArtURL(coverArtID: "a&b") }
    }
    @Test func redactionRemovesTheSecretsFromABuiltURL() throws {
        let text = "failed: \(try builder(pw: "pw").streamURL(songID: "x1", maxBitRate: 128).absoluteString)"
        let out = redactSecrets(text)
        #expect(!out.contains("owner") && !out.contains("salty") && out.contains("maxBitRate=128"))
    }
}
