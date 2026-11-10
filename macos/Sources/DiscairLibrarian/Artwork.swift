import DiscairCore
import Foundation

// An album's images from the Librarian (`GET /api/artwork/index?rgid=&release=` and `GET /api/artwork/image/{id}?size=`).
// Shapes in the "Album artwork" section of docs/SERVER_V2_CONTRACT.md; decided in docs/artwork.md. The Mac only talks to
// the Librarian, which talks to MusicBrainz and the Cover Art Archive. Nothing here reads taste or play data, and an album
// with no images shows nothing extra. Decoding is tolerant: one bad entry never drops the rest.

private extension KeyedDecodingContainer {
    func text(_ key: Key) -> String? { try? decodeIfPresent(String.self, forKey: key) }
    func flag(_ key: Key) -> Bool { (try? decodeIfPresent(Bool.self, forKey: key)) ?? false }
    func number(_ key: Key) -> Int? { try? decodeIfPresent(Int.self, forKey: key) }
}

/// The sizes the image route serves. `full` is the original (a PDF only here), fetched only on zoom or open.
public enum ArtworkSize: String, Sendable, CaseIterable {
    case thumb, display, full
}

/// One image of the album. `comment` is third-party text: show it as plain text, never as markup.
public struct ArtworkPicture: Decodable, Equatable, Sendable, Identifiable {
    public let imageID: Int
    public let release: String
    /// Every fetched release the image is on; the same scan appears once.
    public let releases: [String]
    /// "1999 JP CD"; parts MusicBrainz lacked are left out.
    public let edition: String
    public let types: [String]
    public let comment: String
    public let approved: Bool
    public let width: Int?
    public let height: Int?
    /// The original's file type: `jpg`, `png`, `gif`, `webp` or `pdf`; empty when the server did not say.
    public let format: String
    public var id: Int { imageID }

    /// A PDF original is served only as `size=full`; its thumb and display are a first-page preview image.
    public var isPDF: Bool { format == "pdf" }
    /// Untyped images are in no slot; they are only in the full index.
    public var isUntyped: Bool { types.isEmpty }

    /// The text for VoiceOver and captions: type and edition ("Back cover, 1999 JP CD"), then the comment when there is one.
    public var label: String {
        let type: String
        if let first = types.first { type = ["Front", "Back"].contains(first) ? "\(first) cover" : first } else { type = "Image" }
        let head = edition.isEmpty ? type : "\(type), \(edition)"
        let note = comment.trimmingCharacters(in: .whitespacesAndNewlines)
        return note.isEmpty ? head : "\(head): \(note)"
    }

    enum CodingKeys: String, CodingKey {
        case imageID = "image_id", release, releases, edition, types, comment, approved, width, height, format
    }

    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        guard let id = c.number(.imageID), id > 0 else {
            throw DecodingError.dataCorruptedError(forKey: .imageID, in: c, debugDescription: "image without an id")
        }
        imageID = id
        release = c.text(.release) ?? ""
        releases = (try? c.decodeIfPresent([String].self, forKey: .releases)) ?? []
        edition = c.text(.edition) ?? ""
        types = (try? c.decodeIfPresent([String].self, forKey: .types)) ?? []
        comment = c.text(.comment) ?? ""
        approved = c.flag(.approved)
        width = c.number(.width)
        height = c.number(.height)
        format = (c.text(.format) ?? "").lowercased()
    }

    public init(imageID: Int, release: String = "", releases: [String] = [], edition: String = "", types: [String] = [],
                comment: String = "", approved: Bool = true, width: Int? = nil, height: Int? = nil, format: String = "jpg") {
        self.imageID = imageID; self.release = release; self.releases = releases; self.edition = edition; self.types = types
        self.comment = comment; self.approved = approved; self.width = width; self.height = height; self.format = format
    }
}

