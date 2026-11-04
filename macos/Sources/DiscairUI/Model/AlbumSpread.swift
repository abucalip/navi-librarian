import DiscairLibrarian
import DiscairNavidrome
import Foundation
import Observation

/// The album spread (contract section 6.9): liner notes, credits, MusicBrainz data, similar artists.
/// Everything comes from Navidrome (`getAlbumInfo2`, `getArtistInfo2`, OpenSubsonic `getAlbum`); a part the server
/// has nothing for is left out, never invented. No review source exists, so reviews say so.

public struct SpreadCreditGroup: Identifiable, Equatable, Sendable {
    public var id: String { title }
    public let title: String
    public let names: [String]
}

public struct SpreadFact: Identifiable, Equatable, Sendable {
    public var id: String { label }
    public let label: String
    public let value: String
}

public struct SpreadSimilar: Identifiable, Equatable, Sendable {
    public var id: String { name.lowercased() }
    public let name: String
    /// The library holds this artist, so the name opens their page.
    public let inLibrary: Bool
}

public struct SpreadReview: Identifiable, Equatable, Sendable {
    public var id: String { url.absoluteString }
    public let source: String
    public let quote: String
    public let url: URL
}

public struct AlbumSpreadContent: Equatable, Sendable {
    public var notes: String?
    /// Where the notes came from when the Librarian supplied them ("Apple Music", "Wikipedia"), with the licence.
    public var notesSource: String?
    public var notesURL: URL?
    public var credits: [SpreadCreditGroup] = []
    public var facts: [SpreadFact] = []
    public var musicBrainzURL: URL?
    public var lastFmURL: URL?
    public var similar: [SpreadSimilar] = []

    public var isEmpty: Bool { notes == nil && credits.isEmpty && facts.isEmpty && musicBrainzURL == nil && lastFmURL == nil && similar.isEmpty }
}

public enum AlbumSpread {

    public static func build(facts: NavidromeAlbumFacts?, info: NavidromeAlbumInfo?, artist: NavidromeArtistInfo?,
                             description: AlbumDescription? = nil, libraryArtists: [String]) -> AlbumSpreadContent {
        var out = AlbumSpreadContent()
        out.notes = info?.notes.flatMap(cleanNotes)
        if out.notes == nil, let d = description {
            let paras = d.paragraphs.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
            if !paras.isEmpty {
                out.notes = paras.joined(separator: "\n\n")
                out.notesSource = [d.source, d.license].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: " · ")
                out.notesURL = d.url.flatMap(webURL)
            }
        }
        out.credits = credits(facts?.credits ?? [])

        var rows: [SpreadFact] = []
        if let f = facts {
            if !f.releaseTypes.isEmpty { rows.append(SpreadFact(label: "Release type", value: f.releaseTypes.joined(separator: ", "))) }
            if !f.recordLabels.isEmpty { rows.append(SpreadFact(label: "Label", value: f.recordLabels.joined(separator: ", "))) }
            if let d = f.originalReleaseDate { rows.append(SpreadFact(label: "First released", value: d)) }
            if let v = f.version { rows.append(SpreadFact(label: "Edition", value: v)) }
            if f.isCompilation == true { rows.append(SpreadFact(label: "Compilation", value: "Yes")) }
        }
        let mbid = [facts?.musicBrainzId, info?.musicBrainzId].compactMap { $0 }.first(where: isUUID)
        if let mbid { rows.append(SpreadFact(label: "MusicBrainz", value: mbid)) }
        out.facts = rows
        out.musicBrainzURL = mbid.flatMap { URL(string: "https://musicbrainz.org/release/\($0.lowercased())") }
        out.lastFmURL = info?.lastFmUrl.flatMap(lastFmURL)

