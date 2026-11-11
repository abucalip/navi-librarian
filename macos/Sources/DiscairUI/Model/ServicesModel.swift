import DiscairCore
import DiscairLibrarian
import Foundation

/// The state of every connected service, the summary sentence and the diagram (`docs/redesign.md` section 6, step M6).
/// Pure: it is built from answers the app already has (settings, test results, capabilities, its own reachability checks), with
/// no network and no SwiftUI, so it can be tested from fixtures. The views (step M9) only draw these values.
///
/// Rules from section 6.2:
/// - When the Librarian does not answer, everything it would report is **Unknown**, not failed. Navidrome, the SMB folder and
///   Sonic analysis (a Navidrome plugin) are checked directly and keep their own state.
/// - An optional service that is not set up (Discogs, SMB) is never a problem.
/// - Missing is not working: a configured service that has not been tested yet is Unknown.
public struct ServicesModel: Equatable, Sendable {

    // MARK: Vocabulary

    public enum ServiceID: String, CaseIterable, Codable, Sendable {
        case librarian, navidrome, slskd, lastfm, listenbrainz, musicbrainz, sonic, discogs, smb
    }

    public enum Group: String, CaseIterable, Sendable {
        case core = "Core", gettingMusic = "Getting music", listeningHistory = "Listening history", knowledge = "Knowledge", onThisMac = "On this Mac"
    }

    public enum Tone: Equatable, Sendable { case success, warning, danger, info, neutral }

    /// What a service answered. Each case has a word (never colour alone) and a tone.
    public enum State: Equatable, Sendable {
        case connected
        case available
        /// MusicBrainz data stored on the server: `partial` or `broad`.
        case loaded(String)
        case notLoaded
        case notSetUp
        /// Switched off by the owner (the SMB folder).
        case off
        case unknown
        /// The service answered and refused the credential. The noun names it: "Token", "Key", "Password", "Username".
        case rejected(String)
        case noAnswer

        public var word: String {
            switch self {
            case .connected: "Connected"
            case .available: "Available"
            case .loaded(let coverage): "Loaded · \(coverage)"
            case .notLoaded: "Not loaded"
            case .notSetUp: "Not set up"
            case .off: "Off"
            case .unknown: "Unknown"
            case .rejected(let noun): "\(noun) rejected"
            case .noAnswer: "No answer"
            }
        }

        public var tone: Tone {
            switch self {
            case .connected, .available, .loaded: .success
            case .notLoaded: .info
            case .rejected, .noAnswer: .danger
            case .notSetUp, .off, .unknown: .neutral
            }
        }

        public var isFailing: Bool { tone == .danger }
        public var isWorking: Bool { tone == .success }
    }

    /// What the owner can do from an expanded row.
    public enum Action: Equatable, Sendable {
        case edit, editAddress, testAgain, disconnect, setUp
        /// Primary on a rejected credential: "Replace token".
        case replace(String)
    }

    /// One line of the Setup column.
    public struct Field: Equatable, Sendable {
        public let label: String
        public let value: String
    }

    public struct Row: Equatable, Sendable, Identifiable {
        public var id: ServiceID
        public let name: String
        /// About five words.
        public let role: String
        public let group: Group
        /// The app features that depend on this service.
        public let powers: [String]
        public let state: State
        /// An optional service that is not set up is not a problem and gets a neutral Set up button.
        public let optional: Bool
        /// When the state last changed, as far as this Mac has seen. `nil` until it has seen one.
        public let since: Date?
        /// The last time this Mac saw the service working.
        public let lastGood: Date?
        public let checked: Date?
        public let setup: [Field]
        public let actions: [Action]
        /// A sentence for the danger notice above an expanded failing row: the cause and the fix in words.
        public let notice: String?

        /// Counts toward "needs attention": a failure, or a required service that is not set up.
        public var needsAttention: Bool { state.isFailing || (state == .notSetUp && !optional) }
    }

    // MARK: Inputs

