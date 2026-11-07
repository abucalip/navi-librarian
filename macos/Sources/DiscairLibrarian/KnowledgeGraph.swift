import Foundation

// Server V2 Phase 5/7 graph data for the macOS graph explorer, atlas and timeline:
// `GET /api/knowledge/connections`, `/paths`, `/place` and `/event` (shapes in docs/SERVER_V2_CONTRACT.md).
// Decoding is tolerant like Knowledge.swift: a missing or unknown field becomes an empty value.

private extension KeyedDecodingContainer {
    func text(_ key: Key) -> String? { try? decodeIfPresent(String.self, forKey: key) }
    func flag(_ key: Key) -> Bool { (try? decodeIfPresent(Bool.self, forKey: key)) ?? false }
    func number(_ key: Key) -> Int { (try? decodeIfPresent(Int.self, forKey: key)) ?? 0 }
    func list<T: Decodable>(_ key: Key, _ type: T.Type) -> [T] { (try? decodeIfPresent([T].self, forKey: key)) ?? [] }
    func sources(_ key: Key) -> [String: KnowledgeSource] { (try? decodeIfPresent([String: KnowledgeSource].self, forKey: key)) ?? [:] }
}

/// One entity reached by the bounded walk, once, at its shortest depth. `credit` is true only for a stated credit.
public struct ConnectionHop: Decodable, Equatable, Sendable {
    public let entity: KnowledgeEntity
    public let depth: Int
    public let viaMBID: String
    public let credit: Bool
    public let evidence: [KnowledgeCredit]
    enum CodingKeys: String, CodingKey { case entity, depth, via_mbid, credit, evidence }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        entity = try c.decode(KnowledgeEntity.self, forKey: .entity)
        depth = c.number(.depth)
        viaMBID = c.text(.via_mbid) ?? ""
        credit = c.flag(.credit)
        evidence = c.list(.evidence, KnowledgeCredit.self)
    }
}

/// `GET /api/knowledge/connections`: one page of the walk. `truncated` is "rows", "time" or nil.
public struct KnowledgeConnections: Decodable, Equatable, Sendable {
    public let start: KnowledgeEntity
    public let hops: [ConnectionHop]
    public let nextCursor: String?
    public let truncated: String?
    public let sources: [String: KnowledgeSource]
    enum CodingKeys: String, CodingKey { case start, hops, next_cursor, truncated, sources }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        start = try c.decode(KnowledgeEntity.self, forKey: .start)
        hops = c.list(.hops, ConnectionHop.self)
        nextCursor = c.text(.next_cursor)
        truncated = c.text(.truncated)
        sources = c.sources(.sources)
    }
}

/// One stated reason a path stop follows: a code, readable text, the entity it goes through and its evidence.
public struct PathReason: Decodable, Equatable, Sendable {
    public let code: String
    public let text: String
    public let via: KnowledgeEntity?
    public let anchor: KnowledgeEntity?
    public let evidence: [KnowledgeCredit]
    enum CodingKeys: String, CodingKey { case code, text, via, anchor, evidence }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        code = c.text(.code) ?? ""
        text = c.text(.text) ?? ""
        via = try? c.decodeIfPresent(KnowledgeEntity.self, forKey: .via)
        anchor = try? c.decodeIfPresent(KnowledgeEntity.self, forKey: .anchor)
        evidence = c.list(.evidence, KnowledgeCredit.self)
    }
}

public struct PathStop: Decodable, Equatable, Sendable {
    public let entity: KnowledgeEntity
    public let reasonCount: Int
    public let reasons: [PathReason]
    enum CodingKeys: String, CodingKey { case entity, reason_count, reasons }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        entity = try c.decode(KnowledgeEntity.self, forKey: .entity)
        reasons = c.list(.reasons, PathReason.self)
        reasonCount = (try? c.decodeIfPresent(Int.self, forKey: .reason_count)) ?? reasons.count
    }
}

/// The four path kinds the server computes (sideman-to-leader and same-studio answer 400).
public enum PathKind: String, Sendable, CaseIterable {
    case followTheMusician = "follow_the_musician"
    case labelPath = "label_path"
    case compositionPath = "composition_path"
    case scenePath = "scene_path"
}

/// `GET /api/knowledge/paths`: `status` is "ok" or "empty"; an empty path has no stops and is never padded.
public struct KnowledgePaths: Decodable, Equatable, Sendable {
    public let kind: String
    public let status: String
    public let start: KnowledgeEntity
    public let stops: [PathStop]
    /// "rows", "time", "stops" or nil.
    public let truncated: String?
    public let sources: [String: KnowledgeSource]
    enum CodingKeys: String, CodingKey { case kind, status, start, stops, truncated, sources }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        kind = c.text(.kind) ?? ""
        status = c.text(.status) ?? "empty"
        start = try c.decode(KnowledgeEntity.self, forKey: .start)
        stops = c.list(.stops, PathStop.self)
        truncated = c.text(.truncated)
        sources = (try? c.decodeIfPresent([String: KnowledgeSource].self, forKey: .sources)) ?? [:]
    }
}

