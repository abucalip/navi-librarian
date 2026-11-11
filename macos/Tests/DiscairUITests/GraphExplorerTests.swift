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

@Suite("Graph discs") struct GraphDiscTests {
    private func entity(_ type: String, _ mbid: String) -> KnowledgeEntity {
        try! JSONDecoder().decode(KnowledgeEntity.self, from: Data(#"{"mbid":"\#(mbid)","canonical_name":"X","type":"\#(type)"}"#.utf8))
    }

    @Test func discOnlyForAlbumNodesWithAValidIdAndOnlyWhenOn() {
        let id = "2c4b6c2e-1c43-4d1d-a1f0-5f0e6f4b9a11"
        #expect(GraphNodeFace.discGroup(entity("release_group", id), on: true) == id)
        #expect(GraphNodeFace.discGroup(entity("release_group", id), on: false) == nil)
        #expect(GraphNodeFace.discGroup(entity("artist", id), on: true) == nil)
        #expect(GraphNodeFace.discGroup(entity("release", "nope"), on: true) == nil)
    }

    @MainActor @Test func discsAreOffByDefault() { #expect(GraphExplorerModel().showsDiscs == false) }
}

// MARK: M7 connections model: rings, sectors, crowding, wording and the list view

private func graphEntity(_ mbid: String, kind: String, name: String? = nil) -> KnowledgeEntity {
    try! JSONDecoder().decode(KnowledgeEntity.self, from: Data(#"{"mbid":"\#(mbid)","canonical_name":"\#(name ?? mbid)","type":"\#(kind)"}"#.utf8))
}

private func credit(_ relation: String, role: String? = nil, match: String = "exact_mbid") -> KnowledgeCredit {
    var object: [String: Any] = ["relation": relation, "evidence_class": "source_explicit", "match_quality": match, "source": "musicbrainz"]
    if let role { object["role"] = role }
    return try! JSONDecoder().decode(KnowledgeCredit.self, from: JSONSerialization.data(withJSONObject: object))
}

private func graphNode(_ id: String, kind: String = "artist", depth: Int = 1, evidence: [KnowledgeCredit] = []) -> GraphNode {
    GraphNode(entity: graphEntity(id, kind: kind, name: id), depth: depth, via: "c", credit: !evidence.isEmpty, evidence: evidence)
}

private func layoutItems(_ count: Int, depth: Int, prefix: String = "n") -> [GraphLayout.Item] {
    (0..<count).map { GraphLayout.Item(id: "\(prefix)\($0)", depth: depth, via: "c") }
}

/// Distance between two angles on the circle, in radians.
private func circularDistance(_ a: Double, _ b: Double) -> Double {
    let d = abs(a - b).truncatingRemainder(dividingBy: 2 * Double.pi)
    return min(d, 2 * Double.pi - d)
}

@Suite("Graph rings and sectors") struct GraphSectorTests {
    /// Interleaved on purpose: people, an album, a person, a place, a person, an album.
    private let mixed: [GraphLayout.Item] = [("p1", "artist"), ("a1", "release"), ("p2", "person"), ("x", "area"), ("p3", "group"), ("a2", "release_group")]
        .map { GraphLayout.Item(id: $0.0, depth: 1, via: "c", kind: $0.1) }

    @Test func ringsUseTheMockupRadiiInTheSectorStyle() {
        #expect(GraphLayout.points(of: 1) == 188 && GraphLayout.points(of: 2) == 292)
        #expect(abs(GraphLayout.radius(of: 2, style: .sectors) - 292.0 / 188.0) < 1e-9)
        #expect(GraphLayout.radius(of: 1, style: .sectors) == 1 && GraphLayout.radius(of: 0, style: .sectors) == 0)
    }

    @Test func theClassicStyleKeepsTheRingsTheZineExplorerDraws() {
        #expect(GraphLayout.radius(of: 1) == 1 && abs(GraphLayout.radius(of: 2) - 1.9) < 1e-9 && GraphLayout.radius(of: 0) == 0)
        // Step 1 spreads evenly in the classic style, whatever the kinds: two nodes sit at the top and the bottom.
        let items = [GraphLayout.Item(id: "a", depth: 1, via: "c", kind: "artist"), GraphLayout.Item(id: "b", depth: 1, via: "c", kind: "release")]
        let p = GraphLayout.place(centre: "c", items: items)
        #expect(abs(p["a"]!.x) < 1e-9 && abs(p["a"]!.y + 1) < 1e-9)
        #expect(abs(p["b"]!.x) < 1e-9 && abs(p["b"]!.y - 1) < 1e-9)
    }

    @Test func sectorsKeepTheirKindTogetherAroundTheRing() {
        let p = GraphLayout.place(centre: "c", items: mixed, style: .sectors)
        let kinds = Dictionary(uniqueKeysWithValues: mixed.map { ($0.id, $0.kind) })
        let order = mixed.map(\.id).sorted { atan2(p[$0]!.y, p[$0]!.x) < atan2(p[$1]!.y, p[$1]!.x) }
        let sectors = order.map { GraphSector.of(kind: kinds[$0]!) }
        // Going round the ring, each sector forms one run: three sectors means three changes, wrap-around included.
        let changes = (0..<sectors.count).filter { sectors[$0] != sectors[($0 + 1) % sectors.count] }.count
        #expect(changes == 3)
    }

    @Test func eachNodeIsNearestItsOwnSectorCentre() {
        let p = GraphLayout.place(centre: "c", items: mixed, style: .sectors)
        let centres = GraphLayout.sectorCentres(mixed)
        #expect(Set(centres.keys) == [.albums, .people, .place])
        for item in mixed {
            let a = atan2(p[item.id]!.y, p[item.id]!.x)
            let nearest = centres.min { circularDistance(a, $0.value) < circularDistance(a, $1.value) }!.key
            #expect(nearest == GraphSector.of(kind: item.kind))
        }
    }

    @Test func sectorOfKindFollowsTheMockupGroups() {
        #expect(GraphSector.of(kind: "artist") == .people && GraphSector.of(kind: "group") == .people)
        #expect(GraphSector.of(kind: "release") == .albums && GraphSector.of(kind: "release_group") == .albums)
        #expect(GraphSector.of(kind: "label") == .label && GraphSector.of(kind: "area") == .place)
        #expect(GraphSector.of(kind: "work") == .other && GraphSector.of(kind: "") == .other)
    }

    @Test func sameInputGivesTheSameLayout() {
        #expect(GraphLayout.place(centre: "c", items: mixed, style: .sectors) == GraphLayout.place(centre: "c", items: mixed, style: .sectors))
    }
}

@Suite("Graph too many to draw") struct GraphCrowdingTests {
    @Test func firstRingHoldsTwentyNineNodesAndNotThirty() {
        #expect(!GraphLayout.tooManyToDraw(layoutItems(29, depth: 1)))
        #expect(GraphLayout.tooManyToDraw(layoutItems(30, depth: 1)))
    }

    @Test func secondRingHoldsFortyFiveNodesAndNotFortySix() {
        #expect(!GraphLayout.tooManyToDraw(layoutItems(45, depth: 2)))
        #expect(GraphLayout.tooManyToDraw(layoutItems(46, depth: 2)))
    }

    @Test func oneCrowdedRingIsEnoughOnItsOwn() {
        #expect(GraphLayout.tooManyToDraw(layoutItems(3, depth: 1) + layoutItems(46, depth: 2, prefix: "m")))
    }

    @Test func anEmptyRingHasNoSpacing() {
        #expect(GraphLayout.spacing(depth: 1, count: 0) == nil)
        #expect(GraphLayout.tooManyToDraw([]) == false)
    }

    @MainActor @Test func theModelSaysSoWhenARingIsCrowded() {
        let m = GraphExplorerModel()
        m.preview(centre: graphEntity("c", kind: "artist"), nodes: (0..<30).map { graphNode("n\($0)") })
        #expect(m.tooManyToDraw)
        m.preview(centre: graphEntity("c", kind: "artist"), nodes: (0..<3).map { graphNode("n\($0)") })
        #expect(!m.tooManyToDraw)
    }

    @MainActor @Test func theSectorLayoutPlacesStepTwoOnTheWiderRing() {
        let m = GraphExplorerModel()
        m.preview(centre: graphEntity("c", kind: "artist"), nodes: [graphNode("p1"), graphNode("child", kind: "release", depth: 2)])
        let p = m.sectorLayout
        #expect(abs(hypot(p["p1"]!.x, p["p1"]!.y) - 1) < 1e-9)
        #expect(abs(hypot(p["child"]!.x, p["child"]!.y) - 292.0 / 188.0) < 1e-9)
    }

    @MainActor @Test func theModelCountsNodesBySector() {
        let m = GraphExplorerModel()
        m.preview(centre: graphEntity("c", kind: "artist"), nodes: [
            graphNode("p1"), graphNode("p2", kind: "person"), graphNode("a1", kind: "release"), graphNode("x", kind: "area"),
        ])
        #expect(m.sectorCounts == [.people: 2, .albums: 1, .place: 1])
    }
}

@Suite("Graph wording") struct GraphWordingTests {
    @Test func knownRelationsHaveWords() {
        let words = ["producer": "Producer", "instrument": "Instrument", "main performer": "Main performer", "member_of": "Member of", "held at": "Held at"]
        for (code, text) in words {
            #expect(GraphWording.relation(code) == text)
            #expect(GraphWording.hasWords(relation: code))
        }
    }

    @Test func unknownCodesAreShownCapitalised() {
        #expect(GraphWording.relation("brand_new_code") == "Brand new code")
        #expect(!GraphWording.hasWords(relation: "brand_new_code"))
        #expect(GraphWording.matchQuality("some_new_match") == "Some new match")
        #expect(GraphWording.capitalised("") == "")
    }

    @Test func matchQualityWords() {
        #expect(GraphWording.matchQuality("exact_mbid") == "Exact match")
        #expect(GraphWording.matchQuality("fuzzy_unconfirmed") == "Name match, not confirmed")
        #expect(GraphWording.matchQuality("unresolved") == "Not matched")
    }

    @Test func everyRelationAndMatchInTheFixturesHasWords() throws {
        for name in ["knowledge_connections", "knowledge_connections_page1", "knowledge_connections_page2"] {
            let page = try JSONDecoder().decode(KnowledgeConnections.self, from: fixture(name))
            for hop in page.hops {
                for e in hop.evidence {
                    #expect(GraphWording.hasWords(relation: e.relation), "no words for relation \(e.relation) in \(name)")
                    #expect(GraphWording.matchQuality(e.matchQuality) != GraphWording.capitalised(e.matchQuality), "no words for match \(e.matchQuality)")
                }
            }
        }
    }
}

@Suite("Graph list") struct GraphListTests {
    @Test func groupsAreShownInTheMockupOrder() {
        let groups = GraphListGroup.groups([
            graphNode("tim", evidence: [credit("producer")]),
            graphNode("lee", evidence: [credit("instrument", role: "drums")]),
            graphNode("eden", kind: "release", evidence: [credit("instrument")]),
            graphNode("wessex", kind: "area", evidence: [credit("held at")]),
            graphNode("verve", kind: "label", evidence: [credit("publisher")]),
            graphNode("pent"),
        ])
        #expect(groups.map(\.title) == ["Produced and engineered", "Played with", "Albums", "Places and labels", "Other connections"])
        #expect(groups.first { $0.group == .placesAndLabels }?.rows.count == 2)
    }

    @Test func rowsSayHowTheyConnectAndHowTheyMatched() {
        let groups = GraphListGroup.groups([
            graphNode("tim", evidence: [credit("producer", match: "exact_mbid")]),
            graphNode("lee", evidence: [credit("instrument", role: "drums")]),
        ])
        let tim = groups.first { $0.group == .produced }?.rows.first
        let lee = groups.first { $0.group == .played }?.rows.first
        #expect(tim?.connection == "Producer" && tim?.match == "Exact match")
        #expect(lee?.connection == "Drums")
    }

    @Test func aNodeWithoutEvidenceIsLinkedAndInOtherConnections() {
        let groups = GraphListGroup.groups([graphNode("pent")])
        #expect(groups.count == 1 && groups[0].group == .other)
        #expect(groups[0].rows[0].connection == "Linked" && groups[0].rows[0].match == "")
    }

    @Test func memberOfNamesTheCentreWhenKnown() {
        let node = graphNode("lee", kind: "person", evidence: [credit("member_of")])
        #expect(GraphListGroup.groups([node], centreName: "Talk Talk")[0].rows[0].connection == "Member of Talk Talk")
        #expect(GraphListGroup.groups([node])[0].rows[0].connection == "Member of")
        #expect(GraphListGroup.groups([graphNode("t", evidence: [credit("producer")])], centreName: "Talk Talk")[0].rows[0].connection == "Producer")
    }

    @Test func aGroupRelationBeatsAnEarlierRelationWithNoGroup() {
        let groups = GraphListGroup.groups([graphNode("tim", evidence: [credit("held at"), credit("producer")])])
        #expect(groups.map(\.group) == [.produced])
        #expect(groups[0].rows[0].connection == "Producer")
    }

    @Test func rowsSortByStepsThenName() {
        let near = graphNode("zeta", evidence: [credit("vocal")])
        let far = [graphNode("beta", depth: 2, evidence: [credit("vocal")]), graphNode("alpha", depth: 2, evidence: [credit("vocal")])]
        let rows = GraphListGroup.groups([far[0], near, far[1]]).first { $0.group == .played }?.rows.map(\.node.entity.name)
        #expect(rows == ["zeta", "alpha", "beta"])
    }
}
