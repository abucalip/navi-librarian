import DiscairLibrarian
import Foundation

/// The radio page's rules, pure so a test can drive them (docs/RADIO_PLAYBACK_PROPOSAL.md, S2-1 item 4; the words match
/// Android's `model/Radio.kt`). Nothing here reads the network, the clock (it is passed in) or a view.
enum StationRules {
    // MARK: Status sentence of a row

    /// What a station row says under its name. `isLiveTitle` is true for a song being heard: the row draws it in the accent.
    struct Status: Equatable {
        let text: String
        let isLiveTitle: Bool
    }

    /// The row's sentence. `now` is the station's live answer from `GET /api/radio/now` (nil when nobody listens or nothing
    /// was read yet). A station that is not relayed never has a title, whatever `now` says.
    static func status(for station: RadioStation, now live: RadioNow?, at date: Date, calendar: Calendar = .current) -> Status {
        if !station.proxied { return Status(text: "Not relayed · no song titles", isLiveTitle: false) }
        switch live?.state {
        case .ok:
            if let song = liveTitle(live) { return Status(text: song, isLiveTitle: true) }
            return Status(text: "Sends no song titles", isLiveTitle: false)
        case .noMetadata, .unparsed, .unknown:
            return Status(text: "Sends no song titles", isLiveTitle: false)
        case .unavailable:
            return Status(text: "Station unreachable", isLiveTitle: false)
        case .notProxied:
            return Status(text: "Not relayed · no song titles", isLiveTitle: false)
        case .idle, nil:
            return Status(text: playedText(station.lastPlayedAt, at: date, calendar: calendar), isLiveTitle: false)
        }
    }

    /// "Artist – Title", the title alone, or the station's raw title when it could not be split. Nil when there is none.
    static func liveTitle(_ live: RadioNow?) -> String? {
        guard let live else { return nil }
        if let artist = live.artist, let title = live.title { return "\(artist) – \(title)" }
        return live.title ?? live.rawTitle
    }

    /// "Played today, 18:40", "Played yesterday", "Played 3 days ago", "Never played". Whole calendar days, not 24-hour spans.
    static func playedText(_ lastPlayedAt: Double?, at date: Date, calendar: Calendar = .current) -> String {
        guard let lastPlayedAt else { return "Never played" }
        let played = Date(timeIntervalSince1970: lastPlayedAt)
        let days = calendar.dateComponents([.day], from: calendar.startOfDay(for: played), to: calendar.startOfDay(for: date)).day ?? 0
        switch days {
        case ..<1:     // today, or a clock a little ahead of the server's
            let c = calendar.dateComponents([.hour, .minute], from: played)
            return "Played today, " + String(format: "%02d:%02d", c.hour ?? 0, c.minute ?? 0)
        case 1: return "Played yesterday"
        default: return "Played \(days) days ago"
        }
    }

    // MARK: Tag chips

    /// One chip over the list: `tag` is nil for "All".
    struct Chip: Equatable, Identifiable {
        let label: String
        let tag: String?
        var id: String { tag.map { "tag:" + $0.lowercased() } ?? "all" }
        static let all = Chip(label: "All", tag: nil)
    }

    /// All, then each tag once (case-insensitive; the first spelling met wins), most used first, ties by name.
    static func chips(for stations: [RadioStation]) -> [Chip] {
        var count: [String: Int] = [:], spelling: [String: String] = [:]
        for station in stations {
            var seen = Set<String>()     // a station that lists a tag twice still counts once
            for raw in station.tags {
                let tag = raw.trimmingCharacters(in: .whitespacesAndNewlines)
                let key = tag.lowercased()
                guard !tag.isEmpty, seen.insert(key).inserted else { continue }
                count[key, default: 0] += 1
                if spelling[key] == nil { spelling[key] = tag }
            }
        }
        let tags = count.keys.sorted { a, b in
            count[a]! != count[b]! ? count[a]! > count[b]! : a.localizedStandardCompare(b) == .orderedAscending
        }
        return [.all] + tags.map { Chip(label: spelling[$0]!, tag: spelling[$0]!) }
    }

    /// The stations under a chip, in the server's order. A nil tag is All.
    static func filter(_ stations: [RadioStation], tag: String?) -> [RadioStation] {
        guard let tag else { return stations }
        let key = tag.lowercased()
        return stations.filter { $0.tags.contains { $0.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() == key } }
    }

    // MARK: Tags in the Edit Tags sheet

    static let maxTags = 10
    static let maxTagLength = 24

    enum TagProblem: Error, Equatable {
        case blank, tooLong, duplicate, tooMany

        /// The sentence the sheet shows.
        var message: String {
            switch self {
            case .blank: "Type a tag first."
            case .tooLong: "A tag can have at most \(StationRules.maxTagLength) characters."
            case .duplicate: "That tag is already on the list."
            case .tooMany: "A station can have at most \(StationRules.maxTags) tags."
            }
        }
    }

    enum TagCheck: Equatable {
        case ok(String)
        case rejected(TagProblem)
    }

