import Foundation

/// `GET /api/settings/listenbrainz`: the saved public username and whether a token is stored. The token is never returned.
public struct ListenBrainzSettings: Decodable, Equatable, Sendable {
    public let username: String
    public let tokenConfigured: Bool
    enum CodingKeys: String, CodingKey { case username; case tokenConfigured = "token_configured" }

    public init(username: String, tokenConfigured: Bool) { self.username = username; self.tokenConfigured = tokenConfigured }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        username = (try? c.decode(String.self, forKey: .username)) ?? ""
        tokenConfigured = (try? c.decode(Bool.self, forKey: .tokenConfigured)) ?? false
    }
}

/// `POST /api/settings/listenbrainz/test`: whether the server can read the saved profile.
public struct ListenBrainzTestResult: Decodable, Equatable, Sendable {
    public let ok: Bool
    public let status: String
    public let message: String
}

extension LibrarianClient {
    public func listenBrainzSettings() async throws -> ListenBrainzSettings {
        let (data, http) = try await authedSendPublic("GET", "api/settings/listenbrainz", body: nil)
        return try decodePublic(ListenBrainzSettings.self, data, http)
    }

    /// `PUT /api/settings/listenbrainz`. A blank token keeps the one the server already holds. The server validates both fields
    /// and answers 400 with its own sentence, which `DiscairError` carries.
    public func saveListenBrainz(username: String, token: String = "") async throws {
        let body = try JSONSerialization.data(withJSONObject: ["username": username, "token": token], options: [.sortedKeys])
        let (data, http) = try await authedSendPublic("PUT", "api/settings/listenbrainz", body: body)
        if let failure = failurePublic(http, data) { throw failure }
    }

    public func testListenBrainz() async throws -> ListenBrainzTestResult {
        let (data, http) = try await authedSendPublic("POST", "api/settings/listenbrainz/test", body: nil)
        return try decodePublic(ListenBrainzTestResult.self, data, http)
    }
}
