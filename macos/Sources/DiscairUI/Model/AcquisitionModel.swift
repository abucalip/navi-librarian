import DiscairCore
import DiscairLibrarian
import Foundation
import Observation

/// How one Get button reads. Pending, requested and failed always differ by text, never by colour alone, and a Get is
/// never shown as done before the server answers (Android contract 5.3, honest states).
public enum GetState: Equatable, Sendable {
    case idle
    case pending
    case requested(String)
    case failed(String)
}

/// Get, Save, Not for me (with an Undo window), Never suggest and the job list behind the ticker and the Downloads badge.
/// Themes read this and call it through `DiscairActions`; the Librarian client stays behind it.
@MainActor
@Observable
public final class AcquisitionModel {
    public struct PendingDismissal: Equatable {
        public let artist: String
        public let title: String
        public let album: AlbumItem
    }

    public private(set) var jobs: [Acquisition] = []
    public private(set) var getStates: [String: GetState] = [:]
    public private(set) var saved: Set<String> = []
    /// Hidden from the lists: Not for me (until confirmed or undone) and Never suggest.
    private(set) var dismissed: Set<String> = []
    private(set) var dismissedArtists: Set<String> = []
    public private(set) var pending: PendingDismissal?
    /// The last failure the owner should see (a refused Save, a failed dismissal); cleared by `clearNotice()`.
    public private(set) var notice: String?

    private var librarian: LibrarianClient?
    private let undoWindow: Duration
    @ObservationIgnored private var commitTask: Task<Void, Never>?
    @ObservationIgnored private var pollTask: Task<Void, Never>?

    public init(undoWindow: Duration = .seconds(6)) { self.undoWindow = undoWindow }

    public func configure(librarian: LibrarianClient?) {
        self.librarian = librarian
        pollTask?.cancel()
        jobs = []
        guard librarian != nil else { return }
        pollTask = Task { [weak self] in
            while !Task.isCancelled {
                await self?.refresh()
                // Quick while something is moving, lazy otherwise. The SSE stream is a later step.
                let busy = self?.activeCount ?? 0 > 0
                try? await Task.sleep(for: .seconds(busy ? 4 : 30))
            }
        }
    }

    // MARK: Keys

    static func key(artist: String, title: String) -> String { "\(artist.lowercased())|\(title.lowercased())" }
    static func key(_ a: AlbumItem) -> String { key(artist: a.artist, title: a.title) }

    // MARK: Read

    public func isHidden(_ a: AlbumItem) -> Bool {
        dismissed.contains(Self.key(a)) || dismissedArtists.contains(a.artist.lowercased())
    }

    public func isSaved(_ a: AlbumItem) -> Bool { saved.contains(Self.key(a)) }

    /// The state from this session's own request, else from a matching job the server already has.
    public func state(for a: AlbumItem, song: String? = nil) -> GetState {
        let k = song.map { Self.key(artist: a.artist, title: "\($0)|\(a.title)") } ?? Self.key(a)
        if let s = getStates[k] { return s }
        if song == nil, let job = jobs.first(where: { $0.id == Self.key(a) }) { return Self.describe(job) }
        return .idle
    }

    static func describe(_ job: Acquisition) -> GetState {
        switch job.phase {
        case .working, .queued, .imported: .requested(statusText(job))
        case .failed: .failed(job.details?.message ?? statusText(job))
        case .other: .requested(statusText(job))
        }
    }

    static func statusText(_ job: Acquisition) -> String {
        switch job.status {
        case "downloading":
            if let p = job.details?.liveProgress?.percent { return "Downloading \(Int(p))%" }
            return "Downloading"
        case "imported": return "In your library"
        case "searching": return "Searching"
        case "importing": return "Importing"
        case "no_matches": return "No source found"
        case "settings_required": return "Download service not set up"
        case "queue_failed", "slskd_error": return "Download service error"
        default: return job.status.replacingOccurrences(of: "_", with: " ").capitalized
        }
    }

    public func buttonLabel(for a: AlbumItem, song: String? = nil) -> String {
        switch state(for: a, song: song) {
        case .idle: "Get"
        case .pending: "Getting…"
        case .requested: "Requested"
        case .failed: "Retry"
        }
    }

    public func canGet(_ a: AlbumItem, song: String? = nil) -> Bool {
        switch state(for: a, song: song) { case .idle, .failed: true; case .pending, .requested: false }
    }

    /// Words for VoiceOver and the tooltip: what happened, including the server's own message.
    public func detail(for a: AlbumItem, song: String? = nil) -> String {
        switch state(for: a, song: song) {
        case .idle: ""
        case .pending: "Asking the Librarian"
        case .requested(let m), .failed(let m): m
        }
    }

    public var activeCount: Int { jobs.filter { $0.phase == .working || $0.phase == .queued }.count }

    /// The Zine ticker: what is moving, what waits, what arrived, how many failed.
    public var tickerText: String {
        guard !jobs.isEmpty else { return "Pipeline: no downloads in progress" }
        var parts: [String] = []
        if let j = jobs.first(where: { $0.phase == .working }) { parts.append("▶ \(Self.statusText(j)): \(j.title)") }
        if let j = jobs.first(where: { $0.phase == .queued }) { parts.append("Queued: \(j.title)") }
        if let j = jobs.filter({ $0.phase == .imported }).max(by: { ($0.updatedAt ?? 0) < ($1.updatedAt ?? 0) }) { parts.append("Imported: \(j.title)") }
        let failed = jobs.filter { $0.phase == .failed }.count
        parts.append("Failed: " + (failed == 0 ? "none" : String(failed)))
        return parts.joined(separator: "  ■  ")
    }

