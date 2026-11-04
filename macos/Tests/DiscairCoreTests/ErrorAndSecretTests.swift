import Testing
import Foundation
import Security
@testable import DiscairCore

@Suite("Error mapping") struct ErrorMappingTests {
    @Test func transportErrors() {
        #expect(ErrorMapping.map(URLError(.notConnectedToInternet)) == .noNetwork)
        #expect(ErrorMapping.map(URLError(.dataNotAllowed)) == .noNetwork)
        #expect(ErrorMapping.map(URLError(.timedOut)) == .serverUnreachable)
        #expect(ErrorMapping.map(URLError(.cannotConnectToHost)) == .serverUnreachable)
        #expect(ErrorMapping.map(URLError(.secureConnectionFailed)) == .serverUnreachable)
        #expect(ErrorMapping.map(URLError(.cannotFindHost)) == .serverUnreachable)
        #expect(ErrorMapping.map(URLError(.badURL)) == .serverUnreachable)
        #expect(ErrorMapping.map(CocoaError(.fileNoSuchFile)) == .serverUnreachable)
    }
    @Test func tailscaleHintOnlyChangesUnreachable() {
        #expect(ErrorMapping.map(URLError(.timedOut), tailscaleHint: true) == .tailscaleNotConnected)
        #expect(ErrorMapping.map(URLError(.cannotConnectToHost), tailscaleHint: true) == .tailscaleNotConnected)
        #expect(ErrorMapping.map(URLError(.notConnectedToInternet), tailscaleHint: true) == .noNetwork)
    }
    @Test func ownErrorsPassThrough() {
        #expect(ErrorMapping.map(DiscairError.unauthorised(message: nil)) == .unauthorised(message: nil))
    }
    @Test func httpStatuses() {
        #expect(ErrorMapping.map(status: 200) == nil)
        #expect(ErrorMapping.map(status: 204) == nil)
        #expect(ErrorMapping.map(status: 401, message: "x") == .unauthorised(message: "x"))
        #expect(ErrorMapping.map(status: 403) == .unauthorised(message: nil))
        #expect(ErrorMapping.map(status: 429, message: "later") == .tooManyAttempts(message: "later"))
        #expect(ErrorMapping.map(status: 500) == .server(status: 500, message: nil))
        #expect(ErrorMapping.map(status: 502) == .server(status: 502, message: nil))
        #expect(ErrorMapping.map(status: 404) == .server(status: 404, message: nil))
    }
    @Test func retryability() {
        #expect(DiscairError.noNetwork.isRetryable && DiscairError.tailscaleNotConnected.isRetryable)
        #expect(!DiscairError.insecureOrInvalidAddress(reason: .publicHTTP).isRetryable)
    }
    @Test func summariesAreDistinct() {
        let all: [DiscairError] = [.noNetwork, .serverUnreachable, .tailscaleNotConnected, .unauthorised(message: nil),
                                   .server(status: 500, message: nil), .tooManyAttempts(message: nil)]
        #expect(Set(all.map(\.summary)).count == all.count)
    }
}

@Suite("Secrets") struct SecretTests {
    let secret = "hunter2-very-secret"

