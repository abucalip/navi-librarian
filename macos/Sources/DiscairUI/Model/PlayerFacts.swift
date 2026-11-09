import DiscairAudio
import DiscairLibrarian
import DiscairNavidrome
import Foundation
import Observation

/// One line shown in the player bar while a song plays: about the song, its album or its artist.
public struct PlayerFact: Equatable, Sendable, Identifiable {
    public enum Origin: String, Sendable { case library, knowledge }
    public var id: String { "\(kind)|\(text)" }
    public let kind: String
    public let text: String
    /// Where the line comes from ("MusicBrainz", "Your library"); every line names it.
    public let source: String
    public let origin: Origin
    /// The page that backs a knowledge line (a MusicBrainz address), when the server gave one.
    public let sourceURL: URL?

    public init(kind: String, text: String, source: String, origin: Origin, sourceURL: URL? = nil) {
        self.kind = kind; self.text = text; self.source = source; self.origin = origin; self.sourceURL = sourceURL
    }
}

/// The two switches next to the quality tag in the player bar. Kept across launches; both are on until the owner turns them off.
@MainActor
@Observable
public final class PlayerBarOptions {
    public static let lyricsKey = "discair.playerBar.lyricTicker"
    public static let factsKey = "discair.playerBar.facts"
    @ObservationIgnored private let defaults: UserDefaults

    /// A one-line synced lyric in the middle of the bar when the song has timed lyrics.
    public var showLyrics: Bool { didSet { defaults.set(showLyrics, forKey: Self.lyricsKey) } }
    /// Facts about the song, album and artist, in the same place when no lyric line is showing.
    public var showFacts: Bool { didSet { defaults.set(showFacts, forKey: Self.factsKey) } }

    public init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        showLyrics = defaults.object(forKey: Self.lyricsKey) as? Bool ?? true
        showFacts = defaults.object(forKey: Self.factsKey) as? Bool ?? true
    }
}

/// Facts the library itself holds about the song (Navidrome tags and the owner's own plays). Pure, so they are tested
/// without a server. Every line is a statement about data the library has; a missing value gives no line.
enum LocalFacts {
    static let source = "Your library"

    static func make(song: NavidromeSong?, album: NavidromeAlbumDetail?, artistName: String?, artistAlbumCount: Int?,
                     now: Date = .now) -> [PlayerFact] {
        var out: [PlayerFact] = []
        func add(_ kind: String, _ text: String) { out.append(PlayerFact(kind: kind, text: text, source: source, origin: .library)) }
        let albumName = album?.album.name ?? song?.album

        if let song, let track = song.track, let count = album?.songs.count ?? album?.album.songCount, count > 1, let albumName, !albumName.isEmpty {
            add("track_position", "Track \(track) of \(count) on \(albumName)")
        }
        if let year = album?.album.year ?? song?.year, year > 1000, let albumName, !albumName.isEmpty {
            let age = Calendar.current.component(.year, from: now) - year
            add("album_year", age > 0 ? "\(albumName) came out in \(year), \(age) year\(age == 1 ? "" : "s") ago" : "\(albumName) came out in \(year)")
        }
        if let seconds = album?.album.duration, seconds > 0, let count = album?.album.songCount, count > 1, let albumName, !albumName.isEmpty {
            add("album_runtime", "\(albumName) runs \(max(1, Int((Double(seconds) / 60).rounded()))) minutes over \(count) songs")
        }
        if let song {
            let plays = song.playCount ?? 0
            add("plays", plays > 0 ? "You have played this \(plays) time\(plays == 1 ? "" : "s")" : "No plays of this song are recorded yet")
            if let last = date(song.played), plays > 0 { add("last_played", "You last played this \(relative(last, now: now))") }
            if let added = date(song.created) { add("added", "Added to your library \(relative(added, now: now))") }
            if let file = fileLine(song) { add("file", file) }
            if let rating = song.userRating, rating > 0 { add("rating", "You rated this \(rating) of 5") }
            if let genre = song.genre, !genre.isEmpty { add("genre", "Filed under \(genre) in your library") }
        }
        if let artistName, !artistName.isEmpty, let n = artistAlbumCount, n > 0 {
            add("artist_albums", n == 1 ? "One album by \(artistName) in your library" : "\(n) albums by \(artistName) in your library")
        }
        return out
    }

    static func fileLine(_ song: NavidromeSong) -> String? {
        let format = (song.suffix ?? "").uppercased()
        guard !format.isEmpty else { return nil }
        if let depth = song.bitDepth, depth > 0, let rate = song.samplingRate, rate > 0 {
            let khz = Double(rate) / 1000
            return "This file is \(format), \(depth)-bit / \(khz == khz.rounded() ? String(Int(khz)) : String(format: "%.1f", khz)) kHz"
        }
        if let rate = song.bitRate, rate > 0 { return "This file is \(format) at \(rate) kbps" }
        return "This file is \(format)"
    }