/// A type's best image. `fromOwned` is false when another edition filled in; `edition` then says which.
public struct ArtworkSlot: Decodable, Equatable, Sendable {
    public let imageID: Int
    public let release: String
    public let edition: String
    public let fromOwned: Bool
    enum CodingKeys: String, CodingKey { case imageID = "image_id", release, edition, fromOwned = "from_owned" }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        guard let id = c.number(.imageID), id > 0 else {
            throw DecodingError.dataCorruptedError(forKey: .imageID, in: c, debugDescription: "slot without an image id")
        }
        imageID = id
        release = c.text(.release) ?? ""
        edition = c.text(.edition) ?? ""
        fromOwned = c.flag(.fromOwned)
    }
}

/// The ordered pages of the one release with the most booklet pages. Pages are never mixed across releases.
public struct ArtworkBooklet: Decodable, Equatable, Sendable {
    public let release: String
    public let edition: String
    public let imageIDs: [Int]
    enum CodingKeys: String, CodingKey { case release, edition, imageIDs = "image_ids" }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        release = c.text(.release) ?? ""
        edition = c.text(.edition) ?? ""
        imageIDs = (try? c.decodeIfPresent([Int].self, forKey: .imageIDs)) ?? []
    }
}

public struct ArtworkReleaseCounts: Decodable, Equatable, Sendable {
    public let total: Int, fetched: Int, empty: Int, failed: Int
    enum CodingKeys: String, CodingKey { case total, fetched, empty, failed }
    public init(total: Int, fetched: Int, empty: Int, failed: Int) { self.total = total; self.fetched = fetched; self.empty = empty; self.failed = failed }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        total = c.number(.total) ?? 0; fetched = c.number(.fetched) ?? 0; empty = c.number(.empty) ?? 0; failed = c.number(.failed) ?? 0
    }
}

/// The index of one release group. `images` are in the server's quality order.
public struct ArtworkIndex: Decodable, Equatable, Sendable {
    public let rgid: String
    /// nil, `release_cap`, `served_cap` or `partial`: what was left out. The index is still shown.
    public let truncatedReason: String?
    public let releases: ArtworkReleaseCounts
    /// The id of the best Front image, or nil when nothing is typed Front (never an artist photo, never an untyped image).
    public let bestFront: Int?
    /// One best image per type (Front, Back, Spine, Obi, Medium, Tray, Sticker, Poster), keyed by the type name.
    public let slots: [String: ArtworkSlot]
    public let booklet: ArtworkBooklet?
    public let images: [ArtworkPicture]

    enum CodingKeys: String, CodingKey {
        case rgid, truncated, truncatedReason = "truncated_reason", releases, bestFront = "best_front", slots, booklet, images
    }

    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        rgid = c.text(.rgid) ?? ""
        truncatedReason = c.flag(.truncated) ? (c.text(.truncatedReason).flatMap { $0.isEmpty ? nil : $0 } ?? "partial") : nil
        releases = (try? c.decodeIfPresent(ArtworkReleaseCounts.self, forKey: .releases))
            ?? ArtworkReleaseCounts(total: 0, fetched: 0, empty: 0, failed: 0)
        bestFront = c.number(.bestFront)
        let rawSlots = (try? c.decodeIfPresent([String: LenientEntry<ArtworkSlot>].self, forKey: .slots)) ?? [:]
        slots = rawSlots.compactMapValues { $0.value }
        booklet = (try? c.decodeIfPresent(ArtworkBooklet.self, forKey: .booklet)).flatMap { $0.imageIDs.isEmpty ? nil : $0 }
        images = ((try? c.decodeIfPresent([LenientEntry<ArtworkPicture>].self, forKey: .images)) ?? []).compactMap { $0.value }
    }

    public func image(_ id: Int) -> ArtworkPicture? { images.first { $0.imageID == id } }
    /// The slot image for `type`, or nil when the album has none (or the served list was trimmed past it).
    public func slotImage(_ type: String) -> ArtworkPicture? { slots[type].flatMap { image($0.imageID) } }
    /// The booklet pages that are in `images`, in the server's order. A PDF booklet is one entry.
    public var bookletImages: [ArtworkPicture] { (booklet?.imageIDs ?? []).compactMap { image($0) } }
}

