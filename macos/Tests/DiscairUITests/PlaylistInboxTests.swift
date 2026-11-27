import DiscairCore
import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

func inboxFixture(_ name: String, file: String = #filePath) throws -> [String: Any] {
    let url = URL(fileURLWithPath: file).deletingLastPathComponent()
        .appending(path: "../../../tests/fixtures/listenbrainz_inbox_responses.json").standardized
    let fixtures = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: [String: Any]])
    return try #require(fixtures[name])
}

private actor InboxFixtureTransport: HTTPTransport {
    private(set) var requests: [String] = []
    private let responses: [String: Data]
    private let requireLogin: Bool

    init(list: String = "list", requireLogin: Bool = false) throws {
        self.requireLogin = requireLogin
        responses = try [
            "/api/playlists/inbox": JSONSerialization.data(withJSONObject: inboxFixture(list)),
            "/api/playlists/inbox/1": JSONSerialization.data(withJSONObject: inboxFixture("mixed_detail")),
            "/api/playlists/inbox/2": JSONSerialization.data(withJSONObject: inboxFixture("zero_owned_detail")),
        ]
    }

    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let url = try #require(request.url)
        let path = url.path
        requests.append("\(request.httpMethod ?? "") \(path)")
        let status: Int
        let body: Data
        if requireLogin && requests.count == 1 {
            status = 401
            body = Data()
        } else if request.httpMethod == "POST" && path == "/api/auth/login" {
            status = 200
            body = Data()
        } else if request.httpMethod == "GET", let response = responses[path] {
            status = 200
            body = response
        } else {
            status = 404
            body = Data()
        }
        return (body, try #require(HTTPURLResponse(url: url, statusCode: status, httpVersion: nil, headerFields: nil)))
    }

    nonisolated func client() throws -> LibrarianClient {
        try LibrarianClient(baseURL: URL(string: "https://lib.example.ts.net")!,
                            credential: Credential(username: "owner", password: "fixture"), transport: self)
    }
}

@MainActor
struct PlaylistInboxTests {
    @Test func shelfAndEditionUseAuthenticatedReadsAndPreserveSourcePositions() async throws {
        let transport = try InboxFixtureTransport(requireLogin: true)
        let model = PlaylistInboxModel()
        model.configure(librarian: try transport.client())
        await model.loadShelf()
        guard case .loaded(let shelf) = model.shelf else { Issue.record("Inbox did not load"); return }
        #expect(shelf.state == "ready")
        #expect(shelf.items.map(\.id) == [2, 1])
        #expect(shelf.items.map(\.ownedCount) == [0, 2])
        #expect(shelf.items.last?.generatedAt == "2027-01-08T08:00:00+00:00")

        model.open(1)
        await model.loadDetail(id: 1)
        guard case .loaded(let edition) = model.detail else { Issue.record("Edition did not load"); return }
        #expect(edition.tracks.map(\.position) == Array(0..<6))
        #expect(PlaylistInboxModel.playbackItems(for: edition).map(\.songID) == ["owned", "owned"])

        model.close()
        #expect(model.editionID == nil)
        #expect(await transport.requests == [
            "GET /api/playlists/inbox", "POST /api/auth/login", "GET /api/playlists/inbox", "GET /api/playlists/inbox/1",
        ])
    }

    @Test(arguments: ["empty", "unconfigured"])
    func emptyShelfDecodesItsServerState(_ fixture: String) async throws {
        let transport = try InboxFixtureTransport(list: fixture)
        let model = PlaylistInboxModel()
        model.configure(librarian: try transport.client())
        await model.loadShelf()
        guard case .loaded(let shelf) = model.shelf else { Issue.record("Inbox did not load"); return }
        #expect(shelf.state == fixture)
        #expect(shelf.items.isEmpty)
    }

    @Test func rendersShelfAndMixedAndZeroOwnedEditions() async throws {
        let transport = try InboxFixtureTransport()
        let state = AppState(screen: .discover, output: FakeOutput())
        let model = state.playlistInbox
        model.configure(librarian: try transport.client())
        await model.loadShelf()
        let renderer = CupertinoPagesRenderTests()
        try renderer.render("inbox-shelf", width: 660, height: 450, CupertinoDiscover(state: state)) { _ in }

        for (id, name) in [(Int64(1), "mixed"), (Int64(2), "zero-owned")] {
            model.open(id)
            await model.loadDetail(id: id)
            try renderer.render("inbox-\(name)", width: 540, height: 640, CupertinoDiscover(state: state)) { _ in }
        }
    }
}

