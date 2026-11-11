import CoreGraphics
import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import Foundation
import Observation

/// The sectors of the graph, grouped by kind. The order is the order they take around the first ring.
public enum GraphSector: Int, CaseIterable, Sendable {
    case albums, label, people, place, other

    /// The sector an entity type belongs to. Types the explorer does not group (work, recording, event, instrument) are `other`.
    public static func of(kind: String) -> GraphSector {
        switch kind {
        case "artist", "person", "group": .people
        case "release", "release_group": .albums
        case "label": .label
        case "area", "place": .place
        default: .other
        }
    }

    /// The row label in the inspector's counts by kind.
    public var kindsTitle: String {
        switch self {
        case .albums: "Albums"
        case .label: "Labels"
        case .people: "People"
        case .place: "Places"
        case .other: "Other"
        }
    }

    /// The eyebrow that names the sector on the graph.
    public var title: String {
        switch self {
        case .albums: "Albums"
        case .label: "Label"
        case .people: "People"
        case .place: "Place"
        case .other: "Other"
        }
    }
}

/// Where each node of the connection graph sits, in unit coordinates around the centre (0, 0). Pure, so a test can drive it.
/// A deeper node sits on a wider ring inside a fan around its parent. Two styles place step 1 differently:
/// `.classic` (the Zine explorer, unchanged) spreads step 1 evenly; `.sectors` (the Cupertino redesign) gives each sector its own
/// arc and measures the rings in points as the mockup draws them (step 1 at 188, step 2 at 292).
public enum GraphLayout {
    public enum Style: Sendable {
        case classic, sectors
    }

    public struct Item: Equatable, Sendable {
        public let id: String
        public let depth: Int
        public let via: String
        /// The entity type. It decides the sector; empty or unknown means `other`.
        public let kind: String
        public init(id: String, depth: Int, via: String, kind: String = "") { self.id = id; self.depth = depth; self.via = via; self.kind = kind }
    }

    /// Radius of the first ring, in points.
    public static let firstRingPoints = 188.0
    /// Distance between two rings, in points (292 - 188).
    public static let ringStepPoints = 104.0
    /// The smallest centre-to-centre distance a ring may have, in points. Below it the nodes would have to shrink under 40 pt,
    /// so the page says "Too many to draw" and offers the list instead.
    public static let minimumSpacing = 40.0
    /// The gap between two neighbouring sectors on the first ring, in radians.
    static let sectorGap = 0.15

    /// Radius of a ring in points, as the mockup draws it. Depths below 1 are treated as the first ring.
    public static func points(of depth: Int) -> Double { firstRingPoints + ringStepPoints * Double(max(depth, 1) - 1) }

    /// Radius of a ring in unit coordinates. Zero for the centre; the first ring is 1 in both styles.
    public static func radius(of depth: Int, style: Style = .classic) -> Double {
        guard depth > 0 else { return 0 }
        switch style {
        case .classic: return 1 + 0.9 * Double(depth - 1)
        case .sectors: return points(of: depth) / firstRingPoints
        }
    }

    /// Centre-to-centre spacing of `count` nodes on a ring, in points. Nil for an empty ring.
    public static func spacing(depth: Int, count: Int) -> Double? {
        guard count > 0 else { return nil }
        return 2 * Double.pi * points(of: depth) / Double(count)
    }

    /// True when any ring would need its nodes closer together than `minimumSpacing`.
    public static func tooManyToDraw(_ items: [Item]) -> Bool {
        Dictionary(grouping: items, by: \.depth).contains { entry in
            (spacing(depth: entry.key, count: entry.value.count) ?? .infinity) < minimumSpacing
        }
    }

    /// The angle of each sector's centre on the first ring, for the eyebrow labels. Only sectors with a step-1 node appear.
    public static func sectorCentres(_ items: [Item]) -> [GraphSector: Double] {
        sectorArcs(items.filter { $0.depth == 1 }).centres
    }

