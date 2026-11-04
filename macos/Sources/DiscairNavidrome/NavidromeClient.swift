import DiscairCore
import Foundation

/// Direct Navidrome access over the Subsonic API (ANDROID_CLIENT_CONTRACT 4.2 and 5.1).
/// Calls used: ping, getArtists, getArtist, getAlbum, getAlbumList2, plus the playlist calls needed for
/// smart playlists (getPlaylists, getPlaylist, createPlaylist, updatePlaylist, deletePlaylist).
public struct NavidromeClient: Sendable {
    public let urls: StreamURLBuilder
    private let base: URL
    private let auth: SubsonicAuth
    private let transport: any HTTPTransport
    private let tailscaleHint: @Sendable () -> Bool

    public init(baseURL: URL, credential: Credential,
                transport: any HTTPTransport = URLSessionTransport(keepCookies: false),
                makeSalt: @escaping @Sendable () -> String = SubsonicAuth.randomSalt,
                tailscaleHint: @escaping @Sendable () -> Bool = { false }) throws {
        let checked = try AddressPolicy.validate(baseURL)
        let auth = SubsonicAuth(credential: credential, makeSalt: makeSalt)
        self.base = checked
        self.auth = auth
        self.urls = try StreamURLBuilder(baseURL: checked, auth: auth)
        self.transport = transport
        self.tailscaleHint = tailscaleHint
    }

    // MARK: Reads

    public func ping() async throws {
        _ = try await call("ping", [], as: Empty.self)
    }

    public func artists() async throws -> [NavidromeArtist] {
        let p = try await call("getArtists", [], as: ArtistsPayload.self)
        return (p.artists?.index ?? []).flatMap { $0.artist ?? [] }
    }

    public func artist(id: String) async throws -> NavidromeArtistDetail {
        try requireID(id)
        let d = try await call("getArtist", [.init(name: "id", value: id)], as: ArtistPayload.self).artist
        return NavidromeArtistDetail(
            artist: NavidromeArtist(id: d.id, name: d.name, albumCount: d.albumCount, coverArt: d.coverArt, musicBrainzId: d.musicBrainzId),
            albums: d.album ?? [])
    }

    public func album(id: String) async throws -> NavidromeAlbumDetail {
        try requireID(id)
        let d = try await call("getAlbum", [.init(name: "id", value: id)], as: AlbumPayload.self).album
        let album = NavidromeAlbum(id: d.id, name: d.name, artist: d.artist, artistId: d.artistId, coverArt: d.coverArt,
                                   songCount: d.songCount, duration: d.duration, year: d.year, genre: d.genre,
                                   created: d.created, musicBrainzId: d.musicBrainzId)
        return NavidromeAlbumDetail(album: album, songs: d.song ?? [])
    }

    /// One page of `getAlbumList2` (`size` 1...500).
    public func albumList(_ type: AlbumListType, size: Int = 50, offset: Int = 0) async throws -> [NavidromeAlbum] {
        let q: [URLQueryItem] = [
            .init(name: "type", value: type.rawValue),
            .init(name: "size", value: String(min(max(size, 1), 500))),
            .init(name: "offset", value: String(max(offset, 0))),
        ]
        return try await call("getAlbumList2", q, as: AlbumListPayload.self).albumList2?.album ?? []
    }

    /// Every album, alphabetical, read in pages until a short page arrives (or `maxPages` is reached).
    public func allAlbums(pageSize: Int = 500, maxPages: Int = 100) async throws -> [NavidromeAlbum] {
        var all: [NavidromeAlbum] = []
        for page in 0..<maxPages {
            let items = try await albumList(.alphabeticalByName, size: pageSize, offset: page * pageSize)
            all += items
            if items.count < pageSize { break }
        }
        return all
    }

    /// A page of every song, by title. Navidrome answers `search3` with an empty query by listing the library, so no
    /// artist or album is asked for. Short page = the end.
    public func songs(offset: Int = 0, count: Int = 200) async throws -> [NavidromeSong] {
        let q: [URLQueryItem] = [
            .init(name: "query", value: ""),
            .init(name: "artistCount", value: "0"), .init(name: "albumCount", value: "0"),
            .init(name: "songCount", value: String(min(max(count, 1), 500))),
            .init(name: "songOffset", value: String(max(offset, 0))),
        ]
        return try await call("search3", q, as: SongSearchPayload.self).searchResult3?.song ?? []
    }

