import DiscairCore
import Foundation

/// A dashboard pick (`GET /api/dashboard-picks`). Only fields present in
/// `android/contract-fixtures/librarian/dashboard_picks.json` are read; unknown fields are ignored.
public struct DashboardPick: Decodable, Equatable, Sendable {
    public let artist: String
    public let album: String
    public let reason: String?
    public let genres: [String]?
    public let suggestedTracks: [String]?
    public let similarTo: [String]?
    public let dashboardCategory: String?
    public let discoveryCategory: String?

    enum CodingKeys: String, CodingKey {
        case artist, album, reason, genres
        case suggestedTracks = "suggested_tracks"
        case similarTo = "similar_to"
        case dashboardCategory = "dashboard_category"
        case discoveryCategory = "discovery_category"
    }
}

public struct DashboardPicks: Decodable, Equatable, Sendable {
    public let items: [DashboardPick]
}

/// Librarian client (ANDROID_CLIENT_CONTRACT 4.1 and 5.2): `GET /api/auth/status`, `POST /api/auth/login`,
/// `GET /api/dashboard-picks`. The session cookie lives in the transport's in-memory jar.
/// Any 401 triggers one re-login with the stored credential; a 429 is reported and never retried.
public struct LibrarianClient: Sendable {
    private let base: URL
    private let credential: Credential
    private let transport: any HTTPTransport
    private let tailscaleHint: @Sendable () -> Bool

    public init(baseURL: URL, credential: Credential,
                transport: any HTTPTransport = URLSessionTransport(keepCookies: true),
                tailscaleHint: @escaping @Sendable () -> Bool = { false }) throws {
        self.base = try AddressPolicy.validate(baseURL)
        self.credential = credential
        self.transport = transport
        self.tailscaleHint = tailscaleHint
    }

    /// `true` when the owner still has to create the account in the web UI (the app never does this).
    public func setupRequired() async throws -> Bool {
        struct Status: Decodable { let setup_required: Bool }
        let (data, http) = try await send("GET", "api/auth/status", body: nil)
        return try decode(Status.self, data, http).setup_required
    }

    public func login() async throws {
        struct Body: Encodable { let username: String; let password: String }
        let body = try credential.withPassword { try JSONEncoder().encode(Body(username: credential.username, password: $0)) }
        let (data, http) = try await send("POST", "api/auth/login", body: body)
        if let failure = failure(http, data) { throw failure }
    }

    public func dashboardPicks(count: Int = 10) async throws -> [DashboardPick] {
        let path = "api/dashboard-picks?count=\(min(max(count, 1), 30))"
        var (data, http) = try await send("GET", path, body: nil)
        if http.statusCode == 401 {
            try await login()
            (data, http) = try await send("GET", path, body: nil)
        }
        return try decode(DashboardPicks.self, data, http).items
    }

    // MARK: Plumbing

    private func send(_ method: String, _ path: String, body: Data?) async throws -> (Data, HTTPURLResponse) {
        let parts = path.split(separator: "?", maxSplits: 1).map(String.init)
        var comps = URLComponents(url: base, resolvingAgainstBaseURL: false)!
        comps.path = (comps.path.hasSuffix("/") ? comps.path : comps.path + "/") + parts[0]
        if parts.count > 1 { comps.percentEncodedQuery = parts[1] }
        var request = URLRequest(url: comps.url!)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        do { return try await transport.send(request) }
        catch { throw ErrorMapping.map(error, tailscaleHint: tailscaleHint()) }
    }

    /// FastAPI errors are `{"detail": "..."}`.
    private func failure(_ http: HTTPURLResponse, _ data: Data) -> DiscairError? {
        struct Detail: Decodable { let detail: String? }
        let message = (try? JSONDecoder().decode(Detail.self, from: data))?.detail
        return ErrorMapping.map(status: http.statusCode, message: message)
    }

    private func decode<T: Decodable>(_ type: T.Type, _ data: Data, _ http: HTTPURLResponse) throws -> T {
        if let failure = failure(http, data) { throw failure }
        do { return try JSONDecoder().decode(T.self, from: data) }
        catch { throw DiscairError.server(status: http.statusCode, message: "That address did not answer like the Librarian.") }
    }
}
