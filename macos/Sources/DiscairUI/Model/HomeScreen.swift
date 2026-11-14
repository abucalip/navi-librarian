import DiscairLibrarian
import DiscairNavidrome
import Foundation

/// What each module of the redesigned Cupertino Home says in each state (`docs/redesign.md` section 5.1, step M8). Pure: the
/// figures come from `HomeDashboard` (M5), the taste profiles, the insight lenses and the server's own answers, and this turns
/// them into the state a module draws and the words it uses. No SwiftUI, no network. The views only draw these values.
///
/// Rules kept here: missing is not zero (an absent figure has its own sentence); the server's headline, card titles and card
/// bodies are shown as sent; shifts come only from `shifts[]`; nothing is composed into a claim.
enum HomeScreen {

    // MARK: Layout

    /// Below this content width every row stacks into one column in reading order (section 5.1). The queue inspector being open
    /// narrows the content, so the same rule covers it.
    static let stackBelow: CGFloat = 860

    static func isStacked(contentWidth: CGFloat) -> Bool { contentWidth < stackBelow }

    // MARK: Today's pick

    /// The pick deck. `index` is clamped, so a dismissal that shortens the list never leaves a hole.
    static func pickPosition(index: Int, count: Int) -> (index: Int, label: String)? {
        guard count > 0 else { return nil }
        let i = min(max(index, 0), count - 1)
        return (i, "\(i + 1) of \(count)")
    }

    enum PickKey: Equatable { case get, save, notForMe, play }

    static func pickKey(arrow: PickArrow) -> PickKey? {
        switch arrow { case .right: .get; case .down: .save; case .left: .notForMe }
    }
    enum PickArrow { case left, right, down }

    /// What Space does on the pick: an owned album plays; one the library lacks says so instead of doing nothing.
    enum SpaceOutcome: Equatable { case play, notOwned(notice: String) }
    static func spaceOutcome(owned: Bool) -> SpaceOutcome {
        owned ? .play : .notOwned(notice: "This album is not in your library yet, so there is nothing to play. Press → to get it.")
    }

    /// What the pick panel shows when it has no pick: its own sentence and the button that fixes it.
    enum PickEmpty: Equatable {
        case needsHistory           // no listening source: nothing is guessed
        case noneRightNow           // a source exists and the server has nothing for today
        case withoutLibrarian
    }

    static func pickEmpty(librarianReachable: Bool, hasListeningSource: Bool, note: String?) -> PickEmpty {
        if !librarianReachable { return .withoutLibrarian }
        if note?.contains("Settings") == true || !hasListeningSource { return .needsHistory }
        return .noneRightNow
    }

    // MARK: Collection over time

    enum GrowthMode: String, CaseIterable, Equatable { case total = "Total", added = "Added" }

    /// "Albums in your library, from the date each was added · 1 December 2025 to today". States the exact period.
    static func growthSubtitle(_ series: HomeDashboard.GrowthSeries?, mode: GrowthMode, calendar: Calendar = .current) -> String {
        let what = mode == .total ? "Albums in your library, from the date each was added" : "Albums added per period, from the date each was added"
        guard let first = series?.points.first?.start else { return what }
        return "\(what) · \(fullDate(first, calendar: calendar)) to today"
    }

    /// The growth plot's state: with fewer than 2 buckets there is nothing to draw.
    static func growthAvailable(_ series: HomeDashboard.GrowthSeries?) -> Bool { (series?.points.count ?? 0) >= 2 }

    /// The noun for one point of the series: a week for 3M, a quarter when All spreads over more than 60 months, else a month.
    static func periodNoun(_ series: HomeDashboard.GrowthSeries, calendar: Calendar = .current) -> String {
        if series.range == .threeMonths { return "week" }
        if series.range == .all, series.points.count >= 2,
           let days = calendar.dateComponents([.day], from: series.points[0].start, to: series.points[1].start).day, days > 80 { return "quarter" }
        return "month"
    }

