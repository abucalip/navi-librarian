import DiscairLibrarian
import DiscairNavidrome
import Foundation

/// The figures behind the redesigned Cupertino Home (`docs/redesign.md` section 5.1, step M5). Pure: every figure is computed
/// from models the app already holds, with no network and no SwiftUI, so it can run off the main thread and be tested from
/// fixtures. The views (step M8) only draw these values.
///
/// Rule: missing is not zero. A figure whose input is absent is `nil` (or an empty list) and the view shows that module's own
/// sentence; a zero is only ever a real count. Nothing here writes prose: the taste headline and insight cards stay the
/// server's words, and only shares the server listed are carried through.
public struct HomeDashboard: Equatable, Sendable {

    // MARK: Output types

    public enum Load: Equatable, Sendable {
        /// The album list has not been read (or could not be). No figure is available.
        case notLoaded
        /// The library was read and holds no albums.
        case empty
        case ready
    }

    /// A count for the last 30 days against the 30 before.
    public struct Comparison: Equatable, Sendable {
        public let last: Int
        public let before: Int
        public var delta: Int { last - before }
    }

    /// How the never-played count moved since a saved earlier reading.
    public struct NeverPlayedChange: Equatable, Sendable {
        public let delta: Int
        public let since: Date
    }

    /// Picks the owner has not acted on plus arrived albums nobody has played. `picks` is nil when the Librarian is unavailable.
    public struct Waiting: Equatable, Sendable {
        public let picks: Int?
        public let unplayedArrivals: Int
        public var total: Int { (picks ?? 0) + unplayedArrivals }
    }

    public enum ShelfBin: String, CaseIterable, Equatable, Sendable {
        case thisMonth, oneToSixMonths, sixToTwelveMonths, oneToTwoYears, twoYearsPlus, never
        public var label: String {
            switch self {
            case .thisMonth: "This month"
            case .oneToSixMonths: "1–6 months"
            case .sixToTwelveMonths: "6–12 months"
            case .oneToTwoYears: "1–2 years"
            case .twoYearsPlus: "2+ years"
            case .never: "Never"
            }
        }
    }

    public struct ShelfLife: Equatable, Sendable {
        /// Always the six bins, in order.
        public let bins: [(bin: ShelfBin, count: Int)]
        /// Albums with plays but no last-played time: in no bin, counted here so the bins plus this equal the library.
        public let unknownPlayed: Int
        /// Up to four Navidrome album ids that have waited longest (never played, oldest added first, then oldest last play).
        public let longestUnplayed: [String]
        public func count(_ bin: ShelfBin) -> Int { bins.first { $0.bin == bin }?.count ?? 0 }

        public static func == (a: ShelfLife, b: ShelfLife) -> Bool {
            a.unknownPlayed == b.unknownPlayed && a.longestUnplayed == b.longestUnplayed
                && a.bins.map(\.bin) == b.bins.map(\.bin) && a.bins.map(\.count) == b.bins.map(\.count)
        }
    }

    public enum GrowthRange: String, CaseIterable, Equatable, Sendable {
        case threeMonths = "3M", oneYear = "1Y", fiveYears = "5Y", all = "All"
    }

    public struct GrowthPoint: Equatable, Sendable {
        /// Start of the bucket (a week, a month or three months).
        public let start: Date
        /// Albums added inside the bucket.
        public let added: Int
        /// Albums in the library at the end of the bucket (everything added up to then).
        public let total: Int
    }

    public struct GrowthSeries: Equatable, Sendable {
        public let range: GrowthRange
        public let points: [GrowthPoint]
        /// Albums Navidrome gave no added date, left out of the series.
        public let undated: Int
    }

    /// One decade: its share of the dated albums and, when the server's recent window is sound, its share of recent listens.
    /// Shares are fractions (0.34), written as whole percentages by the view.
    public struct DecadeRow: Equatable, Sendable {
        public let label: String
        public let ownedShare: Double
        public let listenShare: Double?
    }

    public enum ArrivalStage: Int, CaseIterable, Equatable, Sendable {
        case found, downloading, importing, inLibrary
        public var label: String {
            switch self { case .found: "Found"; case .downloading: "Downloading"; case .importing: "Importing"; case .inLibrary: "In library" }
        }
    }

    public enum ArrivalRow: Equatable, Sendable, Identifiable {
        /// A Get in progress, waiting or failed. `failure` is the server's reason in words when it failed.
        case job(id: String, title: String, artist: String, stage: ArrivalStage, failure: String?)
        /// An album that reached the library recently and has no plays; the row offers Play.
        case arrived(albumID: String, title: String, artist: String)

        public var id: String {
            switch self { case .job(let id, _, _, _, _): "job|" + id; case .arrived(let id, _, _): "album|" + id }
        }
    }

