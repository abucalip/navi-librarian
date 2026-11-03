import DiscairCore
import Foundation
import Testing
@testable import DiscairUI

private struct StubProber: Prober {
    let outcome: ProbeOutcome
    func probe(_ url: URL) async -> ProbeOutcome { outcome }
}

private struct PingTransport: HTTPTransport {
    let status: Int
    let body: String
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        (Data(body.utf8), HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
    }
}

private let upNetwork = [NetworkInterface(name: "en0", isUp: true, addresses: ["192.168.1.20"])]

@MainActor
private func makeSession(prober: ProbeOutcome = .reachable, secrets: InMemorySecretStore = InMemorySecretStore(),
                         transport: PingTransport = PingTransport(status: 200, body: #"{"subsonic-response":{"status":"ok","version":"1.16.1"}}"#),
                         dir: URL? = nil) -> (SessionModel, URL) {
    let url = (dir ?? FileManager.default.temporaryDirectory.appending(path: "discair-\(UUID().uuidString)")).appending(path: "profiles.json")
    let model = SessionModel(store: ProfileStore(fileURL: url), secrets: secrets,
                             resolver: ProfileResolver(prober: StubProber(outcome: prober), interfaces: { upNetwork }),
                             navidromeTransport: { transport })
    return (model, url)
}

@MainActor
struct SessionModelTests {
    @Test func profilesPersistAcrossLaunches() throws {
        let (a, url) = makeSession()
        try a.addProfile(name: "Home", librarianURL: "http://192.168.1.87:8686", navidromeURL: "http://192.168.1.87:4533")
        let b = SessionModel(store: ProfileStore(fileURL: url), secrets: InMemorySecretStore())
        #expect(b.profiles.profiles.map(\.name) == ["Home"])
    }

    @Test func publicHTTPAddressIsRefused() {
        let (m, _) = makeSession()
        #expect(throws: (any Error).self) { try m.addProfile(name: "X", librarianURL: "http://example.com", navidromeURL: "http://example.com") }
        #expect(m.profiles.profiles.isEmpty)
    }

    @Test func duplicateNameIsRefused() throws {
        let (m, _) = makeSession()
        try m.addProfile(name: "Home", librarianURL: "http://192.168.1.87:8686", navidromeURL: "http://192.168.1.87:4533")
        #expect(throws: ProfileError.duplicateName) {
            try m.addProfile(name: "home", librarianURL: "http://192.168.1.88:8686", navidromeURL: "http://192.168.1.88:4533")
        }
    }

    @Test func loginIsSavedWithoutExposingThePassword() throws {
        let secrets = InMemorySecretStore()
        let (m, _) = makeSession(secrets: secrets)
        try m.saveLogin(.navidrome, username: "owner", password: "s3cret-pass")
        #expect(m.hasNavidromeLogin && m.navidromeUsername == "owner")
        #expect(!"\(m.label) \(m.statusDetail)".contains("s3cret-pass"))
        #expect(try secrets.credential(for: .navidrome)?.username == "owner")
        #expect(throws: SettingsError.emptyLogin) { try m.saveLogin(.librarian, username: "", password: "x") }
        try m.removeLogin(.navidrome)
        #expect(!m.hasNavidromeLogin)
    }

    @Test func connectWithoutProfilesIsNotConfigured() async {
        let (m, _) = makeSession()
        await m.connect()
        #expect(m.status == .notConfigured)
    }

    @Test func connectNamesAnUnreachableServer() async throws {
        let (m, _) = makeSession(prober: .failed(.serverUnreachable))
        try m.addProfile(name: "Home", librarianURL: "http://192.168.1.87:8686", navidromeURL: "http://192.168.1.87:4533")
        await m.connect()
        #expect(m.status == .failed(.serverUnreachable))
        #expect(m.canRetry)
        #expect(m.statusDetail.contains("did not answer"))
    }

    @Test func connectWithoutANavidromeLoginIsUnauthorised() async throws {
        let (m, _) = makeSession()
        try m.addProfile(name: "Home", librarianURL: "http://192.168.1.87:8686", navidromeURL: "http://192.168.1.87:4533")
        await m.connect()
        guard case .failed(.unauthorised) = m.status else { Issue.record("expected unauthorised, got \(m.status)"); return }
    }

    @Test func connectSucceedsWithAWorkingNavidrome() async throws {
        let (m, _) = makeSession()
        try m.addProfile(name: "Home", librarianURL: "http://192.168.1.87:8686", navidromeURL: "http://192.168.1.87:4533")
        try m.saveLogin(.navidrome, username: "owner", password: "pw")
        await m.connect()
        guard case .connected(let p, let manual) = m.status else { Issue.record("expected connected, got \(m.status)"); return }
        #expect(p.name == "Home" && !manual)
        #expect(m.isUnencrypted)
        #expect(m.label.contains("unencrypted"))
        #expect(m.navidrome != nil)
        #expect(m.librarianNote?.contains("No Librarian login") == true)
    }

    @Test func removingTheActiveProfileDisconnects() async throws {
        let (m, _) = makeSession()
        try m.addProfile(name: "Home", librarianURL: "http://192.168.1.87:8686", navidromeURL: "http://192.168.1.87:4533")
        try m.saveLogin(.navidrome, username: "owner", password: "pw")
        await m.connect()
        let id = try #require(m.activeProfile?.id)
        try m.removeProfile(id: id)
        #expect(m.status == .notConfigured && m.navidrome == nil)
    }
}
