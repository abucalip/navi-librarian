import DiscairLibrarian
import Foundation
import Observation

/// One role of the extended credits with the people who hold it, from the knowledge base.
public struct ExtendedCreditGroup: Identifiable, Equatable, Sendable {
    public var id: String { role }
    public let role: String
    public let names: [String]
}

public enum ExtendedCredits {
    /// One group per role (the credit's role, else its relation), people once each in first-seen order; the roles with the
    /// most people first, ties in the order seen.
    public static func groups(_ people: [KnowledgeCredited]) -> [ExtendedCreditGroup] {
        var order: [String] = []
        var names: [String: [String]] = [:]
        for p in people {
            for credit in p.credits {
                let raw = credit.label.trimmingCharacters(in: .whitespaces)
                guard !raw.isEmpty else { continue }
                let role = raw.prefix(1).uppercased() + raw.dropFirst()
                if names[role] == nil { order.append(role); names[role] = [] }
                if !names[role]!.contains(where: { $0.caseInsensitiveCompare(p.entity.name) == .orderedSame }) { names[role]!.append(p.entity.name) }
            }
        }
        return order.enumerated().sorted { a, b in
            let (na, nb) = (names[a.element]!.count, names[b.element]!.count)
            return na != nb ? na > nb : a.offset < b.offset
        }.map { ExtendedCreditGroup(role: $0.element, names: names[$0.element]!) }
    }
}

/// The album's extended credits, read from the knowledge base by the album's release group.
@MainActor
@Observable
public final class AlbumCreditsModel {
    public private(set) var groups: [ExtendedCreditGroup] = []
    public private(set) var loading = false
    public private(set) var truncated = false
    @ObservationIgnored private var loadedFor: String?

    public init() {}

    public func forget() { groups = []; truncated = false; loadedFor = nil; loading = false }

    public func load(rgid: String?, librarian: LibrarianClient?) async {
        guard let rgid, !rgid.isEmpty, let librarian else { return }
        if loadedFor == rgid { return }
        loading = true
        defer { loading = false }
        let page = try? await librarian.knowledgeAlbum(mbid: rgid)
        guard !Task.isCancelled else { return }
        loadedFor = rgid
        groups = ExtendedCredits.groups(page?.people ?? [])
        truncated = page?.creditsTruncated ?? false
    }
}

/// The biography split into paragraphs: the source's own breaks when it has them; otherwise, once the text is longer than
/// 100 words, a break at the full stop nearest each 100-word mark.
public enum BioParagraphs {
    public static let threshold = 100

    public static func split(_ text: String) -> [String] {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return [] }
        let broken = trimmed.components(separatedBy: "\n").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
        if broken.count > 1 { return broken }
        let words = trimmed.split(whereSeparator: \.isWhitespace).map(String.init)
        guard words.count > threshold else { return [trimmed] }
        var out: [String] = []
        var start = 0
        while words.count - start > threshold {
            let target = start + threshold
            // The sentence ends closest to the target, looking up to half a paragraph either way; none: break at the target.
            var best: Int?
            for i in max(start + 1, target - threshold / 2)...min(words.count - 1, target + threshold / 2) where isSentenceEnd(words[i - 1]) {
                if best == nil || abs(i - target) < abs(best! - target) { best = i }
            }
            let cut = best ?? target
            out.append(words[start..<cut].joined(separator: " "))
            start = cut
        }
        if start < words.count { out.append(words[start...].joined(separator: " ")) }
        return out
    }

    private static func isSentenceEnd(_ w: String) -> Bool {
        var s = Substring(w)
        while let l = s.last, "\"'”’)]".contains(l) { s = s.dropLast() }
        guard let last = s.last, ".!?".contains(last) else { return false }
        // Initials and common abbreviations ("St.", "Mr.", "J.") are not the end of a sentence.
        let core = s.dropLast()
        return core.count > 2 && !["Mr", "Mrs", "Dr", "St", "Jr", "Sr", "vs", "No"].contains(String(core))
    }
}