    /// Lyrics for a song, chosen and cleaned. nil means the song has none (an unknown id, code 70, is also "none").
    /// Lookups can take 20 s or more for a song with no lyrics, so this call waits up to 45 s.
    public func lyrics(songID: String, language: String? = nil) async throws -> Lyrics? {
        try requireID(songID)
        do {
            let p = try await call("getLyricsBySongId", [.init(name: "id", value: songID)], as: LyricsPayload.self, timeout: 45, notFoundAs404: true)
            return LyricsChooser.choose(p.lyricsList?.structuredLyrics ?? [], language: language)
        } catch DiscairError.server(404, _) {
            return nil                                   // Subsonic code 70: no such song, so no lyrics
        }
    }

    /// Whether the server lists the `songLyrics` extension.
    public func supportsLyrics() async throws -> Bool {
        let p = try await call("getOpenSubsonicExtensions", [], as: ExtensionsPayload.self)
        return (p.openSubsonicExtensions ?? []).contains { $0.name == "songLyrics" }
    }

    // MARK: Playlists (contract section 6 item 7, check 6a)

    public func playlists() async throws -> [NavidromePlaylist] {
        try await call("getPlaylists", [], as: PlaylistsPayload.self).playlists?.playlist ?? []
    }

    /// Creates a playlist and returns it. Writes to the server.
    public func createPlaylist(name: String, songIDs: [String]) async throws -> NavidromePlaylist {
        try songIDs.forEach(requireID)
        let q = [URLQueryItem(name: "name", value: name)] + songIDs.map { URLQueryItem(name: "songId", value: $0) }
        return NavidromePlaylist(try await call("createPlaylist", q, as: PlaylistPayload.self).playlist)
    }

    public func playlistSongIDs(id: String) async throws -> [String] {
        try requireID(id)
        return try await call("getPlaylist", [.init(name: "id", value: id)], as: PlaylistPayload.self).playlist.entry?.map(\.id) ?? []
    }

    public func addToPlaylist(id: String, songIDs: [String]) async throws {
        try requireID(id); try songIDs.forEach(requireID)
        let q = [URLQueryItem(name: "playlistId", value: id)] + songIDs.map { URLQueryItem(name: "songIdToAdd", value: $0) }
        _ = try await call("updatePlaylist", q, as: Empty.self)
    }

    public func deletePlaylist(id: String) async throws {
        try requireID(id)
        _ = try await call("deletePlaylist", [.init(name: "id", value: id)], as: Empty.self)
    }

    // MARK: Plumbing

    private func requireID(_ id: String) throws {
        guard isValidSongID(id) else { throw DiscairError.insecureOrInvalidAddress(reason: .notAURL) }
    }

    func call<P: Decodable>(_ endpoint: String, _ extra: [URLQueryItem], as: P.Type, timeout: TimeInterval? = nil, notFoundAs404: Bool = false, rawTransportErrors: Bool = false) async throws -> P {
        var comps = URLComponents(url: base, resolvingAgainstBaseURL: false)!
        comps.path = (comps.path.hasSuffix("/") ? comps.path : comps.path + "/") + "rest/" + endpoint
        comps.queryItems = auth.queryItems(json: true) + extra
        var request = URLRequest(url: comps.url!)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let timeout { request.timeoutInterval = timeout }

        let data: Data, http: HTTPURLResponse
        do { (data, http) = try await transport.send(request) }
        catch { throw rawTransportErrors ? error : ErrorMapping.map(error, tailscaleHint: tailscaleHint()) }

        if let failure = ErrorMapping.map(status: http.statusCode) { throw failure }
        let envelope: SubsonicEnvelope<P>
        do { envelope = try JSONDecoder().decode(SubsonicEnvelope<P>.self, from: data) }
        catch { throw DiscairError.server(status: http.statusCode, message: "That address did not answer like Navidrome.") }

        let inner = envelope.response
        if inner.status == "ok", let payload = inner.payload { return payload }
        let code = inner.error?.code
        // Subsonic 40 and 41 are bad credentials / token auth unsupported, 44 bad API key, 50 not authorised.
        if let code, [40, 41, 44, 50].contains(code) { throw DiscairError.unauthorised(message: inner.error?.message) }
        if notFoundAs404, code == 70 { throw DiscairError.server(status: 404, message: inner.error?.message) }   // data not found
        throw DiscairError.server(status: http.statusCode, message: inner.error?.message)
    }
}

struct PlaylistPayload: Decodable {
    struct Detail: Decodable, Identifiable {
        let id: String; let name: String
        let songCount: Int?; let owner: String?; let `public`: Bool?
        let entry: [NavidromeSong]?
    }
    let playlist: Detail
}

extension NavidromePlaylist {
    init(_ d: PlaylistPayload.Detail) {
        self.init(id: d.id, name: d.name, songCount: d.songCount, owner: d.owner, public: d.public)
    }
}