    /// How the app's own direct check of a service went. `unchecked` is the state before the first check.
    public enum DirectCheck: Equatable, Sendable { case unchecked, ok, rejected, noAnswer }

    public enum ShareState: Equatable, Sendable { case off, mounted, failed }

    public struct Inputs: Sendable {
        /// `nil` until the first check.
        public var librarianReachable: Bool?
        public var librarianAddress: String?
        /// Shown in the unreachable sentence only when the app thinks the address is a Tailscale one.
        public var tailscaleHint: Bool
        /// The app's own check of Navidrome (it talks to Navidrome directly, so this works with the Librarian down).
        public var navidromeCheck: DirectCheck
        public var navidromeSettings: NavidromeSettings?
        public var slskdSettings: SlskdSettings?
        public var lastFMSettings: LastFMSettings?
        public var listenBrainzSettings: ListenBrainzSettings?
        public var discogsSettings: DiscogsSettings?
        /// The most recent `POST …/test` answer for each service. A service with settings and no test is Unknown.
        public var tests: [ServiceID: ServiceTestResult]
        public var capabilities: ServerCapabilities?
        /// Sonic analysis when it was read without the Librarian (Navidrome's own plugin list). Wins over `capabilities`.
        public var sonicAvailable: Bool?
        public var share: ShareState
        public var shareAddress: String
        public var history: History
        public var now: Date
        public var calendar: Calendar

        public init(librarianReachable: Bool? = nil, librarianAddress: String? = nil, tailscaleHint: Bool = false,
                    navidromeCheck: DirectCheck = .unchecked, navidromeSettings: NavidromeSettings? = nil,
                    slskdSettings: SlskdSettings? = nil, lastFMSettings: LastFMSettings? = nil,
                    listenBrainzSettings: ListenBrainzSettings? = nil, discogsSettings: DiscogsSettings? = nil,
                    tests: [ServiceID: ServiceTestResult] = [:], capabilities: ServerCapabilities? = nil, sonicAvailable: Bool? = nil,
                    share: ShareState = .off, shareAddress: String = "", history: History = History(), now: Date = Date(),
                    calendar: Calendar = .current) {
            self.librarianReachable = librarianReachable; self.librarianAddress = librarianAddress; self.tailscaleHint = tailscaleHint
            self.navidromeCheck = navidromeCheck; self.navidromeSettings = navidromeSettings; self.slskdSettings = slskdSettings
            self.lastFMSettings = lastFMSettings; self.listenBrainzSettings = listenBrainzSettings; self.discogsSettings = discogsSettings
            self.tests = tests; self.capabilities = capabilities; self.sonicAvailable = sonicAvailable
            self.share = share; self.shareAddress = shareAddress; self.history = history; self.now = now; self.calendar = calendar
        }
    }

    // MARK: Local history (decision D7: the server returns no "since" time, so the client keeps its own)

    /// The times this Mac last saw each service change state and work. Small, `Codable`, safe to keep in `UserDefaults`.
    public struct History: Codable, Equatable, Sendable {
        public struct Entry: Codable, Equatable, Sendable {
            public var word: String
            public var since: Date
            public var lastGood: Date?
        }
        public var entries: [ServiceID: Entry] = [:]
        public init(entries: [ServiceID: Entry] = [:]) { self.entries = entries }

        /// The history after seeing `rows`. An Unknown state says nothing about the service, so it changes nothing.
        public func recording(_ rows: [Row], at now: Date) -> History {
            var next = self
            for row in rows where row.state != .unknown {
                var entry = entries[row.id] ?? Entry(word: row.state.word, since: now, lastGood: nil)
                if entry.word != row.state.word { entry.word = row.state.word; entry.since = now }
                if row.state.isWorking { entry.lastGood = now }
                next.entries[row.id] = entry
            }
            return next
        }
    }

    // MARK: Output

    public enum EdgeStyle: Equatable, Sendable {
        /// Solid grey.
        case working
        /// Dashed danger.
        case failing
        /// Dashed light grey: not set up, off or unknown.
        case dim
    }

