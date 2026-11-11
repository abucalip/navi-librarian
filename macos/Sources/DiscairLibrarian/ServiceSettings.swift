import DiscairCore
import Foundation

// Client side of the Librarian's connected-service routes (`docs/redesign.md` section 6, step M6). The ListenBrainz pair
// lives in `ListenBrainz.swift`. No route here ever returns a secret: each says only whether one is stored.

/// `GET /api/settings/navidrome`.
public struct NavidromeSettings: Decodable, Equatable, Sendable {
    public let url: String
    public let username: String
    public let passwordConfigured: Bool
    public let musicLibraryPath: String
    enum CodingKeys: String, CodingKey {
        case url = "navidrome_url", username, passwordConfigured = "password_configured", musicLibraryPath = "music_library_path"
    }
    public init(url: String, username: String, passwordConfigured: Bool, musicLibraryPath: String = "") {
        self.url = url; self.username = username; self.passwordConfigured = passwordConfigured; self.musicLibraryPath = musicLibraryPath
    }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        url = (try? c.decode(String.self, forKey: .url)) ?? ""
        username = (try? c.decode(String.self, forKey: .username)) ?? ""
        passwordConfigured = (try? c.decode(Bool.self, forKey: .passwordConfigured)) ?? false
        musicLibraryPath = (try? c.decode(String.self, forKey: .musicLibraryPath)) ?? ""
    }
}

/// `GET /api/settings/lastfm`.
public struct LastFMSettings: Decodable, Equatable, Sendable {
    public let apiKeyConfigured: Bool
    public let username: String
    enum CodingKeys: String, CodingKey { case apiKeyConfigured = "api_key_configured", username }
    public init(apiKeyConfigured: Bool, username: String = "") { self.apiKeyConfigured = apiKeyConfigured; self.username = username }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        apiKeyConfigured = (try? c.decode(Bool.self, forKey: .apiKeyConfigured)) ?? false
        username = (try? c.decode(String.self, forKey: .username)) ?? ""
    }
}

/// `GET /api/settings/slskd`.
public struct SlskdSettings: Decodable, Equatable, Sendable {
    public let url: String
    public let apiKeyConfigured: Bool
    public let downloadsPath: String
    public let musicLibraryPath: String
    public let qualityPriority: [String]
    enum CodingKeys: String, CodingKey {
        case url = "slskd_url", apiKeyConfigured = "api_key_configured", downloadsPath = "slskd_downloads_path"
        case musicLibraryPath = "music_library_path", qualityPriority = "quality_priority"
    }
    public init(url: String, apiKeyConfigured: Bool, downloadsPath: String = "", musicLibraryPath: String = "", qualityPriority: [String] = []) {
        self.url = url; self.apiKeyConfigured = apiKeyConfigured; self.downloadsPath = downloadsPath
        self.musicLibraryPath = musicLibraryPath; self.qualityPriority = qualityPriority
    }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        url = (try? c.decode(String.self, forKey: .url)) ?? ""
        apiKeyConfigured = (try? c.decode(Bool.self, forKey: .apiKeyConfigured)) ?? false
        downloadsPath = (try? c.decode(String.self, forKey: .downloadsPath)) ?? ""
        musicLibraryPath = (try? c.decode(String.self, forKey: .musicLibraryPath)) ?? ""
        qualityPriority = (try? c.decode([String].self, forKey: .qualityPriority)) ?? []
    }
}

/// `GET /api/settings/discogs`. `source` is `settings`, `environment` or `none`.
public struct DiscogsSettings: Decodable, Equatable, Sendable {
    public let tokenConfigured: Bool
    public let source: String
    enum CodingKeys: String, CodingKey { case tokenConfigured = "token_configured", source }
    public init(tokenConfigured: Bool, source: String = "none") { self.tokenConfigured = tokenConfigured; self.source = source }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        tokenConfigured = (try? c.decode(Bool.self, forKey: .tokenConfigured)) ?? false
        source = (try? c.decode(String.self, forKey: .source)) ?? "none"
    }
}

/// The answer of any `POST /api/settings/{service}/test`. These routes answer 200 even when the service does not, so a failure
/// is `ok == false` with a `status`: `connected`, `not_configured`, `authentication_failed`, `connection_failed` or `not_found`.
/// The Discogs route sends `error` instead of `status` and `message`; this type folds that into the same fields.
public struct ServiceTestResult: Decodable, Equatable, Sendable {
    public let ok: Bool
    public let status: String
    public let message: String

    public init(ok: Bool, status: String, message: String = "") { self.ok = ok; self.status = status; self.message = message }
    enum CodingKeys: String, CodingKey { case ok, status, message, error }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        ok = (try? c.decode(Bool.self, forKey: .ok)) ?? false
        let text = (try? c.decode(String.self, forKey: .message)) ?? (try? c.decode(String.self, forKey: .error)) ?? ""
        message = text
        if let status = try? c.decode(String.self, forKey: .status) { self.status = status }
        else if ok { status = "connected" }
        else if text.localizedCaseInsensitiveContains("rejected") { status = "authentication_failed" }
        else if text.localizedCaseInsensitiveContains("add a") { status = "not_configured" }
        else { status = "connection_failed" }
    }
}

