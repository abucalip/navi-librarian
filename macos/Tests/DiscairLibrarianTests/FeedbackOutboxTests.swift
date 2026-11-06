import DiscairCore
import Foundation
import Testing
@testable import DiscairLibrarian

private let fixedNow = Date(timeIntervalSince1970: 1_800_000_000)

/// Records each batch the outbox sends and answers it with `answer(callIndex, batch)`.
private final class Script: @unchecked Sendable {
    private let lock = NSLock()
    private var sent: [[FeedbackEvent]] = []
    private let answer: @Sendable (Int, [FeedbackEvent]) throws -> FeedbackEventsResponse

    init(_ answer: @escaping @Sendable (Int, [FeedbackEvent]) throws -> FeedbackEventsResponse) { self.answer = answer }

    var batches: [[FeedbackEvent]] { lock.withLock { sent } }

    func send(_ batch: [FeedbackEvent]) throws -> FeedbackEventsResponse {
        let call = lock.withLock { sent.append(batch); return sent.count - 1 }
        return try answer(call, batch)
    }
}

/// A clock the test can move forward.
private final class MovableClock: @unchecked Sendable {
    private let lock = NSLock()
    private var now: Date
    init(_ now: Date) { self.now = now }
    var date: Date { lock.withLock { now } }
    func set(_ date: Date) { lock.withLock { now = date } }
}

private struct Boom: Error {}

