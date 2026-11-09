import Foundation

/// Which network a profile is for. Probe order is LAN, then Tailscale, then anything else.
public enum ProfileNetwork: String, Codable, Sendable, CaseIterable {
    case lan, tailscale, other

    var probeRank: Int {
        switch self { case .lan: 0; case .tailscale: 1; case .other: 2 }
    }

    /// Suggested network for a pair of addresses (the owner can change it).
    public static func infer(librarian: URL, navidrome: URL) -> ProfileNetwork {
        let hosts = [librarian.host, navidrome.host].compactMap { $0 }
        if hosts.contains(where: AddressPolicy.isTailscaleHost) { return .tailscale }
        if hosts.allSatisfy({ AddressPolicy.isPlainHTTPAllowed(host: $0) }) { return .lan }
        return .other
    }
}

/// A named pair of server addresses. Holds no secrets, so it can be stored as plain JSON.
public struct Profile: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID
    public var name: String
    public var network: ProfileNetwork
    public let librarianURL: URL
    public let navidromeURL: URL
    /// The public ListenBrainz username the server reads for this profile ("" when none). Not a secret; the token is in the Keychain.
    public var listenBrainzUsername: String

    /// Letters, digits, dot, underscore and hyphen, 1 to 80: the same rule the server applies.
    public static func isValidListenBrainzUsername(_ value: String) -> Bool {
        value.range(of: #"^[A-Za-z0-9_.-]{1,80}$"#, options: .regularExpression) != nil
    }

    public init(id: UUID = UUID(), name: String, network: ProfileNetwork? = nil,
                librarianURL: String, navidromeURL: String, listenBrainzUsername: String = "") throws {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { throw ProfileError.emptyName }
        let lib = try AddressPolicy.validate(librarianURL)
        let navi = try AddressPolicy.validate(navidromeURL)
        let lb = listenBrainzUsername.trimmingCharacters(in: .whitespacesAndNewlines)
        guard lb.isEmpty || Self.isValidListenBrainzUsername(lb) else { throw ProfileError.invalidListenBrainzUsername }
        self.listenBrainzUsername = lb
        self.id = id
        self.name = trimmed
        self.librarianURL = lib
        self.navidromeURL = navi
        self.network = network ?? ProfileNetwork.infer(librarian: lib, navidrome: navi)
    }

    /// Re-checks the rules after decoding stored JSON (a hand-edited file must not bypass them).
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(
            id: c.decode(UUID.self, forKey: .id),
            name: c.decode(String.self, forKey: .name),
            network: c.decode(ProfileNetwork.self, forKey: .network),
            librarianURL: c.decode(URL.self, forKey: .librarianURL).absoluteString,
            navidromeURL: c.decode(URL.self, forKey: .navidromeURL).absoluteString,
            listenBrainzUsername: (try? c.decodeIfPresent(String.self, forKey: .listenBrainzUsername)) ?? ""
        )
    }

    /// Either server is plain http: the UI shows the "unencrypted" badge.
    public var isUnencrypted: Bool {
        AddressPolicy.isUnencrypted(librarianURL) || AddressPolicy.isUnencrypted(navidromeURL)
    }

    /// Either server is a Tailscale address (used to tell "Tailscale not connected" from "unreachable").
    public var usesTailscaleAddress: Bool {
        [librarianURL, navidromeURL].contains { $0.host.map(AddressPolicy.isTailscaleHost) ?? false }
    }
}

public enum ProfileError: Error, Equatable, Sendable {
    case emptyName
    case duplicateName
    case notFound
    case invalidListenBrainzUsername
}

/// The stored list plus the manual override. Plain JSON, no secrets.
public struct ProfileList: Codable, Equatable, Sendable {
    public private(set) var profiles: [Profile]
    /// When set, this profile is used without probing.
    public var overrideID: UUID?

    public init(profiles: [Profile] = [], overrideID: UUID? = nil) {
        self.profiles = profiles
        self.overrideID = overrideID
    }

    public mutating func add(_ profile: Profile) throws {
        guard !profiles.contains(where: { $0.name.caseInsensitiveCompare(profile.name) == .orderedSame }) else {
            throw ProfileError.duplicateName
        }
        profiles.append(profile)
    }

    public mutating func setListenBrainzUsername(_ value: String, for id: UUID) {
        guard let i = profiles.firstIndex(where: { $0.id == id }) else { return }
        profiles[i].listenBrainzUsername = value
    }

    public mutating func remove(id: UUID) {
        profiles.removeAll { $0.id == id }
        if overrideID == id { overrideID = nil }
    }

    /// LAN first, then Tailscale, then others; ties keep the owner's order.
    public var probeOrder: [Profile] {
        profiles.enumerated()
            .sorted { ($0.element.network.probeRank, $0.offset) < ($1.element.network.probeRank, $1.offset) }
            .map(\.element)
    }
}

/// Reads and writes the profile list as JSON (the app passes a file in Application Support).
public struct ProfileStore: Sendable {
    public let fileURL: URL
    public init(fileURL: URL) { self.fileURL = fileURL }

    public func load() throws -> ProfileList {
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return ProfileList() }
        return try JSONDecoder().decode(ProfileList.self, from: Data(contentsOf: fileURL))
    }

    public func save(_ list: ProfileList) throws {
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        try FileManager.default.createDirectory(at: fileURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        try enc.encode(list).write(to: fileURL, options: .atomic)
    }
}