    /// The tooltip's second line: "12 July 2026 · 5 added that week".
    static func growthDetail(_ point: HomeDashboard.GrowthPoint, series: HomeDashboard.GrowthSeries, calendar: Calendar = .current) -> String {
        "\(fullDate(point.start, calendar: calendar)) · \(count(point.added)) added that \(periodNoun(series, calendar: calendar))"
    }

    /// Seven evenly spread labels under the plot: weeks as "6 Sep", months as "Feb", and with years once the series spans more than a year.
    static func growthAxisLabels(_ series: HomeDashboard.GrowthSeries, calendar: Calendar = .current) -> [String] {
        let pts = series.points
        guard pts.count >= 2, let span = calendar.dateComponents([.month], from: pts[0].start, to: pts[pts.count - 1].start).month else { return [] }
        let format = series.range == .threeMonths ? "d MMM" : (span > 12 ? "MMM yy" : "MMM")
        return CUChartMath.labelIndices(count: pts.count, labels: min(7, pts.count)).map { formatted(pts[$0].start, format, calendar: calendar) }
    }

    /// The one annotation of the Total line: the period with the most albums added, when it is clearly a peak.
    static func biggestPeriod(_ series: HomeDashboard.GrowthSeries, calendar: Calendar = .current) -> CUChartAnnotation? {
        guard series.points.count >= 6, let best = series.points.enumerated().max(by: { $0.element.added < $1.element.added }), best.element.added > 0 else { return nil }
        let name = series.range == .threeMonths ? dayAndMonth(best.element.start, calendar: calendar) : formatted(best.element.start, "MMMM", calendar: calendar)
        return CUChartAnnotation(index: best.offset, text: "Biggest \(periodNoun(series, calendar: calendar)): \(name), \(count(best.element.added)) added")
    }

    // MARK: Taste

    struct TasteShiftRow: Equatable {
        let label: String
        /// Percent, 0 to 100.
        let before: Double
        let now: Double
    }

    enum TasteState: Equatable {
        case loading
        /// No headline yet: show progress toward the server's listen minimum.
        case progress(listens: Int, need: Int)
        /// The server's headline, and each listed shift. `shifts` may be empty when the headline is not about a shift.
        case ready(headline: String, shifts: [TasteShiftRow], recentLabel: String, recentListens: Int, allTimeListens: Int)
    }

    static func taste(profiles: TasteProfiles?, loaded: Bool) -> TasteState {
        guard loaded else { return .loading }
        let need = profiles?.config.minListens ?? 50
        guard let profiles, let headline = profiles.cardHeadline, !headline.text.isEmpty else {
            return .progress(listens: profiles?.window("recent")?.listens ?? 0, need: need)
        }
        let rows = profiles.cardShifts(in: headline.window).map {
            TasteShiftRow(label: capitalFirst($0.value), before: $0.fromShare * 100, now: $0.toShare * 100)
        }
        let recentLabel = headline.window == "mid" ? "Past year" : "Last \(profiles.config.recentDays) days"
        return .ready(headline: headline.text, shifts: rows, recentLabel: recentLabel,
                      recentListens: profiles.window(headline.window)?.listens ?? 0, allTimeListens: profiles.window("all_time")?.listens ?? 0)
    }

    /// "YOUR TASTE · LAST 90 DAYS AGAINST ALL TIME", from the window the headline speaks about.
    static func tasteEyebrow(profiles: TasteProfiles?) -> String {
        let window = profiles?.cardHeadline?.window ?? "recent"
        let span = window == "mid" ? "Past year" : "Last \(profiles?.config.recentDays ?? 90) days"
        return "Your taste · \(span) against all time"
    }

    // MARK: Shelf life

    /// The shelf-life chart's state: it needs at least one album in a bin.
    static func shelfAvailable(_ shelf: HomeDashboard.ShelfLife?) -> Bool { (shelf?.bins.reduce(0) { $0 + $1.count } ?? 0) > 0 }

    // MARK: Server activity

    struct ActivityRow: Equatable, Identifiable {
        enum Fix: Equatable { case openSettings, fillPopularity }
        let id: String
        let name: String
        let symbol: String
        let status: CUStatus
        let line: String
        var fix: Fix? = nil
        /// The button's words ("Continue", "Try again"), when there is a fix.
        var fixTitle: String? = nil
    }