    /// Checks one tag typed into the sheet against the list so far. The accepted tag is trimmed.
    static func check(tag raw: String, among existing: [String]) -> TagCheck {
        let tag = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if tag.isEmpty { return .rejected(.blank) }
        if tag.count > maxTagLength { return .rejected(.tooLong) }
        if existing.contains(where: { $0.trimmingCharacters(in: .whitespacesAndNewlines).caseInsensitiveCompare(tag) == .orderedSame }) {
            return .rejected(.duplicate)
        }
        if existing.count >= maxTags { return .rejected(.tooMany) }
        return .ok(tag)
    }

    /// The list Save sends: every tag trimmed, or the first problem found. Nothing is dropped silently.
    static func validated(tags: [String]) -> Result<[String], TagProblem> {
        var out: [String] = []
        for raw in tags {
            switch check(tag: raw, among: out) {
            case .ok(let tag): out.append(tag)
            case .rejected(let problem): return .failure(problem)
            }
        }
        return .success(out)
    }
}

/// The list being edited in the Edit Tags sheet (E5): Return adds the typed tag, a tag's x removes it, Save sends the list.
/// A rejected tag stays typed and the problem is a sentence; nothing is dropped silently.
struct TagDraft: Equatable {
    private(set) var tags: [String]
    var typed = ""
    private(set) var problem: StationRules.TagProblem?
    private let original: [String]

    init(tags: [String]) {
        self.tags = tags
        original = tags
    }

    /// Return in the field. An empty field is not a problem the owner needs told about when tags exist already; Save is the way out.
    mutating func commitTyped() {
        switch StationRules.check(tag: typed, among: tags) {
        case .ok(let tag): tags.append(tag); typed = ""; problem = nil
        case .rejected(let p): problem = p
        }
    }

    mutating func remove(_ tag: String) {
        tags.removeAll { $0 == tag }
        problem = nil
    }

    /// What Save sends: the list, plus a tag still typed but not yet added. Nil when a problem blocks it (then `problem` says which).
    mutating func result() -> [String]? {
        if !typed.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            commitTyped()
            if problem != nil { return nil }
        }
        return tags
    }

    var isChanged: Bool { tags != original || !typed.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    var isFull: Bool { tags.count >= StationRules.maxTags }
    var countLine: String { "\(tags.count) of \(StationRules.maxTags) tags" }
}

/// The state of a Download control (S2.7). Always words plus a mark, never colour alone.
enum DownloadState: Equatable {
    /// Heard, but not yet for 30 seconds: no `play_id`, so nothing can be asked for.
    case waiting
    case ready
    /// The Get request is in flight.
    case working
    /// A Get was sent and accepted.
    case done
    /// Already in the library; wins over everything.
    case owned
    /// The server refused; the button offers a retry.
    case failed
    /// No button: `no_metadata`, `unparsed`, `not_proxied`, `unavailable`, `idle` and unknown words. The row says why instead.
    case none

    /// What the Mac itself knows about a click: a Get sent from this window (`requested`), one in flight, or one refused.
    /// The server's own `grabbed` flag is read separately for a `RadioPlay`.
    struct Attempt: Equatable {
        var requested = false, working = false, failed = false
        static let none = Attempt()
    }

    /// The live song of a station. Owned first, then the state of the request, then the 30-second rule.
    static func of(now: RadioNow, attempt: Attempt = .none) -> DownloadState {
        if now.inLibrary { return .owned }
        guard now.state == .ok else { return .none }
        return resolve(playID: now.playID, attempt: attempt)
    }

    /// A heard song: `grabbed` and `in_library` come from the server.
    static func of(play: RadioPlay, attempt: Attempt = .none) -> DownloadState {
        if play.inLibrary { return .owned }
        var a = attempt
        if play.grabbed { a.requested = true }
        return resolve(playID: play.id, attempt: a)
    }

    /// A song known only by its id (a Home row whose list entry has gone): the request's state, else Download.
    static func resolved(playID: Int, attempt: Attempt) -> DownloadState { resolve(playID: playID, attempt: attempt) }

    private static func resolve(playID: Int?, attempt: Attempt) -> DownloadState {
        if attempt.working { return .working }
        if attempt.requested { return .done }
        if attempt.failed { return .failed }
        return playID == nil ? .waiting : .ready
    }

    /// The words of the button. `listeningSeconds` is the display aid for Waiting.
    func label(listeningSeconds: Int? = nil) -> String? {
        switch self {
        case .waiting: listeningSeconds.map { "Listening · \($0) s" } ?? "Listening"
        case .ready: "Download"
        case .working: "Downloading…"
        case .done: "✓ Downloaded"
        case .owned: "✓ Owned"
        case .failed: "Try again"
        case .none: nil
        }
    }

    /// Only Ready and Failed can be pressed.
    var isEnabled: Bool { self == .ready || self == .failed }

    /// Seconds since the Mac first saw this title, capped at 30. Display only: the server's `play_id` is what enables Download.
    static func listeningSeconds(since firstSeen: Date, now: Date) -> Int {
        min(30, max(0, Int(now.timeIntervalSince(firstSeen))))
    }
}