/// `GET /api/health`: 200 when Navidrome answers an authenticated ping through the Librarian, 503 otherwise (thrown).
public struct LibrarianHealth: Decodable, Equatable, Sendable {
    public let status: String
    public let service: String?
    public let message: String?
    public var isOK: Bool { status == "ok" }
}

/// `GET /api/capabilities`: what the server can serve right now. Only the fields the Services screen reads.
public struct ServerCapabilities: Decodable, Equatable, Sendable {
    /// `none`, `partial` or `broad`; anything else reads as `none`.
    public let graphCoverage: String
    public let sonicAvailable: Bool
    public let listenBrainzConnected: Bool
    public let availableFeatures: Set<String>
    /// The contract version and the data generation the server is on, for the Librarian row's "Server contract" line.
    public let contractVersion: Int?
    public let generation: Int?

    enum CodingKeys: String, CodingKey {
        case contractVersion = "contract_version", generation
        case graphCoverage = "graph_coverage", sonicAvailable = "sonic_available", listenBrainzConnected = "listenbrainz_connected", features
    }
    private struct Feature: Decodable { let available: Bool? }

    public init(graphCoverage: String = "none", sonicAvailable: Bool = false, listenBrainzConnected: Bool = false, availableFeatures: Set<String> = [],
                contractVersion: Int? = nil, generation: Int? = nil) {
        self.contractVersion = contractVersion; self.generation = generation
        self.graphCoverage = graphCoverage; self.sonicAvailable = sonicAvailable
        self.listenBrainzConnected = listenBrainzConnected; self.availableFeatures = availableFeatures
    }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        contractVersion = try? c.decode(Int.self, forKey: .contractVersion)
        generation = try? c.decode(Int.self, forKey: .generation)
        let coverage = (try? c.decode(String.self, forKey: .graphCoverage)) ?? "none"
        graphCoverage = ["none", "partial", "broad"].contains(coverage) ? coverage : "none"
        sonicAvailable = (try? c.decode(Bool.self, forKey: .sonicAvailable)) ?? false
        listenBrainzConnected = (try? c.decode(Bool.self, forKey: .listenBrainzConnected)) ?? false
        let features = (try? c.decode([String: Feature].self, forKey: .features)) ?? [:]
        availableFeatures = Set(features.filter { $0.value.available == true }.keys)
    }
}

extension LibrarianClient {
    public func navidromeSettings() async throws -> NavidromeSettings { try await read("api/settings/navidrome") }
    public func lastFMSettings() async throws -> LastFMSettings { try await read("api/settings/lastfm") }
    public func slskdSettings() async throws -> SlskdSettings { try await read("api/settings/slskd") }
    public func discogsSettings() async throws -> DiscogsSettings { try await read("api/settings/discogs") }

    public func testNavidrome() async throws -> ServiceTestResult { try await probe("api/settings/navidrome/test") }
    public func testLastFM() async throws -> ServiceTestResult { try await probe("api/settings/lastfm/test") }
    public func testSlskd() async throws -> ServiceTestResult { try await probe("api/settings/slskd/test") }
    public func testDiscogs() async throws -> ServiceTestResult { try await probe("api/settings/discogs/test") }

    public func health() async throws -> LibrarianHealth { try await read("api/health") }
    public func capabilities() async throws -> ServerCapabilities { try await read("api/capabilities") }

    /// `PUT /api/settings/navidrome`. A blank password keeps the saved one. The server's own sentence comes back as the error.
    public func saveNavidrome(url: String, username: String, password: String = "") async throws {
        try await write("api/settings/navidrome", ["navidrome_url": url, "username": username, "password": password])
    }

    /// `PUT /api/settings/lastfm`. A blank key keeps the saved one; a `nil` username leaves it unchanged.
    public func saveLastFM(apiKey: String = "", username: String? = nil) async throws {
        var body: [String: Any] = ["api_key": apiKey]
        if let username { body["username"] = username }
        try await write("api/settings/lastfm", body)
    }

    /// `PUT /api/settings/slskd`. The server resets the quality order when it is missing, so the current order is required.
    /// The two folders are sent only when given; the server leaves a folder it was not sent as it is.
    public func saveSlskd(url: String, apiKey: String = "", qualityPriority: [String], downloadsPath: String? = nil, musicLibraryPath: String? = nil) async throws {
        var body: [String: Any] = ["slskd_url": url, "api_key": apiKey, "quality_priority": qualityPriority]
        if let downloadsPath { body["slskd_downloads_path"] = downloadsPath }
        if let musicLibraryPath { body["music_library_path"] = musicLibraryPath }
        try await write("api/settings/slskd", body)
    }

    /// `PUT /api/settings/discogs`. An empty token clears the saved one.
    public func saveDiscogs(token: String) async throws { try await write("api/settings/discogs", ["token": token]) }

    private func read<T: Decodable>(_ path: String) async throws -> T {
        let (data, http) = try await authedSendPublic("GET", path, body: nil)
        return try decodePublic(T.self, data, http)
    }

    private func probe(_ path: String) async throws -> ServiceTestResult {
        let (data, http) = try await authedSendPublic("POST", path, body: nil)
        return try decodePublic(ServiceTestResult.self, data, http)
    }

    private func write(_ path: String, _ object: [String: Any]) async throws {
        let body = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        let (data, http) = try await authedSendPublic("PUT", path, body: body)
        if let failure = failurePublic(http, data) { throw failure }
    }
}
