import Foundation

/// A "Request update" ask the server has queued for its worker (`/api/knowledge/update-store`).
public struct StoreUpdate: Decodable, Equatable, Sendable {
    /// queued, running, done, failed or none.
    public let state: String
    public let message: String?
    public var finished: Bool { state == "done" || state == "failed" }
    public init(state: String, message: String? = nil) { self.state = state; self.message = message }
}

extension LibrarianClient {
    /// Asks the server's worker to add an artist or album to its knowledge store (`POST`). `subject` is "artist" or "album"; `id` is the Navidrome id.
    public func requestStoreUpdate(subject: String, id: String) async throws -> StoreUpdate {
        let body = try JSONSerialization.data(withJSONObject: ["subject": subject, "navidrome_id": id])
        let (data, http) = try await authedSendPublic("POST", "api/knowledge/update-store", body: body)
        return try decodePublic(StoreUpdate.self, data, http)
    }

    /// Where that request stands (`GET`).
    public func storeUpdateStatus(subject: String, id: String) async throws -> StoreUpdate {
        let (data, http) = try await authedSendPublic("GET", "api/knowledge/update-store?subject=\(subject)&navidrome_id=\(Self.enc(id))", body: nil)
        return try decodePublic(StoreUpdate.self, data, http)
    }
}