    public struct Edge: Equatable, Sendable {
        public let from: String
        public let to: String
        public let style: EdgeStyle
    }

    /// The label on the toolbar status button.
    public struct Toolbar: Equatable, Sendable {
        public enum Kind: Equatable, Sendable { case checking, ok, attention, notSetUp, unreachable }
        public let kind: Kind
        public let text: String
        public var tone: Tone {
            switch kind {
            case .ok: .success
            case .attention: .warning
            case .unreachable: .danger
            case .checking, .notSetUp: .neutral
            }
        }
    }

    public struct Summary: Equatable, Sendable {
        public let tone: Tone
        public let title: String
        public let detail: String
    }

    public let rows: [Row]
    public let summary: Summary
    public let toolbar: Toolbar
    /// The Mac to Librarian to Navidrome to the five Librarian services, as the diagram draws them.
    public let edges: [Edge]
    /// What to save after this build; the caller stores it.
    public let history: History
    public let checkedAt: Date

    public var attention: [Row] { rows.filter(\.needsAttention) }
    public func row(_ id: ServiceID) -> Row? { rows.first { $0.id == id } }
    public func rows(in group: Group) -> [Row] { rows.filter { $0.group == group } }

    // MARK: Build

    public static func build(_ input: Inputs) -> ServicesModel {
        let librarianUp = input.librarianReachable
        let down = librarianUp == false
        /// Settings and tests come through the Librarian: with it down or unchecked they say nothing.
        func viaLibrarian(_ state: State) -> State { librarianUp == true ? state : .unknown }

        let states: [ServiceID: State] = [
            .librarian: { switch librarianUp { case true?: .connected; case false?: .noAnswer; case nil: .unknown } }(),
            .navidrome: { switch input.navidromeCheck {
                case .ok: .connected; case .rejected: .rejected("Password"); case .noAnswer: .noAnswer; case .unchecked: .unknown } }(),
            .slskd: viaLibrarian(testedState(input.tests[.slskd], configured: input.slskdSettings.map { $0.apiKeyConfigured && !$0.url.isEmpty }, noun: "Key")),
            .lastfm: viaLibrarian(testedState(input.tests[.lastfm], configured: input.lastFMSettings?.apiKeyConfigured, noun: "Key")),
            .listenbrainz: viaLibrarian(testedState(input.tests[.listenbrainz], configured: listenBrainzConfigured(input), noun: "Token")),
            .discogs: viaLibrarian(testedState(input.tests[.discogs], configured: input.discogsSettings?.tokenConfigured, noun: "Token")),
            .musicbrainz: viaLibrarian(input.capabilities.map { c in
                c.graphCoverage == "none" ? State.notLoaded : .loaded(c.graphCoverage) } ?? .unknown),
            .sonic: sonicState(input),
            .smb: { switch input.share { case .off: .off; case .mounted: .connected; case .failed: .noAnswer } }(),
        ]

        let built = ServiceID.allCases.map { makeRow($0, state: states[$0]!, input: input) }
        let history = input.history.recording(built, at: input.now)
        // Times come from the history as it stands after this check.
        let rows = built.map { r -> Row in
            let e = history.entries[r.id]
            return Row(id: r.id, name: r.name, role: r.role, group: r.group, powers: r.powers, state: r.state, optional: r.optional,
                       since: e?.since, lastGood: e?.lastGood, checked: input.librarianReachable == nil && r.state == .unknown ? nil : input.now,
                       setup: r.setup, actions: r.actions, notice: r.notice)
        }

        return ServicesModel(rows: rows, summary: summary(rows, input, history: history), toolbar: toolbar(rows, input),
                             edges: edges(states), history: history, checkedAt: input.now)
    }

    // MARK: State rules

    private static func listenBrainzConfigured(_ input: Inputs) -> Bool? {
        if let s = input.listenBrainzSettings { return !s.username.isEmpty }
        return input.capabilities?.listenBrainzConnected
    }

