import AppKit
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

/// Renders the Paths sheet in the states of `docs/design/macos-paths-booklet/pages/mockups.html` (`paths-crew` Day and Night,
/// `paths-gaps`, `paths-sonic`, `paths-failed`, `paths-artist-sideman`, plus `paths-room`, `paths-loading`, `paths-empty` and
/// `paths-min`) to PNG, to be put beside the PNGs of the mockups. Output goes to `DISCAIR_SCREENSHOT_DIR` (or a temp folder) as
/// `cupertino-paths-<state>.png`. Each state first checks the inputs that make it that state, so a render cannot pass while
/// showing a different state. No server is asked: the answers are decoded from JSON written here.
@MainActor
struct PathsRenderTests {
    // MARK: Fixtures

    private static func entity(_ name: String, _ type: String, owned: Bool = false) -> String {
        #"{"mbid":"\#(name)-id","canonical_name":"\#(name)","type":"\#(type)","owned":\#(owned)}"#
    }

    private static func reason(_ code: String, via: (String, String), anchor: (String, String), relation: String? = nil) -> String {
        let evidence = relation.map { #","evidence":[{"relation":"\#($0)","evidence_class":"source_explicit","match_quality":"exact_mbid","source":"musicbrainz_dump"}]"# } ?? ""
        return #"{"code":"\#(code)","text":"why","via":\#(entity(via.0, via.1)),"anchor":\#(entity(anchor.0, anchor.1))\#(evidence)}"#
    }

    private static func stop(_ name: String, type: String = "release", owned: Bool, by: String = "", play: String? = nil, album: String? = nil, reasons: [String]) -> String {
        var presentation: [String] = []
        if !by.isEmpty { presentation.append(#""album_artist":"\#(by)""#) }
        if let album { presentation.append(#""album":"\#(album)","artist":"\#(by)""#) }
        let playJSON = play.map { #","play":{"text":"\#($0)"}"# } ?? ""
        return #"{"entity":\#(entity(name, type, owned: owned)),"presentation":{\#(presentation.joined(separator: ","))},"reasons":[\#(reasons.joined(separator: ","))]\#(playJSON)}"#
    }

    private static func paths(_ stops: [String], kind: String, startType: String = "release", start: String = "Round About Midnight", extra: String = "") throws -> KnowledgePaths {
        let json = #"{"kind":"\#(kind)","status":"ok","start":\#(entity(start, startType, owned: true)),\#(extra)"stops":[\#(stops.joined(separator: ","))]}"#
        return try JSONDecoder().decode(KnowledgePaths.self, from: Data(json.utf8))
    }

    private static let midnight = ("Round About Midnight", "release")

    private static func crew() throws -> PathAnswer {
        let producer = { (name: String) in reason("crew_on", via: ("George Avakian", "artist"), anchor: midnight, relation: "producer") + "," + reason("crew_on", via: ("George Avakian", "artist"), anchor: (name, "release"), relation: "producer") }
        let stops = [
            stop("Ellington at Newport", owned: false, by: "Duke Ellington", reasons: [producer("Ellington at Newport")]),
            stop("Time Out", owned: false, by: "The Dave Brubeck Quartet", reasons: [producer("Time Out")]),
            stop("Mingus Ah Um", owned: false, by: "Charles Mingus", reasons: [producer("Mingus Ah Um")]),
            stop("Kind of Blue", owned: true, by: "Miles Davis", reasons: [producer("Kind of Blue")]),
            stop("Sketches of Spain", owned: true, by: "Miles Davis",
                 reasons: [reason("crew_on", via: ("Teo Macero", "artist"), anchor: midnight, relation: "producer")]),
        ]
        return PathAnswer(album: try paths(stops, kind: "album_crew"))
    }

    private static func gaps() throws -> PathAnswer {
        let teo = reason("crew_on", via: ("Teo Macero", "artist"), anchor: midnight, relation: "producer")
        return PathAnswer(album: try paths([
            stop("Sketches of Spain", owned: true, by: "Miles Davis", play: "Not played", reasons: [teo]),
            stop("Someday My Prince Will Come", owned: true, by: "Miles Davis", play: "Played once", reasons: [teo]),
        ], kind: "album_gaps"))
    }

    private static func room() throws -> PathAnswer {
        let studio = { (other: String) in reason("recorded_at", via: ("Columbia 30th Street Studio", "place"), anchor: ("Round Midnight", "recording")) + "," + reason("recorded_at", via: ("Columbia 30th Street Studio", "place"), anchor: (other, "recording")) }
        return PathAnswer(album: try paths([
            stop("Kind of Blue", owned: true, by: "Miles Davis", reasons: [studio("Freddie Freeloader")]),
            stop("Time Out", owned: false, by: "The Dave Brubeck Quartet", reasons: [studio("Take Five")]),
            stop("Mingus Ah Um", owned: false, by: "Charles Mingus", reasons: [studio("Goodbye Pork Pie Hat")]),
        ], kind: "album_room"))
    }

    private static func sonic() throws -> PathAnswer {
        func neighbour(_ id: Int, _ album: String, _ artist: String, _ year: Int, _ matches: Int) -> String {
            #"{"album_id":"n\#(id)","album":"\#(album)","artist":"\#(artist)","year":\#(year),"owned":true,"match_count":\#(matches),"reasons":[{"text":"Sounds like it."}]}"#
        }
        let seeds = (1...8).map { #"{"navidrome_id":"s\#($0)","title":"Track \#($0)"}"# }.joined(separator: ",")
        let json = #"{"status":"ok","start":{"album":"Round About Midnight","album_id":"a1","artist":"Miles Davis","tracks":8,"year":1957},"seeds":[\#(seeds)],"skipped":[{"navidrome_id":"s9","title":"Track 9","reason":"no_analysis"}],"stops":[\#([neighbour(1, "Kind of Blue", "Miles Davis", 1959, 5), neighbour(2, "Workin'", "The Miles Davis Quintet", 1960, 4), neighbour(3, "Blue Train", "John Coltrane", 1958, 3), neighbour(4, "Soultrane", "John Coltrane", 1958, 2), neighbour(5, "Bags' Groove", "Miles Davis", 1957, 2)].joined(separator: ","))]}"#
        return PathAnswer(album: try JSONDecoder().decode(SonicAlbumNeighbours.self, from: Data(json.utf8)))
    }

    private static func sideman() throws -> PathAnswer {
        func led(_ artist: String, owned: Bool, record: String) -> String {
            stop(artist, type: "artist", owned: owned, reasons: [reason("sideman_on", via: (record, "release"), anchor: ("So What", "recording"), relation: "instrument")])
        }
        return PathAnswer(artist: try paths([
            led("Cannonball Adderley", owned: false, record: "Somethin' Else"),
            led("John Coltrane", owned: true, record: "Bags' Groove"),
            led("Milt Jackson", owned: false, record: "Bags' Groove"),
        ], kind: "sideman_to_leader", startType: "artist", start: "Miles Davis"), kind: .sidemanToLeader)
    }

    // MARK: States

    enum Scenario { case crew, gaps, room, sonic, failed, loading, empty, sideman }

    private func model(_ scenario: Scenario) throws -> PathsSheetModel {
        switch scenario {
        case .sideman:
            let m = PathsSheetModel(artistName: "Miles Davis", mbid: { nil })
            m.choose(PathKind.sidemanToLeader.rawValue)
            m.receive(try Self.sideman(), for: PathKind.sidemanToLeader.rawValue)
            return m
        default:
            let m = PathsSheetModel(albumTitle: "Round About Midnight", artist: "Miles Davis", albumID: "a1", year: 1957, sonicAvailable: true)
            m.receive(try Self.crew(), for: AlbumPathTab.studioCrew.id)   // the Crew tab's count shows beside its name
            func show(_ tab: AlbumPathTab, _ answer: PathAnswer) { m.choose(tab.id); m.receive(answer, for: tab.id) }
            switch scenario {
            case .crew, .sideman: m.choose(AlbumPathTab.studioCrew.id)
            case .gaps: show(.listenThroughGaps, try Self.gaps())
            case .room: show(.sameRoom, try Self.room())
            case .sonic: show(.neighboursByEar, try Self.sonic())
            case .failed: m.showForPreview(failed: AlbumPathTab.studioCrew.id)
            case .loading: m.choose(AlbumPathTab.studioCrew.id); m.clearForPreview(AlbumPathTab.studioCrew.id)
            case .empty:
                show(.guestList, PathAnswer(album: try Self.paths([], kind: "album_guests")))
            }
            return m
        }
    }

    /// What makes each scenario the state its mockup shows.
    private func check(_ scenario: Scenario, _ m: PathsSheetModel) {
        switch scenario {
        case .crew:
            #expect(m.tabID == AlbumPathTab.studioCrew.id && m.groups.count == 2 && m.groups[0].link == PathLink(name: "George Avakian", kind: "producer credit"))
            #expect(m.offersFilter && m.step?.name == "Ellington at Newport" && m.step?.owned == false)
        case .gaps:
            #expect(m.tabID == AlbumPathTab.listenThroughGaps.id && m.steps.map(\.play) == ["Not played", "Played once"] && m.steps.allSatisfy(\.owned))
            #expect(!m.offersFilter)
        case .room:
            #expect(m.tabID == AlbumPathTab.sameRoom.id && m.groups.first?.link?.kind == "recorded at" && m.steps.count == 3)
        case .sonic:
            #expect(m.tabID == AlbumPathTab.neighboursByEar.id && m.steps.count == 5 && m.answer?.seeds == 8)
            #expect(!m.groups.contains { $0.link != nil } && !m.offersFilter && m.looseNotes == ["1 track has no sound analysis and was skipped."])
        case .failed:
            if case .failed(let text) = m.phase { #expect(text == "This album isn't in the server's knowledge store yet.") } else { Issue.record("expected the failed phase, got \(m.phase)") }
            #expect(m.notInStore.contains(m.tabID))
        case .loading:
            #expect(m.phase == .loading)
        case .empty:
            #expect(m.tabID == AlbumPathTab.guestList.id && m.answer?.steps.isEmpty == true && m.count(for: m.tabID) == 0)
        case .sideman:
            #expect(m.subject == .artist && m.groups.count == 2 && m.groups[0].link == PathLink(name: "Somethin' Else", kind: "a record they led"))
            #expect(m.steps.allSatisfy { if case .artist? = $0.target { true } else { false } } && m.step?.cover == nil && m.step?.target == .artist(name: "Cannonball Adderley"))
        }
    }

    private func render(_ scenario: Scenario, name: String, night: Bool = false, size: CGSize = CGSize(width: 1040, height: 680)) throws {
        RenderMode.offscreenScreenshot = true
        // `CU` reads the palette global, not the colour scheme, so Night is set here and put back after the render.
        let saved = CUPalette.current
        CUPalette.current = night ? .night : .day
        defer { CUPalette.current = saved }
        let m = try model(scenario)
        check(scenario, m)
        let state = AppState(themeID: .cupertino, screen: .home)
        state.paths = m
        let view = PathsSheet(state: state, model: m).frame(width: size.width, height: size.height).background(CU.content)
            .environment(\.colorScheme, night ? .dark : .light)
        let host = NSHostingView(rootView: view)
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(1.0))
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let png = try #require(rep.representation(using: .png, properties: [:]))
        var colours = Set<Int>()
        for ix in 0..<48 { for iy in 0..<48 {
            guard let c = rep.colorAt(x: (rep.pixelsWide - 1) * ix / 47, y: (rep.pixelsHigh - 1) * iy / 47)?.usingColorSpace(.sRGB) else { continue }
            colours.insert(Int(c.redComponent * 15) << 8 | Int(c.greenComponent * 15) << 4 | Int(c.blueComponent * 15))
        } }
        #expect(colours.count >= 4, "render looks blank (\(colours.count) distinct colours)")
        let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try png.write(to: dir.appendingPathComponent("cupertino-paths-\(name).png"))
    }

    @Test func rendersCrew() throws { try render(.crew, name: "crew") }
    @Test func rendersCrewNight() throws { try render(.crew, name: "crew-night", night: true) }
    @Test func rendersRoom() throws { try render(.room, name: "room") }
    @Test func rendersGaps() throws { try render(.gaps, name: "gaps") }
    @Test func rendersSonic() throws { try render(.sonic, name: "sonic") }
    @Test func rendersLoading() throws { try render(.loading, name: "loading", size: CGSize(width: 1040, height: 420)) }
    @Test func rendersFailed() throws { try render(.failed, name: "failed", size: CGSize(width: 1040, height: 420)) }
    @Test func rendersEmpty() throws { try render(.empty, name: "empty", size: CGSize(width: 1040, height: 420)) }
    @Test func rendersArtistSideman() throws { try render(.sideman, name: "artist-sideman") }
    @Test func rendersMinimumSize() throws { try render(.crew, name: "min", size: CGSize(width: 820, height: 520)) }
}