    /// Each step-1 node's angle, with each sector in its own arc: the arcs follow `GraphSector` order and share the circle
    /// in proportion to how many nodes each holds. Within an arc the nodes keep their input order.
    static func sectorArcs(_ items: [Item]) -> (angles: [String: Double], centres: [GraphSector: Double]) {
        let groups = Dictionary(grouping: items, by: { GraphSector.of(kind: $0.kind) })
        let used = GraphSector.allCases.filter { groups[$0] != nil }
        let gap = used.count > 1 ? sectorGap : 0
        let available = 2 * Double.pi - gap * Double(used.count)
        let total = Double(items.count)
        var angles: [String: Double] = [:], centres: [GraphSector: Double] = [:]
        var start = -Double.pi / 2
        for sector in used {
            let members = groups[sector] ?? []
            let arc = available * Double(members.count) / total
            for (i, item) in members.enumerated() { angles[item.id] = start + arc * (Double(i) + 0.5) / Double(members.count) }
            centres[sector] = start + arc / 2
            start += arc + gap
        }
        return (angles, centres)
    }

    public static func place(centre: String, items: [Item], style: Style = .classic) -> [String: CGPoint] {
        var angle: [String: Double] = [:]
        var out: [String: CGPoint] = [centre: .zero]
        let byDepth = Dictionary(grouping: items, by: \.depth)
        for depth in byDepth.keys.sorted() where depth >= 1 {
            let level = byDepth[depth] ?? []
            if depth == 1, style == .sectors {
                for (id, a) in sectorArcs(level).angles { angle[id] = a }
            } else {
                // Nodes whose parent is placed fan out around it; the rest share the ring evenly.
                let children = Dictionary(grouping: level.filter { depth > 1 && angle[$0.via] != nil && $0.via != centre }, by: \.via)
                let childIDs = Set(children.values.flatMap { $0.map(\.id) })
                for (parent, kids) in children {
                    let m = Double(kids.count)
                    let span = min(1.1, 0.4 * m)
                    for (i, k) in kids.enumerated() {
                        angle[k.id] = (angle[parent] ?? 0) + span * ((Double(i) + 0.5) / m - 0.5)
                    }
                }
                let rest = level.filter { !childIDs.contains($0.id) }
                for (i, item) in rest.enumerated() { angle[item.id] = -Double.pi / 2 + 2 * Double.pi * Double(i) / Double(max(rest.count, 1)) }
            }
            for item in level {
                let a = angle[item.id] ?? 0, r = radius(of: depth, style: style)
                out[item.id] = CGPoint(x: r * cos(a), y: r * sin(a))
            }
        }
        return out
    }
}

/// Words for the codes the server sends with each connection. A code with no words in the table is shown capitalised,
/// so a new code reads as text rather than as a bug.
public enum GraphWording {
    static let relations: [String: String] = [
        "producer": "Producer", "engineer": "Engineer", "mix": "Mixing", "mastering": "Mastering",
        "instrument": "Instrument", "vocal": "Vocals", "performer": "Performer", "main performer": "Main performer",
        "performing orchestra": "Performing orchestra", "performance": "Performance", "member_of": "Member of",
        "composer": "Composer", "arranger": "Arranger", "lyricist": "Lyricist", "publisher": "Publisher",
        "held at": "Held at", "recorded in": "Recorded in", "recording location": "Recording location",
        "area": "Area", "owner": "Owner",
    ]
    static let matchQualities: [String: String] = [
        "exact_mbid": "Exact match", "isrc": "ISRC match", "fuzzy_confirmed": "Name match, confirmed",
        "fuzzy_unconfirmed": "Name match, not confirmed", "unresolved": "Not matched",
    ]

    public static func relation(_ code: String) -> String { relations[code] ?? capitalised(code) }
    public static func matchQuality(_ code: String) -> String { matchQualities[code] ?? capitalised(code) }

    /// "Source: MusicBrainz · exact match": the source code in words and the match quality in lower case.
    public static func sourceLine(source: String, matchQuality code: String) -> String {
        let name = source.lowercased().hasPrefix("musicbrainz") ? "MusicBrainz" : capitalised(source)
        return "Source: \(name) · \(matchQuality(code).prefix(1).lowercased() + matchQuality(code).dropFirst())"
    }

