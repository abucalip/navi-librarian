import DiscairCore
import DiscairNavidrome
import Foundation
import Observation

/// What a smart playlist rule looks at (contract section 6.7).
public enum SmartField: String, Codable, CaseIterable, Sendable, Identifiable {
    case artist, title, genre, format, year, plays, rating, bitrate, addedDaysAgo, playedDaysAgo
    public var id: String { rawValue }
    public var label: String {
        switch self {
        case .artist: "Artist"
        case .title: "Title"
        case .genre: "Genre"
        case .format: "Format"
        case .year: "Year"
        case .plays: "Plays"
        case .rating: "Rating"
        case .bitrate: "Bitrate (kb/s)"
        case .addedDaysAgo: "Added (days ago)"
        case .playedDaysAgo: "Last played (days ago)"
        }
    }
    public var isText: Bool { [.artist, .title, .genre, .format].contains(self) }
    public var operators: [SmartOp] { isText ? [.contains, .equals, .notContains] : [.atLeast, .atMost, .equals] }
}

public enum SmartOp: String, Codable, CaseIterable, Sendable, Identifiable {
    case contains, notContains, equals, atLeast, atMost
    public var id: String { rawValue }
    public var label: String {
        switch self {
        case .contains: "contains"
        case .notContains: "does not contain"
        case .equals: "is"
        case .atLeast: "at least"
        case .atMost: "at most"
        }
    }
}

public struct SmartRule: Codable, Equatable, Sendable, Identifiable {
    public var id = UUID()
    public var field: SmartField
    public var op: SmartOp
    public var value: String
    public init(field: SmartField, op: SmartOp, value: String) { self.field = field; self.op = op; self.value = value }
}

public enum SmartOrder: String, Codable, CaseIterable, Sendable, Identifiable {
    case random, newestAdded, mostPlayed, leastPlayed, highestRated, title
    public var id: String { rawValue }
    public var label: String {
        switch self {
        case .random: "Random"
        case .newestAdded: "Newest added"
        case .mostPlayed: "Most played"
        case .leastPlayed: "Least played"
        case .highestRated: "Highest rated"
        case .title: "Title"
        }
    }
}

public struct SmartPlaylist: Codable, Equatable, Sendable, Identifiable {
    public var id = UUID()
    public var name: String
    /// True: every rule must match. False: any rule.
    public var matchAll = true
    public var rules: [SmartRule]
    public var order: SmartOrder = .random
    /// Most songs the playlist holds; 0 = no limit.
    public var limit = 0
    public init(name: String, matchAll: Bool = true, rules: [SmartRule], order: SmartOrder = .random, limit: Int = 0) {
        self.name = name; self.matchAll = matchAll; self.rules = rules; self.order = order; self.limit = limit
    }
}

/// Runs smart playlist rules over song rows. Pure, so a test can drive it.
public enum SmartEngine {
    /// A rule with an empty or unreadable value matches everything (an unfinished rule never hides songs).
    public static func matches(_ rule: SmartRule, _ s: SongRow, now: Date = Date()) -> Bool {
        let v = rule.value.trimmingCharacters(in: .whitespaces)
        if v.isEmpty { return true }
        if rule.field.isText {
            let text: String
            switch rule.field {
            case .artist: text = s.artist
            case .title: text = s.title
            case .genre: text = s.genre
            default: text = s.suffix ?? s.format
            }
            switch rule.op {
            case .equals: return text.caseInsensitiveCompare(v) == .orderedSame
            case .notContains: return text.range(of: v, options: [.caseInsensitive, .diacriticInsensitive]) == nil
            default: return text.range(of: v, options: [.caseInsensitive, .diacriticInsensitive]) != nil
            }
        }
        guard let n = Int(v) else { return true }
        let actual: Int?
        switch rule.field {
        case .year: actual = s.year > 0 ? s.year : nil
        case .plays: actual = s.plays
        case .rating: actual = s.rating
        case .bitrate: actual = s.bitrateKbps > 0 ? s.bitrateKbps : nil
        case .addedDaysAgo: actual = s.addedAt.map { days(from: $0, to: now) }
        default: actual = s.playedAt.map { days(from: $0, to: now) }
        }
        // "Last played at least 30 days ago" must also catch songs never played.
        if rule.field == .playedDaysAgo, actual == nil { return rule.op == .atLeast }
        guard let actual else { return false }
        switch rule.op {
        case .atMost: return actual <= n
        case .equals: return actual == n
        default: return actual >= n
        }
    }

    private static func days(from d: Date, to now: Date) -> Int { max(0, Int(now.timeIntervalSince(d) / 86_400)) }

