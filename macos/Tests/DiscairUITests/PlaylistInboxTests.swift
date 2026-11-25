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