        let have = Set(libraryArtists.map { $0.lowercased() })
        var seen = Set<String>()
        out.similar = (artist?.similarArtists ?? []).compactMap { a in
            let name = a.name.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !name.isEmpty, seen.insert(name.lowercased()).inserted else { return nil }
            return SpreadSimilar(name: name, inLibrary: have.contains(name.lowercased()))
        }
        return out
    }

    // MARK: Pure helpers (tested)

    private static let rolePriority = ["producer", "composer", "lyricist", "writer", "arranger", "conductor", "engineer", "mixer", "remixer", "djmixer", "performer"]

    /// One group per role (and sub-role), people in first-seen order without repeats; common roles come first.
    static func credits(_ all: [NavidromeCredit]) -> [SpreadCreditGroup] {
        var order: [String] = []
        var groups: [String: (title: String, names: [String], role: String)] = [:]
        for c in all {
            let key = c.role.lowercased() + "|" + (c.subRole ?? "").lowercased()
            if groups[key] == nil {
                order.append(key)
                let base = c.role.prefix(1).uppercased() + c.role.dropFirst()
                groups[key] = (c.subRole.map { "\(base) · \($0)" } ?? base, [], c.role.lowercased())
            }
            if !groups[key]!.names.contains(where: { $0.caseInsensitiveCompare(c.name) == .orderedSame }) { groups[key]!.names.append(c.name) }
        }
        func rank(_ role: String) -> Int { rolePriority.firstIndex(of: role) ?? rolePriority.count }
        return order.enumerated().sorted { a, b in
            let (ra, rb) = (rank(groups[a.element]!.role), rank(groups[b.element]!.role))
            return ra != rb ? ra < rb : a.offset < b.offset
        }.map { SpreadCreditGroup(title: groups[$0.element]!.title, names: groups[$0.element]!.names) }
    }

    /// Plain text from a Last.fm style note: tags removed, entities decoded, the "Read more on Last.fm" line and the
    /// "User-contributed text" licence line dropped. nil when nothing is left.
    static func cleanNotes(_ raw: String) -> String? {
        var s = raw.replacingOccurrences(of: "<br\\s*/?>", with: "\n", options: [.regularExpression, .caseInsensitive])
        s = s.replacingOccurrences(of: "<a [^>]*>[^<]*(read more|more on)[^<]*</a>\\.?", with: "", options: [.regularExpression, .caseInsensitive])
        s = s.replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression)
        for (e, c) in [("&amp;", "&"), ("&quot;", "\""), ("&#39;", "'"), ("&apos;", "'"), ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " ")] {
            s = s.replacingOccurrences(of: e, with: c)
        }
        if let r = s.range(of: "User-contributed text is available", options: .caseInsensitive) { s = String(s[..<r.lowerBound]) }
        let lines = s.split(separator: "\n", omittingEmptySubsequences: true).map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
        let text = lines.joined(separator: "\n\n")
        return text.isEmpty ? nil : text
    }

    /// Reviews from the Librarian: only entries with text and an http(s) link; at most three.
    static func reviews(_ list: [AlbumReview]) -> [SpreadReview] {
        list.compactMap { r in
            let quote = r.quote.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !quote.isEmpty, let u = webURL(r.url) else { return nil }
            return SpreadReview(source: r.source, quote: quote, url: u)
        }.prefix(3).map { $0 }
    }

    static func webURL(_ s: String) -> URL? {
        guard let u = URL(string: s), u.scheme == "https" || u.scheme == "http", u.host != nil else { return nil }
        return u
    }

    static func isUUID(_ s: String) -> Bool { UUID(uuidString: s) != nil }

    /// Only a Last.fm page over https is linked.
    static func lastFmURL(_ s: String) -> URL? {
        guard let u = URL(string: s), u.scheme == "https", let host = u.host?.lowercased(),
              host == "last.fm" || host.hasSuffix(".last.fm") else { return nil }
        return u
    }

    static let sampleReviews = [SpreadReview(source: "Example Magazine", quote: "A record that rewards patience.", url: URL(string: "https://example.com/review")!)]

    /// The mockup's album, for previews and screenshot tests.
    static let sample = AlbumSpreadContent(
        notes: "Spirit of Eden is the fourth studio album by Talk Talk, built from long improvised sessions that were cut apart and rebuilt in the studio.",
        credits: [SpreadCreditGroup(title: "Producer", names: ["Tim Friese-Greene"]),
                  SpreadCreditGroup(title: "Composer", names: ["Mark Hollis", "Tim Friese-Greene"]),
                  SpreadCreditGroup(title: "Engineer", names: ["Phill Brown"])],
        facts: [SpreadFact(label: "Release type", value: "Album"), SpreadFact(label: "Label", value: "EMI"),
                SpreadFact(label: "First released", value: "1988-09-05")],
        similar: [SpreadSimilar(name: "Bark Psychosis", inLibrary: false), SpreadSimilar(name: "Mark Hollis", inLibrary: true)])
}

