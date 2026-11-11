import Foundation

/// One ranked value in a taste window ("jazz", 0.3 share). `docs/SERVER_V2_CONTRACT.md`, `GET /api/insights/taste`.
public struct TasteEntry: Decodable, Equatable, Sendable {
    public let value: String
    public let count: Int
    public let share: Double

    enum CodingKeys: String, CodingKey { case value, count, share }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        value = (try? c.decode(String.self, forKey: .value)) ?? ""
        count = (try? c.decode(Int.self, forKey: .count)) ?? 0
        share = (try? c.decode(Double.self, forKey: .share)) ?? 0
    }
    public init(value: String, count: Int = 0, share: Double) { self.value = value; self.count = count; self.share = share }
}

/// One time window (`recent`, `mid`, `all_time`). `lowSample` and `dimensionLowSample` are the server's own flags: a window
/// or dimension flagged low-sample is shown as progress, never as a finding.
public struct TasteWindow: Decodable, Equatable, Sendable {
    public let listens: Int
    public let lowSample: Bool
    public let attributed: [String: Int]
    public let dimensionLowSample: [String: Bool]
    public let dimensions: [String: [TasteEntry]]

    enum CodingKeys: String, CodingKey { case listens, lowSample = "low_sample", attributed, dimensionLowSample = "dimension_low_sample", dimensions }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        listens = (try? c.decode(Int.self, forKey: .listens)) ?? 0
        lowSample = (try? c.decode(Bool.self, forKey: .lowSample)) ?? true       // unknown means not sound
        attributed = (try? c.decode([String: Int].self, forKey: .attributed)) ?? [:]
        dimensionLowSample = (try? c.decode([String: Bool].self, forKey: .dimensionLowSample)) ?? [:]
        dimensions = (try? c.decode([String: [TasteEntry]].self, forKey: .dimensions)) ?? [:]
    }
    public init(listens: Int, lowSample: Bool, attributed: [String: Int] = [:], dimensionLowSample: [String: Bool] = [:], dimensions: [String: [TasteEntry]] = [:]) {
        self.listens = listens; self.lowSample = lowSample; self.attributed = attributed
        self.dimensionLowSample = dimensionLowSample; self.dimensions = dimensions
    }

    public func isLowSample(_ dimension: String) -> Bool { dimensionLowSample[dimension] ?? true }
    public func entries(_ dimension: String) -> [TasteEntry] { dimensions[dimension] ?? [] }
}

/// A stated shift. The server lists one only when both sides are sound, so a client states none that is not listed.
public struct TasteShift: Decodable, Equatable, Sendable {
    public let window: String
    public let dimension: String
    public let value: String
    public let direction: String
    public let fromShare: Double
    public let toShare: Double

    enum CodingKeys: String, CodingKey { case window, dimension, value, direction, fromShare = "from_share", toShare = "to_share" }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        window = (try? c.decode(String.self, forKey: .window)) ?? ""
        dimension = (try? c.decode(String.self, forKey: .dimension)) ?? ""
        value = (try? c.decode(String.self, forKey: .value)) ?? ""
        direction = (try? c.decode(String.self, forKey: .direction)) ?? ""
        fromShare = (try? c.decode(Double.self, forKey: .fromShare)) ?? 0
        toShare = (try? c.decode(Double.self, forKey: .toShare)) ?? 0
    }
    public init(window: String, dimension: String, value: String, direction: String, fromShare: Double, toShare: Double) {
        self.window = window; self.dimension = dimension; self.value = value; self.direction = direction
        self.fromShare = fromShare; self.toShare = toShare
    }
}

/// The server-written headline. `text` is drawn as given; the app never composes prose.
public struct TasteHeadline: Decodable, Equatable, Sendable {
    public struct Subject: Decodable, Equatable, Sendable { public let dimension: String; public let value: String; public let direction: String }
    public let text: String
    public let kind: String
    public let window: String
    public let subjects: [Subject]

    enum CodingKeys: String, CodingKey { case text, kind, window, subjects }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        text = try c.decode(String.self, forKey: .text).trimmingCharacters(in: .whitespacesAndNewlines)
        kind = (try? c.decode(String.self, forKey: .kind)) ?? ""
        window = (try? c.decode(String.self, forKey: .window)) ?? ""
        subjects = (try? c.decode([Subject].self, forKey: .subjects)) ?? []
    }
}

public struct TasteConfig: Decodable, Equatable, Sendable {
    public let recentDays: Int
    public let midDays: Int
    public let minListens: Int
    public let minAttributed: Int
    public let minShift: Double

