import AppKit
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

/// Renders the redesigned Cupertino Connections and Services in the states of `docs/design/redesign/macos/cupertino/connections--*`
/// and `settings-services--*` to PNG, to be put beside the mockups. Output goes to `DISCAIR_SCREENSHOT_DIR` (or a temp folder) as
/// `cupertino-connections-<state>.png` and `cupertino-services-<state>.png`.
@MainActor
struct ConnectionsServicesRenderTests {
    // MARK: Fixtures shaped like the mockups

    static func entity(_ id: String, _ name: String, _ type: String, owned: Bool) -> KnowledgeEntity {
        let escaped = name.replacingOccurrences(of: "\"", with: "\\\"")
        return try! JSONDecoder().decode(KnowledgeEntity.self, from: Data(#"{"mbid":"\#(id)","canonical_name":"\#(escaped)","type":"\#(type)","owned":\#(owned)}"#.utf8))
    }

    static func credit(_ relation: String, role: String? = nil, track: String? = nil) -> KnowledgeCredit {
        let r = role.map { #","role":"\#($0)""# } ?? "", t = track.map { #","track":"\#($0)""# } ?? ""
        return try! JSONDecoder().decode(KnowledgeCredit.self, from: Data(#"{"relation":"\#(relation)"\#(r)\#(t),"evidence_class":"source_explicit","match_quality":"exact_mbid","source":"musicbrainz_dump"}"#.utf8))
    }

    static let centre = entity("c", "Mark Hollis", "artist", owned: true)

    /// Sixteen step-1 nodes: seven people, seven albums, one label, one place; nine in the library.
    static var nodes: [GraphNode] {
        let producer = [credit("producer", track: "Spirit of Eden · Talk Talk · 1988"), credit("producer", track: "Laughing Stock · Talk Talk · 1991"),
                        credit("composer", track: "After the Flood · and 11 more works")]
        let rows: [(String, String, String, Bool, [KnowledgeCredit], Bool)] = [
            ("p1", "Tim Friese-Greene", "artist", false, producer, true), ("p2", "Phill Brown", "artist", false, [credit("engineer", track: "Spirit of Eden · Talk Talk")], true),
            ("p3", "Lee Harris", "artist", true, [credit("instrument", role: "drums", track: "5 albums")], true),
            ("p4", "Paul Webb", "artist", true, [credit("instrument", role: "bass", track: "3 albums")], true),
            ("p5", "Danny Thompson", "artist", true, [credit("instrument", role: "double bass", track: "Spirit of Eden")], true),
            ("p6", "Mark Feltham", "artist", false, [credit("instrument", role: "harmonica", track: "3 albums")], true),
            ("p7", "Pentangle", "group", false, [credit("member_of")], false),
            ("a1", "Herd of Instinct", "release", false, [credit("vocal", role: "lead vocals")], true), ("a2", "Smiling & Waving", "release", false, [credit("producer")], false),
            ("a3", "Mark Hollis", "release", true, [credit("vocal", role: "lead vocals")], true), ("a4", "The Colour of Spring", "release", true, [credit("vocal", role: "lead vocals")], true),
            ("a5", "Laughing Stock", "release", true, [credit("vocal", role: "lead vocals")], true), ("a6", "Spirit of Eden", "release", true, [credit("vocal", role: "lead vocals")], true),
            ("a7", "Out of Season", "release", true, [credit("vocal", role: "lead vocals")], true),
            ("l1", "Verve", "label", false, [credit("publisher")], true), ("z1", "Wessex Studios", "place", false, [credit("recording location")], true),
        ]
        return rows.map { GraphNode(entity: entity($0.0, $0.1, $0.2, owned: $0.3), depth: 1, via: "c", credit: $0.5, evidence: $0.4) }
    }

    func render<V: View>(_ view: V, name: String, width: CGFloat, height: CGFloat, settle: Double = 0.8) throws {
        RenderMode.offscreenScreenshot = true
        let size = NSSize(width: width, height: height)
        let host = NSHostingView(rootView: view.frame(width: width, height: height).environment(\.colorScheme, .light))
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(settle))
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
        try png.write(to: dir.appendingPathComponent("cupertino-\(name).png"))
    }

    // MARK: Connections

    private func connections(_ tweak: (AppState) -> Void) -> AppState {
        let state = AppState(themeID: .cupertino, screen: .connections)
        state.graph.depth = 2
        state.graph.creditsOnly = false
        tweak(state)
        return state
    }

    private func window(_ state: AppState, name: String, height: CGFloat = 832) throws {
        try render(RootView(state: state), name: name, width: 1280, height: height)
    }

    @Test func rendersGraph() throws {
        let s = connections { $0.graph.preview(centre: Self.centre, nodes: Self.nodes, more: true) }
        try window(s, name: "connections-graph")
    }

    @Test func rendersGraphSelected() throws {
        let s = connections { $0.graph.preview(centre: Self.centre, nodes: Self.nodes, more: true); $0.graph.selectedID = "p1" }
        try window(s, name: "connections-graph-selected")
    }

    @Test func rendersList() throws {
        let s = connections { $0.graph.preview(centre: Self.centre, nodes: Self.nodes, more: true); $0.graph.selectedID = "p1"; $0.graph.showsList = true }
        try window(s, name: "connections-list", height: 1100)
    }

    @Test func rendersEmpty() throws {
        try window(connections { _ in }, name: "connections-empty", height: 700)
    }

    @Test func rendersNotLoaded() throws {
        try window(connections { $0.graph.previewNotLoaded(name: "Bark Psychosis", requested: true) }, name: "connections-not-loaded", height: 700)
        try window(connections { $0.graph.previewNotLoaded(name: "Bark Psychosis", requested: false) }, name: "connections-not-loaded-request", height: 700)
    }

    @Test func rendersTruncatedAndFailed() throws {
        let failure = GraphExplorerModel.LoadFailure(summary: "Librarian did not answer in time.", wasLoadMore: true)
        let s = connections { $0.graph.preview(centre: Self.centre, nodes: Self.nodes, truncated: "rows", failure: failure, more: true, depth: 3) }
        try window(s, name: "connections-truncated-error", height: 900)
    }

    // MARK: Services

    static let now = ServicesModelTests.now
    static func history(_ rows: [ServicesModel.ServiceID: (word: String, since: Date, good: Date?)]) -> ServicesModel.History {
        ServicesModel.History(entries: rows.mapValues { .init(word: $0.word, since: $0.since, lastGood: $0.good) })
    }

    private func services(_ model: ServicesModel, open: Set<ServicesModel.ServiceID>, name: String, height: CGFloat) throws {
        let state = AppState(themeID: .cupertino, screen: .settings)
        state.services.preview(model, expanded: open)
        try window(state, name: "services-\(name)", height: height)
    }

    @Test func rendersServicesHealthy() throws {
        let m = ServicesModelTests.healthy { $0.share = .off }
        try services(m, open: [.librarian], name: "healthy", height: 2000)
    }

    @Test func rendersServicesDegraded() throws {
        let day = Self.now.addingTimeInterval(-2 * 86_400)
        let m = ServicesModelTests.healthy {
            $0.tests[.listenbrainz] = ServiceTestResult(ok: false, status: "authentication_failed", message: "")
            $0.discogsSettings = DiscogsSettings(tokenConfigured: false); $0.tests[.discogs] = nil; $0.share = .off
            $0.history = Self.history([.listenbrainz: ("Connected", day, day)])
        }
        try services(m, open: [.listenbrainz], name: "degraded", height: 2200)
    }

    @Test func rendersServicesLibrarianUnreachable() throws {
        let m = ServicesModelTests.healthy {
            $0.librarianReachable = false; $0.tailscaleHint = true; $0.sonicAvailable = true; $0.share = .off
            $0.history = Self.history([.librarian: ("No answer", Self.now.addingTimeInterval(-3_600), nil)])
        }
        try services(m, open: [], name: "librarian-unreachable", height: 1700)
    }

    @Test func rendersEditSheet() throws {
        let state = AppState(themeID: .cupertino, screen: .settings)
        state.services.preview(ServicesModelTests.healthy())
        state.services.startEditing(.slskd)
        state.services.editNotice = ServicesController.notice(for: ServiceTestResult(ok: true, status: "connected"), name: "slskd", noun: "Key")
        try render(ServiceEditSheet(state: state, id: .slskd), name: "services-edit-sheet", width: 440, height: 560)
    }

    @Test func rendersStatusPopover() throws {
        let day = Self.now.addingTimeInterval(-2 * 86_400)
        let m = ServicesModelTests.healthy {
            $0.tests[.listenbrainz] = ServiceTestResult(ok: false, status: "authentication_failed", message: "")
            $0.discogsSettings = DiscogsSettings(tokenConfigured: false); $0.tests[.discogs] = nil
            $0.history = Self.history([.listenbrainz: ("Connected", day, day)])
        }
        let state = AppState(themeID: .cupertino, screen: .home)
        state.services.preview(m)
        try render(CupertinoServicesPopover(state: state, close: {}), name: "services-popover", width: 340, height: 420)
    }
}
