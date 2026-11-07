import Foundation

/// One rule inside a server rule set (`docs/SERVER_V2_CONTRACT.md`, "Smart playlists"). Values stay strings, as on the server.
public struct ServerSmartRule: Codable, Equatable, Sendable {
    public let field: String
    public let op: String
    public let value: String
    public init(field: String, op: String, value: String) { self.field = field; self.op = op; self.value = value }
}

/// A rule set as the server stores it. `field` may name insight data this client cannot show yet (`obscurity_band`, `in_lens`).
public struct ServerSmartPlaylist: Codable, Equatable, Sendable {
    public let ruleID: String
    public let name: String
    public let match: String
    public let rules: [ServerSmartRule]
    public let order: String
    /// 25 to 250, or nil for no limit.
    public let limit: Int?
    public let createdAt: Double?
    public let updatedAt: Double?

    enum CodingKeys: String, CodingKey {
        case ruleID = "rule_id", name, match, rules, order, limit, createdAt = "created_at", updatedAt = "updated_at"
    }

    public init(ruleID: String, name: String, match: String, rules: [ServerSmartRule], order: String, limit: Int?,
                createdAt: Double? = nil, updatedAt: Double? = nil) {
        self.ruleID = ruleID; self.name = name; self.match = match; self.rules = rules; self.order = order; self.limit = limit
        self.createdAt = createdAt; self.updatedAt = updatedAt
    }
}

public struct ServerSmartPlaylists: Decodable, Equatable, Sendable {
    public let playlists: [ServerSmartPlaylist]
    public let total: Int
}

extension LibrarianClient {
    /// `GET /api/playlists/smart`: every saved rule set, oldest first.
    public func smartPlaylists() async throws -> [ServerSmartPlaylist] {
        let (data, http) = try await authedSendPublic("GET", "api/playlists/smart", body: nil)
        return try decodePublic(ServerSmartPlaylists.self, data, http).playlists
    }

    /// `PUT /api/playlists/smart/{rule_id}`: create or replace. The id is lowercased, so a retry is idempotent.
    /// Invalid content comes back as an error and nothing is stored.
    public func putSmartPlaylist(_ p: ServerSmartPlaylist) async throws {
        struct Body: Encodable { let name: String; let match: String; let rules: [ServerSmartRule]; let order: String; let limit: Int? }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        // `limit` must be sent as null (not omitted) so "no limit" replaces an earlier limit.
        var object = try JSONSerialization.jsonObject(with: encoder.encode(Body(name: p.name, match: p.match, rules: p.rules, order: p.order, limit: p.limit))) as! [String: Any]
        if p.limit == nil { object["limit"] = NSNull() }
        let body = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        let (data, http) = try await authedSendPublic("PUT", "api/playlists/smart/\(p.ruleID.lowercased())", body: body)
        if let failure = failurePublic(http, data) { throw failure }
    }

    /// `DELETE /api/playlists/smart/{rule_id}`. A rule set that is already gone counts as deleted.
    public func deleteSmartPlaylist(id: String) async throws {
        let (data, http) = try await authedSendPublic("DELETE", "api/playlists/smart/\(id.lowercased())", body: nil)
        if http.statusCode == 404 { return }
        if let failure = failurePublic(http, data) { throw failure }
    }
}
