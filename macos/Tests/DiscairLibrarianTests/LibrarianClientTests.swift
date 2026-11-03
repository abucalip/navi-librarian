import Testing
import Foundation
import DiscairCore
@testable import DiscairLibrarian

/// Recorded bodies from the Android contract fixtures (`android/contract-fixtures/librarian/`), linked into this test
/// target as `Fixtures`. `xcodebuild` copies the linked files into the test bundle (and its test process may not be
/// allowed to read ~/Desktop); `swift build` copies only the link, so that case reads the source path instead.
func fixtureBody(_ name: String, file: String = #filePath) throws -> Data {
    let inBundle = Bundle.module.url(forResource: name, withExtension: "json", subdirectory: "Fixtures")
    let root = URL(fileURLWithPath: file).deletingLastPathComponent()
    let url = [inBundle, root.appending(path: "Fixtures/\(name).json")].compactMap { $0 }
        .first { FileManager.default.isReadableFile(atPath: $0.path) }
    guard let url else { throw CocoaError(.fileNoSuchFile) }
    let object = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
    return try JSONSerialization.data(withJSONObject: (object["response"] as! [String: Any])["body"]!)
}

final class MockTransport: HTTPTransport, @unchecked Sendable {
    typealias Handler = @Sendable (URLRequest, Int) throws -> (Int, Data)
    private let lock = NSLock(); private var requests: [URLRequest] = []; private let handler: Handler
    init(_ handler: @escaping Handler) { self.handler = handler }
    var sent: [URLRequest] { lock.withLock { requests } }
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let n = lock.withLock { requests.append(request); return requests.count }
        let (status, data) = try handler(request, n)
        return (data, HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
    }
}

@Suite("Librarian client") struct LibrarianClientTests {
    let base = URL(string: "https://lib.example.ts.net")!
    let cred = Credential(username: "owner", password: "s3cret-pw-1234")
    func client(_ t: MockTransport) throws -> LibrarianClient { try LibrarianClient(baseURL: base, credential: cred, transport: t) }

