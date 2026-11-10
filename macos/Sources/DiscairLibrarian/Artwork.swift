import CoreGraphics
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

extension ArtworkIndex {
    /// The faces behind the cover that it can flip to (docs/artwork.md, idea 1): the best Back, then Tray, then Spine. The front is
    /// the cover the page already shows. An album with no Back image does not flip, even with a Tray or Spine: those are extras on
    /// a flipped cover, not a cover of their own. Chosen by type only, never by taste or play data.
    public var coverBackFaces: [ArtworkPicture] {
        guard let back = slotImage("Back") else { return [] }
        var seen = Set<Int>()
        return [back, slotImage("Tray"), slotImage("Spine")].compactMap { $0 }.filter { seen.insert($0.imageID).inserted }
    }

    /// The covers an owner can pick from (docs/artwork.md, idea 7): Front images of the release group, best first, never a PDF.
    /// The server checks the same rule on `PUT /api/artwork/choice`, so a pick it would refuse is never offered.
    public var coverEditions: [ArtworkPicture] {
        var seen = Set<Int>()
        return images.filter { $0.types.contains("Front") && !$0.isPDF && seen.insert($0.imageID).inserted }
    }
}

/// The picker needs a real choice: one cover or none is nothing to pick from.
public func hasEditionChoice(_ editions: [ArtworkPicture]) -> Bool { editions.count >= 2 }

/// Which face shows after `steps` flips on a card with `backs` back faces: 0 is the front. Negative steps (the other direction) wrap.
public func coverFace(afterSteps steps: Int, backs: Int) -> Int {
    guard backs > 0 else { return 0 }
    let n = backs + 1
    return ((steps % n) + n) % n
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

    /// `GET /api/artwork/choices`: the owner's cover picks, library album id to artwork image id.
    public func artworkChoices() async throws -> [String: Int] {
        struct Body: Decodable { let choices: [String: Int]? }
        let (data, http) = try await authedSendPublic("GET", "api/artwork/choices", body: nil)
        guard http.statusCode == 200 else {
            if let failure = failurePublic(http, data) { throw failure }
            return [:]
        }
        return (try? JSONDecoder().decode(Body.self, from: data))?.choices ?? [:]
    }

    /// `PUT /api/artwork/choice/{album_id}`. The server refuses an image that is not a Front of the album's release group (404)
    /// and answers 409 while the index is still being built.
    public func setArtworkChoice(albumID: String, rgid: String, imageID: Int) async throws {
        let body = try JSONSerialization.data(withJSONObject: ["rgid": rgid, "image_id": imageID])
        let (data, http) = try await authedSendPublic("PUT", "api/artwork/choice/\(Self.enc(albumID))", body: body)
        if let failure = failurePublic(http, data) { throw failure }
    }

    /// `DELETE /api/artwork/choice/{album_id}`: the automatic cover is used again.
    public func clearArtworkChoice(albumID: String) async throws {
        let (data, http) = try await authedSendPublic("DELETE", "api/artwork/choice/\(Self.enc(albumID))", body: nil)
        if let failure = failurePublic(http, data) { throw failure }
    }

    /// `GET /api/owned/artwork/{album_id}?size=`: the library cover as the server resolves it, so the owner's pick, or the best
    /// front when the library has no cover or only a small one. Throws on 404.
    public func ownedCover(albumID: String, px: Int) async throws -> ArtworkImageData {
        let (data, http) = try await authedSendPublic("GET", "api/owned/artwork/\(Self.enc(albumID))?size=\(px)", body: nil)
        guard http.statusCode == 200 else {
            if let failure = failurePublic(http, data) { throw failure }
            throw DiscairError.server(status: http.statusCode, message: nil)
        }
        return ArtworkImageData(data: data, contentType: http.value(forHTTPHeaderField: "Content-Type") ?? "")
    }
}

/// What the album's Booklet sheet shows (docs/artwork.md, idea 2): the pages of the one release with the most booklet pages, in the
/// server's order (never mixed across editions), then the album's Sticker, Obi and Poster, each once. An album with no booklet has
/// no sheet, even when it has a Poster: those follow the pages, they are not a booklet of their own. Chosen by type only.
public struct BookletView: Equatable, Sendable {
    public let edition: String
    public let pages: [ArtworkPicture]
    public let extras: [ArtworkPicture]

    /// Pages then extras, each image once.
    public var items: [ArtworkPicture] { pages + extras }
    /// A PDF booklet is one entry that holds many pages; it opens in the PDF viewer, not the spread.
    public var pdf: ArtworkPicture? { items.first { $0.isPDF } }
    /// The spreads of the bitmap pages: the first page alone (the cover), then pairs, a last odd page alone, then each extra alone.
    public var spreads: [[ArtworkPicture]] {
        bookletSpreads(pages.filter { !$0.isPDF }) + extras.filter { !$0.isPDF }.map { [$0] }
    }
}

extension ArtworkIndex {
    public var bookletView: BookletView? {
        let pages = bookletImages
        guard !pages.isEmpty else { return nil }
        var seen = Set(pages.map(\.imageID))
        let extras = ["Sticker", "Obi", "Poster"].compactMap { slotImage($0) }.filter { seen.insert($0.imageID).inserted }
        return BookletView(edition: booklet?.edition ?? "", pages: pages, extras: extras)
    }
}

/// Two-page spreads like an opened booklet: page 1 alone, then (2, 3), (4, 5) and so on; an odd last page stands alone.
public func bookletSpreads<T>(_ pages: [T]) -> [[T]] {
    guard !pages.isEmpty else { return [] }
    var out: [[T]] = [[pages[0]]]
    var i = 1
    while i < pages.count {
        out.append(Array(pages[i..<min(i + 2, pages.count)]))
        i += 2
    }
    return out
}

/// Where the pointer is on a page as a 0...1 point of the page's fitted picture, clamped to its edges. nil for an empty frame.
public func lensUnitPoint(_ point: CGPoint, in frame: CGRect) -> CGPoint? {
    guard frame.width > 0, frame.height > 0 else { return nil }
    return CGPoint(x: min(max((point.x - frame.minX) / frame.width, 0), 1), y: min(max((point.y - frame.minY) / frame.height, 0), 1))
}

/// The rectangle a picture of `image` size takes when fitted into `frame` and centred (what `scaledToFit` draws).
public func fittedRect(image: CGSize, in frame: CGSize) -> CGRect {
    guard image.width > 0, image.height > 0, frame.width > 0, frame.height > 0 else { return .zero }
    let k = min(frame.width / image.width, frame.height / image.height)
    let size = CGSize(width: image.width * k, height: image.height * k)
    return CGRect(x: (frame.width - size.width) / 2, y: (frame.height - size.height) / 2, width: size.width, height: size.height)
}