    struct ActivityInput {
        var librarianReachable: Bool
        var insightsLive: Bool
        var insightsError: Bool
        var insightsLoadedAt: Date?
        var lensesOn: Int
        var lensesTotal: Int
        var tasteLoaded: Bool
        var tasteRefreshing: Bool
        var tasteNote: String?
        var tasteListens: Int?
        var graphCoverage: String?
        /// `GET /api/insights/popularity/status`, when read.
        var popularity: JobStatus?
        /// `GET /api/insights/refresh/status` (D3), when the server serves it.
        var insightsJob: JobStatus?
        var now = Date()
    }

    /// One state word and one line per background job. With the Librarian unreachable everything it would report is Unknown.
    static func activity(_ i: ActivityInput) -> [ActivityRow] {
        guard i.librarianReachable else {
            return [("insights", "Insight lenses", "lightbulb"), ("taste", "Taste profile", "waveform"), ("popularity", "Artist popularity", "person"), ("musicbrainz", "MusicBrainz data", "point.3.connected.trianglepath.dotted")]
                .map { ActivityRow(id: $0.0, name: $0.1, symbol: $0.2, status: .unknown, line: "Librarian is not answering.") }
        }
        var rows: [ActivityRow] = []

        if let job = i.insightsJob, job.status != nil || job.lastGood != nil {
            rows.append(insightsJobRow(job, i))
        } else if !i.insightsLive {
            rows.append(ActivityRow(id: "insights", name: "Insight lenses", symbol: "lightbulb", status: .notLoaded, line: "Not read yet"))
        } else if i.insightsError {
            let when = i.insightsLoadedAt.map { " Last read \(relative($0, now: i.now))." } ?? ""
            rows.append(ActivityRow(id: "insights", name: "Insight lenses", symbol: "lightbulb", status: .notUpdating, line: "The last read failed.\(when)"))
        } else {
            let when = i.insightsLoadedAt.map { "Read \(relative($0, now: i.now)) · " } ?? ""
            rows.append(ActivityRow(id: "insights", name: "Insight lenses", symbol: "lightbulb", status: .done, line: "\(when)\(i.lensesOn) of \(i.lensesTotal) on"))
        }

        if let note = i.tasteNote {
            rows.append(ActivityRow(id: "taste", name: "Taste profile", symbol: "waveform", status: .notUpdating, line: note))
        } else if !i.tasteLoaded {
            rows.append(ActivityRow(id: "taste", name: "Taste profile", symbol: "waveform", status: .notLoaded, line: i.tasteRefreshing ? "Refreshing now" : "Not read yet"))
        } else {
            let listens = i.tasteListens.map { "\(count($0)) listens in the recent window" } ?? "No listening history yet"
            rows.append(ActivityRow(id: "taste", name: "Taste profile", symbol: "waveform", status: .done, line: (i.tasteRefreshing ? "Refreshing now · " : "At launch · ") + listens))
        }

        rows.append(popularityRow(i.popularity, now: i.now))

        if let coverage = i.graphCoverage {
            let loaded = coverage != "none"
            rows.append(ActivityRow(id: "musicbrainz", name: "MusicBrainz data", symbol: "point.3.connected.trianglepath.dotted",
                                    status: loaded ? .loaded : .notLoaded, line: "Graph coverage: \(coverage)"))
        }
        return rows
    }

    private static func insightsJobRow(_ job: JobStatus, _ i: ActivityInput) -> ActivityRow {
        let finished = job.lastGood?.finishedAt.map { Date(timeIntervalSince1970: $0) }
        let refreshed = finished.map { "Refreshed \(relative($0, now: i.now))" } ?? "Not refreshed yet"
        let next = job.retryAfter.map { $0 <= 0 ? "next due now" : "next in \(duration($0))" }
        let line = [refreshed, next].compactMap { $0 }.joined(separator: " · ")
        let failed = job.status?.state == "failed"
        return ActivityRow(id: "insights", name: "Insight lenses", symbol: "lightbulb", status: failed ? .notUpdating : .done,
                           line: failed ? "The last refresh failed. " + line : (job.running ? "Refreshing now · " + line : line))
    }