private actor InboxDownloadTransport: HTTPTransport {
    private var held: CheckedContinuation<Void, Never>?
    private var started: CheckedContinuation<Void, Never>?
    private let hold: Bool
    private var outcomes: [(Int, String)]
    private(set) var posts: [String] = []
    private var owned = false
    private var detailStatus = 200

    init(outcomes: [(Int, String)], hold: Bool = false) {
        self.outcomes = outcomes
        self.hold = hold
    }

    func waitForPost() async {
        if posts.isEmpty { await withCheckedContinuation { started = $0 } }
    }
    func release() { held?.resume(); held = nil }
    func confirmOwned() { owned = true }
    func failReads() { detailStatus = 503 }

    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let url = try #require(request.url)
        let status: Int
        let data: Data
        if request.httpMethod == "POST" {
            #expect(request.httpBody == nil)
            posts.append(url.path)
            let outcome = outcomes.removeFirst()
            if hold {
                await withCheckedContinuation { continuation in
                    held = continuation
                    started?.resume()
                    started = nil
                }
            }
            status = outcome.0
            data = Data(outcome.1.utf8)
        } else {
            var detail = try inboxFixture("mixed_detail")
            if owned {
                var tracks = try #require(detail["tracks"] as? [[String: Any]])
                tracks[4]["match_state"] = "owned"
                tracks[4]["song_id"] = "new-song"
                detail["tracks"] = tracks
                detail["owned_count"] = 3
            }
            status = detailStatus
            data = try JSONSerialization.data(withJSONObject: detail)
        }
        return (data, try #require(HTTPURLResponse(url: url, statusCode: status, httpVersion: nil, headerFields: nil)))
    }

    nonisolated func client() throws -> LibrarianClient {
        try LibrarianClient(baseURL: URL(string: "https://lib.example.ts.net")!,
                            credential: Credential(username: "owner", password: "fixture"), transport: self)
    }
}

@MainActor
struct PlaylistInboxDownloadTests {
    private let accepted = #"{"ok":true,"status":"requested","artist":"Artist","job_album":"No Album (song on Resolved)"}"#

    private func model(_ transport: InboxDownloadTransport) async throws -> PlaylistInboxModel {
        let model = PlaylistInboxModel()
        model.configure(librarian: try transport.client())
        model.open(1)
        await model.loadDetail(id: 1)
        return model
    }

    private func track(_ model: PlaylistInboxModel, _ position: Int = 4) throws -> PlaylistInboxTrack {
        guard case .loaded(let detail) = model.detail else { throw DiscairError.serverUnreachable }
        return try #require(detail.tracks.first { $0.position == position })
    }

    private func job(_ status: String, album: String = "No Album (song on Resolved)") throws -> Acquisition {
        let data = try JSONSerialization.data(withJSONObject: [
            "artist": "Artist", "album": album, "status": status,
            "details": ["live_progress": ["available": true, "percent": 42]],
        ])
        return try JSONDecoder().decode(Acquisition.self, from: data)
    }

    @Test func albumlessDownloadUsesStoredPositionAndSharedProgressThenWaitsForOwnership() async throws {
        let transport = InboxDownloadTransport(outcomes: [(200, accepted)])
        let model = try await model(transport)
        await model.download(position: 4, jobs: [])
        let row = try track(model)
        #expect(await transport.posts == ["/api/playlists/inbox/1/tracks/4/download"])
        #expect(model.downloadState(for: row, jobs: [try job("downloading")]) == .requested("Downloading 42%"))
        #expect(model.downloadState(for: row, jobs: [try job("imported")]) == .requested("Imported · waiting for library scan"))
        guard case .loaded(let before) = model.detail else { Issue.record("Missing detail"); return }
        #expect(PlaylistInboxModel.playbackItems(for: before).map(\.songID) == ["owned", "owned"])
        await transport.confirmOwned()
        await model.loadDetail(id: 1, refreshing: true)
        guard case .loaded(let after) = model.detail else { Issue.record("Missing detail"); return }
        #expect(PlaylistInboxModel.playbackItems(for: after).map(\.songID) == ["owned", "owned", "new-song"])
        #expect(model.downloadState(for: try track(model), jobs: []) == .requested("Owned"))
    }

