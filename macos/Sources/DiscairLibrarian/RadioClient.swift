import DiscairCore
import Foundation

// Internet radio calls (docs/RADIO_PLAYBACK_PROPOSAL.md S2.4; macOS stage 2, slice S2-1 item 2). Every call is deployed on the
// server; none is added. The stream address (`playableURL`) is never put in a request path, an error or a log line here.

/// `GET /api/radio/settings`: the address Navidrome clients reach the app at. Shown read only on the Mac.
public struct RadioSettings: Decodable, Equatable, Sendable {
    /// Blank when none is saved.
    public let appURL: String

    enum CodingKeys: String, CodingKey { case appURL = "app_url" }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        appURL = ((try? c.decode(String.self, forKey: .appURL)) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
    }
    public init(appURL: String) { self.appURL = appURL }
}

/// The two sizes the server resizes logos to (128 in rows and menus, 512 for the bar, Now Playing and the system cover).
public enum RadioLogoSize: Int, Sendable { case small = 128, large = 512 }

/// The largest logo the server accepts (`MAX_UPLOAD_BYTES`); checked here so a big file is not sent only to be refused.
public let radioLogoUploadLimit = 2 * 1024 * 1024

extension LibrarianClient {
    private static func stationPath(_ id: String, _ tail: String = "") -> String { "api/radio/stations/\(enc(id))\(tail)" }

    /// A write whose answer the Mac does not need: only a refusal matters.
    private func radioWrite(_ method: String, _ path: String, body: Data?, contentType: String = "application/json") async throws {
        let (data, http) = try await authedSendPublic(method, path, body: body, contentType: contentType)
        if let failure = failurePublic(http, data) { throw failure }
    }

    /// `GET /api/radio/stations`, in the server's order. One unreadable row does not hide the rest.
    public func radioStations() async throws -> [RadioStation] {
        let (data, http) = try await authedSendPublic("GET", "api/radio/stations", body: nil)
        return try decodePublic(RadioStationsPayload.self, data, http).items
    }

    /// `GET /api/radio/stations/{id}/now`: the station's live song. An unreadable answer reads as unavailable, never as a song.
    public func radioNow(station: String) async throws -> RadioNow {
        let (data, http) = try await authedSendPublic("GET", Self.stationPath(station, "/now"), body: nil)
        if let failure = failurePublic(http, data) { throw failure }
        return (try? JSONDecoder().decode(RadioNow.self, from: data)) ?? .unavailable
    }

    /// `GET /api/radio/now`: the live song of every relayed station that has a listener, by station id.
    public func radioNowAll() async throws -> RadioNowAll {
        let (data, http) = try await authedSendPublic("GET", "api/radio/now", body: nil)
        return try decodePublic(RadioNowAll.self, data, http)
    }

    /// `PUT /api/radio/stations/{id}/favourite`.
    public func setRadioFavourite(station: String, on: Bool) async throws {
        let body = try JSONSerialization.data(withJSONObject: ["favourite": on])
        try await radioWrite("PUT", Self.stationPath(station, "/favourite"), body: body)
    }

    /// `PUT /api/radio/stations/{id}/tags`. The server keeps at most 10 tags of 24 characters; `StationRules` checks that first.
    public func setRadioTags(station: String, tags: [String]) async throws {
        let body = try JSONSerialization.data(withJSONObject: ["tags": tags])
        try await radioWrite("PUT", Self.stationPath(station, "/tags"), body: body)
    }

    /// `GET /api/radio/stations/{id}/logo?size=`. The server always answers with an image (a generated tile when none is found).
    public func radioLogo(station: String, size: RadioLogoSize = .small) async throws -> ArtworkImageData {
        let (data, http) = try await authedSendPublic("GET", Self.stationPath(station, "/logo?size=\(size.rawValue)"), body: nil)
        guard http.statusCode == 200 else {
            if let failure = failurePublic(http, data) { throw failure }
            throw DiscairError.server(status: http.statusCode, message: nil)
        }
        return ArtworkImageData(data: data, contentType: http.value(forHTTPHeaderField: "Content-Type") ?? "")
    }

    /// The cover of the live song: a server artwork path from `RadioNow.coverPath` (the owned-artwork route). Only paths under
    /// `/api/` are fetched, so a odd answer can never make the Mac ask another host.
    public func radioCover(path: String) async throws -> ArtworkImageData {
        guard path.hasPrefix("/api/"), !path.contains("://") else { throw DiscairError.server(status: 400, message: nil) }
        let (data, http) = try await authedSendPublic("GET", String(path.dropFirst()), body: nil)
        guard http.statusCode == 200 else {
            if let failure = failurePublic(http, data) { throw failure }
            throw DiscairError.server(status: http.statusCode, message: nil)
        }
        return ArtworkImageData(data: data, contentType: http.value(forHTTPHeaderField: "Content-Type") ?? "")
    }

    /// `GET /api/radio/scrobbling`. An unreadable body reads as off and not set up.
    public func radioScrobbling() async throws -> RadioScrobbling {
        let (data, http) = try await authedSendPublic("GET", "api/radio/scrobbling", body: nil)
        return try decodePublic(RadioScrobbling.self, data, http)
    }

    /// `PUT /api/radio/scrobbling`. The server refuses with a sentence when Last.fm is not set up; that sentence is thrown.
    public func setRadioScrobbling(_ on: Bool) async throws -> RadioScrobbling {
        let body = try JSONSerialization.data(withJSONObject: ["enabled": on])
        let (data, http) = try await authedSendPublic("PUT", "api/radio/scrobbling", body: body)
        return try decodePublic(RadioScrobbling.self, data, http)
    }

    /// `PUT /api/radio/stations/{id}/logo`: the owner's own image as the raw body (PNG, JPEG, GIF, WebP or ICO, up to 2 MB).
    public func uploadRadioLogo(station: String, data image: Data, contentType: String = "application/octet-stream") async throws {
        guard !image.isEmpty, image.count <= radioLogoUploadLimit else {
            throw DiscairError.server(status: 413, message: image.isEmpty ? "The image is empty." : "The image is too large.")
        }
        try await radioWrite("PUT", Self.stationPath(station, "/logo"), body: image, contentType: contentType)
    }

    /// `DELETE /api/radio/stations/{id}/logo`: clears the owner's image; the server resolves the logo again from its sources.
    public func resetRadioLogo(station: String) async throws {
        try await radioWrite("DELETE", Self.stationPath(station, "/logo"), body: nil)
    }

    /// `GET /api/radio/settings`.
    public func radioSettings() async throws -> RadioSettings {
        let (data, http) = try await authedSendPublic("GET", "api/radio/settings", body: nil)
        return try decodePublic(RadioSettings.self, data, http)
    }
}
