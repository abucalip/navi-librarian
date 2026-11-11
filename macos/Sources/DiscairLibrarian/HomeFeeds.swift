import Foundation

// Server feeds behind the redesigned Home (`docs/redesign.md` section 5.1, step M8): the radio Heard list, the job-status
// routes of the taste, popularity and insight jobs, and the listens-by-day series (D2). The radio and popularity routes exist;
// `GET /api/insights/refresh/status` (D3) and `listens_by_day` on the taste body (D2) are contract proposals in
// `docs/SERVER_V2_CONTRACT.md`. Until the server serves them the client treats a missing answer as "not available", never zero.

/// One song heard on a relayed radio station (`GET /api/radio/plays`).
public struct RadioPlay: Decodable, Equatable, Sendable, Identifiable {
    public let id: Int
    public let stationName: String
    public let artist: String?
    public let title: String
    public let album: String?
    public let year: Int?
    /// Unix seconds.
    public let heardAt: Double
    /// True once a Get was sent for this song.
    public let grabbed: Bool
    /// True when the song is already in the library (the server checks, one search per song, cached).
    public let inLibrary: Bool

    enum CodingKeys: String, CodingKey {
        case id, artist, title, album, year, grabbed
        case stationName = "station_name", heardAt = "heard_at", inLibrary = "in_library"
    }

    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(Int.self, forKey: .id)
        title = (try? c.decode(String.self, forKey: .title)) ?? ""
        stationName = (try? c.decode(String.self, forKey: .stationName)) ?? ""
        artist = try? c.decode(String.self, forKey: .artist)
        album = try? c.decode(String.self, forKey: .album)
        year = try? c.decode(Int.self, forKey: .year)
        heardAt = (try? c.decode(Double.self, forKey: .heardAt)) ?? 0
        grabbed = ((try? c.decode(Int.self, forKey: .grabbed)) ?? ((try? c.decode(Bool.self, forKey: .grabbed)) == true ? 1 : 0)) != 0
        inLibrary = (try? c.decode(Bool.self, forKey: .inLibrary)) ?? false
    }

    public init(id: Int, stationName: String, artist: String?, title: String, album: String? = nil, year: Int? = nil,
                heardAt: Double, grabbed: Bool = false, inLibrary: Bool = false) {
        self.id = id; self.stationName = stationName; self.artist = artist; self.title = title; self.album = album
        self.year = year; self.heardAt = heardAt; self.grabbed = grabbed; self.inLibrary = inLibrary
    }
}

struct RadioPlaysPayload: Decodable {
    let items: [RadioPlay]
    init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        // One unreadable row must not hide the rest.
        items = ((try? c.decode([FeedLossy<RadioPlay>].self, forKey: .items)) ?? []).compactMap(\.value)
    }
    enum CodingKeys: String, CodingKey { case items }
}

struct FeedLossy<T: Decodable>: Decodable {
    let value: T?
    init(from decoder: any Decoder) throws { value = try? T(from: decoder) }
}

/// `POST /api/radio/plays/{id}/get`: `ok` false carries the server's sentence in `message`.
public struct RadioGetResult: Decodable, Equatable, Sendable {
    public let ok: Bool
    public let message: String?
    public let status: String?
    public let album: String?

    enum CodingKeys: String, CodingKey { case ok, message, status, album }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        ok = (try? c.decode(Bool.self, forKey: .ok)) ?? false
        message = try? c.decode(String.self, forKey: .message)
        status = try? c.decode(String.self, forKey: .status)
        album = try? c.decode(String.self, forKey: .album)
    }
}

/// One run of a background job, as `intelligence/jobs/runner.py` returns it.
public struct JobRun: Decodable, Equatable, Sendable {
    /// `queued`, `running`, `succeeded`, `failed` or `skipped`.
    public let state: String
    /// Unix seconds.
    public let startedAt: Double?
    public let finishedAt: Double?
    public let progress: [String: Double]
    public let error: String?

    enum CodingKeys: String, CodingKey { case state, progress, error, startedAt = "started_at", finishedAt = "finished_at" }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        state = (try? c.decode(String.self, forKey: .state)) ?? "failed"
        startedAt = try? c.decode(Double.self, forKey: .startedAt)
        finishedAt = try? c.decode(Double.self, forKey: .finishedAt)
        progress = (try? c.decode([String: Double].self, forKey: .progress)) ?? [:]
        error = try? c.decode(String.self, forKey: .error)
    }
    public init(state: String, startedAt: Double? = nil, finishedAt: Double? = nil, progress: [String: Double] = [:], error: String? = nil) {
        self.state = state; self.startedAt = startedAt; self.finishedAt = finishedAt; self.progress = progress; self.error = error
    }
}