    public enum Notice: Equatable, Sendable {
        case librarianUnreachable
        /// A failed Get: the first one's title and reason, and how many more failed.
        case failedJob(title: String, reason: String, others: Int)
    }

    // MARK: Values

    public let load: Load
    /// Albums owned. nil only when the list was not read.
    public let albumCount: Int?
    /// Added in the last 30 days against the 30 before. nil when no album carries an added date.
    public let added: Comparison?
    /// Albums with no plays. nil when the list was not read.
    public let neverPlayed: Int?
    public let neverPlayedChange: NeverPlayedChange?
    public let waiting: Waiting?
    public let shelfLife: ShelfLife?
    public let growth: [GrowthRange: GrowthSeries]
    /// Decades of the dated albums, oldest first. Empty when no album has a year.
    public let decades: [DecadeRow]
    /// Whether the listen shares in `decades` came from a sound taste window (else every `listenShare` is nil).
    public let listenSharesAvailable: Bool
    /// At most four rows: Gets needing attention, then moving, then waiting, then arrived and unplayed.
    public let arrivals: [ArrivalRow]
    /// Rows beyond the four shown, for "All downloads".
    public let arrivalsHidden: Int
    public let notice: Notice?

    public func series(_ range: GrowthRange) -> GrowthSeries? { growth[range] }

    public static let notLoaded = HomeDashboard.build(Inputs(albums: nil))

    // MARK: Inputs

    public struct NeverPlayedBaseline: Equatable, Sendable {
        public let count: Int
        public let date: Date
        public init(count: Int, date: Date) { self.count = count; self.date = date }
    }

    /// Everything a build reads. All of it is a model the app already holds.
    public struct Inputs: Sendable {
        /// Navidrome's whole album list, or nil when it was not read.
        public var albums: [NavidromeAlbum]?
        /// The Gets the owner has not cleared (`AcquisitionModel.visibleJobs`).
        public var jobs: [Acquisition] = []
        /// The saved taste profiles, when the server has them.
        public var taste: TasteProfiles?
        /// Recommendations the owner has not acted on, when the Librarian answered.
        public var picksCount: Int?
        public var librarianReachable = true
        public var neverPlayedBaseline: NeverPlayedBaseline?
        public var now = Date()
        public var calendar = Calendar(identifier: .gregorian)

        public init(albums: [NavidromeAlbum]?, jobs: [Acquisition] = [], taste: TasteProfiles? = nil, picksCount: Int? = nil,
                    librarianReachable: Bool = true, neverPlayedBaseline: NeverPlayedBaseline? = nil,
                    now: Date = Date(), calendar: Calendar = Calendar(identifier: .gregorian)) {
            self.albums = albums; self.jobs = jobs; self.taste = taste; self.picksCount = picksCount
            self.librarianReachable = librarianReachable; self.neverPlayedBaseline = neverPlayedBaseline
            self.now = now; self.calendar = calendar
        }
    }

    // MARK: Build

    public static let maxArrivalRows = 4
    /// How recently an album must have arrived to be offered as "arrived and unplayed".
    static let arrivalDays = 14