    /// Artist popularity is filled by hand only (the server has no scheduler): the row says how many artists are left and offers
    /// the button that runs the next bounded batch.
    static func popularityRow(_ job: JobStatus?, now: Date) -> ActivityRow {
        func row(_ status: CUStatus, _ line: String, _ fix: String? = nil) -> ActivityRow {
            ActivityRow(id: "popularity", name: "Artist popularity", symbol: "person", status: status, line: line,
                        fix: fix == nil ? nil : .fillPopularity, fixTitle: fix)
        }
        guard let job else { return row(.notLoaded, "Not read yet") }
        guard let newest = job.status ?? job.lastGood else { return row(.paused, "No figures yet · runs only when you ask", "Start") }
        let pending = Int(newest.progress["pending"] ?? job.lastGood?.progress["pending"] ?? 0)
        if job.running { return row(.paused, "Filling now\(pending > 0 ? " · \(count(pending)) artists left" : "")") }
        switch newest.state {
        case "failed":
            let reason = newest.error.map { ": \($0)" } ?? ""
            return row(.notUpdating, "The last fill failed\(reason). Earlier figures are kept.", "Try again")
        case "queued": return row(.paused, "\(count(pending)) artists left · runs only when you ask", "Continue")
        default:
            if pending > 0 { return row(.paused, "\(count(pending)) artists left · runs only when you ask", "Continue") }
            let when = newest.finishedAt.map { " · filled \(relative(Date(timeIntervalSince1970: $0), now: now))" } ?? ""
            return row(.done, "Figures are up to date\(when)")
        }
    }

    /// "4 hours", "35 minutes", "1 minute".
    static func duration(_ seconds: Double) -> String {
        let minutes = max(1, Int((seconds / 60).rounded()))
        if minutes < 90 { return "\(minutes) minute\(minutes == 1 ? "" : "s")" }
        let hours = Int((Double(minutes) / 60).rounded())
        return "\(hours) hour\(hours == 1 ? "" : "s")"
    }

    // MARK: Phone handoff (D5)

    /// The queue another client saved, offered as "Playing on your phone". Only when it is not this app's own queue, was saved
    /// within `handoffHours`, has a current song, and that song is not the one this Mac is already playing.
    static let handoffHours = 24

    static func handoff(queue: NavidromePlayQueue?, now: Date, clientName: String, playingSongID: String?) -> HomeDashboard.Handoff? {
        guard let queue, let song = queue.current, let changed = queue.changed else { return nil }
        if (queue.changedBy ?? "").lowercased() == clientName.lowercased() { return nil }
        guard now.timeIntervalSince(changed) <= Double(handoffHours) * 3600, changed <= now.addingTimeInterval(300) else { return nil }
        if song.id == playingSongID { return nil }
        return HomeDashboard.Handoff(songID: song.id, title: song.title, artist: song.artist ?? "Unknown artist",
                                     positionSeconds: queue.positionMs / 1000, durationSeconds: song.duration)
    }

    /// "Ascension Day, Talk Talk · 2:41 of 6:00".
    static func handoffText(_ h: HomeDashboard.Handoff) -> String {
        let place = h.durationSeconds.map { "\(clock(h.positionSeconds)) of \(clock($0))" } ?? clock(h.positionSeconds)
        return "\(h.title), \(h.artist) · \(place)"
    }

    static func clock(_ seconds: Int) -> String { String(format: "%d:%02d", max(0, seconds) / 60, max(0, seconds) % 60) }

    /// The queue to start here: from the song that was playing, with the rest behind it.
    static func handoffStart(queue: NavidromePlayQueue) -> (songs: [NavidromeSong], startAt: Int) {
        (queue.songs, queue.songs.firstIndex { $0.id == queue.currentID } ?? 0)
    }

    // MARK: Which page

    /// The whole page's state, for the states that replace more than one module.
    enum Page: Equatable {
        /// The album list has not been read yet.
        case loading
        /// The app is not connected to a library at all (a fresh install, sample data): nothing is drawn as a figure.
        case ready
    }

