import Testing
import Foundation
@testable import DiscairCore

@Suite("Address policy") struct AddressPolicyTests {
    @Test("https is allowed for any host", arguments: [
        "https://navidrome.example.ts.net", "https://music.example.com:4533", "https://192.168.1.5", "https://8.8.8.8"])
    func httpsAllowed(_ text: String) throws { _ = try AddressPolicy.validate(text) }

    @Test("plain http is allowed for private, .local and 100.64/10", arguments: [
        "http://10.0.0.1:4533", "http://10.255.255.255", "http://172.16.0.1", "http://172.31.255.255",
        "http://192.168.1.87:8080", "http://100.64.0.1", "http://100.127.255.255",
        "http://nas.local:4533", "http://NAS.LOCAL", "http://my-mac.local.", "http://a.b.local"])
    func httpAllowed(_ text: String) throws { _ = try AddressPolicy.validate(text) }

    @Test("public and look-alike http is blocked", arguments: [
        "http://172.15.255.255", "http://172.32.0.1", "http://100.63.255.255", "http://100.128.0.1",
        "http://11.0.0.1", "http://192.169.1.1", "http://8.8.8.8", "http://example.com", "http://navidrome.ts.net",
        "http://192.168.1.1.evil.com", "http://evil.local.com", "http://local", "http://.local",
        "http://localhost", "http://127.0.0.1", "http://0xC0.168.1.1", "http://192.168.01.1", "http://192.168.1",
        "http://[fd7a:115c:a1e0::1]", "http://[::1]"])
    func httpBlocked(_ text: String) {
        #expect(throws: DiscairError.insecureOrInvalidAddress(reason: .publicHTTP)) { try AddressPolicy.validate(text) }
    }

    @Test func otherSchemesAndMalformedInput() {
        #expect(throws: DiscairError.insecureOrInvalidAddress(reason: .unsupportedScheme)) { try AddressPolicy.validate("ftp://192.168.1.1") }
        #expect(throws: DiscairError.insecureOrInvalidAddress(reason: .unsupportedScheme)) { try AddressPolicy.validate("file:///tmp") }
        #expect(throws: DiscairError.insecureOrInvalidAddress(reason: .notAURL)) { try AddressPolicy.validate("not a url") }
        #expect(throws: DiscairError.insecureOrInvalidAddress(reason: .notAURL)) { try AddressPolicy.validate("") }
        #expect(throws: DiscairError.insecureOrInvalidAddress(reason: .missingHost)) { try AddressPolicy.validate("https://") }
        #expect(throws: DiscairError.insecureOrInvalidAddress(reason: .embeddedCredentials)) { try AddressPolicy.validate("https://user:pw@host.example") }
        #expect(throws: DiscairError.insecureOrInvalidAddress(reason: .embeddedCredentials)) { try AddressPolicy.validate("http://user@192.168.1.1") }
    }

    @Test func normalisesTrailingSlashQueryAndFragment() throws {
        #expect(try AddressPolicy.validate("  https://host.example/  ").absoluteString == "https://host.example")
        #expect(try AddressPolicy.validate("http://192.168.1.5:4533/sub//?x=1#f").absoluteString == "http://192.168.1.5:4533/sub")
        #expect(try AddressPolicy.validate("HTTPS://Host.Example").scheme == "https")
    }

    @Test func unencryptedBadge() throws {
        #expect(AddressPolicy.isUnencrypted(try AddressPolicy.validate("http://192.168.1.5")))
        #expect(!AddressPolicy.isUnencrypted(try AddressPolicy.validate("https://host.example")))
    }

    @Test func ipv4ParsingIsStrict() {
        #expect(IPv4("192.168.1.1")?.isPrivate == true)
        #expect(IPv4("100.64.0.0")?.isCGNAT == true)
        for bad in ["1.2.3", "1.2.3.4.5", "256.1.1.1", "1.2.3.-4", "01.2.3.4", "1.2.3.", "a.b.c.d", "1..2.3", "1.2.3.0x4", "1.2.3.1234"] {
            #expect(IPv4(bad) == nil, "\(bad)")
        }
    }

    @Test func tailscaleHosts() {
        #expect(AddressPolicy.isTailscaleHost("navidrome.tail1234.ts.net"))
        #expect(AddressPolicy.isTailscaleHost("100.101.102.103"))
        #expect(!AddressPolicy.isTailscaleHost("192.168.1.5"))
        #expect(!AddressPolicy.isTailscaleHost("example.com"))
        #expect(!AddressPolicy.isTailscaleHost("evilts.net"))
    }
}