    static func date(_ iso: String?) -> Date? {
        guard let iso, !iso.isEmpty else { return nil }
        let plain = ISO8601DateFormatter()
        let fractional = ISO8601DateFormatter()
        fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        guard let d = plain.date(from: iso) ?? fractional.date(from: iso), d.timeIntervalSince1970 > 86_400 else { return nil }
        return d
    }

    static func relative(_ date: Date, now: Date) -> String {
        let f = RelativeDateTimeFormatter()
        f.unitsStyle = .full
        f.locale = Locale(identifier: "en_US")
        return f.localizedString(for: min(date, now), relativeTo: now)
    }
}

/// The rotating facts for the song that is playing: what the library knows at once, then what the server's knowledge base
/// adds, mixed so neighbours differ. Nothing is shown that was not read; a failed read just leaves fewer lines.
@MainActor
@Observable
public final class FactsModel {
    public static let maxFacts = 14

    public private(set) var facts: [PlayerFact] = []
    public private(set) var index = 0
    public private(set) var songID: String?

    @ObservationIgnored private var cache: [String: [PlayerFact]] = [:]
    @ObservationIgnored private var cacheOrder: [String] = []

    public init() {}

    public var current: PlayerFact? { facts.isEmpty ? nil : facts[index % facts.count] }

    public func advance() { if facts.count > 1 { index = (index + 1) % facts.count } }

    /// Forgets saved lines (sign-out or a different server).
    public func reset() { facts = []; index = 0; songID = nil; cache = [:]; cacheOrder = [] }

    /// Reads the lines for `item`. Safe to call again for the same song; a later song's call wins over an earlier one.
    public func load(for item: QueueItem?, navidrome: NavidromeClient?, librarian: LibrarianClient?, now: Date = .now) async {
        guard let item else { reset(); return }
        guard item.songID != songID || facts.isEmpty else { return }
        songID = item.songID; index = 0
        if let saved = cache[item.songID] { facts = saved; return }
        facts = []
        var detail: NavidromeAlbumDetail?
        var artistMbid: String?
        var artistCount: Int?
        if let navidrome, let albumID = item.albumID, !albumID.isEmpty {
            detail = try? await navidrome.album(id: albumID)
            if let artistID = detail?.album.artistId, !artistID.isEmpty, let a = try? await navidrome.artist(id: artistID) {
                artistMbid = a.artist.musicBrainzId; artistCount = a.albums.count
            }
        }
        guard songID == item.songID else { return }
        let song = detail?.songs.first { $0.id == item.songID }
        let local = LocalFacts.make(song: song, album: detail, artistName: item.artist, artistAlbumCount: artistCount, now: now)
        facts = Self.mix(knowledge: [], library: local)
        var knowledge: [PlayerFact] = []
        if let librarian, let mbid = item.mbid, !mbid.isEmpty,
           let page = try? await librarian.knowledgeSongFacts(mbid: mbid, albumMbid: detail?.album.musicBrainzId, artistMbid: artistMbid) {
            knowledge = page.facts.map {
                PlayerFact(kind: $0.kind, text: $0.text, source: $0.source, origin: .knowledge, sourceURL: $0.sourceURL.flatMap(Self.safeURL))
            }
        }
        guard songID == item.songID else { return }
        let all = Self.mix(knowledge: knowledge, library: local)
        facts = all
        remember(item.songID, all)
    }

    private func remember(_ id: String, _ list: [PlayerFact]) {
        cache[id] = list; cacheOrder.removeAll { $0 == id }; cacheOrder.append(id)
        while cacheOrder.count > 30 { cache[cacheOrder.removeFirst()] = nil }
    }

    /// Alternates the two sources, knowledge first, and stops at `maxFacts`. A line is never repeated.
    static func mix(knowledge: [PlayerFact], library: [PlayerFact]) -> [PlayerFact] {
        var out: [PlayerFact] = []
        var seen = Set<String>()
        var k = knowledge.makeIterator(), l = library.makeIterator()
        var fromKnowledge = true
        while out.count < maxFacts {
            let next = fromKnowledge ? (k.next() ?? l.next()) : (l.next() ?? k.next())
            guard let fact = next else { break }
            if seen.insert(fact.id).inserted { out.append(fact) }
            fromKnowledge.toggle()
        }
        return out
    }

    /// Only an https page on MusicBrainz is kept as a link.
    static func safeURL(_ s: String) -> URL? {
        guard let u = URL(string: s), u.scheme == "https", let host = u.host?.lowercased(), host == "musicbrainz.org" || host.hasSuffix(".musicbrainz.org") else { return nil }
        return u
    }
}