    static func page(dashboard: HomeDashboard, libraryPhaseLoading: Bool) -> Page {
        dashboard.load == .notLoaded && libraryPhaseLoading ? .loading : .ready
    }

    // MARK: Never-played readings (the baseline for "change since the first of last month")

    struct Reading: Codable, Equatable {
        let count: Int
        let date: Date
    }

    /// The reading to compare against: the earliest on or after the first of last month, unless it was taken today.
    static func baseline(_ readings: [Reading], now: Date, calendar: Calendar) -> HomeDashboard.NeverPlayedBaseline? {
        guard let cutoff = windowStart(now: now, calendar: calendar) else { return nil }
        guard let first = readings.filter({ $0.date >= cutoff }).min(by: { $0.date < $1.date }) else { return nil }
        if calendar.isDate(first.date, inSameDayAs: now) { return nil }
        return HomeDashboard.NeverPlayedBaseline(count: first.count, date: first.date)
    }

    /// Adds today's count (once a day) and forgets readings older than the window.
    static func recording(_ readings: [Reading], count: Int, now: Date, calendar: Calendar) -> [Reading] {
        let cutoff = windowStart(now: now, calendar: calendar) ?? .distantPast
        var kept = readings.filter { $0.date >= cutoff }
        if !kept.contains(where: { calendar.isDate($0.date, inSameDayAs: now) }) { kept.append(Reading(count: count, date: now)) }
        return kept.sorted { $0.date < $1.date }
    }

    private static func windowStart(now: Date, calendar: Calendar) -> Date? {
        guard let thisMonth = calendar.dateInterval(of: .month, for: now)?.start else { return nil }
        return calendar.date(byAdding: .month, value: -1, to: thisMonth)
    }

    /// The column label for a shelf-life bin ("1–6 mo").
    static func shortLabel(_ bin: HomeDashboard.ShelfBin) -> String {
        switch bin {
        case .thisMonth: "This month"
        case .oneToSixMonths: "1–6 mo"
        case .sixToTwelveMonths: "6–12 mo"
        case .oneToTwoYears: "1–2 years"
        case .twoYearsPlus: "2+ years"
        case .never: "Never"
        }
    }

    /// Navidrome writes ISO 8601, with or without fractional seconds.
    static func parseDate(_ s: String?) -> Date? {
        guard let s else { return nil }
        let fractional = ISO8601DateFormatter(); fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return fractional.date(from: s) ?? ISO8601DateFormatter().date(from: s)
    }

    // MARK: New on the shelf and Waiting longest (plan 3.2, 3.3)

    /// One tile of "New on the shelf", in the order of plan 3.2. `arrived` and `added` carry the album's added date.
    enum ShelfTile: Equatable {
        case job(id: String, title: String, artist: String, stage: HomeDashboard.ArrivalStage, failure: String?)
        /// `addedAt` is nil only when the album's date is not known to the caller; the status then says "Arrived recently".
        case arrived(albumID: String, title: String, artist: String, addedAt: Date?)
        case radio(playID: Int, title: String, artist: String, station: String)
        case added(albumID: String, title: String, artist: String, addedAt: Date)
    }

    /// The most tiles on the shelf.
    static let shelfLimit = 6

    /// The shelf's tiles: the dashboard's arrival rows in their own order, then recently added albums (newest first, dated albums
    /// only) that are not already shown, until `limit` tiles. `arrivedDates` maps an arrived album's id to its added date.
    static func shelfTiles(arrivals: [HomeDashboard.ArrivalRow], recentlyAdded: [NavidromeAlbum],
                           arrivedDates: [String: Date] = [:], limit: Int = shelfLimit) -> [ShelfTile] {
        var tiles: [ShelfTile] = []
        var shownAlbums = Set<String>()
        for row in arrivals {
            switch row {
            case let .job(id, title, artist, stage, failure):
                tiles.append(.job(id: id, title: title, artist: artist, stage: stage, failure: failure))
            case let .arrived(albumID, title, artist):
                shownAlbums.insert(albumID)
                tiles.append(.arrived(albumID: albumID, title: title, artist: artist, addedAt: arrivedDates[albumID]))
            case let .radio(playID, title, artist, station, _):
                tiles.append(.radio(playID: playID, title: title, artist: artist, station: station))
            }
        }
        for album in recentlyAdded where tiles.count < limit {
            guard !shownAlbums.contains(album.id), let added = parseDate(album.created) else { continue }
            shownAlbums.insert(album.id)
            tiles.append(.added(albumID: album.id, title: album.name, artist: album.artist ?? "Unknown artist", addedAt: added))
        }
        return Array(tiles.prefix(limit))
    }

