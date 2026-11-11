import DiscairCore
import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

private final class Recorder: HTTPTransport, @unchecked Sendable {
    private let lock = NSLock()
    private var _requests: [URLRequest] = []
    var requests: [URLRequest] { lock.withLock { _requests } }
    let status: Int, body: String
    init(status: Int = 200, body: String = "{}") { self.status = status; self.body = body }
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        lock.withLock { _requests.append(request) }
        return (Data(body.utf8), HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
    }
}

@Suite("Edit sheet Test uses the typed values") struct ServiceDraftProbeTests {
    static func draft(address: String = "", username: String = "", secret: String = "") -> ServiceDraft {
        var d = ServiceDraft(); d.address = address; d.username = username; d.secret = secret; return d
    }

    @Test func untouchedSheetUsesTheServerTestAndAChangeDoesNot() {
        let saved = Self.draft(address: "http://slskd.local:5030")
        #expect(ServiceDraftProbe.plan(for: .slskd, draft: saved, saved: saved) == .useSaved)
        #expect(ServiceDraftProbe.plan(for: .slskd, draft: Self.draft(address: "http://other:5030", secret: "k"), saved: saved) == .probe)
        if case .needsSecret = ServiceDraftProbe.plan(for: .slskd, draft: Self.draft(address: "http://other:5030"), saved: saved) {} else { Issue.record("expected needsSecret") }
        #expect(ServiceDraftProbe.plan(for: .listenbrainz, draft: Self.draft(username: "new"), saved: Self.draft(username: "old")) == .probe)
        #expect(ServiceDraftProbe.plan(for: .discogs, draft: Self.draft(secret: "t"), saved: Self.draft()) == .probe)
    }

    @Test func slskdTestAsksTheTypedAddressWithTheTypedKey() async {
        let net = Recorder()
        let r = await ServiceDraftProbe(transport: net).test(.slskd, draft: Self.draft(address: "http://new-host:5030/", secret: "typed-key"))
        #expect(r.ok)
        #expect(net.requests.first?.url?.absoluteString == "http://new-host:5030/api/v0/server")
        #expect(net.requests.first?.value(forHTTPHeaderField: "X-API-KEY") == "typed-key")
    }

    @Test func rejectedKeysAndMissingUsersAreNamed() async {
        #expect(await ServiceDraftProbe(transport: Recorder(status: 401)).test(.slskd, draft: Self.draft(address: "http://h:1", secret: "k")).status == "authentication_failed")
        #expect(await ServiceDraftProbe(transport: Recorder(status: 200, body: #"{"error":10,"message":"Invalid API key"}"#)).test(.lastfm, draft: Self.draft(secret: "bad")).status == "authentication_failed")
        #expect(await ServiceDraftProbe(transport: Recorder(status: 404)).test(.listenbrainz, draft: Self.draft(username: "nobody")).status == "not_found")
        #expect(await ServiceDraftProbe(transport: Recorder(status: 500)).test(.discogs, draft: Self.draft(secret: "t")).status == "connection_failed")
    }

    @MainActor @Test func nothingIsSavedByTesting() async {
        let c = ServicesController(defaults: UserDefaults(suiteName: "probe-\(UUID())")!)
        c.draft.address = "http://changed"
        let before = c.savedDraft
        _ = await ServiceDraftProbe(transport: Recorder()).test(.slskd, draft: c.draft)
        #expect(c.savedDraft == before)
        c.stopEditing()
        #expect(c.draft == ServiceDraft())
    }
}

@Suite("Librarian row status lines") struct LibrarianStatusLinesTests {
    @Test func routeAndContractComeFromTheCheck() throws {
        let caps = try JSONDecoder().decode(ServerCapabilities.self, from: Data(#"{"contract_version":1,"generation":14,"graph_coverage":"broad"}"#.utf8))
        #expect(caps.contractVersion == 1 && caps.generation == 14)
        var input = ServicesModel.Inputs(librarianReachable: true, librarianAddress: "http://100.92.14.7:8080", tailscaleHint: true, capabilities: caps)
        input.now = Date()
        let row = ServicesModel.build(input).rows.first { $0.id == .librarian }!
        #expect(row.route == "Tailscale")
        #expect(row.contract == "Version 1 · data generation 14")
        input.librarianReachable = false
        let down = ServicesModel.build(input).rows.first { $0.id == .librarian }!
        #expect(down.route == nil && down.contract == nil)
    }
}
