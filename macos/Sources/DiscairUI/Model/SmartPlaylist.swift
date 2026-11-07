import DiscairCore
import DiscairLibrarian
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

/// Rule sets in the server's wire form (snake_case names, `match`, null limit) and back.
extension SmartPlaylist {
    static func snake(_ s: String) -> String {
        s.reduce(into: "") { out, c in if c.isUppercase { out += "_" + c.lowercased() } else { out.append(c) } }
    }
    static func camel(_ s: String) -> String {
        let parts = s.split(separator: "_").map(String.init)
        return (parts.first ?? "") + parts.dropFirst().map { $0.prefix(1).uppercased() + $0.dropFirst() }.joined()
    }

    /// The wire form. The id is lowercase, as the server wants.
    public var wire: ServerSmartPlaylist {
        ServerSmartPlaylist(ruleID: id.uuidString.lowercased(), name: name, match: matchAll ? "all" : "any",
                            rules: rules.map { ServerSmartRule(field: Self.snake($0.field.rawValue), op: Self.snake($0.op.rawValue), value: $0.value) },
                            order: Self.snake(order.rawValue), limit: limit > 0 ? limit : nil)
    }

    /// nil when the rule set uses something this client cannot show (an insight field, an unknown order or operator, a bad id).
    public init?(wire w: ServerSmartPlaylist) {
        guard let id = UUID(uuidString: w.ruleID), let order = SmartOrder(rawValue: Self.camel(w.order)), w.match == "all" || w.match == "any" else { return nil }
        var rules: [SmartRule] = []
        for r in w.rules {
            guard let f = SmartField(rawValue: Self.camel(r.field)), let o = SmartOp(rawValue: Self.camel(r.op)) else { return nil }
            rules.append(SmartRule(field: f, op: o, value: r.value))
        }
        self.init(name: w.name, matchAll: w.match == "all", rules: rules, order: order, limit: w.limit ?? 0)
        self.id = id
    }

    /// Same rule set, ignoring the local-only rule ids.
    func sameContent(as other: SmartPlaylist) -> Bool { wire == other.wire }
}

/// What has not reached the server yet, kept so a restart or a failed call loses nothing.
struct SmartSyncState: Codable, Equatable {
    /// Rule sets the server is known to hold. A local set missing from the server and listed here was deleted elsewhere.
    var synced: Set<String> = []
    /// Local edits not yet accepted by the server; these win over the server copy.
    var dirty: Set<String> = []
    /// Deletes not yet accepted by the server.
    var deleted: Set<String> = []
}

/// The owner's smart playlists. The Librarian holds the rule sets (shared by both clients); this Mac keeps a copy in
/// `UserDefaults` so the screen works offline, plus the playlists already on Navidrome.
@MainActor @Observable
public final class SmartPlaylistModel {
    public private(set) var lists: [SmartPlaylist]
    public var selectedID: UUID?
    /// Playlists already on Navidrome.
    public private(set) var remote: [NavidromePlaylistInfo] = []
    public private(set) var status: String?
    public private(set) var saving = false
    /// Rule sets on the server that use insight fields this screen cannot edit yet. They are left untouched.
    public private(set) var unsupportedOnServer = 0
    private let defaults: UserDefaults
    private var librarian: LibrarianClient?
    private var sync: SmartSyncState
    private var pushTasks: [UUID: Task<Void, Never>] = [:]
    private let debounce: Duration
    private static let key = "smartPlaylists.v1"
    private static let syncKey = "smartPlaylists.sync.v1"

    public init(defaults: UserDefaults = .standard, debounce: Duration = .milliseconds(800)) {
        self.defaults = defaults
        self.debounce = debounce
        if let data = defaults.data(forKey: Self.syncKey), let s = try? JSONDecoder().decode(SmartSyncState.self, from: data) { sync = s } else { sync = SmartSyncState() }
        if let data = defaults.data(forKey: Self.key), let saved = try? JSONDecoder().decode([SmartPlaylist].self, from: data) { lists = saved }
        else { lists = [Self.seed()] }
        selectedID = lists.first?.id
    }

    private static func seed() -> SmartPlaylist {
        SmartPlaylist(name: "Forgotten favourites", rules: [SmartRule(field: .rating, op: .atLeast, value: "4"), SmartRule(field: .playedDaysAgo, op: .atLeast, value: "90")], order: .random, limit: 50)
    }

    public var selected: SmartPlaylist? { lists.first { $0.id == selectedID } }