    /// The words for a Get's stage (plan 3.2).
    static func stageWords(_ stage: HomeDashboard.ArrivalStage) -> String {
        switch stage {
        case .found: return "Looking for a source"
        case .downloading: return "Downloading"
        case .importing: return "Importing"
        case .inLibrary: return "In library"
        }
    }

    /// The colour role of a status line. The view maps each role to a token; the words always carry the meaning too.
    enum StatusRole: Equatable { case warning, danger, accent, secondary }

    struct ShelfStatus: Equatable {
        let text: String
        let role: StatusRole
    }

    /// What VoiceOver says for a tile: "*title* by *artist*, *status line*" (plan section 6). The status is left out when empty.
    static func tileLabel(title: String, artist: String, status: String) -> String {
        "\(title) by \(artist)" + (status.isEmpty ? "" : ", \(status)")
    }

    /// The status line under a shelf tile (plan 3.2).
    static func shelfStatus(_ tile: ShelfTile, now: Date, calendar: Calendar = .current) -> ShelfStatus {
        switch tile {
        case let .job(_, _, _, stage, failure):
            if let failure { return ShelfStatus(text: "Failed · \(failure)", role: .danger) }
            return ShelfStatus(text: stageWords(stage), role: .warning)
        case let .arrived(_, _, _, addedAt):
            guard let addedAt else { return ShelfStatus(text: "Arrived recently", role: .accent) }
            if calendar.isDate(addedAt, inSameDayAs: now) { return ShelfStatus(text: "Arrived today", role: .accent) }
            if let yesterday = calendar.date(byAdding: .day, value: -1, to: now), calendar.isDate(addedAt, inSameDayAs: yesterday) {
                return ShelfStatus(text: "Arrived yesterday", role: .accent)
            }
            return ShelfStatus(text: "Arrived \(dayAndMonth(addedAt, calendar: calendar))", role: .accent)
        case let .radio(_, _, _, station):
            return ShelfStatus(text: station.isEmpty ? "Heard on the radio · Get" : "Heard on \(station) · Get", role: .accent)
        case let .added(_, _, _, addedAt):
            return ShelfStatus(text: "Added \(dayAndMonth(addedAt, calendar: calendar))", role: .secondary)
        }
    }

    /// The header subtitle of "New on the shelf": the full phrase, or "recently added" when every tile is a recently added album
    /// (and when there are no tiles at all).
    static func shelfSubtitle(tiles: [ShelfTile]) -> String {
        let onlyAdded = tiles.allSatisfy { tile in
            if case .added = tile { return true }
            return false
        }
        return onlyAdded ? "recently added" : "arriving, just arrived and heard on the radio"
    }

    /// How far a Get has got, for the stage ring: a quarter, half or three quarters. nil once it is in the library (no ring).
    static func stageFraction(_ stage: HomeDashboard.ArrivalStage) -> Double? {
        switch stage {
        case .found: return 0.25
        case .downloading: return 0.5
        case .importing: return 0.75
        case .inLibrary: return nil
        }
    }

    /// The caption under a "Waiting longest" cover (plan 3.3): "Since March 2023" for an album never played (the month it was
    /// added), "Last played March 2023" for one that was. nil when the date is not known.
    static func waitingCaption(created: Date?, played: Date?, neverPlayed: Bool, calendar: Calendar = .current) -> String? {
        if neverPlayed { return created.map { "Since \(monthAndYear($0, calendar: calendar))" } }
        return played.map { "Last played \(monthAndYear($0, calendar: calendar))" }
    }