    public static func build(_ input: Inputs) -> HomeDashboard {
        let notice = Self.notice(for: input)
        let ownJobs = Self.jobRows(input.jobs)

        guard let albums = input.albums else {
            return HomeDashboard(load: .notLoaded, albumCount: nil, added: nil, neverPlayed: nil, neverPlayedChange: nil,
                                 waiting: nil, shelfLife: nil, growth: [:], decades: [], listenSharesAvailable: false,
                                 arrivals: Array(ownJobs.prefix(maxArrivalRows)), arrivalsHidden: max(0, ownJobs.count - maxArrivalRows),
                                 notice: notice)
        }
        guard !albums.isEmpty else {
            return HomeDashboard(load: .empty, albumCount: 0, added: nil, neverPlayed: nil, neverPlayedChange: nil,
                                 waiting: Waiting(picks: input.librarianReachable ? input.picksCount : nil, unplayedArrivals: 0),
                                 shelfLife: nil, growth: [:], decades: [], listenSharesAvailable: false,
                                 arrivals: Array(ownJobs.prefix(maxArrivalRows)), arrivalsHidden: max(0, ownJobs.count - maxArrivalRows),
                                 notice: notice)
        }

        let cal = input.calendar, now = input.now
        let parse = DateParser()
        let created = albums.map { $0.created.flatMap(parse.date) }
        let played = albums.map { $0.played.flatMap(parse.date) }
        func hasPlays(_ i: Int) -> Bool { (albums[i].playCount ?? 0) > 0 || played[i] != nil }

        // Added in the last 30 days against the 30 before.
        let datedCount = created.compactMap { $0 }.count
        var added: Comparison?
        if datedCount > 0, let d30 = cal.date(byAdding: .day, value: -30, to: now), let d60 = cal.date(byAdding: .day, value: -60, to: now) {
            let last = created.compactMap { $0 }.filter { $0 > d30 && $0 <= now }.count
            let before = created.compactMap { $0 }.filter { $0 > d60 && $0 <= d30 }.count
            added = Comparison(last: last, before: before)
        }

        // Shelf life and never played.
        var counts: [ShelfBin: Int] = [:]
        var unknownPlayed = 0
        for i in albums.indices {
            if let p = played[i] {
                let months = max(0, cal.dateComponents([.month], from: p, to: now).month ?? 0)
                let bin: ShelfBin = months < 1 ? .thisMonth : months < 6 ? .oneToSixMonths : months < 12 ? .sixToTwelveMonths
                    : months < 24 ? .oneToTwoYears : .twoYearsPlus
                counts[bin, default: 0] += 1
            } else if hasPlays(i) {
                unknownPlayed += 1
            } else {
                counts[.never, default: 0] += 1
            }
        }
        let never = counts[.never] ?? 0
        let longest = Self.longestUnplayed(albums: albums, created: created, played: played, hasPlays: hasPlays)
        let shelf = ShelfLife(bins: ShelfBin.allCases.map { ($0, counts[$0] ?? 0) }, unknownPlayed: unknownPlayed, longestUnplayed: longest)
        let change = input.neverPlayedBaseline.map { NeverPlayedChange(delta: never - $0.count, since: $0.date) }

        // Arrived and unplayed: added recently, no plays.
        let arrivalCutoff = cal.date(byAdding: .day, value: -arrivalDays, to: now) ?? now
        let arrivedIdx = albums.indices
            .filter { i in !hasPlays(i) && (created[i].map { $0 > arrivalCutoff } ?? false) }
            .sorted { (created[$0] ?? .distantPast) > (created[$1] ?? .distantPast) }
        let arrivedRows = arrivedIdx.map { ArrivalRow.arrived(albumID: albums[$0].id, title: albums[$0].name, artist: albums[$0].artist ?? "Unknown artist") }
        let allRows = ownJobs + arrivedRows

        // Without the Librarian there are no picks and no listen shares; the Navidrome figures stay.
        let picks = input.librarianReachable ? input.picksCount : nil
        let tasteProfiles = input.librarianReachable ? input.taste : nil
        let (decades, listenOK) = Self.decades(albums: albums, taste: tasteProfiles)

        var growth: [GrowthRange: GrowthSeries] = [:]
        let datedDates = created.compactMap { $0 }.sorted()
        for r in GrowthRange.allCases {
            if let s = Self.growth(r, dates: datedDates, undated: albums.count - datedCount, now: now, calendar: cal) { growth[r] = s }
        }

        return HomeDashboard(load: .ready, albumCount: albums.count, added: added, neverPlayed: never, neverPlayedChange: change,
                             waiting: Waiting(picks: picks, unplayedArrivals: arrivedRows.count), shelfLife: shelf, growth: growth,
                             decades: decades, listenSharesAvailable: listenOK,
                             arrivals: Array(allRows.prefix(maxArrivalRows)), arrivalsHidden: max(0, allRows.count - maxArrivalRows),
                             notice: notice)
    }

    // MARK: Pieces