    public func add() {
        let p = SmartPlaylist(name: "New playlist", rules: [SmartRule(field: .genre, op: .contains, value: "")])
        lists.append(p); selectedID = p.id; changed(p.id)
    }
    public func update(_ p: SmartPlaylist) {
        guard let i = lists.firstIndex(where: { $0.id == p.id }) else { return }
        lists[i] = p; changed(p.id)
    }
    public func remove(_ id: UUID) {
        lists.removeAll { $0.id == id }
        if selectedID == id { selectedID = lists.first?.id }
        pushTasks[id]?.cancel(); pushTasks[id] = nil
        let key = id.uuidString.lowercased()
        sync.dirty.remove(key)
        if sync.synced.contains(key) { sync.deleted.insert(key) }
        persist()
        if sync.deleted.contains(key), let librarian { Task { await self.flushDeletes(librarian) } }
    }

    private func changed(_ id: UUID) {
        sync.dirty.insert(id.uuidString.lowercased())
        persist()
        guard let librarian else { return }
        pushTasks[id]?.cancel()
        let wait = debounce
        pushTasks[id] = Task { [weak self] in
            try? await Task.sleep(for: wait)
            guard !Task.isCancelled else { return }
            await self?.push(id, librarian)
        }
    }

    private func persist() {
        if let d = try? JSONEncoder().encode(lists) { defaults.set(d, forKey: Self.key) }
        if let d = try? JSONEncoder().encode(sync) { defaults.set(d, forKey: Self.syncKey) }
    }

    /// Sends one rule set. A failure leaves it marked unsent for the next sync.
    func push(_ id: UUID, _ librarian: LibrarianClient) async {
        guard let p = lists.first(where: { $0.id == id }) else { return }
        let key = id.uuidString.lowercased()
        do {
            try await librarian.putSmartPlaylist(p.wire)
            sync.dirty.remove(key); sync.synced.insert(key)
            persist()
        } catch {
            status = (error as? DiscairError).map(AcquisitionModel.text) ?? "Could not send the playlist to the server."
        }
    }

    private func flushDeletes(_ librarian: LibrarianClient) async {
        for key in sync.deleted {
            do { try await librarian.deleteSmartPlaylist(id: key); sync.deleted.remove(key); sync.synced.remove(key); persist() }
            catch { status = (error as? DiscairError).map(AcquisitionModel.text) ?? "Could not delete the playlist on the server." }
        }
    }

    /// Brings this Mac and the server together. Server copies win unless this Mac holds an unsent edit; rule sets only
    /// here are uploaded (first run: the old local sets move up); sets deleted elsewhere are dropped here. Offline, nothing changes.
    public func sync(librarian: LibrarianClient?) async {
        guard let librarian else { return }
        self.librarian = librarian
        await flushDeletes(librarian)
        let server: [ServerSmartPlaylist]
        do { server = try await librarian.smartPlaylists() }
        catch { status = "Showing playlists saved on this Mac; the server could not be reached."; return }

        var usable: [UUID: SmartPlaylist] = [:]
        var serverKeys = Set<String>()
        var unsupported = 0
        for w in server {
            serverKeys.insert(w.ruleID.lowercased())
            if let p = SmartPlaylist(wire: w) { usable[p.id] = p } else { unsupported += 1 }
        }
        unsupportedOnServer = unsupported

        // A fresh Mac holding only the untouched example list should not add it next to the owner's real ones.
        if sync.synced.isEmpty, !server.isEmpty, lists.count == 1, lists[0].sameContent(as: Self.seed().with(id: lists[0].id)) { lists = [] }

        var merged: [SmartPlaylist] = []
        var toPush: [UUID] = []
        for local in lists {
            let key = local.id.uuidString.lowercased()
            if sync.deleted.contains(key) { continue }
            if let theirs = usable[local.id] {
                if sync.dirty.contains(key) { merged.append(local); if !local.sameContent(as: theirs) { toPush.append(local.id) } else { sync.dirty.remove(key) } }
                else { merged.append(theirs) }
                usable[local.id] = nil
            } else if serverKeys.contains(key) {
                merged.append(local)   // on the server but unreadable here: keep the local copy, do not overwrite
            } else if sync.synced.contains(key) && !sync.dirty.contains(key) {
                continue               // deleted on another client
            } else {
                merged.append(local); toPush.append(local.id)
            }
        }
        // Sets only the server holds are new here, unless a delete of theirs is still on its way.
        for (_, p) in usable.sorted(by: { $0.value.name < $1.value.name }) where !sync.deleted.contains(p.id.uuidString.lowercased()) { merged.append(p) }
        lists = merged
        for p in merged where serverKeys.contains(p.id.uuidString.lowercased()) && !sync.dirty.contains(p.id.uuidString.lowercased()) {
            sync.synced.insert(p.id.uuidString.lowercased())
        }
        if selectedID == nil || !lists.contains(where: { $0.id == selectedID }) { selectedID = lists.first?.id }
        persist()
        for id in toPush { await push(id, librarian) }
        if status?.hasPrefix("Showing playlists") == true { status = nil }
    }

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

extension SmartPlaylist {
    func with(id: UUID) -> SmartPlaylist { var c = self; c.id = id; return c }
}