    @Test func structuredRefusalAndHTTP200RefusalExplainTheProblemAndAllowRetry() async throws {
        let transport = InboxDownloadTransport(outcomes: [
            (409, #"{"detail":{"code":"unresolved_album","message":"No confirmed album could be resolved."}}"#),
            (200, #"{"ok":false,"status":"settings_required","message":"Set up downloads first."}"#),
            (200, accepted),
        ])
        let model = try await model(transport)
        await model.download(position: 4, jobs: [])
        #expect(model.downloadState(for: try track(model), jobs: []) == .failed("No confirmed album could be resolved."))
        await model.download(position: 4, jobs: [])
        #expect(model.downloadState(for: try track(model), jobs: []) == .failed("Set up downloads first."))
        await model.download(position: 4, jobs: [])
        #expect(model.downloadState(for: try track(model), jobs: [try job("no_matches")]) == .failed("No source found"))
        #expect(await transport.posts.count == 3)
    }

    @Test func pendingClicksAreCoalescedAndOldConnectionRepliesAreIgnored() async throws {
        let transport = InboxDownloadTransport(outcomes: [(200, accepted)], hold: true)
        let model = try await model(transport)
        let request = Task { await model.download(position: 4, jobs: []) }
        await transport.waitForPost()
        #expect(model.downloadState(for: try track(model), jobs: []) == .pending)
        await model.download(position: 4, jobs: [])
        #expect(await transport.posts.count == 1)
        model.configure(librarian: nil)
        await transport.release()
        await request.value
        #expect(model.downloads.isEmpty)
        #expect(model.editionID == nil)
    }

    @Test func savedJobKeysSelectOnlyTheirOwnProgressAndOwnedTracksNeverRequest() async throws {
        let transport = InboxDownloadTransport(outcomes: [])
        let model = try await model(transport)
        let missing = try track(model, 1)
        #expect(model.downloadState(for: missing, jobs: [try job("no_matches", album: "Unrelated")]) == .requested("Downloading"))
        #expect(model.downloadState(for: missing, jobs: [try job("downloading", album: "Missing (song on Album)")]) == .requested("Downloading 42%"))
        await model.download(position: 0, jobs: [])
        #expect(await transport.posts.isEmpty)
    }
    @Test(arguments: ["already_in_progress", "importing", "imported"])
    func existingDownloadsAreNotOfferedRetryWhenOKIsFalse(_ status: String) async throws {
        let response = "{\"ok\":false,\"status\":\"\(status)\",\"message\":\"Already requested.\"}"
        let transport = InboxDownloadTransport(outcomes: [(200, response)])
        let model = try await model(transport)
        await model.download(position: 4, jobs: [])
        let row = try track(model)
        let message = status == "imported" ? "Imported · waiting for library scan" : "Already requested."
        #expect(model.downloadState(for: row, jobs: []) == .requested(message))
        await model.download(position: 4, jobs: [])
        #expect(await transport.posts.count == 1)
    }

    @Test func refreshFailureRetainsPlayableDetailAndShowsNotice() async throws {
        let transport = InboxDownloadTransport(outcomes: [])
        let model = try await model(transport)
        await transport.failReads()
        await model.loadDetail(id: 1, refreshing: true)
        #expect(model.refreshNotice != nil)
        guard case .loaded(let detail) = model.detail else { Issue.record("Detail discarded"); return }
        #expect(PlaylistInboxModel.playbackItems(for: detail).map(\.songID) == ["owned", "owned"])
    }

    @Test func rendersProgressAndUnresolvedRetry() async throws {
        let transport = InboxDownloadTransport(outcomes: [
            (409, #"{"detail":{"code":"unresolved_album","message":"No confirmed album could be resolved."}}"#),
        ])
        let state = AppState(screen: .discover, output: FakeOutput())
        state.playlistInbox.configure(librarian: try transport.client())
        state.playlistInbox.open(1)
        await state.playlistInbox.loadDetail(id: 1)
        await state.playlistInbox.download(position: 4, jobs: [])
        state.acquisition.showJobs([try job("downloading", album: "Missing (song on Album)")])
        try CupertinoPagesRenderTests().render("inbox-downloads", width: 540, height: 740,
                                              CupertinoDiscover(state: state)) { _ in }
    }

}