    /// ISO 8601 with or without fractional seconds, as Navidrome writes them.
    private struct DateParser {
        private let plain = ISO8601DateFormatter()
        private let fractional: ISO8601DateFormatter = {
            let f = ISO8601DateFormatter(); f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]; return f
        }()
        func date(_ s: String) -> Date? { fractional.date(from: s) ?? plain.date(from: s) }
    }

    private static func longestUnplayed(albums: [NavidromeAlbum], created: [Date?], played: [Date?], hasPlays: (Int) -> Bool) -> [String] {
        let never = albums.indices.filter { !hasPlays($0) }
            .sorted { a, b in
                switch (created[a], created[b]) {
                case let (x?, y?): x != y ? x < y : albums[a].id < albums[b].id
                case (_?, nil): true
                case (nil, _?): false
                case (nil, nil): albums[a].id < albums[b].id
                }
            }
        var ids = never.prefix(4).map { albums[$0].id }
        if ids.count < 4 {
            let rest = albums.indices.filter { played[$0] != nil }.sorted { played[$0]! < played[$1]! }
            ids += rest.prefix(4 - ids.count).map { albums[$0].id }
        }
        return ids
    }

    static func decadeLabel(_ year: Int) -> String { "\(year / 10 * 10)s" }

    private static func decades(albums: [NavidromeAlbum], taste: TasteProfiles?) -> ([DecadeRow], Bool) {
        let years = albums.compactMap(\.year).filter { $0 > 0 }
        guard !years.isEmpty else { return ([], false) }
        var owned: [String: Int] = [:]
        for y in years { owned[decadeLabel(y), default: 0] += 1 }
        var listens: [String: Double] = [:]
        var soundWindow = false
        if let w = taste?.window("recent"), !w.lowSample, !w.isLowSample("era") {
            let entries = w.entries("era")
            if !entries.isEmpty { soundWindow = true; for e in entries { listens[e.value] = e.share } }
        }
        let labels = Set(owned.keys).union(listens.keys).sorted()
        let rows = labels.map {
            DecadeRow(label: $0, ownedShare: Double(owned[$0] ?? 0) / Double(years.count), listenShare: soundWindow ? (listens[$0] ?? 0) : nil)
        }
        return (rows, soundWindow)
    }

    /// Cumulative total and albums added per bucket. Weekly for 3M, monthly for 1Y and 5Y, monthly (or three-monthly past
    /// 60 buckets) for All. nil when fewer than two buckets can be drawn or no album carries an added date.
    static func growth(_ range: GrowthRange, dates sorted: [Date], undated: Int, now: Date, calendar cal: Calendar) -> GrowthSeries? {
        guard !sorted.isEmpty else { return nil }
        var starts: [Date] = []
        func back(_ comp: Calendar.Component, _ step: Int, from first: Date, count: Int) -> [Date] {
            var out = [first]
            for i in 1..<max(count, 1) { if let d = cal.date(byAdding: comp, value: -step * i, to: first) { out.append(d) } }
            return out.reversed()
        }
        let monthStart = cal.dateInterval(of: .month, for: now)?.start ?? now
        switch range {
        case .threeMonths:
            let weekStart = cal.dateInterval(of: .weekOfYear, for: now)?.start ?? now
            starts = back(.weekOfYear, 1, from: weekStart, count: 13)
        case .oneYear: starts = back(.month, 1, from: monthStart, count: 12)
        case .fiveYears: starts = back(.month, 1, from: monthStart, count: 60)
        case .all:
            let firstMonth = cal.dateInterval(of: .month, for: sorted[0])?.start ?? sorted[0]
            let months = max(1, (cal.dateComponents([.month], from: firstMonth, to: monthStart).month ?? 0) + 1)
            if months > 60 { starts = back(.month, 3, from: monthStart, count: Int((Double(months) / 3).rounded(.up))) }
            else { starts = back(.month, 1, from: monthStart, count: months) }
        }
        guard starts.count >= 2 else { return nil }
        var points: [GrowthPoint] = []
        var i = 0
        // Everything before the first bucket is already in the library when the series begins.
        while i < sorted.count, sorted[i] < starts[0] { i += 1 }
        var total = i
        for (b, start) in starts.enumerated() {
            let end = b + 1 < starts.count ? starts[b + 1] : Date.distantFuture   // the last bucket also takes anything dated after now
            var n = 0
            while i < sorted.count, sorted[i] < end { n += 1; i += 1 }
            total += n
            points.append(GrowthPoint(start: start, added: n, total: total))
        }
        return GrowthSeries(range: range, points: points, undated: undated)
    }

    // MARK: Arrivals and notice

    static func stage(of job: Acquisition) -> ArrivalStage {
        switch job.status {
        case "downloading", "monitoring", "slskd_error", "monitor_error", "monitor_recovery_failed", "source_switch_failed", "recovery_unavailable": .downloading
        case "download_complete_waiting_for_folder", "importing": .importing
        case "imported": .inLibrary
        default: .found
        }
    }

    private static func jobRows(_ jobs: [Acquisition]) -> [ArrivalRow] {
        func rank(_ j: Acquisition) -> Int { switch j.phase { case .failed: 0; case .working: 1; case .queued: 2; case .other: 3; case .imported: 4 } }
        return jobs.filter { !$0.isSong && $0.phase != .imported }
            .sorted { a, b in rank(a) != rank(b) ? rank(a) < rank(b) : (a.updatedAt ?? 0) > (b.updatedAt ?? 0) }
            .map { j in
                .job(id: j.id, title: j.title, artist: j.artist, stage: stage(of: j),
                     failure: j.phase == .failed ? (j.details?.message ?? AcquisitionModel.statusText(j)) : nil)
            }
    }

    private static func notice(for input: Inputs) -> Notice? {
        if !input.librarianReachable { return .librarianUnreachable }
        let failed = input.jobs.filter { !$0.isSong && $0.phase == .failed }
            .sorted { ($0.updatedAt ?? 0) > ($1.updatedAt ?? 0) }
        guard let first = failed.first else { return nil }
        return .failedJob(title: first.title, reason: first.details?.message ?? AcquisitionModel.statusText(first), others: failed.count - 1)
    }
}
