import Foundation

/// Folds songs into their albums, so the graph and the list show albums and never songs.
/// The server walks artist, recording, person, so a song hangs between the artist and the people who played on it. Here each song
/// is dropped and its credits move to the album it is on: an artist leads to albums, other artists or people, places and labels,
/// and an album leads to the people, places and labels credited on its songs. A song with no album in the walk hands its credits
/// to whoever the song hung from. Pure, so a test can drive it.
public enum GraphAlbums {
    /// Recordings and works are the songs.
    public static func isSong(kind: String) -> Bool { kind == "recording" || kind == "work" }

    public static func collapse(_ nodes: [GraphNode], centre: String) -> [GraphNode] {
        let byID = Dictionary(nodes.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        func song(_ id: String) -> Bool { byID[id].map { isSong(kind: $0.entity.type) } ?? false }
        func album(_ id: String) -> Bool { byID[id].map { GraphSector.of(kind: $0.entity.type) == .albums } ?? false }

        /// The album a song is on, as far as the walk shows: its parent, one of its children, or its parent song's album.
        func home(of id: String, _ seen: Set<String> = []) -> String? {
            guard let node = byID[id], !seen.contains(id) else { return nil }
            if album(node.via) { return node.via }
            if let child = nodes.first(where: { $0.via == id && album($0.id) }) { return child.id }
            return song(node.via) ? home(of: node.via, seen.union([id])) : nil
        }
        /// Where a node hangs from once songs are gone.
        func parent(of node: GraphNode) -> String {
            var via = node.via, seen: Set<String> = [node.id]
            while song(via), !seen.contains(via), let s = byID[via] {
                seen.insert(via)
                if let h = home(of: via), h != node.id { return h }
                via = s.via
            }
            return song(via) ? centre : via
        }

        let kept = nodes.filter { !isSong(kind: $0.entity.type) }
        let parents = Dictionary(kept.map { ($0.id, parent(of: $0)) }, uniquingKeysWith: { a, _ in a })
        var depths: [String: Int] = [:]
        func depth(_ id: String, _ seen: Set<String> = []) -> Int {
            if let d = depths[id] { return d }
            guard let p = parents[id], p != centre, parents[p] != nil, !seen.contains(id) else { return 1 }
            let d = depth(p, seen.union([id])) + 1
            depths[id] = d
            return d
        }
        return kept.map { n in
            let p = parents[n.id] ?? centre
            return GraphNode(entity: n.entity, depth: depth(n.id), via: parents[p] == nil && p != centre ? centre : p, credit: n.credit, evidence: n.evidence)
        }
        .sorted { ($0.depth, $0.entity.name) < ($1.depth, $1.entity.name) }
    }
}
