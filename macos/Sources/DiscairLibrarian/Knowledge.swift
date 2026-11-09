import Foundation

// Server V2 Phase 4 knowledge pages (`GET /api/knowledge/...`, shapes in intelligence/contract-fixtures/knowledge_*.json).
// Decoding is tolerant: a missing or unknown field falls back to an empty value, so a newer server never breaks a page.

private extension KeyedDecodingContainer {
    func text(_ key: Key) -> String? { try? decodeIfPresent(String.self, forKey: key) }
    func flag(_ key: Key) -> Bool { (try? decodeIfPresent(Bool.self, forKey: key)) ?? false }
    func number(_ key: Key) -> Int { (try? decodeIfPresent(Int.self, forKey: key)) ?? 0 }
    func list<T: Decodable>(_ key: Key, _ type: T.Type) -> [T] { (try? decodeIfPresent([T].self, forKey: key)) ?? [] }
}

/// An artist, album, label, work or recording. `mbid` is the only identity; `owned` is always a real boolean.
public struct KnowledgeEntity: Decodable, Equatable, Sendable, Hashable {
    public let mbid: String
    public let name: String
    public let type: String
    public let owned: Bool
    public let sortName: String?

    enum CodingKeys: String, CodingKey { case mbid, type, owned, canonical_name, sort_name }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        mbid = c.text(.mbid) ?? ""
        name = c.text(.canonical_name) ?? ""
        type = c.text(.type) ?? ""
        owned = c.flag(.owned)
        sortName = c.text(.sort_name)
    }
}

/// One stated connection with its source, so every line on a page can show where it came from.
public struct KnowledgeCredit: Decodable, Equatable, Sendable {
    public let relation: String
    public let role: String?
    public let scope: String?
    public let track: String?
    public let direction: String?
    public let evidenceClass: String
    public let matchQuality: String
    public let source: String
    public let sourceURL: String?
    public let validFrom: String?
    public let validTo: String?

    enum CodingKeys: String, CodingKey {
        case relation, role, scope, track, direction, source, evidence_class, match_quality, source_url, valid_from, valid_to
    }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        relation = c.text(.relation) ?? ""
        role = c.text(.role)
        scope = c.text(.scope)
        track = c.text(.track)
        direction = c.text(.direction)
        evidenceClass = c.text(.evidence_class) ?? ""
        matchQuality = c.text(.match_quality) ?? ""
        source = c.text(.source) ?? ""
        sourceURL = c.text(.source_url)
        validFrom = c.text(.valid_from)
        validTo = c.text(.valid_to)
    }

    /// "guitar" for an instrument credit, otherwise the role, otherwise the relation name.
    public var label: String { (role?.isEmpty == false ? role : nil) ?? relation }
}

/// A source's state: `coverage` is "loaded" or "pending" (the slice is not on the server yet).
public struct KnowledgeSource: Decodable, Equatable, Sendable {
    public let coverage: String
    public let dumpTimestamp: String?
    enum CodingKeys: String, CodingKey { case coverage, dump_timestamp }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        coverage = c.text(.coverage) ?? "pending"
        dumpTimestamp = c.text(.dump_timestamp)
    }
}

public struct KnowledgeLifeSpan: Decodable, Equatable, Sendable {
    public let begin: String?
    public let end: String?
    public let ended: Bool
    enum CodingKeys: String, CodingKey { case begin, end, ended }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        begin = c.text(.begin); end = c.text(.end); ended = c.flag(.ended)
    }
}

/// An entity with the credits that connect it to the page's subject (the server calls the list `credits` or `relations`).
public struct KnowledgeCredited: Decodable, Equatable, Sendable {
    public let entity: KnowledgeEntity
    public let credits: [KnowledgeCredit]
    enum CodingKeys: String, CodingKey { case entity, credits, relations }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        entity = try c.decode(KnowledgeEntity.self, forKey: .entity)
        let named = c.list(.credits, KnowledgeCredit.self)
        credits = named.isEmpty ? c.list(.relations, KnowledgeCredit.self) : named
    }
}

public struct KnowledgeTrack: Decodable, Equatable, Sendable {
    public let position: String
    public let title: String
    public let recordingMBID: String?
    enum CodingKeys: String, CodingKey { case position, title, recording_mbid }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        position = c.text(.position) ?? ""; title = c.text(.title) ?? ""; recordingMBID = c.text(.recording_mbid)
    }
}

public struct KnowledgeEdition: Decodable, Equatable, Sendable {
    public let mbid: String
    public let title: String
    public let owned: Bool
    public let date: String?
    public let country: String?
    public let status: String?
    public let trackCount: Int?
    public let factsSource: String?
    enum CodingKeys: String, CodingKey { case release, date, country, status, track_count, facts_source }
    enum ReleaseKeys: String, CodingKey { case mbid, title, owned }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let r = try? c.nestedContainer(keyedBy: ReleaseKeys.self, forKey: .release)
        mbid = r?.text(.mbid) ?? ""; title = r?.text(.title) ?? ""; owned = r?.flag(.owned) ?? false
        date = c.text(.date); country = c.text(.country); status = c.text(.status)
        trackCount = try? c.decodeIfPresent(Int.self, forKey: .track_count)
        factsSource = c.text(.facts_source)
    }
}

