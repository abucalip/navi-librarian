import Foundation

/// A JSON value inside a card's `reasons[].evidence`. Evidence keys differ per lens, so a generic card shows them as
/// plain label/value pairs instead of knowing every lens.
public enum InsightValue: Decodable, Equatable, Sendable {
    case string(String), number(Double), bool(Bool), list([InsightValue]), object([String: InsightValue]), null

    public init(from decoder: any Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .null }
        else if let v = try? c.decode(Bool.self) { self = .bool(v) }
        else if let v = try? c.decode(Double.self) { self = .number(v) }
        else if let v = try? c.decode(String.self) { self = .string(v) }
        else if let v = try? c.decode([InsightValue].self) { self = .list(v) }
        else { self = .object(try c.decode([String: InsightValue].self)) }
    }

    /// Short text for a label/value row; nested values are flattened with commas.
    public var text: String {
        switch self {
        case .string(let s): s
        case .number(let n): n == n.rounded() && abs(n) < 1e15 ? String(Int(n)) : String(n)
        case .bool(let b): b ? "yes" : "no"
        case .list(let l): l.map(\.text).joined(separator: ", ")
        case .object(let o): o.keys.sorted().map { "\($0): \(o[$0]!.text)" }.joined(separator: ", ")
        case .null: ""
        }
    }
}

/// Why a card was shown (`reasons[]`). Never advice: a count, a date or a listen total.
public struct InsightReason: Decodable, Equatable, Sendable {
    public let kind: String
    public let evidence: [String: InsightValue]

    enum CodingKeys: String, CodingKey { case kind, evidence }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        kind = (try? c.decode(String.self, forKey: .kind)) ?? ""
        evidence = (try? c.decode([String: InsightValue].self, forKey: .evidence)) ?? [:]
    }
    public init(kind: String, evidence: [String: InsightValue] = [:]) { self.kind = kind; self.evidence = evidence }
}

/// What a card is about. `key` is the dismiss and accept key, so it must be kept as the server wrote it.
public struct InsightSubject: Decodable, Equatable, Sendable {
    public let key: String
    public let type: String
    public let title: String?
    public let artist: String?
    public let mbid: String?
    public let year: Int?

    enum CodingKeys: String, CodingKey { case key, type, title, artist, mbid, year }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        key = (try? c.decode(String.self, forKey: .key)) ?? ""
        type = (try? c.decode(String.self, forKey: .type)) ?? ""
        title = try? c.decode(String.self, forKey: .title)
        artist = try? c.decode(String.self, forKey: .artist)
        mbid = try? c.decode(String.self, forKey: .mbid)
        year = try? c.decode(Int.self, forKey: .year)
    }
    public init(key: String, type: String = "", title: String? = nil, artist: String? = nil, mbid: String? = nil, year: Int? = nil) {
        self.key = key; self.type = type; self.title = title; self.artist = artist; self.mbid = mbid; self.year = year
    }
}

/// A run of missing chapters in a series card ("missing 3-5").
public struct InsightMissingRun: Decodable, Equatable, Sendable {
    public let firstPosition: Int
    public let lastPosition: Int
    public let titles: [String]
    /// The titles with their year where the server gave one ("Title 2 (2002)").
    public let labels: [String]

    enum CodingKeys: String, CodingKey { case firstPosition = "first_position", lastPosition = "last_position", items }
    struct Item: Decodable { let title: String?; let year: Int? }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        firstPosition = (try? c.decode(Int.self, forKey: .firstPosition)) ?? 0
        lastPosition = (try? c.decode(Int.self, forKey: .lastPosition)) ?? firstPosition
        let items = ((try? c.decode([Item].self, forKey: .items)) ?? []).filter { $0.title != nil }
        titles = items.compactMap(\.title)
        labels = items.map { i in i.year.map { "\(i.title ?? "") (\($0))" } ?? (i.title ?? "") }
    }
}

/// One generic insight card (docs/SERVER_V2_CONTRACT.md, `GET /api/insights`). The title and body are the server's words
/// and are shown as they are; a card with no key or no reasons is dropped by the response, so every shown card is explainable.
public struct InsightCard: Decodable, Equatable, Sendable, Identifiable {
    public var id: String { kind + "|" + subject.key }
    public let kind: String
    public let title: String
    public let body: String
    public let subject: InsightSubject
    public let reasons: [InsightReason]
    public let dismissible: Bool
    public let score: Double
    public let owned: Int?
    public let total: Int?
    public let missingRuns: [InsightMissingRun]

    enum CodingKeys: String, CodingKey { case kind, title, body, subject, reasons, dismissible, score, owned, total, missingRuns = "missing_runs" }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        kind = (try? c.decode(String.self, forKey: .kind)) ?? ""
        title = ((try? c.decode(String.self, forKey: .title)) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        body = ((try? c.decode(String.self, forKey: .body)) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        subject = (try? c.decode(InsightSubject.self, forKey: .subject)) ?? InsightSubject(key: "")
        reasons = (try? c.decode([InsightReason].self, forKey: .reasons)) ?? []
        dismissible = (try? c.decode(Bool.self, forKey: .dismissible)) ?? false
        score = (try? c.decode(Double.self, forKey: .score)) ?? 0
        owned = try? c.decode(Int.self, forKey: .owned)
        total = try? c.decode(Int.self, forKey: .total)
        missingRuns = (try? c.decode([InsightMissingRun].self, forKey: .missingRuns)) ?? []
    }
}

/// One lens. `enabled == false` means the lens is off (show "off"); `enabled` with no cards is an empty state, never invented cards.
public struct InsightLens: Decodable, Equatable, Sendable {
    public let enabled: Bool
    public let cards: [InsightCard]

    enum CodingKeys: String, CodingKey { case enabled, cards }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        enabled = (try? c.decode(Bool.self, forKey: .enabled)) ?? false
        // A card the app cannot explain (no key or no reasons) is dropped rather than shown unexplained.
        let all = (try? c.decode([LossyCard].self, forKey: .cards)) ?? []
        cards = all.compactMap(\.card).filter { !$0.subject.key.isEmpty && !$0.reasons.isEmpty }
    }
    private struct LossyCard: Decodable {
        let card: InsightCard?
        init(from decoder: any Decoder) throws { card = try? InsightCard(from: decoder) }
    }
}

public struct InsightsResponse: Decodable, Equatable, Sendable {
    public let lenses: [String: InsightLens]
    public let dataVersion: Int
    public let generation: Int

    enum CodingKeys: String, CodingKey { case lenses, dataVersion = "data_version", generation }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        lenses = (try? c.decode([String: InsightLens].self, forKey: .lenses)) ?? [:]
        dataVersion = (try? c.decode(Int.self, forKey: .dataVersion)) ?? 0
        generation = (try? c.decode(Int.self, forKey: .generation)) ?? 0
    }

    /// Lens kinds in the order the dashboard lists them; kinds the app does not know yet follow, alphabetically.
    public static let knownOrder = ["forgotten_gem", "series_completion", "blind_spot", "hidden_canon", "anniversary"]

    public var orderedKinds: [String] {
        let known = Self.knownOrder.filter { lenses[$0] != nil }
        return known + lenses.keys.filter { !Self.knownOrder.contains($0) }.sorted()
    }
}
