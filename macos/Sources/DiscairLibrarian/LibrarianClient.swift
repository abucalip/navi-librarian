import DiscairCore
import Foundation

/// A dashboard pick (`GET /api/dashboard-picks`). Only fields present in
/// `android/contract-fixtures/librarian/dashboard_picks.json` are read; unknown fields are ignored.
public struct DashboardPick: Codable, Equatable, Sendable {
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

/// One discovery list (`GET /api/discovery/{list}`). Items share the dashboard pick shape; an empty list carries the
/// server's own `message` ("No saved list yet…"), which is shown as it is.
public struct DiscoveryList: Decodable, Equatable, Sendable {
    public let list: String?
    public let items: [DashboardPick]
    public let message: String?
    public let generatedAt: Double?

    enum CodingKeys: String, CodingKey { case list, items, message; case generatedAt = "generated_at" }

    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        list = try c.decodeIfPresent(String.self, forKey: .list)
        items = try c.decodeIfPresent([DashboardPick].self, forKey: .items) ?? []
        message = try c.decodeIfPresent(String.self, forKey: .message)
        generatedAt = try c.decodeIfPresent(Double.self, forKey: .generatedAt)
    }
}

/// Librarian client (ANDROID_CLIENT_CONTRACT 4.1 and 5.2): `GET /api/auth/status`, `POST /api/auth/login`,
/// `GET /api/dashboard-picks`. The session cookie lives in the transport's in-memory jar.
/// Any 401 triggers one re-login with the stored credential; a 429 is reported and never retried.
public struct AlbumDescription: Decodable, Equatable, Sendable {
    public let paragraphs: [String]
    public let source: String?
    public let url: String?
    public let license: String?
    public init(paragraphs: [String], source: String?, url: String?, license: String?) {
        self.paragraphs = paragraphs; self.source = source; self.url = url; self.license = license
    }
}

public struct AlbumReview: Decodable, Equatable, Sendable {
    public let source: String
    public let quote: String
    public let url: String
    public init(source: String, quote: String, url: String) { self.source = source; self.quote = quote; self.url = url }
}