/// `GET /api/knowledge/album?mbid=`: editions, tracks, people and labels. The client shows ten credits per list with a "more" control.
public struct KnowledgeAlbum: Decodable, Equatable, Sendable {
    public let album: KnowledgeEntity
    public let releaseGroup: KnowledgeEntity?
    public let editions: [KnowledgeEdition]
    public let tracks: [KnowledgeTrack]
    public let people: [KnowledgeCredited]
    public let labels: [KnowledgeCredited]
    public let creditsTruncated: Bool
    public let notLoaded: [String]
    public let sources: [String: KnowledgeSource]
    enum CodingKeys: String, CodingKey {
        case album, release_group, release_family, tracks, people, labels, credits_truncated, not_loaded, sources
    }
    enum FamilyKeys: String, CodingKey { case editions }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        album = try c.decode(KnowledgeEntity.self, forKey: .album)
        releaseGroup = try? c.decodeIfPresent(KnowledgeEntity.self, forKey: .release_group)
        editions = (try? c.nestedContainer(keyedBy: FamilyKeys.self, forKey: .release_family))?.list(.editions, KnowledgeEdition.self) ?? []
        tracks = c.list(.tracks, KnowledgeTrack.self)
        people = c.list(.people, KnowledgeCredited.self)
        labels = c.list(.labels, KnowledgeCredited.self)
        creditsTruncated = c.flag(.credits_truncated)
        notLoaded = c.list(.not_loaded, String.self)
        sources = (try? c.decodeIfPresent([String: KnowledgeSource].self, forKey: .sources)) ?? [:]
    }
}

/// One album tied to a person or label, with why it is there.
public struct KnowledgeAlbumLink: Decodable, Equatable, Sendable {
    public let album: KnowledgeEntity
    public let owned: Bool
    public let credits: [KnowledgeCredit]
    public let why: String?
    enum CodingKeys: String, CodingKey { case album, owned, credits, relations, why }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        album = try c.decode(KnowledgeEntity.self, forKey: .album)
        owned = c.flag(.owned)
        let named = c.list(.credits, KnowledgeCredit.self)
        credits = named.isEmpty ? c.list(.relations, KnowledgeCredit.self) : named
        why = c.text(.why)
    }
}

/// `GET /api/knowledge/person?mbid=`. `sources["musicbrainz_dump"].coverage == "pending"` means the slice is not on the server yet.
public struct KnowledgePerson: Decodable, Equatable, Sendable {
    public let person: KnowledgeEntity
    public let lifeSpan: KnowledgeLifeSpan?
    public let inLibrary: [KnowledgeAlbumLink]
    public let notInLibrary: [KnowledgeAlbumLink]
    public let notLoaded: [String]
    public let sources: [String: KnowledgeSource]
    public let truncated: Bool
    enum CodingKeys: String, CodingKey { case person, life_span, in_library, not_in_library, not_loaded, sources, truncated }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        person = try c.decode(KnowledgeEntity.self, forKey: .person)
        lifeSpan = try? c.decodeIfPresent(KnowledgeLifeSpan.self, forKey: .life_span)
        inLibrary = c.list(.in_library, KnowledgeAlbumLink.self)
        notInLibrary = c.list(.not_in_library, KnowledgeAlbumLink.self)
        notLoaded = c.list(.not_loaded, String.self)
        sources = (try? c.decodeIfPresent([String: KnowledgeSource].self, forKey: .sources)) ?? [:]
        truncated = c.flag(.truncated)
    }
}

/// `GET /api/knowledge/label?mbid=`.
public struct KnowledgeLabel: Decodable, Equatable, Sendable {
    public let label: KnowledgeEntity
    public let ownedCatalogue: [KnowledgeAlbumLink]
    public let notInLibrary: [KnowledgeAlbumLink]
    public let notLoaded: [String]
    public let sources: [String: KnowledgeSource]
    public let truncated: Bool
    enum CodingKeys: String, CodingKey { case label, owned_catalogue, not_in_library, not_loaded, sources, truncated }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        label = try c.decode(KnowledgeEntity.self, forKey: .label)
        ownedCatalogue = c.list(.owned_catalogue, KnowledgeAlbumLink.self)
        notInLibrary = c.list(.not_in_library, KnowledgeAlbumLink.self)
        notLoaded = c.list(.not_loaded, String.self)
        sources = (try? c.decodeIfPresent([String: KnowledgeSource].self, forKey: .sources)) ?? [:]
        truncated = c.flag(.truncated)
    }
}

