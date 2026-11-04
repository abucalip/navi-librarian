import DiscairCore
import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

private func job(_ artist: String, _ album: String, _ status: String, message: String? = nil) -> Acquisition {
    var details = ""
    if let message { details = #","details":{"message":"\#(message)"}"# }
    let json = #"{"artist":"\#(artist)","album":"\#(album)","status":"\#(status)"\#(details)}"#
    return try! JSONDecoder().decode(Acquisition.self, from: Data(json.utf8))
}

@MainActor @Suite struct GetFinishedDetectorTests {
    @Test func firstPollOnlySeeds() {
        var d = GetFinishedDetector()
        #expect(d.events(for: [job("A", "One", "imported"), job("B", "Two", "downloading")]).isEmpty)
    }

    @Test func movingToImportedNotifiesOnce() {
        var d = GetFinishedDetector()
        _ = d.events(for: [job("Talk Talk", "Laughing Stock", "downloading")])
        let e = d.events(for: [job("Talk Talk", "Laughing Stock", "imported")])
        #expect(e.count == 1)
        #expect(e[0].outcome == .imported)
        #expect(e[0].title == "Added to your library")
        #expect(e[0].body == "Laughing Stock by Talk Talk is ready to play.")
        #expect(d.events(for: [job("Talk Talk", "Laughing Stock", "imported")]).isEmpty)
    }

    @Test func movingToFailedCarriesTheServerMessage() {
        var d = GetFinishedDetector()
        _ = d.events(for: [job("A", "One", "searching")])
        let e = d.events(for: [job("A", "One", "no_matches", message: "Nothing matched.")])
        #expect(e.map(\.outcome) == [.failed])
        #expect(e[0].body == "A: Nothing matched.")
    }

    @Test func failedThenRetriedThenImportedNotifiesAgain() {
        var d = GetFinishedDetector()
        _ = d.events(for: [job("A", "One", "queued")])
        #expect(d.events(for: [job("A", "One", "no_matches")]).count == 1)
        _ = d.events(for: [job("A", "One", "retry_requested")])
        #expect(d.events(for: [job("A", "One", "imported")]).count == 1)
    }

    @Test func jobAppearingAlreadyDoneIsNotAnnounced() {
        var d = GetFinishedDetector()
        _ = d.events(for: [])
        #expect(d.events(for: [job("A", "One", "imported")]).isEmpty)
    }

    @Test func resetSeedsAgain() {
        var d = GetFinishedDetector()
        _ = d.events(for: [job("A", "One", "downloading")])
        d.reset()
        #expect(d.events(for: [job("A", "One", "imported")]).isEmpty)
    }
}

@MainActor private final class FakeNotifier: GetNotifier {
    var delivered: [GetFinishedEvent] = []
    func deliver(_ event: GetFinishedEvent) { delivered.append(event) }
}

private final class JobsTransport: HTTPTransport, @unchecked Sendable {
    private let lock = NSLock()
    private var status = "downloading"
    func finish() { lock.withLock { status = "imported" } }
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let s = lock.withLock { status }
        let json = #"{"ok":true,"acquisitions":[{"artist":"A","album":"One","status":"\#(s)"}]}"#
        return (Data(json.utf8), HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!)
    }
}

@MainActor @Suite struct GetNotificationModelTests {
    private func run(enabled: Bool) async throws -> [GetFinishedEvent] {
        let t = JobsTransport()
        let client = try LibrarianClient(baseURL: URL(string: "https://lib.example.ts.net")!,
                                         credential: Credential(username: "owner", password: "pw"), transport: t)
        let m = AcquisitionModel(defaults: UserDefaults(suiteName: "discair-test-\(UUID().uuidString)")!)
        let fake = FakeNotifier()
        m.notifier = fake
        m.notifiesWhenFinished = enabled
        m.configure(librarian: client)
        await m.refresh()   // sees it downloading
        t.finish()
        await m.refresh()   // sees it imported
        m.configure(librarian: nil)   // stops the background poll
        return fake.delivered
    }

    @Test func aFinishedJobIsDelivered() async throws {
        let d = try await run(enabled: true)
        #expect(d.map(\.outcome) == [.imported])
    }

    @Test func offMeansNothingIsDelivered() async throws {
        #expect(try await run(enabled: false).isEmpty)
    }
}