    /// The state of a service the Librarian tests. `configured` is `nil` when its settings were not read.
    private static func testedState(_ test: ServiceTestResult?, configured: Bool?, noun: String) -> State {
        if configured == false { return .notSetUp }
        guard let test else { return .unknown }       // configured or unread, and not tested: not known to work
        if test.ok { return .connected }
        switch test.status {
        case "not_configured": return .notSetUp
        case "authentication_failed": return .rejected(noun)
        case "not_found": return .rejected("Username")
        default: return .noAnswer
        }
    }

    private static func sonicState(_ input: Inputs) -> State {
        if let direct = input.sonicAvailable { return direct ? .available : .notSetUp }
        guard input.librarianReachable == true, let caps = input.capabilities else { return .unknown }
        return caps.sonicAvailable ? .available : .notSetUp
    }

    // MARK: Rows

    private struct Info {
        let name: String, role: String, group: Group, powers: [String], optional: Bool, noun: String
    }

    private static let info: [ServiceID: Info] = [
        .librarian: Info(name: "Librarian", role: "Picks, downloads, insights", group: .core, powers: ["Home", "Discover", "Insights", "Downloads"], optional: false, noun: "Password"),
        .navidrome: Info(name: "Navidrome", role: "Your library and playback", group: .core, powers: ["Library", "Playback", "Playlists"], optional: false, noun: "Password"),
        .slskd: Info(name: "slskd", role: "Finds and downloads what you Get", group: .gettingMusic, powers: ["Get", "Downloads"], optional: false, noun: "Key"),
        .lastfm: Info(name: "Last.fm", role: "Listening history for picks", group: .listeningHistory, powers: ["Picks", "Listener counts"], optional: false, noun: "Key"),
        .listenbrainz: Info(name: "ListenBrainz", role: "Listening history for taste", group: .listeningHistory, powers: ["Taste", "Popularity", "Lenses"], optional: false, noun: "Token"),
        .musicbrainz: Info(name: "MusicBrainz data", role: "Credits stored on the server", group: .knowledge, powers: ["Connections", "Paths", "Atlas", "Timeline"], optional: false, noun: ""),
        .sonic: Info(name: "Sonic analysis", role: "Navidrome’s analysis of each song", group: .knowledge, powers: ["Sonic paths", "Neighbours by ear"], optional: true, noun: ""),
        .discogs: Info(name: "Discogs", role: "Edition details, optional", group: .knowledge, powers: ["Editions"], optional: true, noun: "Token"),
        .smb: Info(name: "Music folder over SMB", role: "Optional, read only", group: .onThisMac, powers: ["Quick tag reads"], optional: true, noun: ""),
    ]

    /// The service's name as the screen writes it.
    public static func name(for id: ServiceID) -> String { info[id]!.name }
    /// The credential a service is refused on: "Token", "Key", "Password" (empty for a service with none).
    public static func noun(for id: ServiceID) -> String { info[id]!.noun }

    private static func makeRow(_ id: ServiceID, state: State, input: Inputs) -> Row {
        let i = info[id]!
        return Row(id: id, name: i.name, role: i.role, group: i.group, powers: i.powers, state: state, optional: i.optional,
                   since: nil, lastGood: nil, checked: nil, setup: setup(id, input), actions: actions(id, state, optional: i.optional),
                   notice: notice(id, state, input))
    }

    private static let secretLine = "Saved on the server, never shown"

