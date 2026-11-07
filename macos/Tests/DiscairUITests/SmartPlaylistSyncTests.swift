import Foundation
import Testing
import DiscairCore
import DiscairLibrarian
@testable import DiscairUI

/// A fake Librarian holding rule sets, so the model's sync can be driven without a network.
private final class FakeServer: HTTPTransport, @unchecked Sendable {
    private let lock = NSLock()
    private var store: [String: [String: Any]] = [:]
    private var log: [String] = []
    var online = true
    var calls: [String] { lock.withLock { log } }
    var ids: Set<String> { lock.withLock { Set(store.keys) } }
    func seed(_ w: ServerSmartPlaylist) { lock.withLock { store[w.ruleID] = Self.object(w) } }

    static func object(_ w: ServerSmartPlaylist) -> [String: Any] {
        var o: [String: Any] = ["rule_id": w.ruleID, "name": w.name, "match": w.match, "order": w.order,
                                "rules": w.rules.map { ["field": $0.field, "op": $0.op, "value": $0.value] }]
        if let l = w.limit { o["limit"] = l }
        return o
    }

    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        if !online { throw URLError(.notConnectedToInternet) }
        let (status, body) = try handle(request)
        return ((try? JSONSerialization.data(withJSONObject: body)) ?? Data(), HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
    }

    private func handle(_ request: URLRequest) throws -> (Int, Any) {
        lock.lock(); defer { lock.unlock() }
        let method = request.httpMethod ?? "GET", path = request.url!.path
        log.append("\(method) \(path)")
        let id = path.split(separator: "/").last.map(String.init) ?? ""
        switch method {
        case "GET": return (200, ["playlists": store.keys.sorted().map { store[$0]! }, "total": store.count])
        case "PUT":
            var o = try JSONSerialization.jsonObject(with: request.httpBody!) as! [String: Any]
            o["rule_id"] = id; store[id] = o
            return (200, ["status": "created"])
        default:
            return store.removeValue(forKey: id) == nil ? (404, ["detail": "not found"]) : (200, ["deleted": true])
        }
    }
}

@MainActor
struct SmartPlaylistSyncTests {
    private func defaults() -> UserDefaults { UserDefaults(suiteName: "sync-\(UUID().uuidString)")! }
    private func librarian(_ s: FakeServer) throws -> LibrarianClient {
        try LibrarianClient(baseURL: URL(string: "https://lib.example.ts.net")!, credential: Credential(username: "owner", password: "s3cret-pw-1234"), transport: s)
    }
    private func model(_ d: UserDefaults) -> SmartPlaylistModel { SmartPlaylistModel(defaults: d, debounce: .milliseconds(1)) }
    private func list(_ name: String) -> SmartPlaylist { SmartPlaylist(name: name, rules: [SmartRule(field: .playedDaysAgo, op: .atLeast, value: "30")], order: .mostPlayed, limit: 25) }

    @Test func wireFormRoundTripsAndRejectsInsightFields() {
        let p = list("A")
        let w = p.wire
        #expect(w.ruleID == p.id.uuidString.lowercased() && w.order == "most_played" && w.rules[0].field == "played_days_ago" && w.rules[0].op == "at_least")
        #expect(SmartPlaylist(wire: w)?.sameContent(as: p) == true)
        var unknown = w
        unknown = ServerSmartPlaylist(ruleID: w.ruleID, name: "x", match: "all", rules: [ServerSmartRule(field: "obscurity_band", op: "equals", value: "deep_cut")], order: "random", limit: nil)
        #expect(SmartPlaylist(wire: unknown) == nil)
        #expect(SmartPlaylist(name: "n", rules: [], limit: 0).wire.limit == nil)
    }

    @Test func firstSyncUploadsLocalListsAndReplayIsQuiet() async throws {
        let server = FakeServer(), d = defaults()
        let m = model(d)
        m.update(SmartPlaylist(name: "Mine", rules: [], limit: 50).with(id: m.lists[0].id))
        await m.sync(librarian: try librarian(server))
        #expect(server.ids == [m.lists[0].id.uuidString.lowercased()])
        let puts = server.calls.filter { $0.hasPrefix("PUT") }.count
        await m.sync(librarian: try librarian(server))
        #expect(server.calls.filter { $0.hasPrefix("PUT") }.count == puts)
    }

    @Test func serverCopiesWinAndAnUntouchedExampleListIsDropped() async throws {
        let server = FakeServer(), d = defaults()
        let theirs = list("From the other Mac")
        server.seed(theirs.wire)
        let m = model(d)
        await m.sync(librarian: try librarian(server))
        #expect(m.lists.map(\.name) == ["From the other Mac"])
        #expect(!server.calls.contains { $0.hasPrefix("PUT") })
    }

    @Test func anUnsentLocalEditBeatsTheServerCopy() async throws {
        let server = FakeServer(), d = defaults()
        let m = model(d)
        await m.sync(librarian: try librarian(server))
        server.online = false
        var edited = m.lists[0]; edited.name = "Edited offline"
        m.update(edited)
        server.online = true
        await m.sync(librarian: try librarian(server))
        #expect(m.lists[0].name == "Edited offline")
        let m2 = model(d)
        #expect(m2.lists[0].name == "Edited offline")   // the cache survives a restart
    }

    @Test func aListDeletedElsewhereIsDroppedAndALocalDeleteReachesTheServer() async throws {
        let server = FakeServer(), d = defaults()
        let m = model(d)
        let keep = list("Keep"); m.update(keep)   // not present yet: ignored
        m.add(); m.update({ var p = m.lists.last!; p.name = "Second"; return p }())
        await m.sync(librarian: try librarian(server))
        #expect(server.ids.count == 2)
        let gone = m.lists[1]
        m.remove(gone.id)
        await m.sync(librarian: try librarian(server))
        #expect(server.ids == [m.lists[0].id.uuidString.lowercased()])
        // another Mac deletes the remaining one
        let other = server.ids.first!
        _ = try await librarian(server).deleteSmartPlaylist(id: other)
        await m.sync(librarian: try librarian(server))
        #expect(m.lists.isEmpty)
    }

    @Test func offlineSyncChangesNothing() async throws {
        let server = FakeServer(), d = defaults()
        server.online = false
        let m = model(d)
        let before = m.lists
        await m.sync(librarian: try librarian(server))
        #expect(m.lists == before && m.status != nil)
    }

    @Test func insightRuleSetsOnTheServerAreCountedAndNeverOverwritten() async throws {
        let server = FakeServer(), d = defaults()
        server.seed(ServerSmartPlaylist(ruleID: "00000001-0000-4000-8000-00000005ba17", name: "Deep cuts", match: "all",
                                        rules: [ServerSmartRule(field: "obscurity_band", op: "equals", value: "deep_cut")], order: "random", limit: nil))
        let m = model(d)
        await m.sync(librarian: try librarian(server))
        #expect(m.unsupportedOnServer == 1)
        #expect(!server.calls.contains { $0.hasPrefix("PUT") || $0.hasPrefix("DELETE") } || m.lists.count == 1)
        #expect(server.ids.contains("00000001-0000-4000-8000-00000005ba17"))
    }
}
