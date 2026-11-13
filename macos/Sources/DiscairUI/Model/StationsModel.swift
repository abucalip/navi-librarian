import DiscairCore
import DiscairLibrarian
import Foundation
import Observation

/// What the stations model asks of the Librarian. `LibrarianClient` is the real one; tests pass a fake.
public protocol StationsSource: Sendable {
    func radioStations() async throws -> [RadioStation]
    func radioNowAll() async throws -> RadioNowAll
    func setRadioFavourite(station: String, on: Bool) async throws
    func setRadioTags(station: String, tags: [String]) async throws
}
extension LibrarianClient: StationsSource {}

/// The station list, the live titles and the tag filter behind the Radio page (S2-1 item 5).
/// The server owns the order (favourites, then last played, then name); nothing here re-sorts it.
@MainActor
@Observable
public final class StationsModel {
    public enum Phase: Equatable {
        case idle, loading, loaded
        /// The list could not be read. `retryable` is false only for an address the app refuses.
        case failed(message: String, retryable: Bool)
    }

    public private(set) var stations: [RadioStation] = []
    /// The live song by station id, from `GET /api/radio/now`. Only relayed stations with a listener appear.
    public private(set) var nowByID: [String: RadioNow] = [:]
    public private(set) var phase: Phase = .idle
    /// The chip chosen over the list; nil is All.
    public private(set) var tagFilter: String?
    /// The server's sentence after a refused favourite or tag change; cleared by the next successful one.
    public private(set) var actionNote: String?
    public private(set) var loadedAt: Date?

    /// True while the Radio page is on screen and the window is shown. Polling runs only then (S2.5).
    public private(set) var pageVisible = false

    // Request budget (S2.5): the list at most once a minute, live titles every 15 s.
    public static let listInterval: TimeInterval = 60
    public static let nowInterval: TimeInterval = 15

    @ObservationIgnored private var source: (any StationsSource)?
    @ObservationIgnored private let clock: @Sendable () -> Date
    @ObservationIgnored private let pause: @Sendable (TimeInterval) async -> Void
    @ObservationIgnored private var pollTask: Task<Void, Never>?
    @ObservationIgnored private var listBusy = false
    @ObservationIgnored private var nowBusy = false
    /// Changes shown but not yet confirmed, by station id. A reload that arrives meanwhile must not undo them.
    @ObservationIgnored private var pendingFavourite: [String: Bool] = [:]
    @ObservationIgnored private var pendingTags: [String: [String]] = [:]

    public init(clock: @escaping @Sendable () -> Date = { Date() },
                pause: @escaping @Sendable (TimeInterval) async -> Void = { try? await Task.sleep(for: .seconds($0)) }) {
        self.clock = clock
        self.pause = pause
    }

    public func configure(source: (any StationsSource)?) {
        self.source = source
        if source == nil { stop(); stations = []; nowByID = [:]; phase = .idle; loadedAt = nil }
        else if pageVisible { startPolling() }
    }

    // MARK: What the page reads

    var chips: [StationRules.Chip] { StationRules.chips(for: stations) }
    public var visibleStations: [RadioStation] { StationRules.filter(stations, tag: tagFilter) }
    /// "No stations yet": the list was read and is empty.
    public var isEmpty: Bool { phase == .loaded && stations.isEmpty }
    public var isLoading: Bool { phase == .loading }
    public var favourites: [RadioStation] { stations.filter(\.favourite) }

    func status(for station: RadioStation) -> StationRules.Status {
        StationRules.status(for: station, now: nowByID[station.id], at: clock())
    }

    public func select(tag: String?) {
        guard let tag else { tagFilter = nil; return }
        tagFilter = chips.contains { $0.tag?.lowercased() == tag.lowercased() } ? tag : nil
    }

    // MARK: Visibility and polling

    public func setPageVisible(_ visible: Bool) {
        guard visible != pageVisible else { return }
        pageVisible = visible
        visible ? startPolling() : stop()
    }

    private func startPolling() {
        guard source != nil, pollTask == nil else { return }
        pollTask = Task { [weak self] in
            while !Task.isCancelled {
                guard let self else { return }
                await self.tick()
                await self.pause(Self.nowInterval)
            }
        }
    }

    private func stop() {
        pollTask?.cancel()
        pollTask = nil
    }