/// What the Librarian said about an album's images.
public enum ArtworkIndexResult: Equatable, Sendable {
    /// `ok`: the index, possibly truncated.
    case ready(ArtworkIndex)
    /// Every release answered "no images". Show nothing extra: no placeholder, no empty tab.
    case empty
    /// The lookup failed. This says nothing about the album and is never worded as "no images".
    case unavailable
    /// A background build has started; ask again after this many seconds.
    case notLoaded(retryAfter: Int)

    /// Reads an index body. Anything that is not an answer in the contract is `unavailable`.
    public static func decode(_ data: Data) -> ArtworkIndexResult {
        struct Head: Decodable {
            let status: String?
            let retryAfter: Int?
            enum CodingKeys: String, CodingKey { case status, retryAfter = "retry_after" }
        }
        guard let head = try? JSONDecoder().decode(Head.self, from: data) else { return .unavailable }
        switch head.status {
        case "ok":
            guard let index = try? JSONDecoder().decode(ArtworkIndex.self, from: data) else { return .unavailable }
            // An "ok" with nothing to show is not an error and not a statement either: show nothing extra.
            return index.images.isEmpty ? .empty : .ready(index)
        case "empty": return .empty
        // "pending" is the knowledge-base name for the same state (docs/efficiency.md, E1): a fetch is queued, ask again.
        case "not_loaded", "pending": return .notLoaded(retryAfter: min(max(head.retryAfter ?? 5, 1), 60))
        default: return .unavailable
        }
    }
}

extension ArtworkIndexResult {
    /// Asks until the index is built: the server answers `not_loaded` while its background job runs. After `tries` answers
    /// that are still `not_loaded` the result is `unavailable` (still building says nothing about the album). A throw from
    /// `ask` is `unavailable` too, except cancellation, which is rethrown by the caller's own task checks.
    public static func load(tries: Int = 8, wait: @Sendable (Duration) async -> Void = { try? await Task.sleep(for: $0) },
                            ask: @Sendable () async throws -> ArtworkIndexResult) async -> ArtworkIndexResult {
        var last = ArtworkIndexResult.unavailable
        for _ in 0..<tries {
            if Task.isCancelled { return .unavailable }
            last = (try? await ask()) ?? .unavailable
            guard case .notLoaded(let seconds) = last else { return last }
            await wait(.seconds(seconds))
        }
        if case .notLoaded = last { return .unavailable }
        return last
    }
}

/// One image's bytes with the type the server gave them.
public struct ArtworkImageData: Equatable, Sendable {
    public let data: Data
    public let contentType: String
    public var isPDF: Bool { contentType.lowercased().hasPrefix("application/pdf") }
}

extension LibrarianClient {
    /// An album's images by MusicBrainz release group; `release` is the owned release, which wins the slots. A 400 (malformed
    /// id) throws; every other body is read by `ArtworkIndexResult.decode`, so a failed lookup is `unavailable`, never `empty`.
    public func artworkIndex(rgid: String, release: String? = nil) async throws -> ArtworkIndexResult {
        var path = "api/artwork/index?rgid=\(Self.enc(rgid))"
        if let release, !release.isEmpty { path += "&release=\(Self.enc(release))" }
        let (data, http) = try await authedSendPublic("GET", path, body: nil)
        if http.statusCode == 200 { return ArtworkIndexResult.decode(data) }
        if let failure = failurePublic(http, data) { throw failure }
        return .unavailable
    }

    /// One image's bytes. A PDF original is served only at `.full`. Throws on 404 (unknown id or no file) and 503 (the provider is
    /// temporarily unavailable: ask again later). The caller decides whether the bytes can be a bitmap by `isPDF`.
    public func artworkImage(id: Int, size: ArtworkSize) async throws -> ArtworkImageData {
        let (data, http) = try await authedSendPublic("GET", "api/artwork/image/\(id)?size=\(size.rawValue)", body: nil)
        guard http.statusCode == 200 else {
            if let failure = failurePublic(http, data) { throw failure }
            throw DiscairError.server(status: http.statusCode, message: nil)
        }
        return ArtworkImageData(data: data, contentType: http.value(forHTTPHeaderField: "Content-Type") ?? "")
    }
}