/// A reply in the server's shape: one result per item, by index.
private func settle(_ items: [(index: Int, status: String, duplicate: Bool)]) -> FeedbackEventsResponse {
    let parts = items.map { #"{"index":\#($0.index),"status":"\#($0.status)","duplicate":\#($0.duplicate)}"# }
    let json = #"{"results":[\#(parts.joined(separator: ","))]}"#
    return try! JSONDecoder().decode(FeedbackEventsResponse.self, from: Data(json.utf8))
}

/// Accepts every item in the batch.
private func acceptAll(_ batch: [FeedbackEvent]) -> FeedbackEventsResponse {
    settle(batch.indices.map { (index: $0, status: "accepted", duplicate: false) })
}

private func event(_ id: String, occurredAt: Double = fixedNow.timeIntervalSince1970 - 60) -> FeedbackEvent {
    FeedbackEvent(eventID: id, kind: .skip, subjectKind: .track, subjectID: "song-\(id)", occurredAt: occurredAt,
                  playedSeconds: 10, durationSeconds: 200)
}

private func tempFile() -> URL {
    FileManager.default.temporaryDirectory.appending(path: "feedback-outbox-tests-\(UUID().uuidString)/feedback-outbox.json")
}

private func outbox(_ file: URL, _ script: Script, clock: MovableClock? = nil) -> FeedbackOutbox {
    let c = clock ?? MovableClock(fixedNow)
    return FeedbackOutbox(fileURL: file, send: { batch in try script.send(batch) }, clock: { c.date })
}

struct FeedbackOutboxTests {
    @Test func replayAfterANetworkErrorKeepsTheSameEventID() async {
        let script = Script { call, batch in
            if call == 0 { throw Boom() }
            return acceptAll(batch)
        }
        let box = outbox(tempFile(), script)
        await box.enqueue(event("first-id"))

        await box.flush()
        #expect(await box.pending.map(\.eventID) == ["first-id"])

        await box.flush()
        #expect(script.batches.count == 2)
        #expect(script.batches[0].map(\.eventID) == ["first-id"])
        #expect(script.batches[1].map(\.eventID) == ["first-id"])
        #expect(await box.pending.isEmpty)
    }

    @Test func aRejectedEventIsDroppedAndNeverSentAgain() async {
        let script = Script { _, _ in settle([(index: 0, status: "rejected", duplicate: false), (index: 1, status: "accepted", duplicate: false)]) }
        let box = outbox(tempFile(), script)
        await box.enqueue(event("bad"))
        await box.enqueue(event("good"))

        await box.flush()
        #expect(await box.pending.isEmpty)
        await box.flush()
        #expect(script.batches.count == 1)
    }

    @Test func aDuplicateCountsAsAccepted() async {
        let script = Script { _, _ in settle([(index: 0, status: "accepted", duplicate: true)]) }
        let box = outbox(tempFile(), script)
        await box.enqueue(event("replayed"))

        await box.flush()
        #expect(await box.pending.isEmpty)
    }

    @Test func aNetworkErrorKeepsEveryEventAndIsNotRetriedInTheSameFlush() async {
        let script = Script { _, _ in throw Boom() }
        let box = outbox(tempFile(), script)
        await box.enqueue(event("a"))
        await box.enqueue(event("b"))

        await box.flush()
        #expect(await box.pending.map(\.eventID) == ["a", "b"])
        #expect(script.batches.count == 1)
    }

    @Test func aServerErrorKeepsEveryEvent() async {
        let script = Script { _, _ in throw DiscairError.server(status: 503, message: "unavailable") }
        let box = outbox(tempFile(), script)
        await box.enqueue(event("kept"))

        await box.flush()
        #expect(await box.pending.map(\.eventID) == ["kept"])
    }

    @Test func aFullOutboxDropsTheOldestEvent() async {
        let script = Script { _, _ in throw Boom() }
        let box = outbox(tempFile(), script)
        for i in 0...FeedbackOutbox.capacity { await box.enqueue(event("e\(i)")) }

        let pending = await box.pending
        #expect(pending.count == FeedbackOutbox.capacity)
        #expect(pending.first?.eventID == "e1")
        #expect(pending.last?.eventID == "e\(FeedbackOutbox.capacity)")
    }

    @Test func batchesHoldAtMostOneHundredEvents() async {
        let script = Script { _, batch in acceptAll(batch) }
        let box = outbox(tempFile(), script)
        for i in 0..<250 { await box.enqueue(event("n\(i)")) }

        await box.flush()
        #expect(script.batches.map(\.count) == [100, 100, 50])
        #expect(await box.pending.isEmpty)
    }

    @Test func aReplyThatSettlesNothingStopsTheFlush() async {
        let script = Script { _, _ in settle([]) }
        let box = outbox(tempFile(), script)
        await box.enqueue(event("unanswered"))

        await box.flush()
        #expect(script.batches.count == 1)
        #expect(await box.pending.map(\.eventID) == ["unanswered"])
    }

    @Test func aFutureEventIsHeldUntilTheServerClockCanAcceptIt() async {
        let script = Script { _, batch in acceptAll(batch) }
        let clock = MovableClock(fixedNow)
        let box = outbox(tempFile(), script, clock: clock)
        await box.enqueue(event("due"))
        await box.enqueue(event("ahead", occurredAt: fixedNow.timeIntervalSince1970 + 400))

        await box.flush()
        #expect(script.batches.map { $0.map(\.eventID) } == [["due"]])
        #expect(await box.pending.map(\.eventID) == ["ahead"])

        clock.set(fixedNow.addingTimeInterval(200))
        await box.flush()
        #expect(script.batches.last.map { $0.map(\.eventID) } == ["ahead"])
        #expect(await box.pending.isEmpty)
    }

    @Test func pendingEventsSurviveARestartWithTheirIDs() async {
        let file = tempFile()
        let failing = Script { _, _ in throw Boom() }
        let first = outbox(file, failing)
        await first.enqueue(event("kept-1"))
        await first.enqueue(event("kept-2"))

        let second = outbox(file, Script { _, batch in acceptAll(batch) })
        #expect(await second.pending.map(\.eventID) == ["kept-1", "kept-2"])
        await second.flush()
        #expect(await outbox(file, Script { _, _ in throw Boom() }).pending.isEmpty)
    }

    // MARK: Durability (corrective change before slice 11c)

    /// A folder the test owns, with the queue file inside it.
    private func ownFolder() throws -> (dir: URL, file: URL) {
        let dir = FileManager.default.temporaryDirectory.appending(path: "feedback-outbox-tests-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return (dir, dir.appending(path: "feedback-outbox.json"))
    }

    private func setMode(_ url: URL, _ mode: Int) throws {
        try FileManager.default.setAttributes([.posixPermissions: mode], ofItemAtPath: url.path)
    }

    @Test func aFailedWriteIsReportedKeptInMemoryAndStillSent() async throws {
        let folder = try ownFolder()
        try setMode(folder.dir, 0o500)   // read-only folder: the queue file cannot be written
        defer { try? setMode(folder.dir, 0o755) }
        let script = Script { _, batch in acceptAll(batch) }
        let box = outbox(folder.file, script)

        await box.enqueue(event("write-fails"))
        #expect(await box.storageError != nil)
        #expect(await box.pending.map(\.eventID) == ["write-fails"])

        await box.flush()
        #expect(script.batches.map { $0.map(\.eventID) } == [["write-fails"]])
        #expect(await box.pending.isEmpty)
    }

    @Test func aLaterSuccessfulWriteClearsTheErrorAndSavesEverything() async throws {
        let folder = try ownFolder()
        try setMode(folder.dir, 0o500)
        let box = outbox(folder.file, Script { _, _ in throw Boom() })
        await box.enqueue(event("a"))
        #expect(await box.storageError != nil)

        try setMode(folder.dir, 0o755)
        await box.enqueue(event("b"))
        #expect(await box.storageError == nil)
        #expect(await outbox(folder.file, Script { _, _ in throw Boom() }).pending.map(\.eventID) == ["a", "b"])
    }

    @Test func anUnreadableSavedQueueIsMovedAsideAndNotOverwrittenAsEmpty() async throws {
        let folder = try ownFolder()
        let garbage = Data("not json {".utf8)
        try garbage.write(to: folder.file)
        let box = outbox(folder.file, Script { _, _ in throw Boom() })

        #expect(await box.storageError != nil)
        #expect(await box.pending.isEmpty)
        let aside = try FileManager.default.contentsOfDirectory(atPath: folder.dir.path)
            .first { $0.hasPrefix("feedback-outbox.unreadable-") }
        let kept = try #require(aside)
        #expect(try Data(contentsOf: folder.dir.appending(path: kept)) == garbage)

        await box.enqueue(event("after-move"))
        #expect(await box.storageError == nil)
        #expect(await outbox(folder.file, Script { _, _ in throw Boom() }).pending.map(\.eventID) == ["after-move"])
    }

    @Test func anUnreadableSavedQueueThatCannotBeMovedIsLeftIntact() async throws {
        let folder = try ownFolder()
        let garbage = Data("not json {".utf8)
        try garbage.write(to: folder.file)
        try setMode(folder.dir, 0o500)   // read-only folder: the file cannot be moved aside either
        defer { try? setMode(folder.dir, 0o755) }
        let box = outbox(folder.file, Script { _, _ in throw Boom() })
        #expect(await box.storageError != nil)

        await box.enqueue(event("refused"))
        #expect(await box.storageError != nil)
        try setMode(folder.dir, 0o755)
        #expect(try Data(contentsOf: folder.file) == garbage)
    }
}