/// One recording of a work: who played, which albums hold it, and whether it is owned.
public struct KnowledgeVersion: Decodable, Equatable, Sendable {
    public let recording: KnowledgeEntity
    public let owned: Bool
    public let performers: [KnowledgeCredited]
    public let albums: [KnowledgeAlbumLink]
    public let attributes: [String]
    enum CodingKeys: String, CodingKey { case recording, owned, performers, albums, attributes }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        recording = try c.decode(KnowledgeEntity.self, forKey: .recording)
        owned = c.flag(.owned)
        performers = c.list(.performers, KnowledgeCredited.self)
        albums = c.list(.albums, KnowledgeAlbumLink.self)
        attributes = c.list(.attributes, String.self)
    }
}

/// `GET /api/knowledge/work?mbid=`: a song and its versions, with the covers and in-library counts.
public struct KnowledgeWork: Decodable, Equatable, Sendable {
    public let work: KnowledgeEntity
    public let writtenBy: [KnowledgeCredited]
    public let versions: [KnowledgeVersion]
    public let recordings: Int
    public let covers: Int
    public let inLibrary: Int
    public let notLoaded: [String]
    public let sources: [String: KnowledgeSource]
    public let truncated: Bool
    enum CodingKeys: String, CodingKey { case work, written_by, versions, summary, not_loaded, sources, truncated }
    enum SummaryKeys: String, CodingKey { case recordings, covers, in_library }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        work = try c.decode(KnowledgeEntity.self, forKey: .work)
        writtenBy = c.list(.written_by, KnowledgeCredited.self)
        versions = c.list(.versions, KnowledgeVersion.self)
        let s = try? c.nestedContainer(keyedBy: SummaryKeys.self, forKey: .summary)
        recordings = s?.number(.recordings) ?? 0; covers = s?.number(.covers) ?? 0; inLibrary = s?.number(.in_library) ?? 0
        notLoaded = c.list(.not_loaded, String.self)
        sources = (try? c.decodeIfPresent([String: KnowledgeSource].self, forKey: .sources)) ?? [:]
        truncated = c.flag(.truncated)
    }
}

public struct KnowledgeWorkLink: Decodable, Equatable, Sendable {
    public let work: KnowledgeEntity
    public let otherRecordings: Int
    public let credits: [KnowledgeCredit]
    enum CodingKeys: String, CodingKey { case work, other_recordings, relations }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        work = try c.decode(KnowledgeEntity.self, forKey: .work)
        otherRecordings = c.number(.other_recordings)
        credits = c.list(.relations, KnowledgeCredit.self)
    }
}

/// `GET /api/knowledge/recording-works?mbid=`: the works a track performs, for "Who played on this?" and "Other versions".
public struct KnowledgeRecordingWorks: Decodable, Equatable, Sendable {
    public let recording: KnowledgeEntity
    public let works: [KnowledgeWorkLink]
    public let sources: [String: KnowledgeSource]
    public let truncated: Bool
    enum CodingKeys: String, CodingKey { case recording, works, sources, truncated }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        recording = try c.decode(KnowledgeEntity.self, forKey: .recording)
        works = c.list(.works, KnowledgeWorkLink.self)
        sources = (try? c.decodeIfPresent([String: KnowledgeSource].self, forKey: .sources)) ?? [:]
        truncated = c.flag(.truncated)
    }
}

/// One line of `GET /api/knowledge/song-facts`: a statement MusicBrainz makes, with its source and the page that backs it.
public struct KnowledgeSongFact: Decodable, Equatable, Sendable {
    public struct Link: Decodable, Equatable, Sendable { public let type: String; public let mbid: String }
    public let kind: String
    /// `song`, `album` or `artist`.
    public let scope: String
    public let text: String
    public let source: String
    public let sourceURL: String?
    public let link: Link?
    enum CodingKeys: String, CodingKey { case kind, scope, text, source, source_url, link }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        kind = c.text(.kind) ?? ""
        scope = c.text(.scope) ?? "song"
        text = c.text(.text) ?? ""
        source = c.text(.source) ?? "MusicBrainz"
        sourceURL = c.text(.source_url)
        link = try? c.decodeIfPresent(Link.self, forKey: .link)
    }
    public init(kind: String, scope: String, text: String, source: String = "MusicBrainz", sourceURL: String? = nil, link: Link? = nil) {
        self.kind = kind; self.scope = scope; self.text = text; self.source = source; self.sourceURL = sourceURL; self.link = link
    }
}

public struct KnowledgeSongFacts: Decodable, Equatable, Sendable {
    public let facts: [KnowledgeSongFact]
    public let sources: [String: KnowledgeSource]
    enum CodingKeys: String, CodingKey { case facts, sources }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        // One bad line is dropped, not the whole answer.
        facts = ((try? c.decodeIfPresent([Lossy<KnowledgeSongFact>].self, forKey: .facts)) ?? []).compactMap(\.value).filter { !$0.text.isEmpty }
        sources = (try? c.decodeIfPresent([String: KnowledgeSource].self, forKey: .sources)) ?? [:]
    }
    public init(facts: [KnowledgeSongFact], sources: [String: KnowledgeSource] = [:]) { self.facts = facts; self.sources = sources }
}

private struct Lossy<T: Decodable>: Decodable {
    let value: T?
    init(from decoder: any Decoder) throws { value = try? T(from: decoder) }
}