    @Test func authStatus() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("auth_status")) }
        #expect(try await client(t).setupRequired() == false)
        #expect(t.sent[0].url!.path == "/api/auth/status" && t.sent[0].httpMethod == "GET")
    }

    @Test func loginSendsJSONToTheDocumentedRoute() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("auth_login")) }
        try await client(t).login()
        let req = t.sent[0]
        #expect(req.httpMethod == "POST" && req.url!.path == "/api/auth/login")
        #expect(req.value(forHTTPHeaderField: "Content-Type") == "application/json")
        let body = try JSONSerialization.jsonObject(with: req.httpBody!) as! [String: String]
        #expect(body == ["username": "owner", "password": "s3cret-pw-1234"])
        #expect(req.url!.query == nil)   // the password is in the body, never the URL
    }

    @Test func badLoginIsUnauthorised() async throws {
        let t = MockTransport { _, _ in (401, try fixtureBody("auth_login_bad_credentials")) }
        await #expect(throws: DiscairError.unauthorised(message: "Invalid username or password.")) { try await client(t).login() }
    }

    @Test func rateLimitIsReportedAndNeverRetried() async throws {
        let body = Data(#"{"detail":"Too many login attempts. Try again in 15 minutes."}"#.utf8)
        let t = MockTransport { _, _ in (429, body) }
        await #expect(throws: DiscairError.tooManyAttempts(message: "Too many login attempts. Try again in 15 minutes.")) { try await client(t).login() }
        #expect(t.sent.count == 1)
    }

    @Test func accountNotSetUpIsAServerError() async {
        let t = MockTransport { _, _ in (409, Data(#"{"detail":"Create the app account first."}"#.utf8)) }
        await #expect(throws: DiscairError.server(status: 409, message: "Create the app account first.")) { try await client(t).login() }
    }

    @Test func dashboardPicksFromFixture() async throws {
        let t = MockTransport { _, _ in (200, try fixtureBody("dashboard_picks")) }
        let picks = try await client(t).dashboardPicks(count: 10)
        #expect(t.sent[0].url!.path == "/api/dashboard-picks" && t.sent[0].url!.query == "count=10")
        #expect(picks.count >= 2)
        #expect(picks[0].artist == "Arctic Monkeys" && picks[0].album == "AM")
        #expect(picks[0].suggestedTracks?.first == "Arabella" && picks[0].similarTo?.first == "The Strokes")
        #expect(picks[0].dashboardCategory == "Personal discoveries" && picks[0].discoveryCategory == "cross_genre")
        #expect(picks[0].genres?.contains("art rock") == true)
        #expect(picks[1].artist == "Dave Grusin")
    }

    @Test func countIsClamped() async throws {
        let t = MockTransport { _, _ in (200, Data(#"{"items":[]}"#.utf8)) }
        let c = try client(t)
        _ = try await c.dashboardPicks(count: 500); _ = try await c.dashboardPicks(count: 0)
        #expect(t.sent.map { $0.url!.query } == ["count=30", "count=1"])
    }

    @Test func a401ReLogsInOnceAndRetries() async throws {
        let t = MockTransport { req, n in
            switch (req.url!.path, n) {
            case ("/api/dashboard-picks", 1): return (401, Data(#"{"detail":"Authentication required."}"#.utf8))
            case ("/api/auth/login", _): return (200, try fixtureBody("auth_login"))
            default: return (200, try fixtureBody("dashboard_picks"))
            }
        }
        #expect(try await client(t).dashboardPicks().count >= 2)
        #expect(t.sent.map { $0.url!.path } == ["/api/dashboard-picks", "/api/auth/login", "/api/dashboard-picks"])
    }

    @Test func aSecond401IsReportedWithoutLooping() async throws {
        let t = MockTransport { req, _ in
            req.url!.path == "/api/auth/login" ? (200, try fixtureBody("auth_login")) : (401, Data(#"{"detail":"Authentication required."}"#.utf8))
        }
        await #expect(throws: DiscairError.unauthorised(message: "Authentication required.")) { try await client(t).dashboardPicks() }
        #expect(t.sent.count == 3)
    }

    @Test func failedReLoginStops() async throws {
        let t = MockTransport { req, _ in
            req.url!.path == "/api/auth/login" ? (401, Data(#"{"detail":"Invalid username or password."}"#.utf8)) : (401, Data())
        }
        await #expect(throws: DiscairError.unauthorised(message: "Invalid username or password.")) { try await client(t).dashboardPicks() }
        #expect(t.sent.count == 2)
    }

    @Test func serverAndTransportErrors() async throws {
        await #expect(throws: DiscairError.server(status: 502, message: nil)) {
            try await client(MockTransport { _, _ in (502, Data()) }).dashboardPicks()
        }
        await #expect(throws: DiscairError.self) {
            try await client(MockTransport { _, _ in (200, Data("<html>".utf8)) }).dashboardPicks()
        }
        await #expect(throws: DiscairError.noNetwork) {
            try await client(MockTransport { _, _ in throw URLError(.notConnectedToInternet) }).dashboardPicks()
        }
        await #expect(throws: DiscairError.serverUnreachable) {
            try await client(MockTransport { _, _ in throw URLError(.cannotConnectToHost) }).login()
        }
        let tail = try LibrarianClient(baseURL: base, credential: cred, transport: MockTransport { _, _ in throw URLError(.timedOut) }, tailscaleHint: { true })
        await #expect(throws: DiscairError.tailscaleNotConnected) { try await tail.login() }
    }

    @Test func errorsNeverContainTheSecret() async {
        let t = MockTransport { _, _ in (401, Data(#"{"detail":"Invalid username or password."}"#.utf8)) }
        do { try await client(t).login() } catch {
            #expect(!"\(error)".contains("s3cret-pw-1234"))
        }
    }

    @Test func theTransportRulesApply() {
        #expect(throws: DiscairError.insecureOrInvalidAddress(reason: .publicHTTP)) {
            try LibrarianClient(baseURL: URL(string: "http://lib.example.com")!, credential: cred)
        }
        #expect(throws: Never.self) { try LibrarianClient(baseURL: URL(string: "http://192.168.1.87:8080")!, credential: cred) }
    }
}