    /// The inspector's name for a kind of entity: "Person", "Album", "Label".
    public static func kindWord(_ kind: String) -> String {
        switch GraphSector.of(kind: kind) {
        case .people: "Person"
        case .albums: "Album"
        case .label: "Label"
        case .place: "Place"
        case .other: capitalised(kind)
        }
    }
    /// True when the relation has words of its own in the table (not the capitalised fallback).
    public static func hasWords(relation code: String) -> Bool { relations[code] != nil }

    /// The list group a relation belongs to. Nil for a relation no group takes (places, ownership).
    static func group(relation code: String) -> GraphGroup? {
        switch code {
        case "producer", "engineer", "mix", "mastering": GraphGroup.produced
        case "instrument", "vocal", "performer", "main performer", "performing orchestra", "performance", "member_of": GraphGroup.played
        case "composer", "arranger", "lyricist", "publisher": GraphGroup.written
        default: nil
        }
    }

    /// The code with underscores as spaces and its first letter capitalised: "new_code" becomes "New code".
    static func capitalised(_ code: String) -> String {
        let spaced = code.replacingOccurrences(of: "_", with: " ")
        return spaced.prefix(1).uppercased() + spaced.dropFirst()
    }
}

/// The groups of the list view, in the order they are shown. Albums and places and labels group by kind; people, works
/// and the rest group by the relation that reaches them.
public enum GraphGroup: Int, CaseIterable, Sendable {
    case produced, played, written, albums, placesAndLabels, other

    public var title: String {
        switch self {
        case .produced: "Produced and engineered"
        case .played: "Played with"
        case .written: "Written and published"
        case .albums: "Albums"
        case .placesAndLabels: "Places and labels"
        case .other: "Other connections"
        }
    }

    static func of(_ node: GraphNode) -> GraphGroup {
        switch GraphSector.of(kind: node.entity.type) {
        case .albums: return .albums
        case .place, .label: return .placesAndLabels
        case .people, .other:
            return GraphListRow.primary(of: node).flatMap { GraphWording.group(relation: $0.relation) } ?? .other
        }
    }
}

/// One row of the list view: a hop, what connects it to the centre in words, and how the link was matched.
public struct GraphListRow: Identifiable, Equatable, Sendable {
    public var id: String { node.id }
    public let node: GraphNode
    /// The instrument or vocal part for a played-with row ("Guitar"), otherwise the relation's words.
    public let connection: String
    /// The match quality of the row's evidence in words. Empty when there is no evidence.
    public let match: String

    public init(node: GraphNode) {
        self.node = node
        let primary = Self.primary(of: node)
        connection = primary.map(Self.words) ?? "Linked"
        match = primary.map { GraphWording.matchQuality($0.matchQuality) } ?? ""
    }

    /// The evidence that names the row's group: the first with a list group, else the first of any.
    static func primary(of node: GraphNode) -> KnowledgeCredit? {
        node.evidence.first { GraphWording.group(relation: $0.relation) != nil } ?? node.evidence.first
    }

    static func words(_ e: KnowledgeCredit) -> String {
        if GraphWording.group(relation: e.relation) == .played, let role = e.role, !role.isEmpty { return GraphWording.capitalised(role) }
        return GraphWording.relation(e.relation)
    }
}

/// One group of the list view. Rows are sorted by steps, then by name.
public struct GraphListGroup: Identifiable, Equatable, Sendable {
    public var id: String { title }
    public let group: GraphGroup
    public let rows: [GraphListRow]
    public var title: String { group.title }

    /// The non-empty groups, in `GraphGroup` order, with their rows sorted.
    public static func groups(_ nodes: [GraphNode]) -> [GraphListGroup] {
        let byGroup = Dictionary(grouping: nodes.map(GraphListRow.init), by: { GraphGroup.of($0.node) })
        return GraphGroup.allCases.compactMap { group in
            guard let rows = byGroup[group], !rows.isEmpty else { return nil }
            let sorted = rows.sorted { a, b in
                if a.node.depth != b.node.depth { return a.node.depth < b.node.depth }
                return a.node.entity.name.localizedCaseInsensitiveCompare(b.node.entity.name) == .orderedAscending
            }
            return GraphListGroup(group: group, rows: sorted)
        }
    }
}

