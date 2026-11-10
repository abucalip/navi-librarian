import DiscairCore
import DiscairLibrarian
import DiscairNavidrome
import Foundation
import Observation

/// The tabs of the album Paths sheet: the six graph kinds plus Neighbours by Ear (only when the server reports sonic similarity).
public enum AlbumPathTab: String, CaseIterable, Identifiable, Sendable {
    case studioCrew, guestList, coversAndSources, sameYearSameScene, sameRoom, listenThroughGaps, neighboursByEar
    public var id: String { rawValue }
    public var label: String {
        switch self {
        case .studioCrew: "Crew"
        case .guestList: "Guests"
        case .coversAndSources: "Covers"
        case .sameYearSameScene: "Scene"
        case .sameRoom: "Room"
        case .listenThroughGaps: "Gaps"
        case .neighboursByEar: "Sonic"
        }
    }
    /// The path's full name, for sentences ("No Guest List path from ...").
    public var fullName: String {
        switch self {
        case .studioCrew: "Studio Crew"
        case .guestList: "Guest List"
        case .coversAndSources: "Covers and Sources"
        case .sameYearSameScene: "Same Year, Same Scene"
        case .sameRoom: "Same Room"
        case .listenThroughGaps: "Listen-through Gaps"
        case .neighboursByEar: "Neighbours by Ear"
        }
    }
    public var graph: AlbumPathKind? {
        switch self {
        case .studioCrew: .studioCrew
        case .guestList: .guestList
        case .coversAndSources: .coversAndSources
        case .sameYearSameScene: .sameYearSameScene
        case .sameRoom: .sameRoom
        case .listenThroughGaps: .listenThroughGaps
        case .neighboursByEar: nil
        }
    }
    public static func available(sonic: Bool) -> [AlbumPathTab] { allCases.filter { $0.graph != nil || sonic } }

    /// The line under the segmented control. `seeds` is how many tracks Neighbours by Ear used, once known.
    public func summary(album: String, seeds: Int = 0) -> String {
        switch self {
        case .studioCrew: "Albums that share a producer, engineer or mixer credit with \(album), those not in your library first."
        case .guestList: "Albums where the guests credited on \(album) also appear, those not in your library first."
        case .coversAndSources: "Albums with another recording of a song on \(album), or of a work it comes from, those not in your library first."
        case .sameYearSameScene: "Albums from the same years as \(album), linked by a label, an area or a shared artist, those not in your library first."
        case .sameRoom: "Albums with a track made in the same studio or at the same event as a track on \(album), those not in your library first."
        case .listenThroughGaps: "Albums in your library that share a credit with \(album) and that you have played little or never."
        case .neighboursByEar: seeds > 0 ? "Albums in your library that sound like \(album), found from \(seeds) of its tracks." : "Albums in your library that sound like \(album)."
        }
    }
}

/// The artist's five paths (ported from the Android sheet; the wording is the same).
public extension PathKind {
    var label: String {
        switch self {
        case .followTheMusician: "Follow the Musician"
        case .sidemanToLeader: "Sideman"
        case .labelPath: "Label"
        case .compositionPath: "Composition"
        case .scenePath: "Scene"
        }
    }
    /// `startType` is the start's entity type (`group`, `person`), so wording fits a band or a single musician.
    func summary(artist: String, startType: String) -> String {
        switch self {
        case .followTheMusician: "Songs, not in your library, by musicians who also played with \(artist)."
        case .sidemanToLeader:
            switch startType {
            case "group": "Artists whose records \(artist) appeared on as guests."
            case "person": "Artists whose records \(artist) played on as a sideman."
            default: "Artists whose records \(artist) played on as a guest."
            }
        case .labelPath: "Albums released on the same labels as \(artist)'s records."
        case .compositionPath: "Other recordings of the same compositions as \(artist)'s, covers and live versions included."
        case .scenePath: "Artists from the same place and era as \(artist)."
        }
    }
}