    /// The songs the playlist holds right now. Only songs with a Navidrome id can be played or saved.
    public static func run(_ p: SmartPlaylist, over songs: [SongRow], now: Date = Date()) -> [SongRow] {
        var out = songs.filter { s in
            guard s.remoteID != nil else { return false }
            if p.rules.isEmpty { return true }
            return p.matchAll ? p.rules.allSatisfy { matches($0, s, now: now) } : p.rules.contains { matches($0, s, now: now) }
        }
        switch p.order {
        case .random: out.shuffle()
        case .newestAdded: out.sort { ($0.addedAt ?? .distantPast) > ($1.addedAt ?? .distantPast) }
        case .mostPlayed: out.sort { $0.plays > $1.plays }
        case .leastPlayed: out.sort { $0.plays < $1.plays }
        case .highestRated: out.sort { $0.rating > $1.rating }
        case .title: out.sort { $0.title.localizedCaseInsensitiveCompare($1.title) == .orderedAscending }
        }
        return p.limit > 0 ? Array(out.prefix(p.limit)) : out
    }
}

/// The owner's smart playlists, kept on this Mac (Navidrome has no rule storage), plus the playlists on the server.
@MainActor @Observable
public final class SmartPlaylistModel {
    public private(set) var lists: [SmartPlaylist]
    public var selectedID: UUID?
    /// Playlists already on Navidrome.
    public private(set) var remote: [NavidromePlaylistInfo] = []
    public private(set) var status: String?
    public private(set) var saving = false
    private let defaults: UserDefaults
    private static let key = "smartPlaylists.v1"

    public init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        if let data = defaults.data(forKey: Self.key), let saved = try? JSONDecoder().decode([SmartPlaylist].self, from: data) { lists = saved }
        else { lists = [SmartPlaylist(name: "Forgotten favourites", rules: [SmartRule(field: .rating, op: .atLeast, value: "4"), SmartRule(field: .playedDaysAgo, op: .atLeast, value: "90")], order: .random, limit: 50)] }
        selectedID = lists.first?.id
    }

    public var selected: SmartPlaylist? { lists.first { $0.id == selectedID } }

    public func add() {
        let p = SmartPlaylist(name: "New playlist", rules: [SmartRule(field: .genre, op: .contains, value: "")])
        lists.append(p); selectedID = p.id; persist()
    }
    public func update(_ p: SmartPlaylist) {
        guard let i = lists.firstIndex(where: { $0.id == p.id }) else { return }
        lists[i] = p; persist()
    }
    public func remove(_ id: UUID) {
        lists.removeAll { $0.id == id }
        if selectedID == id { selectedID = lists.first?.id }
        persist()
    }
    private func persist() { if let d = try? JSONEncoder().encode(lists) { defaults.set(d, forKey: Self.key) } }

    public func loadRemote(navidrome: NavidromeClient?) async {
        guard let navidrome, let list = try? await navidrome.playlists() else { return }
        remote = list.map { NavidromePlaylistInfo(id: $0.id, name: $0.name, songCount: $0.songCount ?? 0) }
    }

    /// Writes the current result to Navidrome as a new playlist. Never overwrites an existing one.
    public func save(_ p: SmartPlaylist, songs: [SongRow], navidrome: NavidromeClient?) async {
        guard let navidrome else { status = "Not connected to Navidrome."; return }
        let ids = songs.compactMap(\.remoteID)
        guard !ids.isEmpty else { status = "No songs match yet, so nothing was saved."; return }
        saving = true; defer { saving = false }
        let name = Self.freeName(p.name, taken: remote.map(\.name))
        do {
            _ = try await navidrome.createPlaylist(name: name, songIDs: ids)
            status = "Saved \(ids.count) songs to Navidrome as “\(name)”."
            await loadRemote(navidrome: navidrome)
        } catch { status = (error as? DiscairError).map(AcquisitionModel.text) ?? "Could not save the playlist." }
    }

    /// A playlist name not yet used on the server ("Name", "Name 2", ...).
    static func freeName(_ name: String, taken: [String]) -> String {
        let base = name.trimmingCharacters(in: .whitespaces).isEmpty ? "Smart playlist" : name.trimmingCharacters(in: .whitespaces)
        let used = Set(taken.map { $0.lowercased() })
        if !used.contains(base.lowercased()) { return base }
        var n = 2
        while used.contains("\(base) \(n)".lowercased()) { n += 1 }
        return "\(base) \(n)"
    }
}

public struct NavidromePlaylistInfo: Identifiable, Equatable, Sendable {
    public let id: String
    public let name: String
    public let songCount: Int
}