/// One entity in the explorer, once, at its shortest depth.
public struct GraphNode: Identifiable, Equatable, Sendable {
    public var id: String { entity.mbid }
    public let entity: KnowledgeEntity
    public let depth: Int
    public let via: String
    /// True only for a stated credit; any other edge is drawn dashed and never called a credit.
    public let credit: Bool
    public let evidence: [KnowledgeCredit]
}

/// State of the connection graph explorer (Server V2 Phase 7 client gate): the artist in the middle, the bounded walk
/// around them, and what is selected. It only reads `GET /api/knowledge/connections`.
@MainActor
@Observable
public final class GraphExplorerModel {
    public private(set) var centre: KnowledgeEntity?
    public private(set) var nodes: [GraphNode] = []
    public private(set) var loading = false
    public private(set) var note: String?
    /// "rows" or "time" when the server stopped the walk early.
    public private(set) var truncated: String?
    public private(set) var coverage: String?
    public private(set) var nextCursor: String?
    public var selectedID: String?
    /// True when the library artist the explorer started from is not in the knowledge store yet (404), so "Request update" is offered.
    public private(set) var canRequestUpdate = false
    public private(set) var updating = false
    public private(set) var updateNote: String?
    public var depth = 1
    public var creditsOnly = true
    /// The View control: the graph (false) or the list (true).
    public var showsList = false
    /// What a failed read says. The nodes already drawn are kept; `retry` repeats the read that failed.
    public struct LoadFailure: Equatable, Sendable {
        public let summary: String
        /// True when the failed read was "Load more", so the connections already shown are kept.
        public let wasLoadMore: Bool
    }
    public private(set) var loadFailure: LoadFailure?
    /// The artist the explorer was asked to start from, even when the server has nothing on them yet (the not-loaded state).
    public private(set) var startName: String?
    /// True once the server accepted a store update; the not-loaded notice then gives way to "Requested".
    public private(set) var updateRequested = false
    public private(set) var updateFailed = false
    /// Off until the owner turns it on: each album disc asks the server for one artwork index.
    public var showsDiscs = false
    /// Navidrome artist id the explorer last started from, so opening the screen again does not reload it.
    public private(set) var startedFor: String?
    private(set) var trail: [KnowledgeEntity] = []

    public init() {}

    /// Shows a finished walk without a server: screenshots and tests.
    func preview(centre: KnowledgeEntity, nodes: [GraphNode], truncated: String? = nil, failure: LoadFailure? = nil, more: Bool = false, depth: Int? = nil) {
        self.centre = centre; self.nodes = nodes; coverage = "loaded"; self.truncated = truncated; loadFailure = failure
        nextCursor = more ? "next" : nil
        if let depth { self.depth = depth }
    }

    /// Shows the not-loaded state without a server: an artist the store has no data on, with the update requested or not.
    func previewNotLoaded(name: String, requested: Bool) {
        startName = name; centre = nil; nodes = []; coverage = "pending"; note = "This artist is not in the knowledge store yet."
        canRequestUpdate = !requested; updateRequested = requested
    }

    public var selected: GraphNode? { nodes.first { $0.id == selectedID } }
    public var canGoBack: Bool { !trail.isEmpty }
    /// The artist Back returns to, named on the button.
    public var backTitle: String? { trail.last?.name }

    /// "16 connections within 2 steps · 9 in your library". The server sends no total, so this counts what has been read.
    public var summaryLine: String {
        let owned = nodes.filter(\.entity.owned).count
        let reach = max(nodes.map(\.depth).max() ?? depth, 1)
        let steps = reach == 1 ? "1 step" : "\(reach) steps"
        return "\(nodes.count) \(nodes.count == 1 ? "connection" : "connections") within \(steps) · \(owned) in your library"
    }

