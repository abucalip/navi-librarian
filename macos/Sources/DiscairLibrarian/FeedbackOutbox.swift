import Foundation

/// Thrown by a sender that has no Librarian connection to send through. The outbox keeps every event in that case.
public struct FeedbackUnavailable: Error, Sendable {
    public init() {}
}

/// Holds skip events until the Librarian has taken them (`docs/SERVER_V2_CONTRACT.md`, `POST /api/feedback/events`).
///
/// Events are kept in a JSON file so they survive a restart. A flush sends them in batches of at most 100 and removes an
/// event once the server settles it: `accepted`, `duplicate` (a replay counts as accepted) or `rejected`. A rejected event is
/// dropped, never retried unchanged. A network error, a 5xx or any other failure of the whole request keeps every event for
/// the next flush. Each event keeps the `event_id` it was created with, so a retry is recognised as a replay.
///
/// A write that fails is recorded in `storageError` and the events stay in memory; nothing is dropped for a disk error. A
/// saved file that cannot be read is moved aside, not treated as an empty queue, so pending events are never overwritten.
/// A re-sent event that was already settled on disk is a server duplicate, so a failed save at worst causes a harmless replay.
///
/// The outbox holds at most `capacity` events and drops the oldest. An event whose `occurred_at` is more than 300 s ahead
/// of this clock is held rather than sent, because the server would reject it as `future`; it goes out once the clock
/// catches up.
public actor FeedbackOutbox {
    /// Sends one batch and returns the server's per-item answers. Throws when the request as a whole failed.
    public typealias Sender = @Sendable ([FeedbackEvent]) async throws -> FeedbackEventsResponse

    public static let capacity = 500
    /// The server refuses an `occurred_at` more than this many seconds ahead of its clock.
    public static let maxFutureSeconds = 300.0

    /// `~/Library/Application Support/Discair/feedback-outbox.json`.
    public static var defaultURL: URL {
        URL.applicationSupportDirectory.appending(path: "Discair/feedback-outbox.json")
    }

    private let fileURL: URL
    private let send: Sender
    private let clock: @Sendable () -> Date
    private var events: [FeedbackEvent]
    private var isFlushing = false
    /// True when an unreadable queue file could not be moved aside. Saving is then refused, so that file is never overwritten.
    private var preserveExistingFile = false

    /// Why the queue could not be read or written, in plain words. Nil after a clean load and a successful save.
    /// Events stay in memory while this is set, so the owner can be told; they are not dropped.
    public private(set) var storageError: String?

    public init(fileURL: URL, send: @escaping Sender, clock: @escaping @Sendable () -> Date = Date.init) {
        self.fileURL = fileURL
        self.send = send
        self.clock = clock
        let loaded = Self.load(fileURL)
        events = loaded.events
        storageError = loaded.problem
        preserveExistingFile = loaded.mustPreserve
    }

    /// Events not yet settled, oldest first.
    public var pending: [FeedbackEvent] { events }

    /// Adds an event at the end and saves. Past `capacity`, the oldest events are dropped.
    public func enqueue(_ event: FeedbackEvent) {
        events.append(event)
        if events.count > Self.capacity { events.removeFirst(events.count - Self.capacity) }
        save()
    }

    /// Sends what is due, batch by batch, until nothing is due or a request fails. Only one flush runs at a time; a call
    /// made during a flush returns at once, and the running flush picks up anything newly queued.
    public func flush() async {
        guard !isFlushing else { return }
        isFlushing = true
        defer { isFlushing = false }
        while true {
            let limit = clock().timeIntervalSince1970 + Self.maxFutureSeconds
            let batch = Array(events.lazy.filter { $0.occurredAt <= limit }.prefix(FeedbackEvent.batchLimit))
            guard !batch.isEmpty else { return }
            // Any failure keeps the whole batch; the next flush sends the same events with the same IDs.
            guard let response = try? await send(batch) else { return }
            let settled = Set(response.results.compactMap { result -> String? in
                batch.indices.contains(result.index) ? batch[result.index].eventID : nil
            })
            // A reply that settles nothing (no per-item answers) stops here instead of resending the same batch forever.
            guard !settled.isEmpty else { return }
            events.removeAll { settled.contains($0.eventID) }
            save()
        }
    }

    // MARK: Disk

    /// A missing file is an empty queue. A file that cannot be read or decoded is moved aside, never treated as empty and
    /// overwritten; if it cannot be moved either, it is left alone and saving is refused.
    private static func load(_ url: URL) -> (events: [FeedbackEvent], problem: String?, mustPreserve: Bool) {
        guard FileManager.default.fileExists(atPath: url.path) else { return ([], nil, false) }
        do {
            let saved = try JSONDecoder().decode([FeedbackEvent].self, from: Data(contentsOf: url))
            return (Array(saved.suffix(capacity)), nil, false)
        } catch {
            let aside = url.deletingLastPathComponent()
                .appending(path: "feedback-outbox.unreadable-\(UUID().uuidString.lowercased().prefix(8)).json")
            do {
                try FileManager.default.moveItem(at: url, to: aside)
                return ([], "The saved feedback queue could not be read and was moved aside; it is not sent again.", false)
            } catch {
                return ([], "The saved feedback queue could not be read or moved aside, so it will not be overwritten.", true)
            }
        }
    }

    /// Writes the whole queue. A failed write keeps the queue in memory and records `storageError`; the next change tries again.
    private func save() {
        guard !preserveExistingFile else {
            storageError = "The saved feedback queue could not be read or moved aside, so it will not be overwritten."
            return
        }
        do {
            try FileManager.default.createDirectory(at: fileURL.deletingLastPathComponent(), withIntermediateDirectories: true)
            try JSONEncoder().encode(events).write(to: fileURL, options: .atomic)
            storageError = nil
        } catch {
            storageError = "The feedback queue could not be saved; events are kept in memory until a later save succeeds."
        }
    }
}