    @Test func credentialNeverPrints() {
        let c = Credential(username: "owner", password: secret)
        var dumped = ""; dump(c, to: &dumped)
        let texts = [String(describing: c), "\(c)", String(reflecting: c), c.debugDescription, dumped,
                     "\(DiscairError.unauthorised(message: nil))"]
        for t in texts { #expect(!t.contains(secret)) }
        #expect(String(describing: c).contains("owner"))
    }
    @Test func inMemoryStoreKeepsTheTwoLoginsApart() throws {
        let s = InMemorySecretStore()
        try s.save(Credential(username: "navi", password: "a"), for: .navidrome)
        try s.save(Credential(username: "lib", password: "b"), for: .librarian)
        #expect(try s.credential(for: .navidrome)?.username == "navi")
        #expect(try s.credential(for: .librarian)?.username == "lib")
        try s.delete(.navidrome)
        #expect(try s.credential(for: .navidrome) == nil)
        #expect(try s.credential(for: .librarian)?.username == "lib")
    }
    @Test func redaction() {
        let url = "https://h.example/rest/stream?u=owner&t=abc123&s=salt99&v=1.16.1&c=discair&id=x1&password=pw&token=tk"
        let out = redactSecrets(url)
        for leak in ["owner", "abc123", "salt99", "=pw", "=tk"] { #expect(!out.contains(leak), "\(leak)") }
        #expect(out.contains("id=x1") && out.contains("v=1.16.1"))
        #expect(redactSecrets(nil) == "")
    }

    /// Real macOS Keychain round trip under a throw-away service name (removed afterwards).
    /// Set DISCAIR_SKIP_KEYCHAIN_TESTS=1 on a machine without an unlocked login keychain.
    @Test(.enabled(if: ProcessInfo.processInfo.environment["DISCAIR_SKIP_KEYCHAIN_TESTS"] == nil))
    func keychainRoundTrip() throws {
        let store = KeychainSecretStore(servicePrefix: "app.discair.tests.\(UUID().uuidString)")
        defer { for k in SecretKind.allCases { try? store.delete(k) } }
        #expect(try store.credential(for: .navidrome) == nil)
        try store.save(Credential(username: "navi", password: secret), for: .navidrome)
        try store.save(Credential(username: "lib", password: "other"), for: .librarian)
        #expect(try store.credential(for: .navidrome)?.username == "navi")
        #expect(try store.credential(for: .navidrome)?.withPassword { $0 } == secret)
        #expect(try store.credential(for: .librarian)?.username == "lib")
        try store.save(Credential(username: "navi", password: "changed"), for: .navidrome)   // update path
        #expect(try store.credential(for: .navidrome)?.withPassword { $0 } == "changed")
        try store.delete(.navidrome)
        #expect(try store.credential(for: .navidrome) == nil)
        #expect(try store.credential(for: .librarian) != nil)
    }

    /// One combined item, and a build that left one item per login is moved over once and the old items removed.
    @Test(.enabled(if: ProcessInfo.processInfo.environment["DISCAIR_SKIP_KEYCHAIN_TESTS"] == nil))
    func keychainMigratesOlderItems() throws {
        let prefix = "app.discair.tests.\(UUID().uuidString)"
        func raw(_ service: String) -> [String: Any] {
            [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service,
             kSecAttrAccount as String: "login", kSecAttrSynchronizable as String: false]
        }
        func add(_ kind: String, _ c: Credential) throws {
            var q = raw("\(prefix).\(kind)")
            q[kSecValueData as String] = try JSONEncoder().encode(c)
            #expect(SecItemAdd(q as CFDictionary, nil) == errSecSuccess)
        }
        func exists(_ service: String) -> Bool { SecItemCopyMatching(raw(service) as CFDictionary, nil) == errSecSuccess }
        try add("navidrome", Credential(username: "navi", password: "p1"))
        try add("smb", Credential(username: "nas", password: "p2"))
        let store = KeychainSecretStore(servicePrefix: prefix)
        defer { for k in SecretKind.allCases { try? store.delete(k) }; for s in ["logins", "navidrome", "librarian", "smb"] { SecItemDelete(raw("\(prefix).\(s)") as CFDictionary) } }
        #expect(try store.credential(for: .navidrome)?.withPassword { $0 } == "p1")
        #expect(try store.credential(for: .smb)?.username == "nas")
        #expect(try store.credential(for: .librarian) == nil)
        #expect(exists("\(prefix).logins") && !exists("\(prefix).navidrome") && !exists("\(prefix).smb"))
        // A second store (a new launch) reads the combined item.
        #expect(try KeychainSecretStore(servicePrefix: prefix).credential(for: .smb)?.username == "nas")
        // Deleting the last login removes the item.
        try store.delete(.navidrome); try store.delete(.smb)
        #expect(!exists("\(prefix).logins"))
    }
}
