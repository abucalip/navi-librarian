import DiscairLibrarian
import Foundation

// The Trail layout of the macOS Paths sheet (docs/plans/MACOS_PATHS_BOOKLET.md, section 4.2): the link that joins a step to the
// start, the grouping of steps under their links, the filter, the visual order the keys walk, and the notes no group owns.
// Pure: no SwiftUI. The same grouping rules as Android's `model/PathTrail.kt` (docs/archive/completed/pathsredesign.md, section 5).

/// What connects a step to the start: the person, studio, work, label or place it goes through (`name`) and what that link is
/// (`kind`, lower case: "same label"). A step whose first reason names nothing to link through has an empty `name` and is
/// shown under its kind alone ("production credit").
public struct PathLink: Hashable, Sendable {
    public let name: String
    public let kind: String
    public init(name: String, kind: String) { self.name = name; self.kind = kind }
}

/// The steps that share one link, in the server's order.
public struct PathTrailGroup: Identifiable, Equatable, Sendable {
    public let id: String            // kind + "|" + folded name
    public let link: PathLink?       // nil only for the flat Sonic answer
    public let role: [StorySpan]     // empty: no role line
    public let stepIDs: [Int]        // PathStep.id, server order
    public let cappedMore: Int?      // from PathAnswer.capped
    /// The same group with fewer steps (the filter).
    func with(stepIDs: [Int]) -> PathTrailGroup {
        PathTrailGroup(id: id, link: link, role: role, stepIDs: stepIDs, cappedMore: cappedMore)
    }
}

/// What the Trail shows steps of: an album sheet's tab or an artist sheet's path.
public enum PathContext: Equatable, Sendable {
    case album(AlbumPathTab)
    case artist(PathKind)

    /// The noun for the count beside a group: "4 albums", "3 songs".
    var noun: (one: String, many: String) {
        switch self {
        case .album: ("album", "albums")
        case .artist(.followTheMusician): ("song", "songs")
        case .artist(.sidemanToLeader), .artist(.scenePath): ("artist", "artists")
        case .artist(.compositionPath): ("recording", "recordings")
        case .artist(.labelPath): ("album", "albums")
        }
    }
}

public enum PathFilter: String, CaseIterable, Sendable {
    case all = "All", notOwned = "Not in library", owned = "In library"

    func keeps(_ step: PathStep) -> Bool {
        switch self {
        case .all: true
        case .notOwned: !step.owned
        case .owned: step.owned
        }
    }
}

public enum PathTrail {
    // MARK: Links

    /// The role of a studio credit, from the relation the server stored for it; "production credit" when it names none.
    static func crewKind(_ relation: String?) -> String {
        switch relation {
        case "producer": "producer credit"
        case "engineer": "engineer credit"
        case "mix": "mixing credit"
        case "mastering": "mastering credit"
        default: "production credit"
        }
    }

    private static func sceneKind(_ code: String) -> String {
        switch code {
        case "same_period_label": "same label"
        case "same_period_area": "same area"
        case "same_period_credit": "shared artist"
        default: PathStepReason.eyebrow(for: code).lowercased()
        }
    }

    private static func name(_ entity: KnowledgeEntity?) -> String {
        entity?.name.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    }

    private static func isRelated(_ code: String) -> Bool { code == "derived_work" || code == "related_work" }

    /// The link of an album step, from its first reason so the grouping is stable. Neighbours by Ear has none (a flat answer).
    public static func link(album step: PathStep, tab: AlbumPathTab) -> PathLink? {
        let via = name(step.firstVia)
        switch tab {
        case .studioCrew: return PathLink(name: via, kind: crewKind(step.creditRole))
        case .guestList: return PathLink(name: via, kind: "guest credit")
        case .coversAndSources: return PathLink(name: via, kind: isRelated(step.firstCode) ? "related work" : "same work")
        case .sameYearSameScene: return PathLink(name: via, kind: sceneKind(step.firstCode))
        case .sameRoom: return PathLink(name: via, kind: "recorded at")
        case .listenThroughGaps: return PathLink(name: via, kind: PathStepReason.eyebrow(for: step.firstCode).lowercased())
        case .neighboursByEar: return nil
        }
    }

    /// The link of an artist step. Follow the Musician links through a musician and Sideman through a record they led; a first
    /// reason that names neither goes under its kind alone.
    public static func link(artist step: PathStep, kind: PathKind) -> PathLink? {
        let via = step.firstVia
        switch kind {
        case .followTheMusician:
            let isMusician = ["artist", "person", "group"].contains(via?.type ?? "")
            return PathLink(name: isMusician ? name(via) : "", kind: "musician")
        case .sidemanToLeader:
            return PathLink(name: via?.type == "release" ? name(via) : "", kind: "a record they led")
        case .labelPath: return PathLink(name: name(via), kind: "same label")
        case .compositionPath: return PathLink(name: name(via), kind: isRelated(step.firstCode) ? "related work" : "same work")
        case .scenePath: return PathLink(name: name(via), kind: "same place")
        }
    }

    static func links(_ answer: PathAnswer, context: PathContext) -> [Int: PathLink?] {
        var out: [Int: PathLink?] = [:]
        for s in answer.steps {
            switch context {
            case .album(let tab): out[s.id] = link(album: s, tab: tab)
            case .artist(let kind): out[s.id] = link(artist: s, kind: kind)
            }
        }
        return out
    }

    // MARK: Groups

