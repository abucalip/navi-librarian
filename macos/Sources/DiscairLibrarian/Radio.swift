import Foundation

// Internet radio decoders (docs/RADIO_PLAYBACK_CONTRACT.md sections 3.1 to 3.5; macOS stage 2, slice S2-1).
// The server owns "what is playing": these types only read what it says. The Android reference is
// `android/app/src/main/kotlin/app/discair/model/Radio.kt`. The name `RadioModel` already means "Radio from this"
// (similar songs), so everything here uses the `Station` and `Radio` prefixes.

/// A station from `GET /api/radio/stations`. `stream_url` is deliberately not decoded: the Mac plays `playableURL` only.
public struct RadioStation: Decodable, Equatable, Sendable, Identifiable {
    /// A string, as the server sends it.
    public let id: String
    public let name: String
    /// True when the server relays the station (live title and Download are possible).
    public let proxied: Bool
    /// What the player opens: the relay address when proxied, else the station's own. Never shown, logged or put in an error.
    public let playableURL: String
    public let homepageURL: String?
    /// A server path, always present (the generated tile is served when nothing else is found).
    public let logoPath: String
    public let favourite: Bool
    public let tags: [String]
    /// Unix seconds.
    public let lastPlayedAt: Double?

    enum CodingKeys: String, CodingKey {
        case id, name, proxied, favourite, tags
        case playableURL = "playable_url", homepageURL = "homepage_url", logoPath = "logo_url", lastPlayedAt = "last_played_at"
    }

    /// A row without an id, a name or a playable address cannot be played and fails to decode (the list drops it).
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        func text(_ key: CodingKeys) -> String? {
            guard let s = try? c.decode(String.self, forKey: key) else { return nil }
            return s.isEmpty ? nil : s
        }
        let rawID: String? = text(.id) ?? (try? c.decode(Int.self, forKey: .id)).map(String.init)
        guard let rawID, let name = text(.name), let playable = text(.playableURL) else {
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "station row unusable"))
        }
        id = rawID
        self.name = name
        playableURL = playable
        proxied = (try? c.decode(Bool.self, forKey: .proxied)) ?? false
        homepageURL = text(.homepageURL)
        logoPath = text(.logoPath) ?? "/api/radio/stations/\(rawID)/logo"
        favourite = (try? c.decode(Bool.self, forKey: .favourite)) ?? false
        tags = ((try? c.decode([FeedLossy<String>].self, forKey: .tags)) ?? []).compactMap(\.value)
        lastPlayedAt = try? c.decode(Double.self, forKey: .lastPlayedAt)
    }

    public init(id: String, name: String, proxied: Bool = false, playableURL: String, homepageURL: String? = nil,
                logoPath: String? = nil, favourite: Bool = false, tags: [String] = [], lastPlayedAt: Double? = nil) {
        self.id = id; self.name = name; self.proxied = proxied; self.playableURL = playableURL; self.homepageURL = homepageURL
        self.logoPath = logoPath ?? "/api/radio/stations/\(id)/logo"
        self.favourite = favourite; self.tags = tags; self.lastPlayedAt = lastPlayedAt
    }
}

/// The description leaves the address out, so a station cannot leak it through string interpolation, `print`, `dump` or a
/// test failure message (contract principle 6).
extension RadioStation: CustomStringConvertible, CustomDebugStringConvertible, CustomReflectable {
    public var description: String { "RadioStation(id: \(id), name: \(name), proxied: \(proxied), favourite: \(favourite))" }
    public var debugDescription: String { description }
    public var customMirror: Mirror {
        Mirror(self, children: ["id": id, "name": name, "proxied": proxied, "favourite": favourite, "tags": tags],
               displayStyle: .struct)
    }
}

/// `GET /api/radio/stations`. The server's order (favourites, then last played, then name) is kept. One unreadable row
/// does not hide the rest; an unreadable body is an empty list.
struct RadioStationsPayload: Decodable {
    let items: [RadioStation]
    init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        items = ((try? c.decode([FeedLossy<RadioStation>].self, forKey: .items)) ?? []).compactMap(\.value)
    }
    enum CodingKeys: String, CodingKey { case items }
}