    private static func setup(_ id: ServiceID, _ input: Inputs) -> [Field] {
        func secret(_ label: String, _ stored: Bool?) -> Field? {
            guard let stored else { return nil }
            return Field(label: label, value: stored ? secretLine : "Not saved")
        }
        func text(_ label: String, _ value: String?) -> Field? {
            guard let value, !value.isEmpty else { return nil }
            return Field(label: label, value: value)
        }
        let usedBy = Field(label: "Used by", value: info[id]!.powers.joined(separator: ", "))
        let fields: [Field?]
        switch id {
        case .librarian: fields = [text("Address", input.librarianAddress), usedBy]
        case .navidrome: fields = [text("Address", input.navidromeSettings?.url), text("Username", input.navidromeSettings?.username),
                                   secret("Password", input.navidromeSettings?.passwordConfigured), usedBy]
        case .slskd: fields = [text("Address", input.slskdSettings?.url), secret("API key", input.slskdSettings?.apiKeyConfigured), usedBy]
        case .lastfm: fields = [text("Username", input.lastFMSettings?.username), secret("API key", input.lastFMSettings?.apiKeyConfigured), usedBy]
        case .listenbrainz: fields = [text("Username", input.listenBrainzSettings?.username), secret("Token", input.listenBrainzSettings?.tokenConfigured), usedBy]
        case .discogs:
            let source: String? = input.discogsSettings.map { s in
                switch s.source { case "settings": "Saved on the server, never shown"; case "environment": "Set in the server’s environment, never shown"; default: "Not saved" } }
            fields = [text("Token", source), usedBy]
        case .musicbrainz, .sonic: fields = [usedBy]
        case .smb: fields = [text("Address", input.shareAddress), usedBy]
        }
        return fields.compactMap { $0 }
    }

    private static func actions(_ id: ServiceID, _ state: State, optional: Bool) -> [Action] {
        switch id {
        case .musicbrainz, .sonic: return state == .unknown ? [] : [.testAgain]
        case .librarian: return state == .connected ? [.editAddress, .testAgain] : [.testAgain, .editAddress]
        default: break
        }
        switch state {
        case .notSetUp, .off: return [.setUp]
        case .rejected(let noun): return [.replace(noun.lowercased()), .testAgain, .disconnect]
        case .unknown: return [.testAgain]
        case .noAnswer: return [.testAgain, .edit]
        default: return [.edit, .testAgain, .disconnect]
        }
    }

    private static func notice(_ id: ServiceID, _ state: State, _ input: Inputs) -> String? {
        let name = info[id]!.name
        switch state {
        case .rejected(let noun):
            return "\(name) did not accept the \(noun.lowercased()). Replace it, then test again."
        case .noAnswer:
            switch id {
            case .librarian:
                var s = "No answer from \(input.librarianAddress ?? "the Librarian address")."
                if input.tailscaleHint { s += " Check that Tailscale is connected on this Mac." }
                return s
            case .smb: return "The music folder could not be mounted. Quick tag reads are off; playback is not affected."
            default: return "\(name) did not answer. Check that it is running and that the address is right."
            }
        case .notSetUp where !info[id]!.optional:
            return "\(name) is not set up, so \(info[id]!.powers.joined(separator: ", ")) cannot work."
        default: return nil
        }
    }

    // MARK: Summary, toolbar, diagram

    /// Features named in the "not affected" half of the sentence, with the services each needs.
    private static let keyFeatures: [(name: String, needs: [ServiceID])] = [
        ("Playback", [.navidrome]), ("picks", [.librarian]), ("Get", [.librarian, .slskd]),
    ]