    static func fold(_ s: String) -> String {
        s.folding(options: [.caseInsensitive, .diacriticInsensitive], locale: nil).trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Steps with the same link name and kind form one group. Groups appear in the order of their first step in the answer and
    /// steps keep the server's order inside a group, so a step that is not first in its group can move up to join it. Steps with no
    /// link form one group without a link (a flat answer). `links` is read by step id; a missing or nil entry means no link.
    public static func groups(_ answer: PathAnswer, links: [Int: PathLink?], context: PathContext, start: String) -> [PathTrailGroup] {
        var order: [String] = []
        var members: [String: [PathStep]] = [:]
        var linkOf: [String: PathLink?] = [:]
        for s in answer.steps {
            let link = links[s.id] ?? nil
            let id = link.map { $0.kind + "|" + fold($0.name) } ?? "|"
            if members[id] == nil { order.append(id); linkOf[id] = link }
            members[id, default: []].append(s)
        }
        return order.map { id in
            let steps = members[id]!
            let link = linkOf[id] ?? nil
            let capped = link.map { l in answer.capped.filter { !l.name.isEmpty && fold($0.via) == fold(l.name) }.reduce(0) { $0 + $1.more } }
            return PathTrailGroup(id: id, link: link, role: link == nil ? [] : role(steps, context: context, start: start),
                                  stepIDs: steps.map(\.id), cappedMore: capped.flatMap { $0 > 0 ? $0 : nil })
        }
    }

    /// The groups of an answer, links and all.
    public static func groups(_ answer: PathAnswer, context: PathContext, start: String) -> [PathTrailGroup] {
        groups(answer, links: links(answer, context: context), context: context, start: start)
    }

    // MARK: Role line

    /// The line beside a group's pill, from the start-side anchors of its steps. Nothing is invented: a group with no anchors
    /// to read has no role line.
    static func role(_ steps: [PathStep], context: PathContext, start: String) -> [StorySpan] {
        switch context {
        case .artist(.followTheMusician): return start.isEmpty ? [] : [.init("Played with \(start)")]
        case .artist(.sidemanToLeader): return start.isEmpty ? [] : [.init("\(start) played on it")]
        case .artist: return []
        case .album(let tab):
            guard tab == .studioCrew || tab == .listenThroughGaps || tab == .coversAndSources else { return [] }
            var tracks: [String] = []
            var onAlbum = false
            for a in steps.flatMap(\.anchors) {
                if a.type == "release" || a.name.caseInsensitiveCompare(start) == .orderedSame { onAlbum = true }
                else if !tracks.contains(a.name) { tracks.append(a.name) }
            }
            if tab == .coversAndSources { return tracks.isEmpty ? [] : [.init("Behind ")] + titles(tracks) }
            if onAlbum { return [.init("On the album itself")] }
            return tracks.isEmpty ? [] : [.init("On ")] + titles(tracks)
        }
    }

    /// Two titles at most, in italics: "A", "A and B", "A, B and 2 more".
    static func titles(_ names: [String]) -> [StorySpan] {
        switch names.count {
        case 0: return []
        case 1: return [.init(names[0], .title)]
        case 2: return [.init(names[0], .title), .init(" and "), .init(names[1], .title)]
        default: return [.init(names[0], .title), .init(", "), .init(names[1], .title), .init(" and \(names.count - 2) more")]
        }
    }

    // MARK: Counts

    /// "4 albums"; with a filter on, "2 of 4 albums".
    public static func countText(shown: Int, of total: Int, context: PathContext) -> String {
        let noun = context.noun
        if shown == total { return "\(total) \(total == 1 ? noun.one : noun.many)" }
        return "\(shown) of \(total) \(total == 1 ? noun.one : noun.many)"
    }

    /// "12 more albums with Rudy van Gelder are not shown.", for a group that has capped albums.
    public static func cappedText(_ group: PathTrailGroup) -> String? {
        guard let more = group.cappedMore, let name = group.link?.name else { return nil }
        return PathAnswer.cappedSentence(via: name, more: more)
    }

    // MARK: Filter and order

    /// The filter's choice shown only when the answer holds both owned and not-owned steps and is not flat.
    public static func offersFilter(_ answer: PathAnswer, groups: [PathTrailGroup]) -> Bool {
        guard groups.contains(where: { $0.link != nil }) else { return false }
        return answer.steps.contains(where: \.owned) && answer.steps.contains { !$0.owned }
    }

    /// The groups with only the steps the filter keeps; a group left with none is dropped.
    public static func visible(_ groups: [PathTrailGroup], steps: [PathStep], filter: PathFilter) -> [PathTrailGroup] {
        let byID = Dictionary(steps.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        return groups.compactMap { g in
            let kept = g.stepIDs.filter { id in byID[id].map(filter.keeps) ?? false }
            return kept.isEmpty ? nil : (kept.count == g.stepIDs.count ? g : g.with(stepIDs: kept))
        }
    }

    /// The visual order of step ids (group by group), which the arrow keys walk.
    public static func order(_ groups: [PathTrailGroup]) -> [Int] { groups.flatMap(\.stepIDs) }

    // MARK: Loose notes

    /// The notes under the trail: the answer's own (history, skipped, truncation), then the capped sentence of each person or work
    /// that no group in `groups` carries.
    public static func looseNotes(_ answer: PathAnswer, groups: [PathTrailGroup]) -> [String] {
        let named = Set(groups.compactMap { g in g.cappedMore == nil ? nil : g.link.map { fold($0.name) } })
        return answer.notes + answer.capped.filter { !named.contains(fold($0.via)) }.map { PathAnswer.cappedSentence(via: $0.via, more: $0.more) }
    }
}