    /// The header subtitle of "Waiting longest" (plan 3.3).
    static func waitingSubtitle(allNeverPlayed: Bool) -> String {
        allNeverPlayed ? "albums you own and have never played" : "albums you have not played for the longest time"
    }

    /// How many pick covers the "Next picks" row shows.
    static let nextPicksLimit = 6

    /// The other picks in the order "Next picks" shows them: starting after `index` and wrapping round, the current one left out,
    /// at most `limit`. `index` is clamped as in `pickPosition`. Fewer than two picks gives nothing.
    static func nextPicks(index: Int, count: Int, limit: Int = nextPicksLimit) -> [Int] {
        guard count > 1, limit > 0 else { return [] }
        let current = min(max(index, 0), count - 1)
        return (1..<count).prefix(limit).map { (current + $0) % count }
    }

    // MARK: Summary line (plan 3.4)

    /// Where a summary figure goes when clicked.
    enum SummaryTarget: Equatable { case library, history, neverPlayed }

    struct SummaryFigure: Equatable {
        let text: String
        let target: SummaryTarget
    }

    /// The figures of the summary line, in order. Each is left out when its value is nil. Listens are "as of" a day when the series
    /// is stale (its last day is older than yesterday, in UTC like the series itself).
    static func summaryFigures(_ d: HomeDashboard, now: Date) -> [SummaryFigure] {
        var out: [SummaryFigure] = []
        if let albums = d.albumCount {
            out.append(SummaryFigure(text: "\(count(albums)) \(albums == 1 ? "album" : "albums")", target: .library))
        }
        if let added = d.added?.last {
            out.append(SummaryFigure(text: "\(count(added)) added in 30 days", target: .library))
        }
        if let listens = d.listens {
            let n = listens.last
            let noun = n == 1 ? "listen" : "listens"
            var utc = Calendar(identifier: .gregorian); utc.timeZone = TimeZone(identifier: "UTC")!
            let stale = (utc.dateComponents([.day], from: listens.asOf, to: now).day ?? 0) > 1
            let text = stale ? "\(count(n)) \(noun) in the 7 days to \(dayAndMonth(listens.asOf, calendar: utc))" : "\(count(n)) \(noun) in 7 days"
            out.append(SummaryFigure(text: text, target: .history))
        }
        if let never = d.neverPlayed {
            out.append(SummaryFigure(text: "\(count(never)) never played", target: .neverPlayed))
        }
        return out
    }

    // MARK: Words

    static func count(_ n: Int) -> String { CUValueFormat.number(Double(n)) }

    static func capitalFirst(_ s: String) -> String { s.prefix(1).uppercased() + s.dropFirst() }

    private static func formatted(_ date: Date, _ format: String, calendar: Calendar) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_GB"); f.calendar = calendar; f.timeZone = calendar.timeZone; f.dateFormat = format
        return f.string(from: date)
    }

    /// "1 October".
    static func dayAndMonth(_ date: Date, calendar: Calendar = .current) -> String { formatted(date, "d MMMM", calendar: calendar) }
    /// "March 2023".
    static func monthAndYear(_ date: Date, calendar: Calendar = .current) -> String { formatted(date, "MMMM yyyy", calendar: calendar) }
    /// "1 December 2025".
    static func fullDate(_ date: Date, calendar: Calendar = .current) -> String { formatted(date, "d MMMM yyyy", calendar: calendar) }
    /// "Wednesday 11 November", the date on the page header.
    static func headerDate(_ date: Date, calendar: Calendar = .current) -> String { formatted(date, "EEEE d MMMM", calendar: calendar) }

    /// "2 hours ago" under a day, a full date after that (section 3).
    static func relative(_ date: Date, now: Date) -> String {
        if now.timeIntervalSince(date) < 60 { return "just now" }
        if now.timeIntervalSince(date) < 86_400 {
            let f = RelativeDateTimeFormatter()
            f.locale = Locale(identifier: "en_GB"); f.unitsStyle = .full; f.dateTimeStyle = .numeric
            return f.localizedString(for: date, relativeTo: now)
        }
        return dayAndMonth(date) + ", " + formatted(date, "HH:mm", calendar: .current)
    }
}
