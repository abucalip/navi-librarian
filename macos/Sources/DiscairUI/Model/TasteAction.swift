import Foundation

/// What a taste card can do with a value the server listed (Server V2 Phase 6 presentation slice 7): turn it into a
/// smart-playlist rule set, or filter the Library's Songs tab by it. Only genre and era map onto fields the library has;
/// area, label and collaborator are not song fields here, so they offer no action rather than a guess. Pure and read-only:
/// nothing here touches recommendation ranking, the server or the player.
public enum TasteAction: Equatable, Sendable {
    case genre(String)
    /// A decade, inclusive of both years (`1980s` is 1980...1989).
    case era(label: String, years: ClosedRange<Int>)

    /// nil for a dimension the library cannot filter on, or an era label that is not a decade like `1980s`.
    public init?(dimension: String, value: String) {
        let v = value.trimmingCharacters(in: .whitespaces)
        guard !v.isEmpty else { return nil }
        switch dimension {
        case "genre": self = .genre(v)
        case "era":
            guard v.hasSuffix("s"), let start = Int(v.dropLast()), start % 10 == 0, (1000...2990).contains(start) else { return nil }
            self = .era(label: v, years: start...(start + 9))
        default: return nil
        }
    }

    public var label: String {
        switch self { case .genre(let g): g; case .era(let l, _): l }
    }

    public var playlistName: String {
        switch self { case .genre(let g): "Taste: \(g)"; case .era(let l, _): "Taste: \(l)" }
    }

    /// The rules the new smart playlist starts with; the owner edits them like any other.
    public var rules: [SmartRule] {
        switch self {
        case .genre(let g): [SmartRule(field: .genre, op: .contains, value: g)]
        case .era(_, let y): [SmartRule(field: .year, op: .atLeast, value: String(y.lowerBound)),
                              SmartRule(field: .year, op: .atMost, value: String(y.upperBound))]
        }
    }

    public var playlist: SmartPlaylist { SmartPlaylist(name: playlistName, matchAll: true, rules: rules) }

    /// True when the song belongs to the filter. Genre is a folded substring match, like the smart-playlist `contains` rule.
    public func matches(_ s: SongRow) -> Bool {
        switch self {
        case .genre(let g): LibrarySearch.fold(s.genre).contains(LibrarySearch.fold(g))
        case .era(_, let y): y.contains(s.year)
        }
    }
}