/// One reason on a step, as the server sent it.
public struct PathStepReason: Equatable, Sendable {
    public let code: String
    public let text: String
    public let via: String?
    /// "Production credit", "Same label"...: the small label above the reason.
    public var eyebrow: String {
        switch code {
        case "crew_on": "Production credit"
        case "guest_on": "Guest credit"
        case "same_work": "Same work"
        case "derived_work", "related_work": "Related work"
        case "same_period_label": "Same label"
        case "same_period_credit": "Shared artist"
        case "same_period_area": "Same area"
        case "recorded_at": "Recorded at"
        case "sonic_neighbour": "Sounds alike"
        case "sideman_on": "Sideman"
        default: "Why it's here"
        }
    }
}

/// What a step opens.
public enum PathTarget: Equatable, Sendable {
    case album(title: String, artist: String, albumID: String?)
    case artist(name: String)
    public var label: String { if case .album = self { "Open Album" } else { "Open Artist" } }
}

/// One step of a path. `detail` and `why` are the table's second and third columns; `symbol` replaces the cover for a step
/// that is not an album (an artist, a song).
public struct PathStep: Identifiable, Equatable, Sendable {
    public let id: Int
    public let name: String
    public let detail: String
    public let why: String
    public let year: Int?
    public let cover: AlbumCover?
    public let symbol: String
    public let reasons: [PathStepReason]
    public let evidence: String?
    public let target: PathTarget?
    public let artistName: String?
    public let owned: Bool
    /// Listen-through Gaps: the server's play label ("Not played"); nil elsewhere.
    public var play: String? = nil
    /// Album paths: the story of why the step is here, one paragraph per person, place or work.
    public var story: [[StorySpan]] = []
    public struct AlbumCover: Equatable, Sendable { public let title: String; public let artist: String; public let albumID: String?; public let coverArt: String? }
}

/// The steps of one tab and the honest notes under them (what was cut, what was skipped).
public struct PathAnswer: Equatable, Sendable {
    public var steps: [PathStep]
    public var notes: [String]
    public var seeds: Int = 0
    public var startType: String = ""
    /// Said instead of the generic empty line when the server's own figures explain why nothing is listed.
    public var empty: String?

    /// What a Gaps answer's play history means for the list, in words. Never reads a count as taste.
    static func historyNotes(_ h: PathHistory?) -> [String] {
        guard let h else { return [] }
        func albums(_ n: Int) -> String { "\(n) \(n == 1 ? "album" : "albums")" }
        switch h.state {
        case "thin": return ["Your play history is too short to tell which albums you have not played, so every album these credits reach is listed, played or not."]
        case "unavailable": return ["Your play history could not be read, so every album these credits reach is listed, played or not."]
        default:
            var n: [String] = []
            let most = h.littlePlaysBelow - 1
            if h.filteredOut > 0 { n.append("\(albums(h.filteredOut)) reached by these credits left out because you have played \(h.filteredOut == 1 ? "it" : "them") more than \(most) \(most == 1 ? "time" : "times").") }
            if h.unknown > 0 { n.append("\(albums(h.unknown)) left out because \(h.unknown == 1 ? "it has" : "they have") no play record.") }
            return n
        }
    }

    static func truncation(_ reason: String) -> String {
        let words = switch reason { case "rows": "row limit"; case "time": "time limit"; case "stops": "stop limit"; default: "limit" }
        return "The server stopped this path early (\(words)), so later steps may be missing."
    }

    public init(steps: [PathStep], notes: [String], seeds: Int = 0, startType: String = "", empty: String? = nil) {
        self.steps = steps; self.notes = notes; self.seeds = seeds; self.startType = startType; self.empty = empty
    }