    // MARK: Get

    public func get(_ a: AlbumItem) async {
        await request(key: Self.key(a)) { l in
            try await l.acquire(artist: a.artist, album: a.title, metadata: Self.metadata(a))
        }
    }

    public func getSong(_ a: AlbumItem, title: String, trackNumber: Int?) async {
        await request(key: Self.key(artist: a.artist, title: "\(title)|\(a.title)")) { l in
            try await l.acquireTrack(artist: a.artist, album: a.title, title: title, trackNumber: trackNumber,
                                     year: a.year > 0 ? a.year : nil, metadata: Self.metadata(a))
        }
    }

    private func request(key: String, _ call: (LibrarianClient) async throws -> AcquireResult) async {
        guard let librarian else {
            getStates[key] = .failed("Not connected to the Librarian. Check Settings.")
            return
        }
        getStates[key] = .pending
        do {
            let r = try await call(librarian)
            if r.ok { getStates[key] = .requested(r.message ?? "Requested") }
            else { getStates[key] = .failed(r.message ?? Self.refusal(r.status)) }
        } catch let e as DiscairError {
            getStates[key] = .failed(Self.text(e))
        } catch {
            getStates[key] = .failed(ErrorMapping.map(error).summary)
        }
        await refresh()
    }

    static func refusal(_ status: String?) -> String {
        switch status {
        case "settings_required": "The Librarian's download service is not set up."
        case "no_matches": "No source was found."
        default: "The Librarian did not start the download."
        }
    }

    static func text(_ e: DiscairError) -> String {
        if case .server(_, let m?) = e { return m }
        if case .unauthorised(let m?) = e { return m }
        return e.summary
    }

    static func metadata(_ a: AlbumItem) -> [String: String] {
        var m = ["source": "discair-macos"]
        if a.year > 0 { m["year"] = String(a.year) }
        return m
    }

    // MARK: Save, Not for me, Never suggest

    public func save(_ a: AlbumItem) async {
        guard let librarian else { notice = "Not connected to the Librarian. Check Settings."; return }
        do { try await librarian.feedback(artist: a.artist, album: a.title, action: .save, metadata: Self.metadata(a)); saved.insert(Self.key(a)) }
        catch let e as DiscairError { notice = "Could not save: " + Self.text(e) }
        catch { notice = "Could not save." }
    }

    /// Hides the album at once and sends the dismissal after the Undo window. Another dismissal inside the window
    /// sends the first one now.
    public func notForMe(_ a: AlbumItem) {
        guard librarian != nil else { notice = "Not connected to the Librarian. Check Settings."; return }
        if let p = pending { commitTask?.cancel(); Task { await self.send(.dismiss, p) } }
        dismissed.insert(Self.key(a))
        let p = PendingDismissal(artist: a.artist, title: a.title, album: a)
        pending = p
        commitTask = Task { [weak self, undoWindow] in
            try? await Task.sleep(for: undoWindow)
            guard !Task.isCancelled else { return }
            await self?.commit(p)
        }
    }

    public func undo() {
        guard let p = pending else { return }
        commitTask?.cancel()
        dismissed.remove(Self.key(p.album))
        pending = nil
    }

    /// Sends the dismissal now and also tells the Librarian never to suggest this artist.
    public func neverSuggest() async {
        guard let p = pending else { return }
        commitTask?.cancel()
        pending = nil
        dismissedArtists.insert(p.artist.lowercased())
        guard let librarian else { return }
        do { try await librarian.feedback(artist: p.artist, album: p.title, action: .dismissArtist, metadata: Self.metadata(p.album)) }
        catch {
            dismissedArtists.remove(p.artist.lowercased())
            notice = "Could not hide this artist: " + ((error as? DiscairError).map(Self.text) ?? "try again.")
        }
    }

    /// Sends a waiting dismissal now (used when the app quits).
    public func flush() async {
        guard let p = pending else { return }
        commitTask?.cancel()
        await commit(p)
    }

    private func commit(_ p: PendingDismissal) async {
        guard pending == p else { return }
        pending = nil
        await send(.dismiss, p)
    }

    private func send(_ action: FeedbackAction, _ p: PendingDismissal) async {
        guard let librarian else { return }
        do { try await librarian.feedback(artist: p.artist, album: p.title, action: action, metadata: Self.metadata(p.album)) }
        catch {
            dismissed.remove(Self.key(p.album))   // the server did not take it, so the album comes back
            notice = "Could not dismiss \(p.title): " + ((error as? DiscairError).map(Self.text) ?? "try again.")
        }
    }

    public func clearNotice() { notice = nil }

    // MARK: Jobs

    public func refresh() async {
        guard let librarian else { return }
        if let list = try? await librarian.acquisitions() { jobs = list }
    }
}

/// `DiscairActions` backed by the model; the app uses it once a session exists.
@MainActor
public final class AcquisitionActions: DiscairActions {
    private let model: AcquisitionModel
    public init(_ model: AcquisitionModel) { self.model = model }
    public func play(album: AlbumItem) {}
    public func get(album: AlbumItem) { Task { await model.get(album) } }
    public func getSong(album: AlbumItem, title: String, trackNumber: Int?) { Task { await model.getSong(album, title: title, trackNumber: trackNumber) } }
    public func save(album: AlbumItem) { Task { await model.save(album) } }
    public func notForMe(album: AlbumItem) { model.notForMe(album) }
    public func resume() {}
}
