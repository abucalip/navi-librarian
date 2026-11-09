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

/// Which login a Keychain item holds. Navidrome, Librarian, ListenBrainz (token is the password, may be empty) and the SMB share are separate and never shared.
public enum SecretKind: String, Sendable, CaseIterable {
    case navidrome, librarian, smb, listenbrainz
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

/// macOS Keychain. **All logins live in one generic-password item** (`<prefix>.logins`, a JSON object of kind to login), so the
/// system asks about this app once, not once per login, and the answer is read once per run and kept in memory.
/// Default access (only this app), this device only, no iCloud sync, no shared access group.
/// Older builds kept one item per login (`<prefix>.navidrome`, `.librarian`, `.smb`); the first read moves them into the combined
/// item and deletes them. If the move fails nothing is deleted.
public final class KeychainSecretStore: SecretStore, @unchecked Sendable {
    /// The one store the app shares, so every model sees the same cache.
    public static let shared = KeychainSecretStore()

    private let servicePrefix: String
    private let lock = NSLock()
    private var cache: [String: Credential]?

    public init(servicePrefix: String = "app.discair") { self.servicePrefix = servicePrefix }

    private func query(service: String) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service,
         kSecAttrAccount as String: "login",
         kSecAttrSynchronizable as String: false]
    }
    private var combinedService: String { "\(servicePrefix).logins" }
    private func legacyService(_ kind: SecretKind) -> String { "\(servicePrefix).\(kind.rawValue)" }

    private func readItem(service: String) throws -> Data? {
        var q = query(service: service)
        q[kSecReturnData as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitOne
        var out: CFTypeRef?
        let status = SecItemCopyMatching(q as CFDictionary, &out)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess else { throw SecretStoreError.keychain(status: status) }
        guard let data = out as? Data else { throw SecretStoreError.corrupted }
        return data
    }

    private func writeItem(_ data: Data, service: String) throws {
        let update = SecItemUpdate(query(service: service) as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if update == errSecSuccess { return }
        guard update == errSecItemNotFound else { throw SecretStoreError.keychain(status: update) }
        var add = query(service: service)
        add[kSecValueData as String] = data
        add[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        let status = SecItemAdd(add as CFDictionary, nil)
        guard status == errSecSuccess else { throw SecretStoreError.keychain(status: status) }
    }

    private func deleteItem(service: String) throws {
        let status = SecItemDelete(query(service: service) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw SecretStoreError.keychain(status: status) }
    }

    /// Caller holds the lock.
    private func loadAll() throws -> [String: Credential] {
        if let cache { return cache }
        var all: [String: Credential]
        if let data = try readItem(service: combinedService) {
            guard let decoded = try? JSONDecoder().decode([String: Credential].self, from: data) else { throw SecretStoreError.corrupted }
            all = decoded
        } else {
            all = [:]
            var migrated: [SecretKind] = []
            for kind in SecretKind.allCases {
                guard let data = try readItem(service: legacyService(kind)) else { continue }
                guard let cred = try? JSONDecoder().decode(Credential.self, from: data) else { throw SecretStoreError.corrupted }
                all[kind.rawValue] = cred; migrated.append(kind)
            }
            if !migrated.isEmpty {
                try writeItem(JSONEncoder().encode(all), service: combinedService)   // written first: a failure below loses nothing
                for kind in migrated { try? deleteItem(service: legacyService(kind)) }
            }
        }
        cache = all
        return all
    }

    private func persist(_ all: [String: Credential]) throws {
        if all.isEmpty { try deleteItem(service: combinedService) }
        else { try writeItem(JSONEncoder().encode(all), service: combinedService) }
        cache = all
    }

    public func credential(for kind: SecretKind) throws -> Credential? {
        try lock.withLock { try loadAll()[kind.rawValue] }
    }

    public func save(_ credential: Credential, for kind: SecretKind) throws {
        try lock.withLock {
            var all = try loadAll()
            all[kind.rawValue] = credential
            try persist(all)
        }
    }

    public func delete(_ kind: SecretKind) throws {
        try lock.withLock {
            var all = try loadAll()
            guard all.removeValue(forKey: kind.rawValue) != nil else { return }
            try persist(all)
        }
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