    static func evidence(_ r: PathReason?) -> String? {
        guard let c = r?.evidence.first else { return nil }
        return ([c.relation, c.role].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: ", ")) + " · MusicBrainz"
    }

    /// An album path: a stop is an album in or out of the library (`entity.owned`), those out of it first.
    public init(album p: KnowledgePaths) {
        steps = p.stops.enumerated().map { i, stop in
            let by = stop.albumArtist ?? ""
            let first = stop.reasons.first
            return PathStep(
                id: i, name: stop.entity.name, detail: by, why: stop.play ?? first?.via?.name ?? first?.text ?? "", year: nil,
                cover: .init(title: stop.entity.name, artist: by, albumID: nil, coverArt: nil), symbol: "opticaldisc",
                reasons: stop.reasons.map { PathStepReason(code: $0.code, text: $0.text, via: $0.via?.name) },
                evidence: Self.evidence(first), target: .album(title: stop.entity.name, artist: by, albumID: nil),
                artistName: by.isEmpty ? nil : by, owned: stop.entity.owned, play: stop.play,
                story: PathStory.compose(stop.reasons, start: p.start.name, stop: stop.entity.name))
        }
        if let h = p.history, h.state == "ok", steps.isEmpty, h.filteredOut > 0 {
            let most = h.littlePlaysBelow - 1
            empty = "Every album these credits reach is one you have already played more than \(most) \(most == 1 ? "time" : "times"), so there is no gap to list."
        }
        var n = Self.historyNotes(p.history) + p.capped.map { "\($0.more) more \($0.more == 1 ? "album" : "albums") with \($0.via) \($0.more == 1 ? "is" : "are") not shown." }
        if let t = p.truncated { n.append(Self.truncation(t)) }
        notes = n
        startType = p.start.type
    }

    public init(album s: SonicAlbumNeighbours) {
        let of = s.seeds.count
        steps = s.stops.enumerated().map { i, stop in
            let tracks = of > 0 ? "\(stop.matchCount) of \(of) tracks" : "\(stop.matchCount) \(stop.matchCount == 1 ? "track" : "tracks")"
            return PathStep(
                id: i, name: stop.album, detail: stop.artist, why: tracks, year: stop.year,
                cover: .init(title: stop.album, artist: stop.artist, albumID: stop.albumID, coverArt: stop.coverArt), symbol: "opticaldisc",
                reasons: stop.reasonText.map { [PathStepReason(code: "sonic_neighbour", text: $0, via: nil)] } ?? [], evidence: nil,
                target: .album(title: stop.album, artist: stop.artist, albumID: stop.albumID),
                artistName: stop.artist.isEmpty ? nil : stop.artist, owned: true)
        }
        var n: [String] = []
        if !s.skipped.isEmpty { n.append("\(s.skipped.count) \(s.skipped.count == 1 ? "track has" : "tracks have") no sound analysis and \(s.skipped.count == 1 ? "was" : "were") skipped.") }
        if let t = s.truncated { n.append(Self.truncation(t)) }
        notes = n
        seeds = of
    }

    /// An artist path. A step is a song (Follow the Musician), an artist (Sideman, Scene), an album (Label) or a recording
    /// (Composition); the columns follow the Android rows.
    public init(artist p: KnowledgePaths, kind: PathKind) {
        steps = p.stops.enumerated().map { i, stop in
            let first = stop.reasons.first
            let name = stop.entity.name
            let reasons = stop.reasons.map { PathStepReason(code: $0.code, text: $0.text, via: $0.via?.name) }
            let owned = stop.entity.owned
            func step(_ n: String, _ detail: String, _ why: String, symbol: String, cover: PathStep.AlbumCover? = nil,
                      target: PathTarget?, artist: String?) -> PathStep {
                PathStep(id: i, name: n, detail: detail, why: why, year: nil, cover: cover, symbol: symbol, reasons: reasons,
                         evidence: Self.evidence(first), target: target, artistName: artist, owned: owned)
            }
            switch kind {
            case .followTheMusician:
                let album = stop.album ?? "", by = stop.albumArtist ?? ""
                let who = stop.reasons.first(where: { ["artist", "person", "group"].contains($0.via?.type ?? "") })?.via?.name
                return step(name, [album, by].filter { !$0.isEmpty }.joined(separator: " · "), who ?? first?.text ?? "", symbol: "music.note",
                            cover: album.isEmpty || by.isEmpty ? nil : .init(title: album, artist: by, albumID: nil, coverArt: nil),
                            target: !album.isEmpty && !by.isEmpty ? .album(title: album, artist: by, albumID: nil) : (by.isEmpty ? nil : .artist(name: by)),
                            artist: by.isEmpty ? nil : by)
            case .sidemanToLeader:
                let release = stop.reasons.first(where: { $0.via?.type == "release" })?.via?.name
                return step(name, release.map { "Led \($0)" } ?? "", first?.anchor.map { "Played on \($0.name)" } ?? "", symbol: "person.fill",
                            target: .artist(name: name), artist: name)
            case .labelPath:
                let by = stop.albumArtist ?? ""
                return step(name, by, first?.via?.name ?? "", symbol: "opticaldisc",
                            cover: by.isEmpty ? nil : .init(title: name, artist: by, albumID: nil, coverArt: nil),
                            target: by.isEmpty ? nil : .album(title: name, artist: by, albumID: nil), artist: by.isEmpty ? nil : by)
            case .compositionPath:
                let who = stop.artist ?? ""
                return step(who.isEmpty ? "Artist not listed" : who, name, first?.via?.name ?? "", symbol: "music.note",
                            target: who.isEmpty ? nil : .artist(name: who), artist: who.isEmpty ? nil : who)
            case .scenePath:
                return step(name, ["person": "Person", "group": "Group"][stop.entity.type] ?? "Artist", first?.via.map { "From \($0.name)" } ?? "",
                            symbol: "person.fill", target: .artist(name: name), artist: name)
            }
        }
        // The server collapses repeats; this guards older answers (one row per place a row leads to).
        var seen = Set<String>()
        if kind == .followTheMusician || kind == .labelPath {
            steps = steps.filter { s in
                guard let key = (s.artistName.map { $0.lowercased() }) else { return true }
                return seen.insert(kind == .followTheMusician ? "song:" + s.name.lowercased() : key).inserted
            }.enumerated().map { i, s in PathStep(id: i, name: s.name, detail: s.detail, why: s.why, year: s.year, cover: s.cover, symbol: s.symbol,
                                                  reasons: s.reasons, evidence: s.evidence, target: s.target, artistName: s.artistName, owned: s.owned) }
        }
        notes = p.truncated.map { [Self.truncation($0)] } ?? []
        startType = p.start.type
    }
}

