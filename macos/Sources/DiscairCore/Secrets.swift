import Foundation
import Security

/// A login. Printing it, interpolating it or dumping it never shows the password.
public struct Credential: Codable, Equatable, Sendable, CustomStringConvertible, CustomDebugStringConvertible, CustomReflectable {
    public let username: String
    private let password: String

    public init(username: String, password: String) {
        self.username = username
        self.password = password
    }

    /// The only way to read the password: callers name what they are doing (token, login body).
    public func withPassword<R>(_ body: (String) throws -> R) rethrows -> R { try body(password) }

    public var description: String { "Credential(username: \(username), password: <redacted>)" }
    public var debugDescription: String { description }
    public var customMirror: Mirror { Mirror(self, children: ["username": username, "password": "<redacted>"]) }
}

/// Which login a Keychain item holds. Navidrome and Librarian are separate and never shared.
public enum SecretKind: String, Sendable, CaseIterable {
    case navidrome, librarian
}

public protocol SecretStore: Sendable {
    func credential(for kind: SecretKind) throws -> Credential?
    func save(_ credential: Credential, for kind: SecretKind) throws
    func delete(_ kind: SecretKind) throws
}

public enum SecretStoreError: Error, Equatable, Sendable {
    /// `OSStatus` only: never the account or the secret.
    case keychain(status: Int32)
    case corrupted
}

/// macOS Keychain, generic passwords, one item per login. Default access (only this app), this device only,
/// no iCloud sync, no shared access group.
public struct KeychainSecretStore: SecretStore {
    private let servicePrefix: String

    public init(servicePrefix: String = "app.discair") { self.servicePrefix = servicePrefix }

    private func query(_ kind: SecretKind) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: "\(servicePrefix).\(kind.rawValue)",
         kSecAttrAccount as String: "login",
         kSecAttrSynchronizable as String: false]
    }

    public func credential(for kind: SecretKind) throws -> Credential? {
        var q = query(kind)
        q[kSecReturnData as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitOne
        var out: CFTypeRef?
        let status = SecItemCopyMatching(q as CFDictionary, &out)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess else { throw SecretStoreError.keychain(status: status) }
        guard let data = out as? Data, let cred = try? JSONDecoder().decode(Credential.self, from: data) else {
            throw SecretStoreError.corrupted
        }
        return cred
    }

    public func save(_ credential: Credential, for kind: SecretKind) throws {
        let data = try JSONEncoder().encode(credential)
        let update = SecItemUpdate(query(kind) as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if update == errSecSuccess { return }
        guard update == errSecItemNotFound else { throw SecretStoreError.keychain(status: update) }
        var add = query(kind)
        add[kSecValueData as String] = data
        add[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        let status = SecItemAdd(add as CFDictionary, nil)
        guard status == errSecSuccess else { throw SecretStoreError.keychain(status: status) }
    }

    public func delete(_ kind: SecretKind) throws {
        let status = SecItemDelete(query(kind) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw SecretStoreError.keychain(status: status) }
    }
}

/// In-memory store for tests and previews.
public final class InMemorySecretStore: SecretStore, @unchecked Sendable {
    private let lock = NSLock()
    private var items: [SecretKind: Credential] = [:]
    public init() {}
    public func credential(for kind: SecretKind) throws -> Credential? { lock.withLock { items[kind] } }
    public func save(_ credential: Credential, for kind: SecretKind) throws { lock.withLock { items[kind] = credential } }
    public func delete(_ kind: SecretKind) throws { _ = lock.withLock { items.removeValue(forKey: kind) } }
}

private let secretParams = try! NSRegularExpression(
    pattern: "([?&;](?:u|t|s|p|password|token|salt)=)[^&\\s\"'<>]*", options: [.caseInsensitive])

/// Removes credential parameters from any text that may contain a Subsonic URL (errors, logs).
public func redactSecrets(_ text: String?) -> String {
    guard let text else { return "" }
    return secretParams.stringByReplacingMatches(
        in: text, range: NSRange(text.startIndex..., in: text), withTemplate: "$1***")
}
