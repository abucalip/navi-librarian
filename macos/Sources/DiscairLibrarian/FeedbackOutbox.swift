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

    public init(fileURL: URL, send: @escaping Sender, clock: @escaping @Sendable () -> Date = Date.init) {
        self.fileURL = fileURL
        self.send = send
        self.clock = clock
        events = Self.load(fileURL)
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

    private static func load(_ url: URL) -> [FeedbackEvent] {
        guard let data = try? Data(contentsOf: url),
              let saved = try? JSONDecoder().decode([FeedbackEvent].self, from: data) else { return [] }
        return Array(saved.suffix(capacity))
    }

    /// Writes the whole queue. A failed write leaves the queue in memory, and the next change tries again.
    private func save() {
        try? FileManager.default.createDirectory(at: fileURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? JSONEncoder().encode(events).write(to: fileURL, options: .atomic)
    }
}