/// One tab of a Paths sheet.
public struct PathTabSpec: Identifiable {
    public let id: String
    public let label: String
    let summary: (PathAnswer?) -> String
    public let empty: String
    let load: (LibrarianClient) async throws -> PathAnswer
}

/// A Paths sheet, for an album or an artist: one tab per path, asked only while the sheet is open and never saved.
@MainActor @Observable
public final class PathsSheetModel: Identifiable {
    public enum Phase: Equatable { case loading, ready(PathAnswer), failed(String) }
    public enum Subject: Sendable { case album, artist }
    public let id = UUID()
    public let subject: Subject
    public let title: String
    public let artist: String
    /// For an album sheet, its Navidrome id.
    public let albumID: String?
    let tabs: [PathTabSpec]
    public var tabID: String
    public var selected: Int?
    public private(set) var phases: [String: Phase] = [:]

    init(subject: Subject, title: String, artist: String, albumID: String?, tabs: [PathTabSpec]) {
        self.subject = subject; self.title = title; self.artist = artist; self.albumID = albumID; self.tabs = tabs
        tabID = tabs[0].id
    }

    /// An album's sheet: Neighbours by Ear only when sonic similarity is reported.
    public convenience init(albumTitle: String, artist: String, albumID: String, sonicAvailable: Bool) {
        let tabs = AlbumPathTab.available(sonic: sonicAvailable).map { t in
            PathTabSpec(
                id: t.id, label: t.label, summary: { t.summary(album: albumTitle, seeds: $0?.seeds ?? 0) },
                empty: "No \(t.fullName) path from \(albumTitle) yet. A path appears only when every step has evidence.",
                load: { lib in
                    if let kind = t.graph { return PathAnswer(album: try await lib.albumPaths(albumID: albumID, kind: kind)) }
                    return PathAnswer(album: try await lib.sonicAlbumNeighbours(albumID: albumID))
                })
        }
        self.init(subject: .album, title: albumTitle, artist: artist, albumID: albumID, tabs: tabs)
    }