/// Loads the spread of the album last opened. The Navidrome and Librarian calls run side by side and fail on their
/// own: a server without OpenSubsonic still gives liner notes and similar artists. Reviews are slower (the Librarian
/// asks outlets), so they load after the rest and have their own state.
@MainActor
@Observable
public final class AlbumSpreadModel {
    public enum ReviewsState: Equatable, Sendable { case idle, loading, loaded([SpreadReview], retryable: Bool), failed }

    public private(set) var content: AlbumSpreadContent? = AlbumSpread.sample
    public private(set) var reviews: ReviewsState = .loaded(AlbumSpread.sampleReviews, retryable: false)
    public private(set) var loading = false
    public private(set) var isLive = false
    private var loadedFor: String?

    public init() {}

    public func load(album: AlbumItem, navidrome: NavidromeClient?, librarian: LibrarianClient? = nil, libraryArtists: [String]) async {
        guard navidrome != nil || librarian != nil else {
            isLive = false; content = AlbumSpread.sample; reviews = .loaded(AlbumSpread.sampleReviews, retryable: false); loadedFor = nil; return
        }
        isLive = true
        let key = album.remoteID ?? "pick:\(album.artist.lowercased())|\(album.title.lowercased())"
        if loadedFor == key, content != nil { return }
        loading = true; content = nil; reviews = .idle
        defer { loading = false }
        let ids = (album: album.remoteID, artist: album.artistRemoteID)
        async let facts: NavidromeAlbumFacts? = { guard let navidrome, let id = ids.album else { return nil }; return try? await navidrome.albumFacts(id: id) }()
        async let info: NavidromeAlbumInfo? = { guard let navidrome, let id = ids.album else { return nil }; return (try? await navidrome.albumInfo(id: id)) ?? nil }()
        async let artist: NavidromeArtistInfo? = { guard let navidrome, let id = ids.artist else { return nil }; return (try? await navidrome.artistInfo(id: id)) ?? nil }()
        async let description: AlbumDescription? = { guard let librarian else { return nil }; return try? await librarian.albumDescription(artist: album.artist, album: album.title) }()
        let (f, i, a, d) = await (facts, info, artist, description)
        guard !Task.isCancelled else { return }
        content = AlbumSpread.build(facts: f, info: i, artist: a, description: d, libraryArtists: libraryArtists)
        loadedFor = key
        loading = false
        await loadReviews(album: album, librarian: librarian)
    }

    /// Asks the Librarian for reviews again (the Retry button, or an outlet that did not answer).
    public func loadReviews(album: AlbumItem, librarian: LibrarianClient?) async {
        guard let librarian else { reviews = .idle; return }
        reviews = .loading
        do {
            let r = try await librarian.albumReviews(artist: album.artist, album: album.title)
            guard !Task.isCancelled else { return }
            reviews = .loaded(AlbumSpread.reviews(r.reviews), retryable: r.retryable ?? false)
        } catch {
            if !Task.isCancelled { reviews = .failed }
        }
    }

    public func reset() { content = nil; reviews = .idle; loadedFor = nil; isLive = false }
}