    enum CodingKeys: String, CodingKey { case recentDays = "recent_days", midDays = "mid_days", minListens = "min_listens", minAttributed = "min_attributed", minShift = "min_shift" }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        recentDays = Int((try? c.decode(Double.self, forKey: .recentDays)) ?? 90)
        midDays = Int((try? c.decode(Double.self, forKey: .midDays)) ?? 365)
        minListens = (try? c.decode(Int.self, forKey: .minListens)) ?? 50
        minAttributed = (try? c.decode(Int.self, forKey: .minAttributed)) ?? 30
        minShift = (try? c.decode(Double.self, forKey: .minShift)) ?? 0.05
    }
    public init(recentDays: Int = 90, midDays: Int = 365, minListens: Int = 50, minAttributed: Int = 30, minShift: Double = 0.05) {
        self.recentDays = recentDays; self.midDays = midDays; self.minListens = minListens
        self.minAttributed = minAttributed; self.minShift = minShift
    }
}

public struct TasteProfiles: Decodable, Equatable, Sendable {
    public static let windowNames = ["recent", "mid", "all_time"]
    public static let dimensions = ["genre", "era", "area", "label", "collaborator"]

    public let headline: TasteHeadline?
    public let windows: [String: TasteWindow]
    public let shifts: [TasteShift]
    public let config: TasteConfig

    enum CodingKeys: String, CodingKey { case headline, windows, shifts, config }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        headline = try? c.decode(TasteHeadline.self, forKey: .headline)
        windows = (try? c.decode([String: TasteWindow].self, forKey: .windows)) ?? [:]
        shifts = (try? c.decode([LossyShift].self, forKey: .shifts))?.compactMap(\.shift) ?? []
        config = (try? c.decode(TasteConfig.self, forKey: .config)) ?? TasteConfig()
    }
    public init(headline: TasteHeadline? = nil, windows: [String: TasteWindow], shifts: [TasteShift] = [], config: TasteConfig = TasteConfig()) {
        self.headline = headline; self.windows = windows; self.shifts = shifts; self.config = config
    }
    private struct LossyShift: Decodable {
        let shift: TasteShift?
        init(from decoder: any Decoder) throws { shift = try? TasteShift(from: decoder) }
    }

    public func window(_ name: String) -> TasteWindow? { windows[name] }
    /// Shifts of one window, biggest move first. Only what the server listed.
    public func shifts(in window: String) -> [TasteShift] {
        shifts.filter { $0.window == window }.sorted { abs($0.toShare - $0.fromShare) > abs($1.toShare - $1.fromShare) }
    }
}

/// `GET /api/insights/taste`. `profiles` is nil until a refresh has saved some ("not computed yet").
public struct TasteResponse: Decodable, Equatable, Sendable {
    public let profiles: TasteProfiles?
    public let dataVersion: Int
    public let generation: Int
    /// D2 (proposed): one entry per UTC day for the last 84 days, zero days included. nil until the server serves it.
    public let listensByDay: [ListensDay]?

    enum CodingKeys: String, CodingKey { case profiles, dataVersion = "data_version", generation, listensByDay = "listens_by_day" }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        profiles = try? c.decode(TasteProfiles.self, forKey: .profiles)
        dataVersion = (try? c.decode(Int.self, forKey: .dataVersion)) ?? 0
        generation = (try? c.decode(Int.self, forKey: .generation)) ?? 0
        listensByDay = (try? c.decode([FeedLossy<ListensDay>].self, forKey: .listensByDay))?.compactMap(\.value)
    }
}

/// `POST /api/insights/taste/refresh`. `state` is `refreshed`, `unchanged`, `too_soon`, `failed` or `no_listens_source`.
public struct TasteRefreshResult: Decodable, Equatable, Sendable {
    public let state: String
    public let changed: Bool
    public let retryAfter: Double
    public let error: String?

    enum CodingKeys: String, CodingKey { case state, changed, retryAfter = "retry_after", error }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        state = (try? c.decode(String.self, forKey: .state)) ?? "failed"
        changed = (try? c.decode(Bool.self, forKey: .changed)) ?? false
        retryAfter = (try? c.decode(Double.self, forKey: .retryAfter)) ?? 0
        error = try? c.decode(String.self, forKey: .error)
    }
}

extension LibrarianClient {
    /// `GET /api/insights/taste`: the saved profiles. Read-only; computes and fetches nothing.
    public func taste() async throws -> TasteResponse {
        let (data, http) = try await authedSendPublic("GET", "api/insights/taste", body: nil)
        return try decodePublic(TasteResponse.self, data, http)
    }

    /// `POST /api/insights/taste/refresh`: asks the server to rebuild the profiles from the owner's listens. It can take about a
    /// minute on a long history, answers `too_soon` inside the one-hour interval, and is `409` while another run is going.
    public func refreshTaste() async throws -> TasteRefreshResult {
        let (data, http) = try await authedSendPublic("POST", "api/insights/taste/refresh", body: nil)
        return try decodePublic(TasteRefreshResult.self, data, http)
    }
}