    private static func timeText(_ date: Date, _ input: Inputs) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_GB"); f.calendar = input.calendar; f.timeZone = input.calendar.timeZone
        f.dateFormat = "HH:mm"
        return f.string(from: date)
    }

    private static func listed(_ words: [String]) -> String {
        guard words.count > 1 else { return words.first ?? "" }
        return words.dropLast().joined(separator: ", ") + " and " + words.last!
    }

    private static func summary(_ rows: [Row], _ input: Inputs, history: History) -> Summary {
        let byID = Dictionary(uniqueKeysWithValues: rows.map { ($0.id, $0) })
        let checked = "checked at \(timeText(input.now, input))"

        if input.librarianReachable == false {
            var detail = "No answer from \(input.librarianAddress ?? "the Librarian address")"
            if let since = history.entries[.librarian]?.since { detail += " since \(timeText(since, input))" }
            detail += "."
            if input.tailscaleHint { detail += " Check that Tailscale is connected on this Mac." }
            if byID[.navidrome]?.state.isWorking == true { detail += " Your library still plays from Navidrome." }
            return Summary(tone: .danger, title: "Can’t reach Librarian", detail: detail)
        }
        if input.librarianReachable == nil && rows.allSatisfy({ $0.state == .unknown || $0.id == .smb }) {
            return Summary(tone: .neutral, title: "Checking services…", detail: "Nothing has answered yet.")
        }

        let attention = rows.filter(\.needsAttention)
        if attention.isEmpty {
            let unknown = rows.filter { $0.state == .unknown }
            if !unknown.isEmpty {
                return Summary(tone: .neutral, title: "Some services are not checked yet",
                               detail: "\(listed(unknown.map(\.name))) \(unknown.count == 1 ? "has" : "have") not answered a test. Use Check again · \(checked)")
            }
            let missing = rows.filter { $0.state == .notSetUp }
            let tail = missing.isEmpty ? "Every service answered" : "\(listed(missing.map(\.name))) \(missing.count == 1 ? "is" : "are") optional and not set up"
            return Summary(tone: .success, title: "Everything is working", detail: "\(tail) · \(checked)")
        }

        let title = attention.count == 1 ? "One service needs attention" : "\(attention.count) services need attention"
        let first = attention[0]
        var cause: String
        switch first.state {
        case .rejected(let noun): cause = "\(first.name) rejected the saved \(noun.lowercased())."
        case .notSetUp: cause = "\(first.name) is not set up."
        default: cause = "\(first.name) did not answer."
        }
        if attention.count > 1 { cause += " \(listed(attention.dropFirst().map(\.name))) also need\(attention.count == 2 ? "s" : "") attention." }
        let working = keyFeatures.filter { f in f.needs.allSatisfy { byID[$0]?.state.isWorking == true } }.map(\.name)
        let affected = working.isEmpty ? "" : " \(listed(working)) \(working.count == 1 ? "is" : "are") not affected"
        return Summary(tone: .warning, title: title, detail: "\(cause)\(affected) · \(checked)")
    }

    private static func toolbar(_ rows: [Row], _ input: Inputs) -> Toolbar {
        if input.librarianReachable == false { return Toolbar(kind: .unreachable, text: "Librarian unreachable") }
        if input.librarianReachable == nil && rows.allSatisfy({ $0.state == .unknown || $0.id == .smb }) { return Toolbar(kind: .checking, text: "Checking…") }
        let attention = rows.filter(\.needsAttention).count
        if attention > 0 { return Toolbar(kind: .attention, text: "\(attention) needs attention") }
        let missing = rows.filter { $0.state == .notSetUp }.count
        if missing > 0 { return Toolbar(kind: .notSetUp, text: "\(missing) not set up") }
        return Toolbar(kind: .ok, text: "All working")
    }

    private static func edges(_ states: [ServiceID: State]) -> [Edge] {
        func style(_ s: State) -> EdgeStyle { s.isWorking ? .working : s.isFailing ? .failing : .dim }
        let lib = states[.librarian]!, nav = states[.navidrome]!
        // The Librarian-to-Navidrome link is only as good as the Librarian's own answer; a failing Navidrome shows on this link.
        let libNav: EdgeStyle = !lib.isWorking ? .dim : nav.isFailing ? .failing : style(nav)
        var out = [Edge(from: "mac", to: "librarian", style: style(lib)),
                   Edge(from: "mac", to: "navidrome", style: style(nav)),
                   Edge(from: "librarian", to: "navidrome", style: libNav)]
        for id in [ServiceID.slskd, .lastfm, .listenbrainz, .discogs, .musicbrainz] {
            out.append(Edge(from: "librarian", to: id.rawValue, style: style(states[id]!)))
        }
        return out
    }
}
