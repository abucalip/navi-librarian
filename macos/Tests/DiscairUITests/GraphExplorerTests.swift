import Foundation
import Testing
import CoreGraphics
import DiscairCore
import DiscairLibrarian
@testable import DiscairUI

private struct StubTransport: HTTPTransport {
    let body: Data
    var status = 200
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        (body, HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
    }
}

private func fixture(_ name: String, file: String = #filePath) throws -> Data {
    let url = URL(fileURLWithPath: file).deletingLastPathComponent().appending(path: "../../../intelligence/contract-fixtures/\(name).json").standardized
    let object = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
    return try JSONSerialization.data(withJSONObject: object["response"]!)
}

@Suite("Graph layout") struct GraphLayoutTests {
    @Test func firstRingIsEvenlySpreadAtRadiusOne() {
        let items = (0..<4).map { GraphLayout.Item(id: "n\($0)", depth: 1, via: "c") }
        let p = GraphLayout.place(centre: "c", items: items)
        #expect(p["c"] == .zero)
        for i in items { let q = p[i.id]!; #expect(abs(hypot(q.x, q.y) - 1) < 1e-9) }
        #expect(Set(items.map { p[$0.id]! }).count == 4)
    }

    @Test func deeperNodesSitOnWiderRingsNearTheirParent() {
        let items = [GraphLayout.Item(id: "a", depth: 1, via: "c"), .init(id: "b", depth: 1, via: "c"), .init(id: "a1", depth: 2, via: "a")]
        let p = GraphLayout.place(centre: "c", items: items)
        let a = p["a"]!, a1 = p["a1"]!
        #expect(hypot(a1.x, a1.y) > hypot(a.x, a.y))
        #expect(hypot(a1.x - a.x, a1.y - a.y) < hypot(p["b"]!.x - a.x, p["b"]!.y - a.y))
    }

    @Test func aNodeWithAnUnknownParentStillGetsAPlace() {
        let p = GraphLayout.place(centre: "c", items: [.init(id: "x", depth: 2, via: "missing")])
        #expect(p["x"] != nil)
    }
}

@MainActor @Suite("Graph explorer model") struct GraphExplorerModelTests {
    private func client(_ body: Data, status: Int = 200) throws -> LibrarianClient {
        try LibrarianClient(baseURL: URL(string: "https://lib.example.ts.net")!, credential: Credential(username: "owner", password: "s3cret-pw-1234"),
                            transport: StubTransport(body: body, status: status))
    }
    private func node(_ id: String = "n") -> GraphNode {
        GraphNode(entity: try! JSONDecoder().decode(KnowledgeEntity.self, from: Data(#"{"mbid":"\#(id)","canonical_name":"X","type":"artist","owned":false}"#.utf8)),
                  depth: 1, via: "c", credit: true, evidence: [])
    }

    @Test func walkFillsNodesAndKeepsTheCreditFlag() async throws {
        let m = GraphExplorerModel()
        await m.recentre(on: node(), librarian: try client(fixture("knowledge_connections")))
        #expect(m.centre?.name == "Example Artist" && !m.nodes.isEmpty)
        #expect(m.nodes.allSatisfy { $0.depth >= 1 } && m.nodes.first?.credit == true)
        #expect(m.layout.count == m.nodes.count + 1)
        #expect(m.note == nil && m.coverage == "loaded")
    }

    @Test func loadMoreAppendsWithoutDuplicates() async throws {
        let m = GraphExplorerModel()
        await m.recentre(on: node(), librarian: try client(fixture("knowledge_connections_page1")))
        let first = m.nodes.count
        #expect(m.nextCursor != nil)
        await m.loadMore(librarian: try client(fixture("knowledge_connections_page2")))
        #expect(m.nodes.count > first && Set(m.nodes.map(\.id)).count == m.nodes.count)
    }

    @Test func backReturnsToThePreviousCentre() async throws {
        let m = GraphExplorerModel()
        let c = try client(fixture("knowledge_connections"))
        await m.recentre(on: node("one"), librarian: c)
        let first = m.centre
        await m.recentre(on: node("two"), librarian: c)
        #expect(m.canGoBack)
        await m.back(librarian: c)
        #expect(m.centre == first && !m.canGoBack)
    }

    @Test func missingEntityIsSaidPlainly() async throws {
        let m = GraphExplorerModel()
        await m.recentre(on: node(), librarian: try client(Data(#"{"detail":"not found"}"#.utf8), status: 404))
        #expect(m.note == "This artist is not in the knowledge store yet." && m.nodes.isEmpty)
    }

    @Test func noLibrarianMeansANoteNotACrash() async {
        let m = GraphExplorerModel()
        await m.recentre(on: node(), librarian: nil)
        #expect(m.note == "The Librarian is not connected.")
    }
}