    /// Under the graph: how many connections are drawn, and that the walk was cut or has more to read.
    public var footerCount: String {
        let n = nodes.count
        let word = n == 1 ? "connection" : "connections"
        if truncated != nil { return "\(n) of \(n)+ connections" }
        return nextCursor != nil ? "\(n) \(word) so far" : "\(n) \(word)"
    }

    /// The truncated-walk sentence, with the server's limits named (docs/redesign.md section 5.2).
    public var truncatedNotice: (lead: String, message: String)? {
        guard truncated != nil else { return nil }
        return ("Showing the first \(nodes.count) connections.",
                "The server stops a walk at 200 rows or 2 seconds. Turn on Credits only, lower the reach, or use List to page through the rest.")
    }

    /// Owned albums that sit next to a node in the walk (its parent or its children), for "Also on, in your library".
    public func alsoOnInLibrary(_ node: GraphNode) -> [GraphNode] {
        nodes.filter { other in
            GraphSector.of(kind: other.entity.type) == .albums && other.entity.owned && other.id != node.id
                && (other.id == node.via || other.via == node.id)
        }
    }

    /// The name of the node a step-2 node hangs from, or the centre's for step 1.
    public func parentName(of node: GraphNode) -> String? {
        node.via == centre?.mbid ? centre?.name : nodes.first { $0.id == node.via }?.entity.name
    }

    /// Repeats the read that failed: Load more when that was it, otherwise the walk again.
    public func retry(librarian: LibrarianClient?) async {
        if loadFailure?.wasLoadMore == true { await loadMore(librarian: librarian) } else { await reload(librarian: librarian) }
    }
    public var truncatedText: String? {
        switch truncated {
        case "rows": "The walk stopped at its row limit. Showing what it reached."
        case "time": "The walk stopped at its time limit. Showing what it reached."
        default: nil
        }
    }

    /// Places every node, centre included, in unit coordinates, in the classic style the Zine explorer draws.
    public var layout: [String: CGPoint] {
        guard let centre else { return [:] }
        return GraphLayout.place(centre: centre.mbid, items: layoutItems)
    }

    /// Places every node in the Cupertino style: sectors by kind on the first ring, rings at 188 and 292 pt.
    public var sectorLayout: [String: CGPoint] {
        guard let centre else { return [:] }
        return GraphLayout.place(centre: centre.mbid, items: layoutItems, style: .sectors)
    }

    private var layoutItems: [GraphLayout.Item] {
        nodes.map { .init(id: $0.id, depth: $0.depth, via: $0.via, kind: $0.entity.type) }
    }

    /// True when a ring would need its nodes under 40 pt apart, so the graph should say "Too many to draw" and offer the list.
    public var tooManyToDraw: Bool { GraphLayout.tooManyToDraw(layoutItems) }

    /// How many nodes each sector holds, for the inspector's counts by kind.
    public var sectorCounts: [GraphSector: Int] { Dictionary(grouping: nodes, by: { GraphSector.of(kind: $0.entity.type) }).mapValues(\.count) }

    /// The list view's groups, in the order they are shown.
    public var listGroups: [GraphListGroup] { GraphListGroup.groups(nodes) }

    /// Starts from a library artist: reads their MusicBrainz id from Navidrome, then walks from it.
    public func start(artistRemoteID: String?, name: String, navidrome: NavidromeClient?, librarian: LibrarianClient?) async {
        guard let artistRemoteID, let navidrome else {
            note = "Connect to your library and open an artist you own to explore their connections."; return
        }
        guard startedFor != artistRemoteID else { return }
        startName = name; updateRequested = false; updateFailed = false; updateNote = nil
        loading = true; note = nil
        defer { loading = false }
        guard let detail = try? await navidrome.artist(id: artistRemoteID), let mbid = detail.artist.musicBrainzId, !mbid.isEmpty else {
            note = "\(name) has no MusicBrainz id in Navidrome, so there is nothing to connect yet."; return
        }
        startedFor = artistRemoteID
        mbidForRetry = mbid
        trail = []
        await walk(mbid: mbid, type: "artist", name: name, librarian: librarian)
    }