/// The status answer of a job route: the newest run, the newest good run, whether one is running and, for the refresh jobs,
/// how long until the next is allowed.
public struct JobStatus: Decodable, Equatable, Sendable {
    public let status: JobRun?
    public let lastGood: JobRun?
    public let running: Bool
    /// Seconds between refreshes the server allows (refresh jobs only).
    public let minInterval: Double?
    /// Seconds until the next refresh is allowed; 0 means now (refresh jobs only).
    public let retryAfter: Double?

    enum CodingKeys: String, CodingKey { case status, running, lastGood = "last_good", minInterval = "min_interval", retryAfter = "retry_after" }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        status = try? c.decode(JobRun.self, forKey: .status)
        lastGood = try? c.decode(JobRun.self, forKey: .lastGood)
        running = (try? c.decode(Bool.self, forKey: .running)) ?? false
        minInterval = try? c.decode(Double.self, forKey: .minInterval)
        retryAfter = try? c.decode(Double.self, forKey: .retryAfter)
    }
    public init(status: JobRun?, lastGood: JobRun?, running: Bool = false, minInterval: Double? = nil, retryAfter: Double? = nil) {
        self.status = status; self.lastGood = lastGood; self.running = running; self.minInterval = minInterval; self.retryAfter = retryAfter
    }
}

/// `POST /api/insights/popularity/fill`. `state` is `succeeded`, `queued` (artists still pending) or `failed`.
public struct PopularityFillResult: Decodable, Equatable, Sendable {
    public let state: String
    public let progress: [String: Double]
    public let error: String?

    enum CodingKeys: String, CodingKey { case state, progress, error }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        state = (try? c.decode(String.self, forKey: .state)) ?? "failed"
        progress = (try? c.decode([String: Double].self, forKey: .progress)) ?? [:]
        error = try? c.decode(String.self, forKey: .error)
    }
}

/// One day of listens (D2). `date` is a UTC calendar day, "2026-11-10".
public struct ListensDay: Decodable, Equatable, Sendable {
    public let date: String
    public let count: Int
    public init(date: String, count: Int) { self.date = date; self.count = count }
}

extension LibrarianClient {
    /// `GET /api/radio/plays`: the Heard list, newest first.
    public func radioPlays(limit: Int = 100) async throws -> [RadioPlay] {
        let (data, http) = try await authedSendPublic("GET", "api/radio/plays?limit=\(min(max(limit, 1), 500))", body: nil)
        return try decodePublic(RadioPlaysPayload.self, data, http).items
    }

    /// `POST /api/radio/plays/{id}/get`: the song-only Get for a heard song.
    public func getRadioPlay(id: Int) async throws -> RadioGetResult {
        let (data, http) = try await authedSendPublic("POST", "api/radio/plays/\(id)/get", body: nil)
        return try decodePublic(RadioGetResult.self, data, http)
    }

    /// `GET /api/insights/popularity/status`. Makes no provider call on the server.
    public func popularityStatus() async throws -> JobStatus {
        let (data, http) = try await authedSendPublic("GET", "api/insights/popularity/status", body: nil)
        return try decodePublic(JobStatus.self, data, http)
    }

    /// `POST /api/insights/popularity/fill`: one bounded batch (default 5 requests, capped at 20). `409` while another runs.
    public func fillPopularity(maxRequests: Int = 5) async throws -> PopularityFillResult {
        let body = try JSONSerialization.data(withJSONObject: ["max_requests": min(max(maxRequests, 1), 20)])
        let (data, http) = try await authedSendPublic("POST", "api/insights/popularity/fill", body: body)
        return try decodePublic(PopularityFillResult.self, data, http)
    }

    /// `GET /api/insights/taste/refresh/status`.
    public func tasteRefreshStatus() async throws -> JobStatus {
        let (data, http) = try await authedSendPublic("GET", "api/insights/taste/refresh/status", body: nil)
        return try decodePublic(JobStatus.self, data, http)
    }

    /// `GET /api/insights/refresh/status` (D3, proposed): the insight lenses' refresh job, shaped like the taste one.
    public func insightsRefreshStatus() async throws -> JobStatus {
        let (data, http) = try await authedSendPublic("GET", "api/insights/refresh/status", body: nil)
        return try decodePublic(JobStatus.self, data, http)
    }
}
