import Foundation
import Testing
@testable import DiscairCore

@Suite struct UpdateConfigurationTests {
    private let goodKey = Data(repeating: 7, count: 32).base64EncodedString()
    private func info(feed: String? = "https://example.com/appcast.xml", key: String? = nil) -> [String: Any] {
        var d: [String: Any] = [:]
        if let feed { d["SUFeedURL"] = feed }
        d["SUPublicEDKey"] = key ?? goodKey
        return d
    }

    @Test func readyWithAnHttpsFeedAndA32ByteKey() {
        #expect(UpdateConfiguration(info: info(), isBundledApp: true) == .ready(feedURL: URL(string: "https://example.com/appcast.xml")!))
        #expect(UpdateConfiguration(info: info(), isBundledApp: true).isReady)
    }

    @Test func aDevelopmentBuildNeverUpdates() {
        #expect(UpdateConfiguration(info: info(), isBundledApp: false) == .unavailable(.notBundled))
        #expect(UpdateConfiguration(info: nil, isBundledApp: true) == .unavailable(.notBundled))
    }

    @Test func plainHttpOrLoginInTheFeedIsRefused() {
        #expect(UpdateConfiguration(info: info(feed: "http://example.com/a.xml"), isBundledApp: true) == .unavailable(.insecureFeed))
        #expect(UpdateConfiguration(info: info(feed: "https://me:pw@example.com/a.xml"), isBundledApp: true) == .unavailable(.insecureFeed))
        #expect(UpdateConfiguration(info: info(feed: "file:///tmp/a.xml"), isBundledApp: true) == .unavailable(.insecureFeed))
        #expect(UpdateConfiguration(info: info(feed: nil), isBundledApp: true) == .unavailable(.noFeed))
    }

    @Test func noUpdatesWithoutAValidSigningKey() {
        #expect(UpdateConfiguration(info: info(key: ""), isBundledApp: true) == .unavailable(.noPublicKey))
        #expect(UpdateConfiguration(info: info(key: "not base64!!"), isBundledApp: true) == .unavailable(.noPublicKey))
        #expect(UpdateConfiguration(info: info(key: Data(repeating: 1, count: 16).base64EncodedString()), isBundledApp: true) == .unavailable(.noPublicKey))
        var noKey = info(); noKey.removeValue(forKey: "SUPublicEDKey")
        #expect(UpdateConfiguration(info: noKey, isBundledApp: true) == .unavailable(.noPublicKey))
    }

    @Test func everyStateHasAReadableSummary() {
        let all: [UpdateConfiguration] = [.ready(feedURL: URL(string: "https://x.test/a")!), .unavailable(.notBundled), .unavailable(.noFeed),
                                          .unavailable(.insecureFeed), .unavailable(.noPublicKey)]
        for c in all { #expect(!c.summary.isEmpty) }
        #expect(Set(all.map(\.summary)).count == all.count)
    }

    @Test func theRunningTestProcessIsNotABundledApp() {
        #expect(UpdateConfiguration.current == .unavailable(.notBundled))
    }
}