/// Dates and, for a place, coordinates. Any of them may be missing.
public struct KnowledgeFacts: Decodable, Equatable, Sendable {
    public let kind: String?
    public let begin: String?
    public let end: String?
    public let latitude: Double?
    public let longitude: Double?
    public let cancelled: Bool
    enum CodingKeys: String, CodingKey { case kind, begin, end, latitude, longitude, cancelled }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        kind = c.text(.kind); begin = c.text(.begin); end = c.text(.end)
        latitude = try? c.decodeIfPresent(Double.self, forKey: .latitude)
        longitude = try? c.decodeIfPresent(Double.self, forKey: .longitude)
        cancelled = c.flag(.cancelled)
    }
    /// True when both coordinates are present, the only case the atlas may draw a pin.
    public var hasCoordinates: Bool { latitude != nil && longitude != nil }
}

/// An area in a stated containment chain (nearest first). Nothing is derived beyond what MusicBrainz states.
public struct AreaRef: Decodable, Equatable, Sendable {
    public let entity: KnowledgeEntity
    public let kind: String?
    public let isoCode: String?
    enum CodingKeys: String, CodingKey { case mbid, type, owned, canonical_name, sort_name, kind, iso_code }
    public init(from decoder: any Decoder) throws {
        entity = try KnowledgeEntity(from: decoder)
        let c = try decoder.container(keyedBy: CodingKeys.self)
        kind = c.text(.kind); isoCode = c.text(.iso_code)
    }
}

public struct PlaceArea: Decodable, Equatable, Sendable {
    public let area: AreaRef
    public let containedIn: [AreaRef]
    public let credits: [KnowledgeCredit]
    enum CodingKeys: String, CodingKey { case entity, kind, iso_code, contained_in, relations }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let e = try c.decode(KnowledgeEntity.self, forKey: .entity)
        area = AreaRef(entity: e, kind: c.text(.kind), isoCode: c.text(.iso_code))
        containedIn = c.list(.contained_in, AreaRef.self)
        credits = c.list(.relations, KnowledgeCredit.self)
    }
}

extension AreaRef {
    init(entity: KnowledgeEntity, kind: String?, isoCode: String?) { self.entity = entity; self.kind = kind; self.isoCode = isoCode }
}

/// A place or event linked to the page (an event's venue, a place's festival), with its facts and the stated relation.
public struct KnowledgeLinked: Decodable, Equatable, Sendable {
    public let entity: KnowledgeEntity
    public let facts: KnowledgeFacts?
    public let credits: [KnowledgeCredit]
    enum CodingKeys: String, CodingKey { case entity, facts, relations }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        entity = try c.decode(KnowledgeEntity.self, forKey: .entity)
        facts = try? c.decodeIfPresent(KnowledgeFacts.self, forKey: .facts)
        credits = c.list(.relations, KnowledgeCredit.self)
    }
}

/// A recording made at a place or event, with the albums that carry it and whether the library owns it.
public struct KnowledgeRecordingLink: Decodable, Equatable, Sendable {
    public let recording: KnowledgeEntity
    public let owned: Bool
    public let albums: [KnowledgeAlbumLink]
    public let credits: [KnowledgeCredit]
    enum CodingKeys: String, CodingKey { case recording, owned, albums, relations }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        recording = try c.decode(KnowledgeEntity.self, forKey: .recording)
        owned = c.flag(.owned)
        albums = c.list(.albums, KnowledgeAlbumLink.self)
        credits = c.list(.relations, KnowledgeCredit.self)
    }
}

/// `GET /api/knowledge/place?mbid=` (a studio, venue and so on) for the atlas.
public struct KnowledgePlace: Decodable, Equatable, Sendable {
    public let place: KnowledgeEntity
    public let facts: KnowledgeFacts?
    public let area: [PlaceArea]
    public let recordings: [KnowledgeRecordingLink]
    public let people: [KnowledgeCredited]
    public let events: [KnowledgeLinked]
    public let notLoaded: [String]
    public let sources: [String: KnowledgeSource]
    public let truncated: Bool
    enum CodingKeys: String, CodingKey { case place, facts, area, recordings, people, events, not_loaded, sources, truncated }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        place = try c.decode(KnowledgeEntity.self, forKey: .place)
        facts = try? c.decodeIfPresent(KnowledgeFacts.self, forKey: .facts)
        area = c.list(.area, PlaceArea.self)
        recordings = c.list(.recordings, KnowledgeRecordingLink.self)
        people = c.list(.people, KnowledgeCredited.self)
        events = c.list(.events, KnowledgeLinked.self)
        notLoaded = c.list(.not_loaded, String.self)
        sources = c.sources(.sources)
        truncated = c.flag(.truncated)
    }
}

/// `GET /api/knowledge/event?mbid=` (a festival, concert and so on) for the timeline.
public struct KnowledgeEvent: Decodable, Equatable, Sendable {
    public let event: KnowledgeEntity
    public let facts: KnowledgeFacts?
    public let places: [KnowledgeLinked]
    public let area: [PlaceArea]
    public let recordings: [KnowledgeRecordingLink]
    public let people: [KnowledgeCredited]
    public let notLoaded: [String]
    public let sources: [String: KnowledgeSource]
    public let truncated: Bool
    enum CodingKeys: String, CodingKey { case event, facts, places, area, recordings, people, not_loaded, sources, truncated }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        event = try c.decode(KnowledgeEntity.self, forKey: .event)
        facts = try? c.decodeIfPresent(KnowledgeFacts.self, forKey: .facts)
        places = c.list(.places, KnowledgeLinked.self)
        area = c.list(.area, PlaceArea.self)
        recordings = c.list(.recordings, KnowledgeRecordingLink.self)
        people = c.list(.people, KnowledgeCredited.self)
        notLoaded = c.list(.not_loaded, String.self)
        sources = c.sources(.sources)
        truncated = c.flag(.truncated)
    }
}