    /// Asks the server's worker to add the starting artist to the store, waits for it, then walks again.
    public func requestUpdate(name: String, librarian: LibrarianClient?) async {
        guard let librarian, let id = startedFor, !updating else { return }
        updating = true; updateNote = "Asking the server…"
        defer { updating = false }
        do {
            var result = try await librarian.requestStoreUpdate(subject: "artist", id: id)
            updateRequested = true; updateFailed = false
            var polls = 0
            while !result.finished, polls < 60 {
                updateNote = "The server is updating its store…"
                try await Task.sleep(for: .seconds(3))
                result = try await librarian.storeUpdateStatus(subject: "artist", id: id)
                polls += 1
            }
            switch result.state {
            case "done":
                updateNote = nil
                if let centreMBID = mbidForRetry { await walk(mbid: centreMBID, type: "artist", name: name, librarian: librarian) }
            case "failed": updateNote = result.message ?? "The server could not add this."; updateRequested = false; updateFailed = true
            default: updateNote = "The server is still working on it. Try again in a minute."
            }
        } catch { updateNote = "The server could not be reached. Try again."; updateRequested = false; updateFailed = true }
    }
    private var mbidForRetry: String?

    /// Makes a node the new centre. The old centre goes on the trail for Back.
    public func recentre(on node: GraphNode, librarian: LibrarianClient?) async {
        if let centre { trail.append(centre) }
        await walk(mbid: node.entity.mbid, type: node.entity.type, name: node.entity.name, librarian: librarian)
    }

    public func back(librarian: LibrarianClient?) async {
        guard let previous = trail.popLast() else { return }
        await walk(mbid: previous.mbid, type: previous.type, name: previous.name, librarian: librarian)
    }

    /// Reloads the current centre with the current depth and filter.
    public func reload(librarian: LibrarianClient?) async {
        guard let centre else { return }
        await walk(mbid: centre.mbid, type: centre.type, name: centre.name, librarian: librarian)
    }

    public func loadMore(librarian: LibrarianClient?) async {
        guard let centre, let cursor = nextCursor, !loading else { return }
        await fetch(mbid: centre.mbid, type: centre.type, cursor: cursor, replace: false, librarian: librarian)
    }

    private func walk(mbid: String, type: String, name: String, librarian: LibrarianClient?) async {
        await fetch(mbid: mbid, type: type, cursor: nil, replace: true, librarian: librarian)
    }

    private func fetch(mbid: String, type: String, cursor: String?, replace: Bool, librarian: LibrarianClient?) async {
        guard let librarian else { note = "The Librarian is not connected."; return }
        loading = true; defer { loading = false }
        do {
            let page = try await librarian.knowledgeConnections(mbid: mbid, type: type, depth: depth, limit: 50, creditsOnly: creditsOnly, cursor: cursor)
            note = nil; canRequestUpdate = false; loadFailure = nil
            let fresh = page.hops.map { GraphNode(entity: $0.entity, depth: $0.depth, via: $0.viaMBID, credit: $0.credit, evidence: $0.evidence) }
            if replace { centre = page.start; nodes = fresh; selectedID = nil }
            else { let have = Set(nodes.map(\.id)); nodes += fresh.filter { !have.contains($0.id) } }
            nextCursor = page.nextCursor; truncated = page.truncated
            coverage = page.sources["musicbrainz_dump"]?.coverage
            if replace, fresh.isEmpty { note = coverage == "pending" ? "The MusicBrainz data for this artist is not on the server yet." : "No connections are stated for \(page.start.name)." }
        } catch let e as DiscairError {
            if case .server(let status, _) = e, status == 404 {
                note = "This artist is not in the knowledge store yet."
                canRequestUpdate = trail.isEmpty && mbid == mbidForRetry
            }
            else { note = e.summary; loadFailure = LoadFailure(summary: e.summary, wasLoadMore: !replace) }
            if replace { nodes = []; nextCursor = nil }
        } catch {
            note = "Could not read connections."; loadFailure = LoadFailure(summary: "The connections could not be read.", wasLoadMore: !replace)
            if replace { nodes = []; nextCursor = nil }
        }
    }
}
