import CoreGraphics
import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import Foundation
import Observation

/// Where each node of the connection graph sits, in unit coordinates around the centre (0, 0). Pure, so a test can drive it.
/// Depth 1 nodes spread evenly on the first ring; a deeper node sits on a wider ring inside a fan around its parent.
public enum GraphLayout {
    public struct Item: Equatable, Sendable {
        public let id: String
        public let depth: Int
        public let via: String
        public init(id: String, depth: Int, via: String) { self.id = id; self.depth = depth; self.via = via }
    }

    /// Radius of a ring, in unit coordinates. The outermost ring a layout can have is `radius(of: 3)`.
    public static func radius(of depth: Int) -> Double { depth <= 0 ? 0 : 1 + 0.9 * Double(depth - 1) }

    public static func place(centre: String, items: [Item]) -> [String: CGPoint] {
        var angle: [String: Double] = [centre: -Double.pi / 2]
        var out: [String: CGPoint] = [centre: .zero]
        let byDepth = Dictionary(grouping: items, by: \.depth)
        for depth in byDepth.keys.sorted() where depth >= 1 {
            let level = byDepth[depth] ?? []
            // Nodes whose parent is placed fan out around it; the rest (and all of depth 1) share the ring evenly.
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
            for item in level {
                let a = angle[item.id] ?? 0, r = radius(of: depth)
                out[item.id] = CGPoint(x: r * cos(a), y: r * sin(a))
            }
        }
        return out
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
    /// Navidrome artist id the explorer last started from, so opening the screen again does not reload it.
    public private(set) var startedFor: String?
    private(set) var trail: [KnowledgeEntity] = []

    public init() {}

    /// Shows a finished walk without a server: screenshots and tests.
    func preview(centre: KnowledgeEntity, nodes: [GraphNode]) { self.centre = centre; self.nodes = nodes; coverage = "loaded" }

    public var selected: GraphNode? { nodes.first { $0.id == selectedID } }
    public var canGoBack: Bool { !trail.isEmpty }
    public var truncatedText: String? {
        switch truncated {
        case "rows": "The walk stopped at its row limit. Showing what it reached."
        case "time": "The walk stopped at its time limit. Showing what it reached."
        default: nil
        }
    }

    /// Places every node, centre included, in unit coordinates.
    public var layout: [String: CGPoint] {
        guard let centre else { return [:] }
        return GraphLayout.place(centre: centre.mbid, items: nodes.map { .init(id: $0.id, depth: $0.depth, via: $0.via) })
    }

    /// Starts from a library artist: reads their MusicBrainz id from Navidrome, then walks from it.
    public func start(artistRemoteID: String?, name: String, navidrome: NavidromeClient?, librarian: LibrarianClient?) async {
        guard let artistRemoteID, let navidrome else {
            note = "Connect to your library and open an artist you own to explore their connections."; return
        }
        guard startedFor != artistRemoteID else { return }
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
            case "failed": updateNote = result.message ?? "The server could not add this."
            default: updateNote = "The server is still working on it. Try again in a minute."
            }
        } catch { updateNote = "The server could not be reached. Try again." }
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
            note = nil; canRequestUpdate = false
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
            else { note = e.summary }
            if replace { nodes = []; nextCursor = nil }
        } catch { note = "Could not read connections."; if replace { nodes = []; nextCursor = nil } }
    }
}