/// The state of a live song (contract 3.2). `idle` means nobody is listening, so the server holds no title.
public enum RadioNowState: Equatable, Sendable {
    case ok, noMetadata, unparsed, notProxied, unavailable, idle
    /// A word from a newer server. Shown like `noMetadata`: honest text, never a dead Download button.
    case unknown

    init(word: String?) {
        switch word {
        case "ok": self = .ok
        case "no_metadata": self = .noMetadata
        case "unparsed": self = .unparsed
        case "not_proxied": self = .notProxied
        case "unavailable": self = .unavailable
        case "idle": self = .idle
        default: self = .unknown
        }
    }
}

/// The live song of a station: `GET /api/radio/stations/{id}/now`, and one row of `GET /api/radio/now`.
public struct RadioNow: Decodable, Equatable, Sendable {
    public let state: RadioNowState
    public let rawTitle: String?
    public let artist: String?
    public let title: String?
    /// Null until the song has been heard for the 30-second threshold.
    public let playID: Int?
    public let inLibrary: Bool
    /// A server artwork path for the live song; null when none was found.
    public let coverPath: String?

    enum CodingKeys: String, CodingKey {
        case state, artist, title
        case rawTitle = "raw_title", playID = "play_id", inLibrary = "in_library", coverPath = "cover_url"
    }

    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        func text(_ key: CodingKeys) -> String? {
            guard let s = try? c.decode(String.self, forKey: key), !s.trimmingCharacters(in: .whitespaces).isEmpty else { return nil }
            return s
        }
        state = RadioNowState(word: try? c.decode(String.self, forKey: .state))
        rawTitle = text(.rawTitle); artist = text(.artist); title = text(.title); coverPath = text(.coverPath)
        playID = (try? c.decode(Int.self, forKey: .playID)) ?? (try? c.decode(Double.self, forKey: .playID)).map { Int($0) }
        inLibrary = (try? c.decode(Bool.self, forKey: .inLibrary)) ?? false
    }

    public init(state: RadioNowState, rawTitle: String? = nil, artist: String? = nil, title: String? = nil,
                playID: Int? = nil, inLibrary: Bool = false, coverPath: String? = nil) {
        self.state = state; self.rawTitle = rawTitle; self.artist = artist; self.title = title
        self.playID = playID; self.inLibrary = inLibrary; self.coverPath = coverPath
    }

    /// An unreadable body reads as unreachable, never as a song.
    public static let unavailable = RadioNow(state: .unavailable)

    /// Contract 3.2: Download is enabled only when the state is `ok` and the song has a play id.
    public var canDownload: Bool { state == .ok && playID != nil }
}

/// `GET /api/radio/now`: the live song of every relayed station, by station id. A row without an id is dropped.
public struct RadioNowAll: Decodable, Equatable, Sendable {
    public let byStation: [String: RadioNow]

    enum CodingKeys: String, CodingKey { case items }
    private struct Row: Decodable {
        let id: String
        let now: RadioNow
        enum Keys: String, CodingKey { case id }
        init(from decoder: any Decoder) throws {
            let c = try decoder.container(keyedBy: Keys.self)
            guard let id = try? c.decode(String.self, forKey: .id), !id.isEmpty else {
                throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "row without id"))
            }
            self.id = id
            now = try RadioNow(from: decoder)
        }
    }

    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let rows = ((try? c.decode([FeedLossy<Row>].self, forKey: .items)) ?? []).compactMap(\.value)
        byStation = Dictionary(rows.map { ($0.id, $0.now) }, uniquingKeysWith: { _, last in last })
    }

    public init(byStation: [String: RadioNow]) { self.byStation = byStation }
}

/// `GET` and `PUT /api/radio/scrobbling`. An unreadable body reads as off and not set up, never as on.
public struct RadioScrobbling: Decodable, Equatable, Sendable {
    public let enabled: Bool
    /// False when Last.fm is not set up on the server; the switch is then disabled with an explanation.
    public let configured: Bool

    enum CodingKeys: String, CodingKey { case enabled, configured }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        enabled = (try? c.decode(Bool.self, forKey: .enabled)) ?? false
        configured = (try? c.decode(Bool.self, forKey: .configured)) ?? false
    }
    public init(enabled: Bool, configured: Bool) { self.enabled = enabled; self.configured = configured }
}