public struct AlbumReviews: Decodable, Equatable, Sendable {
    public let reviews: [AlbumReview]
    public let retryable: Bool?
}

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
        let (data, http) = try await authedSend("GET", "api/dashboard-picks?count=\(min(max(count, 1), 30))", body: nil)
        return try decode(DashboardPicks.self, data, http).items
    }

    /// A saved discovery list, in the order the server gives it (`personal`, `classics`, `new_releases`, `for_me`).
    public func discoveryList(_ list: String, count: Int = 20) async throws -> DiscoveryList {
        let (data, http) = try await authedSend("GET", "api/discovery/\(list)?count=\(min(max(count, 1), 150))", body: nil)
        return try decode(DiscoveryList.self, data, http)
    }

    /// Builds a list that has no saved copy yet (the Android "Build this list" button).
    public func refreshDiscoveryList(_ list: String, count: Int = 20) async throws {
        let (data, http) = try await authedSend("POST", "api/discovery/\(list)/refresh", body: try json(["count": min(max(count, 1), 20)]))
        if let failure = failure(http, data) { throw failure }
    }

    // MARK: Acquisition and feedback (Android contract 5.3, macOS contract section 5)

    /// Get an album: the Librarian searches and queues the best source automatically (`auto_queue: true`).
    /// The result is the server's answer; nothing here assumes success.
    public func acquire(artist: String, album: String, metadata: [String: String] = [:]) async throws -> AcquireResult {
        let body = try json(["artist": artist, "album": album, "metadata": metadata, "auto_queue": true])
        let (data, http) = try await authedSend("POST", "api/acquire", body: body)
        return try decode(AcquireResult.self, data, http)
    }

    /// Get one song of an album; the best clear file is chosen by the server.
    public func acquireTrack(artist: String, album: String, title: String, trackNumber: Int? = nil, year: Int? = nil,
                             metadata: [String: String] = [:]) async throws -> AcquireResult {
        var payload: [String: Any] = ["artist": artist, "album": album, "title": title]
        if let trackNumber, trackNumber >= 1 { payload["track_number"] = trackNumber }
        if let year { payload["year"] = year }
        if !metadata.isEmpty { payload["metadata"] = metadata }
        let (data, http) = try await authedSend("POST", "api/acquire/track", body: try json(payload))
        return try decode(AcquireResult.self, data, http)
    }

    /// A snapshot of every job. The app polls this while a screen that shows jobs is visible (the SSE stream is a later step).
    public func acquisitions() async throws -> [Acquisition] {
        let (data, http) = try await authedSend("GET", "api/acquisitions", body: nil)
        return try decode(AcquisitionsPayload.self, data, http).acquisitions
    }

    /// Ask the server to switch the download source of a job that is downloading (409 when it is not).
    public func skipSource(artist: String, album: String) async throws {
        let (data, http) = try await authedSend("POST", "api/acquisitions/skip", body: try json(["artist": artist, "album": album]))
        if let failure = failure(http, data) { throw failure }
    }

    /// Dismiss a job. **This deletes the job's downloaded files on the server**, so callers confirm first.
    public func dismissAcquisition(artist: String, album: String) async throws -> String? {
        let (data, http) = try await authedSend("POST", "api/acquisitions/dismiss", body: try json(["artist": artist, "album": album]))
        return try decode(AcquireResult.self, data, http).message
    }

    /// Save, Not for me (`dismiss`), Never suggest (`dismiss_artist`) and removal from For me.
    public func feedback(artist: String, album: String, action: FeedbackAction, metadata: [String: String] = [:]) async throws {
        let body = try json(["artist": artist, "album": album, "action": action.rawValue, "metadata": metadata])
        let (data, http) = try await authedSend("POST", "api/discovery/feedback", body: body)
        if let failure = failure(http, data) { throw failure }
    }

    // MARK: Album page text (the web album page's Info and Reviews tabs)

    /// The album's description: Apple Music notes, else the Wikipedia lead, else no paragraphs.
    public func albumDescription(artist: String, album: String) async throws -> AlbumDescription {
        let (data, http) = try await authedSend("GET", "api/album-description?" + Self.query(artist, album), body: nil)
        return try decode(AlbumDescription.self, data, http)
    }

    /// Up to three outlets' summary lines with links. `retryable` means an outlet failed or was slow.
    public func albumReviews(artist: String, album: String) async throws -> AlbumReviews {
        let (data, http) = try await authedSend("GET", "api/album-reviews?" + Self.query(artist, album), body: nil)
        return try decode(AlbumReviews.self, data, http)
    }

    static func query(_ artist: String, _ album: String) -> String {
        var allowed = CharacterSet.urlQueryAllowed
        allowed.remove(charactersIn: "&+=#?/")
        func enc(_ s: String) -> String { s.addingPercentEncoding(withAllowedCharacters: allowed) ?? "" }
        return "artist=\(enc(String(artist.prefix(180))))&album=\(enc(String(album.prefix(180))))"
    }

    // MARK: Related artists and albums (the web album and artist pages)

    /// The related parts of an album page (`GET /api/albums/{artist_key}/{album_key}`, JSON form): similar artists, similar
    /// albums the library lacks, and the track list for an album the library does not hold.
    public func albumPage(artist: String, album: String) async throws -> AlbumPageRelated {
        let path = "api/albums/\(Self.key(artist))/\(Self.key(album))?" + Self.nameQuery(artist: artist, name: album)
        let (data, http) = try await authedSend("GET", path, body: nil)
        return try decode(AlbumPageEnvelope.self, data, http).related
    }

    /// Similar artists for an artist page (`GET /api/artists/{key}`, JSON form). The server marks which the library holds.
    public func artistSimilar(name: String, id: String? = nil) async throws -> [SimilarArtistEntry] {
        var q = Self.nameQuery(artist: nil, name: name)
        if let id { q += "&id=" + Self.enc(id) }
        let (data, http) = try await authedSend("GET", "api/artists/\(Self.key(name))?" + q, body: nil)
        return try decode(ArtistPageEnvelope.self, data, http).sections.similar?.items ?? []
    }

    /// An artist photo (`GET /api/artist-image`), found by the server from public sources. Only https addresses.
    public func artistImageURL(name: String) async throws -> URL? {
        struct Lookup: Decodable { let artworkUrl: String?; enum CodingKeys: String, CodingKey { case artworkUrl = "artwork_url" } }
        let (data, http) = try await authedSend("GET", "api/artist-image?name=" + Self.enc(String(name.prefix(180))), body: nil)
        guard let s = try decode(Lookup.self, data, http).artworkUrl, let u = URL(string: s), u.scheme == "https" else { return nil }
        return u
    }

    /// The server's page key for a name: lower case, letters and digits, a leading "the" dropped ("The Beatles" is "beatles").
    static func key(_ name: String) -> String {
        var s = name.folding(options: .diacriticInsensitive, locale: nil).lowercased()
        s = String(s.map { $0.isLetter || $0.isNumber ? $0 : " " })
        var words = s.split(separator: " ").map(String.init)
        if words.count > 1, words.first == "the" { words.removeFirst() }
        let k = words.joined(separator: " ")
        return k.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed.subtracting(CharacterSet(charactersIn: "/"))) ?? ""
    }

    static func enc(_ s: String) -> String {
        var allowed = CharacterSet.urlQueryAllowed
        allowed.remove(charactersIn: "&+=#?/")
        return s.addingPercentEncoding(withAllowedCharacters: allowed) ?? ""
    }

    static func nameQuery(artist: String?, name: String) -> String {
        var parts: [String] = []
        if let artist { parts.append("artist=" + enc(String(artist.prefix(180)))) }
        parts.append("name=" + enc(String(name.prefix(180))))
        return parts.joined(separator: "&")
    }

    /// A cover for an album the library does not hold (`GET /api/artwork`), found by the server from public sources.
    /// Nil when the server has none. Only https addresses are returned.
    public func artworkURL(artist: String, album: String) async throws -> URL? {
        struct Lookup: Decodable { let artworkUrl: String?; enum CodingKeys: String, CodingKey { case artworkUrl = "artwork_url" } }
        let (data, http) = try await authedSend("GET", "api/artwork?" + Self.query(artist, album), body: nil)
        let found = try decode(Lookup.self, data, http).artworkUrl
        guard let found, let url = URL(string: found), url.scheme == "https" else { return nil }
        return url
    }

    // MARK: Plumbing

    private func json(_ object: [String: Any]) throws -> Data {
        try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
    }

    /// One send with a single re-login on 401 (the session cookie lives in memory only).
    private func authedSend(_ method: String, _ path: String, body: Data?) async throws -> (Data, HTTPURLResponse) {
        var (data, http) = try await send(method, path, body: body)
        if http.statusCode == 401 {
            try await login()
            (data, http) = try await send(method, path, body: body)
        }
        return (data, http)
    }

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
