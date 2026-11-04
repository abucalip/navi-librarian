import DiscairCore
import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

private final class RouteTransport: HTTPTransport, @unchecked Sendable {
    private let lock = NSLock()
    private var sentRequests: [(path: String, body: [String: Any])] = []
    var routes: [String: (Int, String)]
    init(_ routes: [String: (Int, String)]) { self.routes = routes }
    var sent: [(path: String, body: [String: Any])] { lock.withLock { sentRequests } }
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let path = request.url!.path
        let body = (try? JSONSerialization.jsonObject(with: request.httpBody ?? Data())) as? [String: Any] ?? [:]
        lock.withLock { sentRequests.append((path, body)) }
        let (status, json) = routes[path] ?? (404, #"{"detail":"no route"}"#)
        return (Data(json.utf8), HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
    }
}

private let ok = (200, #"{"ok":true,"status":"queued","message":"Queued for download."}"#)
private let refused = (200, #"{"ok":false,"status":"settings_required","message":"Add the slskd API key in Discovery Settings first."}"#)
private let fb = (200, #"{"ok":true}"#)
private let jobsEmpty = (200, #"{"ok":true,"acquisitions":[]}"#)

@MainActor
private func make(_ routes: [String: (Int, String)], window: Duration = .milliseconds(60)) throws -> (AcquisitionModel, RouteTransport) {
    let t = RouteTransport(routes)
    let client = try LibrarianClient(baseURL: URL(string: "https://lib.example.ts.net")!,
                                     credential: Credential(username: "owner", password: "pw"), transport: t)
    let m = AcquisitionModel(undoWindow: window)
    m.configure(librarian: client)
    return (m, t)
}

/// Waits for a condition instead of a fixed sleep: the main actor is shared with the screenshot tests, so timing varies.
@MainActor
private func until(_ condition: () -> Bool) async {
    for _ in 0..<500 where !condition() { try? await Task.sleep(for: .milliseconds(20)) }
}

private let album = AlbumItem(id: 1, title: "Tago Mago", artist: "Can", year: 1971, genre: "Krautrock", format: "", owned: false, hue: 100)

@MainActor
struct AcquisitionModelTests {
    @Test func getShowsPendingThenTheServersAnswer() async throws {
        let (m, t) = try make(["/api/acquire": ok, "/api/acquisitions": jobsEmpty])
        #expect(m.buttonLabel(for: album) == "Get" && m.canGet(album))
        await m.get(album)
        #expect(m.buttonLabel(for: album) == "Requested" && !m.canGet(album))
        #expect(m.detail(for: album) == "Queued for download.")
        let first = try #require(t.sent.first { $0.path == "/api/acquire" })
        #expect(first.body["artist"] as? String == "Can" && first.body["album"] as? String == "Tago Mago")
        #expect(first.body["auto_queue"] as? Bool == true)
    }

    @Test func aRefusalIsNotShownAsSuccess() async throws {
        let (m, _) = try make(["/api/acquire": refused, "/api/acquisitions": jobsEmpty])
        await m.get(album)
        #expect(m.buttonLabel(for: album) == "Retry" && m.canGet(album))
        #expect(m.detail(for: album).contains("slskd API key"))
    }

    @Test func aServerErrorKeepsItsText() async throws {
        let (m, _) = try make(["/api/acquire": (502, #"{"detail":"Could not search slskd for this album."}"#), "/api/acquisitions": jobsEmpty])
        await m.get(album)
        #expect(m.buttonLabel(for: album) == "Retry" && m.detail(for: album) == "Could not search slskd for this album.")
    }

    @Test func getWithoutALibrarianSaysSo() async {
        let m = AcquisitionModel()
        await m.get(album)
        #expect(m.buttonLabel(for: album) == "Retry" && m.detail(for: album).contains("Settings"))
    }

    @Test func getSongTracksItsOwnState() async throws {
        let (m, t) = try make(["/api/acquire/track": ok, "/api/acquisitions": jobsEmpty])
        await m.getSong(album, title: "Halleluhwah", trackNumber: 2)
        #expect(m.buttonLabel(for: album, song: "Halleluhwah") == "Requested")
        #expect(m.buttonLabel(for: album, song: "Paperhouse") == "Get")   // other songs and the album are untouched
        #expect(m.buttonLabel(for: album) == "Get")
        let r = try #require(t.sent.first { $0.path == "/api/acquire/track" })
        #expect(r.body["title"] as? String == "Halleluhwah" && r.body["track_number"] as? Int == 2 && r.body["year"] as? Int == 1971)
    }

    @Test func anExistingJobShowsAsRequestedAfterARestart() async throws {
        let jobs = #"{"ok":true,"acquisitions":[{"artist":"Can","album":"Tago Mago","status":"downloading","details":{"live_progress":{"available":true,"percent":64.2}}}]}"#
        let (m, _) = try make(["/api/acquisitions": (200, jobs)])
        await m.refresh()
        #expect(m.buttonLabel(for: album) == "Requested" && m.detail(for: album) == "Downloading 64%")
        #expect(m.activeCount == 1 && m.tickerText.contains("Downloading 64%: Tago Mago"))
    }

    @Test func tickerNamesWorkingQueuedImportedAndFailed() async throws {
        let jobs = #"{"ok":true,"acquisitions":[{"artist":"A","album":"One","status":"downloading"},{"artist":"B","album":"Two","status":"queued"},{"artist":"C","album":"Three","status":"imported","updated_at":5},{"artist":"D","album":"Four","status":"no_matches"}]}"#
        let (m, _) = try make(["/api/acquisitions": (200, jobs)])
        await m.refresh()
        #expect(m.tickerText == "▶ Downloading: One  ■  Queued: Two  ■  Imported: Three  ■  Failed: 1")
        #expect(AcquisitionModel().tickerText == "Pipeline: no downloads in progress")
    }

    @Test func saveSendsFeedbackAndMarksSaved() async throws {
        let (m, t) = try make(["/api/discovery/feedback": fb, "/api/acquisitions": jobsEmpty])
        await m.save(album)
        #expect(m.isSaved(album))
        #expect(t.sent.last { $0.path == "/api/discovery/feedback" }?.body["action"] as? String == "save")
    }

    @Test func aFailedSaveShowsANoticeAndStaysUnsaved() async throws {
        let (m, _) = try make(["/api/discovery/feedback": (502, #"{"detail":"Could not save discovery feedback."}"#)])
        await m.save(album)
        #expect(!m.isSaved(album) && m.notice == "Could not save: Could not save discovery feedback.")
        m.clearNotice()
        #expect(m.notice == nil)
    }

    @Test func notForMeHidesAtOnceAndSendsAfterTheUndoWindow() async throws {
        let (m, t) = try make(["/api/discovery/feedback": fb, "/api/acquisitions": jobsEmpty])
        m.notForMe(album)
        #expect(m.isHidden(album) && m.pending?.title == "Tago Mago")
        #expect(!t.sent.contains { $0.path == "/api/discovery/feedback" })   // nothing sent yet
        await until { m.pending == nil && t.sent.contains { $0.path == "/api/discovery/feedback" } }
        #expect(m.pending == nil && m.isHidden(album))
        let sent = try #require(t.sent.first { $0.path == "/api/discovery/feedback" })
        #expect(sent.body["action"] as? String == "dismiss")
    }

    @Test func undoBringsTheAlbumBackAndSendsNothing() async throws {
        let (m, t) = try make(["/api/discovery/feedback": fb, "/api/acquisitions": jobsEmpty])
        m.notForMe(album)
        m.undo()
        #expect(!m.isHidden(album) && m.pending == nil)
        try await Task.sleep(for: .milliseconds(300))   // longer than the 60 ms window: nothing may be sent
        #expect(!t.sent.contains { $0.path == "/api/discovery/feedback" })
    }

    @Test func neverSuggestSendsTheArtistActionAndHidesTheirAlbums() async throws {
        let (m, t) = try make(["/api/discovery/feedback": fb, "/api/acquisitions": jobsEmpty], window: .seconds(30))
        m.notForMe(album)
        await m.neverSuggest()
        let other = AlbumItem(id: 2, title: "Ege Bamyasi", artist: "Can", year: 1972, genre: "", format: "", owned: false, hue: 1)
        #expect(m.isHidden(other) && m.pending == nil)
        let sends = t.sent.filter { $0.path == "/api/discovery/feedback" }
        #expect(sends.count == 1 && sends[0].body["action"] as? String == "dismiss_artist")
    }

    @Test func aFailedDismissalBringsTheAlbumBackWithANotice() async throws {
        let (m, _) = try make(["/api/discovery/feedback": (502, #"{"detail":"Could not save discovery feedback."}"#), "/api/acquisitions": jobsEmpty])
        m.notForMe(album)
        await until { m.notice != nil }
        #expect(!m.isHidden(album))
        #expect(m.notice?.contains("Could not dismiss Tago Mago") == true)
    }

    @Test func flushSendsAWaitingDismissalNow() async throws {
        let (m, t) = try make(["/api/discovery/feedback": fb, "/api/acquisitions": jobsEmpty], window: .seconds(30))
        m.notForMe(album)
        await m.flush()
        #expect(m.pending == nil && t.sent.contains { $0.path == "/api/discovery/feedback" })
    }

    @Test func aSecondDismissalSendsTheFirstImmediately() async throws {
        let (m, t) = try make(["/api/discovery/feedback": fb, "/api/acquisitions": jobsEmpty], window: .seconds(30))
        m.notForMe(album)
        m.notForMe(AlbumItem(id: 3, title: "Monster Movie", artist: "Can", year: 1969, genre: "", format: "", owned: false, hue: 2))
        await until { t.sent.contains { $0.path == "/api/discovery/feedback" } }
        #expect(m.pending?.title == "Monster Movie")
        #expect(t.sent.filter { $0.path == "/api/discovery/feedback" }.count == 1)
        #expect(m.isHidden(album))
    }

    // MARK: Downloads screen

    static let sampleJobs: [Acquisition] = {
        let json = """
        {"acquisitions":[
         {"artist":"Can","album":"Tago Mago","status":"downloading","updated_at":30,"details":{"kind":"album","album_name":"Tago Mago","live_progress":{"available":true,"total_tracks":11,"completed_tracks":3,"percent":27.5,"speed_bytes_per_second":1200000}}},
         {"artist":"Neu!","album":"Neu! 75","status":"queued","updated_at":20,"details":{"kind":"album"}},
         {"artist":"Faust","album":"Zamzam (song on Faust IV)","status":"no_matches","updated_at":10,"details":{"kind":"track","album_name":"Faust IV","track_title":"Zamzam","message":"No source found."}},
         {"artist":"Talk Talk","album":"Laughing Stock","status":"imported","updated_at":5,"details":{"kind":"album"}}]}
        """
        struct P: Decodable { let acquisitions: [Acquisition] }
        return try! JSONDecoder().decode(P.self, from: Data(json.utf8)).acquisitions
    }()

    @Test func downloadsAreOrderedMovingWaitingFailedImported() {
        let m = AcquisitionModel()
        m.showJobs(Self.sampleJobs.reversed())
        #expect(m.sortedJobs.map(\.artist) == ["Can", "Neu!", "Faust", "Talk Talk"])
        #expect(m.importedCount == 1)
    }

    @Test func progressIsWordsAndAFraction() {
        let m = AcquisitionModel()
        let can = Self.sampleJobs[0]
        #expect(m.fraction(can) == 0.275)
        #expect(m.progressLine(can).hasPrefix("3 of 11 tracks · "))
        #expect(m.statusLine(can) == "Downloading 27%")
        #expect(m.fraction(Self.sampleJobs[1]) == nil && m.progressLine(Self.sampleJobs[1]).isEmpty)
        #expect(m.canSkip(can) && !m.canRetry(can))
        #expect(m.canRetry(Self.sampleJobs[2]) && !m.canSkip(Self.sampleJobs[2]))
    }

    @Test func retryOfASongAsksForThatSongOnItsAlbum() async throws {
        let (m, t) = try make(["/api/acquire/track": ok, "/api/acquisitions": jobsEmpty])
        await m.retry(Self.sampleJobs[2])
        let sent = try #require(t.sent.first { $0.path == "/api/acquire/track" })
        #expect(sent.body["title"] as? String == "Zamzam" && sent.body["album"] as? String == "Faust IV")
        #expect(m.notice == nil)
    }

    @Test func skipSourceAndDismissSendTheJobAndDismissRemovesIt() async throws {
        let (m, t) = try make(["/api/acquisitions/skip": fb, "/api/acquisitions/dismiss": ok, "/api/acquisitions": jobsEmpty])
        await m.skipSource(Self.sampleJobs[0])
        #expect(t.sent.contains { $0.path == "/api/acquisitions/skip" && $0.body["artist"] as? String == "Can" })
        await m.dismiss(Self.sampleJobs[3])
        #expect(t.sent.contains { $0.path == "/api/acquisitions/dismiss" && $0.body["album"] as? String == "Laughing Stock" })
    }

    @Test func aRefusedDismissKeepsTheJobAndShowsTheServersWords() async throws {
        let (m, _) = try make(["/api/acquisitions/dismiss": (409, #"{"detail":"Files are in use."}"#), "/api/acquisitions": (200, #"{"ok":true,"acquisitions":[{"artist":"Talk Talk","album":"Laughing Stock","status":"imported"}]}"#)])
        await m.refresh()
        await m.dismiss(try #require(m.jobs.first))
        #expect(m.jobs.count == 1)
        #expect(m.notice?.contains("Files are in use.") == true)
    }
}