    /// An artist's sheet: the five kinds. `mbid` resolves the artist's MusicBrainz id (it needs the Navidrome artist record).
    public convenience init(artistName: String, mbid: @escaping @Sendable () async throws -> String?) {
        let tabs = PathKind.allCases.map { kind in
            PathTabSpec(
                id: kind.rawValue, label: kind.label, summary: { kind.summary(artist: artistName, startType: $0?.startType ?? "") },
                empty: "No \(kind.label) path from \(artistName) yet. A path appears only when every step has evidence.",
                load: { lib in
                    guard let id = try await mbid(), !id.isEmpty else { throw DiscairError.server(status: 404, message: nil) }
                    return PathAnswer(artist: try await lib.knowledgePaths(mbid: id, type: "artist", kind: kind), kind: kind)
                })
        }
        self.init(subject: .artist, title: artistName, artist: artistName, albumID: nil, tabs: tabs)
    }

    public var tabLabels: [(id: String, label: String)] { tabs.map { ($0.id, $0.label) } }
    var tab: PathTabSpec { tabs.first { $0.id == tabID } ?? tabs[0] }
    public var tabLabel: String { tab.label }
    public var emptyText: String { answer?.empty ?? tab.empty }
    public var phase: Phase { phases[tabID] ?? .loading }
    public var answer: PathAnswer? { if case .ready(let a) = phase { a } else { nil } }
    public var summary: String { tab.summary(answer) }
    public var steps: [PathStep] { answer?.steps ?? [] }
    public var step: PathStep? { selected.flatMap { i in steps.indices.contains(i) ? steps[i] : nil } }
    public var heading: String { "Paths from \(title)" }

    public func choose(_ id: String) { tabID = id; selected = nil }
    public func move(by d: Int) {
        guard !steps.isEmpty else { return }
        selected = min(max((selected ?? (d > 0 ? -1 : steps.count)) + d, 0), steps.count - 1)
    }

    static func failure(_ error: Error, subject: Subject) -> String {
        let thing = subject == .album ? "album" : "artist"
        guard let e = error as? DiscairError else { return "Could not read this path." }
        if case .server(let status, _) = e {
            switch status {
            case 400: return "The server can't build this path for the \(thing)."
            case 404: return "This \(thing) isn't in the server's knowledge store yet."
            case 422: return "The server rejected the request."
            case 501: return "The server can't build this path yet."
            case 502: return "The server couldn't read its knowledge store. Try again later."
            default: break
            }
        }
        return AcquisitionModel.text(e)
    }

    /// Reads the chosen tab once (a read answer is kept); `retry` asks again after a failure.
    public func load(librarian: LibrarianClient?, retry: Bool = false) async {
        let id = tabID, spec = tab
        if !retry, case .ready? = phases[id] { return }
        phases[id] = .loading
        guard let librarian else { phases[id] = .failed("Paths need the server."); return }
        do {
            let answer = try await spec.load(librarian)
            phases[id] = .ready(answer)
            // The first step is selected, so the pane and the buttons are never empty.
            if tabID == id, selected == nil, !answer.steps.isEmpty { selected = 0 }
        } catch { phases[id] = .failed(Self.failure(error, subject: subject)) }
    }
}
