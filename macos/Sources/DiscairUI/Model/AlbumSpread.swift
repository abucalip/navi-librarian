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

public struct AlbumSpreadContent: Equatable, Sendable {
    public var notes: String?
    public var credits: [SpreadCreditGroup] = []
    public var facts: [SpreadFact] = []
    public var musicBrainzURL: URL?
    public var lastFmURL: URL?
    public var similar: [SpreadSimilar] = []

    public var isEmpty: Bool { notes == nil && credits.isEmpty && facts.isEmpty && musicBrainzURL == nil && lastFmURL == nil && similar.isEmpty }
}

public enum AlbumSpread {
    /// What the Reviews part says: no review source is connected to Navidrome or the Librarian.
    public static let reviewsNote = "No review source is connected."

    public static func build(facts: NavidromeAlbumFacts?, info: NavidromeAlbumInfo?, artist: NavidromeArtistInfo?,
                             libraryArtists: [String]) -> AlbumSpreadContent {
        var out = AlbumSpreadContent()
        out.notes = info?.notes.flatMap(cleanNotes)
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

    static func isUUID(_ s: String) -> Bool { UUID(uuidString: s) != nil }

    /// Only a Last.fm page over https is linked.
    static func lastFmURL(_ s: String) -> URL? {
        guard let u = URL(string: s), u.scheme == "https", let host = u.host?.lowercased(),
              host == "last.fm" || host.hasSuffix(".last.fm") else { return nil }
        return u
    }

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

/// Loads the spread of the album last opened. The three Navidrome calls run side by side and fail on their own: a
/// server without OpenSubsonic still gives liner notes and similar artists.
@MainActor
@Observable
public final class AlbumSpreadModel {
    public private(set) var content: AlbumSpreadContent? = AlbumSpread.sample
    public private(set) var loading = false
    public private(set) var isLive = false
    private var loadedFor: String?

    public init() {}

    public func load(album: AlbumItem, navidrome: NavidromeClient?, libraryArtists: [String]) async {
        guard let navidrome else { isLive = false; content = AlbumSpread.sample; loadedFor = nil; return }
        isLive = true
        guard let albumID = album.remoteID else { content = nil; loadedFor = nil; return }   // a pick the library does not hold
        if loadedFor == albumID, content != nil { return }
        loading = true; content = nil
        defer { loading = false }
        let artistID = album.artistRemoteID
        async let facts = try? navidrome.albumFacts(id: albumID)
        async let info = try? navidrome.albumInfo(id: albumID)
        async let artist: NavidromeArtistInfo? = {
            guard let artistID else { return nil }
            return (try? await navidrome.artistInfo(id: artistID)) ?? nil
        }()
        let (f, i, a) = await (facts, info ?? nil, artist)
        guard !Task.isCancelled else { return }
        content = AlbumSpread.build(facts: f, info: i, artist: a, libraryArtists: libraryArtists)
        loadedFor = albumID
    }

    public func reset() { content = nil; loadedFor = nil; isLive = false }
}
