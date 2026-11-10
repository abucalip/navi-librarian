import DiscairLibrarian
import Foundation

/// One piece of a step's story: plain words, a person or place (bold) or an album, song or work (italic).
public struct StorySpan: Equatable, Sendable {
    public enum Kind: Sendable { case plain, name, title }
    public let text: String
    public let kind: Kind
    init(_ text: String, _ kind: Kind = .plain) { self.text = text; self.kind = kind }
}

/// The right-hand text of an album path step: one sentence per person, place or work, built from the names the server sent.
/// Reasons that differ only by a track title are one sentence with the titles listed, never one sentence each. The wording
/// never says "this album" or "a recording": it names the start album, the stop and their tracks.
public enum PathStory {
    static let maxParagraphs = 3
    static let maxTitles = 4

    public static func compose(_ reasons: [PathReason], start: String, stop: String) -> [[StorySpan]] {
        var order: [String] = []
        var groups: [String: [PathReason]] = [:]
        for r in reasons {
            let key = r.code + "|" + (r.via?.name ?? r.text)
            if groups[key] == nil { order.append(key) }
            groups[key, default: []].append(r)
        }
        return order.prefix(maxParagraphs).map { paragraph(groups[$0]!, start: start, stop: stop) }
    }

    static func paragraph(_ rs: [PathReason], start: String, stop: String) -> [StorySpan] {
        let first = rs[0]
        guard let via = first.via?.name, !via.isEmpty, !start.isEmpty, !stop.isEmpty else { return [StorySpan(first.text.endingInPeriod)] }
        let mine = startSide(rs, start: start)
        let theirs = stopSide(first.target, stop: stop)
        let single = mine.count == 1
        switch first.code {
        case "crew_on":
            return [.init(via, .name), .init(" has a production credit on ")] + mine.spans + [.init(" and on ")] + theirs + [.init(".")]
        case "guest_on":
            return [.init(via, .name), .init(" is credited as a guest on ")] + mine.spans + [.init(" and also appears on ")] + theirs + [.init(".")]
        case "recorded_at":
            return [.init(via, .name), .init(" is where ")] + mine.spans
                + [.init(single ? " was made (recorded, mixed or engineered) and where " : " were made (recorded, mixed or engineered) and where ")]
                + theirs + [.init(" was made.")]
        case "same_work":
            return theirs + [.init(" is another recording of "), .init(via, .title), .init(", the work behind ")] + mine.spans + [.init(".")]
        case "derived_work":
            return theirs + [.init(" is a recording of "), .init(via, .title), .init(", a work related to the work behind ")] + mine.spans + [.init(".")]
        default:
            return [StorySpan(first.text.endingInPeriod)]
        }
    }

    /// The start album's side: its tracks the credit sits on ("Round Midnight, All of You from Round About Midnight"), or the album itself.
    static func startSide(_ rs: [PathReason], start: String) -> (spans: [StorySpan], count: Int) {
        var tracks: [String] = []
        var onAlbum = false
        for a in rs.compactMap(\.anchor) {
            if a.type == "release" || a.name.caseInsensitiveCompare(start) == .orderedSame { onAlbum = true }
            else if !tracks.contains(a.name) { tracks.append(a.name) }
        }
        if onAlbum || tracks.isEmpty { return ([.init(start, .title)], 1) }
        return (list(tracks) + [.init(" from "), .init(start, .title)], tracks.count)
    }

    /// The stop's side: the track the credit reaches with its album, or the album.
    static func stopSide(_ target: KnowledgeEntity?, stop: String) -> [StorySpan] {
        guard let t = target, t.type != "release", !t.name.isEmpty, t.name.caseInsensitiveCompare(stop) != .orderedSame else { return [.init(stop, .title)] }
        return [.init(t.name, .title), .init(" from "), .init(stop, .title)]
    }

    /// "A, B and C"; past four titles, "A, B, C, D and 2 more".
    static func list(_ names: [String]) -> [StorySpan] {
        var shown = Array(names.prefix(maxTitles))
        let more = names.count - shown.count
        var out: [StorySpan] = []
        let last = shown.removeLast()
        for (i, n) in shown.enumerated() { out += [.init(n, .title), .init(i < shown.count - 1 ? ", " : more > 0 ? ", " : " and ")] }
        out.append(.init(last, .title))
        if more > 0 { out.append(.init(" and \(more) more")) }
        return out
    }
}

private extension String {
    var endingInPeriod: String { isEmpty || hasSuffix(".") ? self : self + "." }
}
