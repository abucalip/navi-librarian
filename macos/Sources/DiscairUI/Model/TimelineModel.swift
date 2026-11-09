import DiscairLibrarian
import DiscairNavidrome
import Foundation
import Observation

/// One band of the timeline: a year or a decade, with the items stated for it.
public struct TimelineGroup: Equatable, Sendable, Identifiable {
    public let id: String
    public let label: String
    public let items: [TimelineItem]
}

/// Pure grouping, so a test can drive it without a window. Items arrive in server order (dated, oldest first).
public enum TimelineGrouping {
    public static func groups(_ items: [TimelineItem], byDecade: Bool) -> [TimelineGroup] {
        var order: [Int] = [], buckets: [Int: [TimelineItem]] = [:]
        for item in items {
            guard let y = item.year else { continue }
            let key = byDecade ? y / 10 * 10 : y
            if buckets[key] == nil { order.append(key) }
            buckets[key, default: []].append(item)
        }
        return order.map { TimelineGroup(id: "\($0)", label: byDecade ? "\($0)s" : "\($0)", items: buckets[$0] ?? []) }
    }

    /// Studio albums only. An album is one when MusicBrainz types it "Album" with no secondary type (no live, compilation,
    /// soundtrack...). Where the server holds no type for an album, the title decides: live, compilation or reissue wording
    /// leaves it out. Events are never shown.
    public static func studioAlbums(_ items: [TimelineItem]) -> [TimelineItem] {
        items.filter { item in
            guard item.kind == "album" else { return false }
            if let primary = item.primaryType { return primary.lowercased() == "album" && item.secondaryTypes.isEmpty }
            if !item.secondaryTypes.isEmpty { return false }
            return isStudioTitle(item.entity.name)
        }
    }

    static let nonStudioWords = ["live", "greatest hits", "best of", "the best", "anthology", "collection", "compilation", "complete", "box set",
                                 "boxset", "sessions", "soundtrack", "remaster", "deluxe", "bootleg", "unplugged", "in concert", "essential",
                                 "gold", "hits", "singles", "rarities", "outtakes", "demos", "alternate takes", "tribute", "karaoke", "radio"]
    static func isStudioTitle(_ title: String) -> Bool {
        let words = title.lowercased().split(whereSeparator: { !$0.isLetter && !$0.isNumber }).map(String.init)
        let joined = " " + words.joined(separator: " ") + " "
        return !nonStudioWords.contains { joined.contains(" \($0) ") }
    }

    /// The date as MusicBrainz states it, never padded: "1972", "June 1972" or "2 June 1972".
    public static func display(_ date: String?) -> String {
        guard let date, date.count >= 4 else { return "No stated date" }
        let parts = date.split(separator: "-").map(String.init)
        let months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        guard parts.count >= 2, let m = Int(parts[1]), (1...12).contains(m) else { return parts[0] }
        if parts.count >= 3, let d = Int(parts[2]) { return "\(d) \(months[m - 1]) \(parts[0])" }
        return "\(months[m - 1]) \(parts[0])"
    }
}

/// State of the timeline (Server V2 Phase 7 client gate): one artist's albums and events by stated date. It only reads
/// `GET /api/knowledge/timeline`; no date is taken from a file tag or guessed on the Mac.
@MainActor
@Observable
public final class TimelineModel {
    public private(set) var person: KnowledgeEntity?
    public private(set) var items: [TimelineItem] = []
    public private(set) var undatedCount = 0
    public private(set) var loading = false
    public private(set) var note: String?
    public private(set) var truncated = false
    public private(set) var coverage: String?
    public private(set) var notLoaded: [String] = []
    public private(set) var startedFor: String?
    public var byDecade = false
    public var showsUndated = false
    public var selectedID: String?

    public init() {}

    /// Shows a finished load without a server: screenshots and tests.
    func preview(person: KnowledgeEntity, items: [TimelineItem], undated: Int = 0) {
        self.person = person; self.items = items; undatedCount = undated; coverage = "loaded"
    }

    public var dated: [TimelineItem] { items.filter { $0.year != nil } }
    public var undated: [TimelineItem] { items.filter { $0.year == nil } }
    public var groups: [TimelineGroup] { TimelineGrouping.groups(dated, byDecade: byDecade) }
    public var notLoadedText: String { notLoaded.isEmpty ? "" : "Not loaded: \(notLoaded.map { $0.replacingOccurrences(of: "_", with: " ") }.joined(separator: ", "))" }
    public var selected: TimelineItem? { items.first { $0.id == selectedID } }

    /// Starts from a library artist: reads their MusicBrainz id from Navidrome, then reads the timeline for it.
    public func start(artistRemoteID: String?, name: String, navidrome: NavidromeClient?, librarian: LibrarianClient?) async {
        guard let artistRemoteID, let navidrome, let librarian else {
            note = "Connect to your library and open an artist you own to see their timeline."; return
        }
        guard startedFor != artistRemoteID else { return }
        loading = true; note = nil
        defer { loading = false }
        guard let detail = try? await navidrome.artist(id: artistRemoteID), let mbid = detail.artist.musicBrainzId, !mbid.isEmpty else {
            note = "\(name) has no MusicBrainz id in Navidrome, so there is no timeline yet."; return
        }
        startedFor = artistRemoteID
        do {
            let page = try await librarian.knowledgeTimeline(mbid: mbid)
            person = page.person; items = TimelineGrouping.studioAlbums(page.items); undatedCount = items.filter { $0.year == nil }.count; truncated = page.truncated
            notLoaded = page.notLoaded
            coverage = page.sources["musicbrainz_dump"]?.coverage
            selectedID = nil
            if items.isEmpty {
                note = coverage == "pending" ? "MusicBrainz data is not on the server yet, so there is nothing to place."
                                             : "No album or event is linked to \(name) in the MusicBrainz data yet."
            }
        } catch {
            startedFor = nil
            note = "Could not read the timeline from the Librarian."
        }
    }
}