    /// One round of the poll: the list when a minute has passed (or was never read), the live titles when 15 s have.
    /// A slow answer is never stacked with a second request of the same kind. Public so a test can drive the clock.
    public func tick() async {
        guard pageVisible, source != nil else { return }
        let now = clock()
        let listDue = loadedAt.map { now.timeIntervalSince($0) >= Self.listInterval } ?? true
        async let list: Void = listDue ? reload() : ()
        async let live: Void = refreshNow()
        _ = await (list, live)
    }

    // MARK: Loading

    /// Reads the list. Keeps what is on screen when the read fails, and says so.
    public func reload() async {
        guard let source, !listBusy else { return }
        listBusy = true; defer { listBusy = false }
        if stations.isEmpty { phase = .loading }
        do {
            let list = try await source.radioStations()
            stations = applyPending(to: list)
            loadedAt = clock()
            phase = .loaded
            if let tagFilter, !chips.contains(where: { $0.tag?.lowercased() == tagFilter.lowercased() }) { self.tagFilter = nil }
        } catch {
            phase = .failed(message: Self.message(error), retryable: Self.retryable(error))
        }
    }

    /// Reads the live titles. A failure keeps the last ones; the status sentence then goes on to say what it knew.
    public func refreshNow() async {
        guard let source, !nowBusy else { return }
        nowBusy = true; defer { nowBusy = false }
        if let all = try? await source.radioNowAll() { nowByID = all.byStation }
    }

    // MARK: Favourite and tags

    /// Shows the change at once, sends it, then reloads. A refusal puts the old value back and keeps the server's sentence.
    public func setFavourite(_ station: RadioStation, on: Bool) async {
        guard let source, let old = stations.first(where: { $0.id == station.id })?.favourite, old != on else { return }
        pendingFavourite[station.id] = on
        update(station.id) { $0.replacing(favourite: on) }
        do {
            try await source.setRadioFavourite(station: station.id, on: on)
            pendingFavourite[station.id] = nil
            actionNote = nil
            await reload()
        } catch {
            pendingFavourite[station.id] = nil
            update(station.id) { $0.replacing(favourite: old) }
            actionNote = Self.message(error)
        }
    }

    /// The list is checked first (`StationRules.validated`); a problem is the note and nothing is sent.
    public func setTags(_ station: RadioStation, to tags: [String]) async {
        guard let source, let old = stations.first(where: { $0.id == station.id })?.tags else { return }
        let clean: [String]
        switch StationRules.validated(tags: tags) {
        case .success(let list): clean = list
        case .failure(let problem): actionNote = problem.message; return
        }
        guard clean != old else { return }
        pendingTags[station.id] = clean
        update(station.id) { $0.replacing(tags: clean) }
        do {
            try await source.setRadioTags(station: station.id, tags: clean)
            pendingTags[station.id] = nil
            actionNote = nil
            await reload()
        } catch {
            pendingTags[station.id] = nil
            update(station.id) { $0.replacing(tags: old) }
            actionNote = Self.message(error)
        }
    }

    public func clearNote() { actionNote = nil }

    private func update(_ id: String, _ change: (RadioStation) -> RadioStation) {
        guard let i = stations.firstIndex(where: { $0.id == id }) else { return }
        stations[i] = change(stations[i])
        // Dropping a tag can empty the chip that is chosen.
        if let tagFilter, !chips.contains(where: { $0.tag?.lowercased() == tagFilter.lowercased() }) { self.tagFilter = nil }
    }

    private func applyPending(to list: [RadioStation]) -> [RadioStation] {
        guard !pendingFavourite.isEmpty || !pendingTags.isEmpty else { return list }
        return list.map { s in
            var s = s
            if let f = pendingFavourite[s.id] { s = s.replacing(favourite: f) }
            if let t = pendingTags[s.id] { s = s.replacing(tags: t) }
            return s
        }
    }

    // MARK: Words for errors

    /// The server's own sentence when it sent one, else the app's usual short text. Never an address.
    static func message(_ error: Error) -> String {
        if let e = error as? DiscairError {
            if case .server(_, let text?) = e, !text.isEmpty { return text }
            return e.summary
        }
        return "The server did not answer."
    }

    static func retryable(_ error: Error) -> Bool { (error as? DiscairError)?.isRetryable ?? true }
}

extension RadioStation {
    func replacing(favourite: Bool? = nil, tags: [String]? = nil) -> RadioStation {
        RadioStation(id: id, name: name, proxied: proxied, playableURL: playableURL, homepageURL: homepageURL, logoPath: logoPath,
                     favourite: favourite ?? self.favourite, tags: tags ?? self.tags, lastPlayedAt: lastPlayedAt)
    }
}
