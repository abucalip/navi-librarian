import CoreGraphics
import DiscairCore
import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

private struct Stub: HTTPTransport {
    let body: Data
    var status = 200
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        (body, HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
    }
}

private func client(_ body: Data, status: Int = 200) throws -> LibrarianClient {
    try LibrarianClient(baseURL: URL(string: "https://lib.example.ts.net")!, credential: Credential(username: "owner", password: "s3cret-pw-1234"),
                        transport: Stub(body: body, status: status))
}

// MARK: Connections: wording and model state (M9)

@MainActor @Suite("Connections screen model") struct ConnectionsScreenModelTests {
    typealias R = ConnectionsServicesRenderTests

    private func loaded(more: Bool = false, truncated: String? = nil, failure: GraphExplorerModel.LoadFailure? = nil) -> GraphExplorerModel {
        let m = GraphExplorerModel()
        m.preview(centre: R.centre, nodes: R.nodes, truncated: truncated, failure: failure, more: more)
        return m
    }

    @Test func sourceLineIsWordsNotCodes() {
        #expect(GraphWording.sourceLine(source: "musicbrainz_dump", matchQuality: "exact_mbid") == "Source: MusicBrainz · exact match")
        #expect(GraphWording.sourceLine(source: "musicbrainz", matchQuality: "fuzzy_confirmed") == "Source: MusicBrainz · name match, confirmed")
        // A code with no words falls back to the capitalised code, never to a raw one.
        #expect(GraphWording.sourceLine(source: "new_source", matchQuality: "brand_new") == "Source: New source · brand new")
    }

    @Test func kindWordsNameTheKind() {
        #expect(GraphWording.kindWord("artist") == "Person" && GraphWording.kindWord("group") == "Person")
        #expect(GraphWording.kindWord("release") == "Album" && GraphWording.kindWord("release_group") == "Album")
        #expect(GraphWording.kindWord("label") == "Label" && GraphWording.kindWord("area") == "Place")
        #expect(GraphWording.kindWord("recording") == "Recording")
    }

    @Test func kindsTitlesArePlural() {
        #expect(GraphSector.people.kindsTitle == "People" && GraphSector.albums.kindsTitle == "Albums")
        #expect(GraphSector.place.kindsTitle == "Places" && GraphSector.label.kindsTitle == "Labels")
    }

    @Test func summaryCountsWhatIsRead() {
        let m = loaded()
        #expect(m.summaryLine == "16 connections within 1 step · 8 in your library")
        #expect(m.sectorCounts[.people] == 7 && m.sectorCounts[.albums] == 7)
        let empty = GraphExplorerModel()
        #expect(empty.summaryLine == "0 connections within 1 step · 0 in your library")
    }

    @Test func footerNeverInventsATotal() {
        #expect(loaded().footerCount == "16 connections")
        #expect(loaded(more: true).footerCount == "16 connections so far")
        #expect(loaded(more: true, truncated: "rows").footerCount == "16 of 16+ connections")
    }

    @Test func truncatedNoticeNamesTheServerLimits() throws {
        #expect(loaded().truncatedNotice == nil)
        let n = try #require(loaded(truncated: "time").truncatedNotice)
        #expect(n.lead == "Showing the first 16 connections.")
        #expect(n.message.contains("200 rows or 2 seconds") && n.message.contains("Credits only") && n.message.contains("List"))
    }

    @Test func alsoOnListsOwnedAlbumsNextToANode() {
        let m = GraphExplorerModel()
        let person = R.nodes.first { $0.id == "p3" }!
        let ownedAlbum = GraphNode(entity: R.entity("a9", "Owned Album", "release", owned: true), depth: 2, via: "p3", credit: true, evidence: [])
        let unowned = GraphNode(entity: R.entity("a8", "Other Album", "release", owned: false), depth: 2, via: "p3", credit: true, evidence: [])
        m.preview(centre: R.centre, nodes: [person, ownedAlbum, unowned])
        #expect(m.alsoOnInLibrary(person).map(\.id) == ["a9"])
        #expect(m.parentName(of: ownedAlbum) == "Lee Harris")
        #expect(m.parentName(of: person) == "Mark Hollis")
    }

    @Test func notLoadedStateAsksOnceAndThenSaysRequested() {
        let m = GraphExplorerModel()
        m.previewNotLoaded(name: "Bark Psychosis", requested: false)
        #expect(m.startName == "Bark Psychosis" && m.canRequestUpdate && !m.updateRequested && m.nodes.isEmpty)
        m.previewNotLoaded(name: "Bark Psychosis", requested: true)
        #expect(!m.canRequestUpdate && m.updateRequested)
    }

    @Test func aFailedReadKeepsWhatIsDrawnAndRetryRepeatsIt() async throws {
        let m = loaded(more: true)
        // Load more fails: the nodes stay, the failure says it was a load more, and Try again repeats a load more.
        await m.loadMore(librarian: try client(Data("{}".utf8), status: 503))
        #expect(m.nodes.count == 16 && m.loadFailure?.wasLoadMore == true)
        #expect(m.loadFailure?.summary.isEmpty == false)
        let body = #"{"start":{"mbid":"c","canonical_name":"Mark Hollis","type":"artist","owned":true},"hops":[],"next_cursor":null,"truncated":null,"sources":{}}"#
        await m.retry(librarian: try client(Data(body.utf8)))
        #expect(m.loadFailure == nil && m.nodes.count == 16)
    }

    @Test func aFailedFirstReadClearsTheNodesAndRetryReloads() async throws {
        let m = loaded()
        await m.reload(librarian: try client(Data("{}".utf8), status: 503))
        #expect(m.nodes.isEmpty && m.loadFailure?.wasLoadMore == false)
    }

    @Test func zineKeepsItsOwnLayout() {
        #expect(GraphStyle.cupertino.redesigned && !GraphStyle.zine.redesigned)
        // The classic layout the Zine explorer draws is untouched.
        let items = (0..<4).map { GraphLayout.Item(id: "n\($0)", depth: 1, via: "c") }
        let p = GraphLayout.place(centre: "c", items: items)
        for i in items { let q = p[i.id]!; #expect(abs(hypot(q.x, q.y) - 1) < 1e-9) }
    }

    @Test func evidenceCardsSayWhatTheCreditIsOn() {
        let node = R.nodes.first { $0.id == "p1" }!
        #expect(CupertinoConnections.whatItIsOn(node.evidence[0], node: node, parent: "Mark Hollis") == "Spirit of Eden · Talk Talk · 1988")
        let bare = R.credit("producer")
        #expect(CupertinoConnections.whatItIsOn(bare, node: node, parent: "Mark Hollis") == "With Mark Hollis")
        #expect(CupertinoConnections.accessibilityName(node) == "Tim Friese-Greene, Person, 1 step, not in your library, credit")
    }

    @Test func labelsSitOnTheOuterSideOfTheirNode() {
        let p = CGPoint(x: 300, y: 200)
        let right = CupertinoConnections.labelCentre(for: p, angle: 0, size: 48)
        #expect(right.x > p.x + 24 && right.y == p.y)
        let left = CupertinoConnections.labelCentre(for: p, angle: .pi, size: 48)
        #expect(left.x < p.x - 24 && left.y == p.y)
        let top = CupertinoConnections.labelCentre(for: p, angle: -.pi / 2, size: 48)
        #expect(top.y < p.y && top.x == p.x)
        let bottom = CupertinoConnections.labelCentre(for: p, angle: .pi / 2, size: 48)
        #expect(bottom.y > p.y)
    }
}

// MARK: Services: controller, spec and helpers (M9)

@MainActor @Suite("Services screen") struct ServicesScreenTests {
    private func defaults() -> UserDefaults { UserDefaults(suiteName: "discair-services-test-\(UUID().uuidString)")! }

    @Test func firstResultOpensTheRowThatNeedsTheOwner() {
        let c = ServicesController(defaults: defaults())
        #expect(c.expanded.isEmpty && !c.hasChecked)
        var bad = ServicesModel.Inputs()
        bad.librarianReachable = true; bad.navidromeCheck = .ok
        bad.listenBrainzSettings = ListenBrainzSettings(username: "abc", tokenConfigured: true)
        bad.tests = [.listenbrainz: ServiceTestResult(ok: false, status: "authentication_failed")]
        c.finish(bad)
        #expect(c.hasChecked && !c.checking)
        #expect(c.expanded == [.listenbrainz])
    }

    @Test func aHealthyFirstResultOpensTheLibrarian() {
        let c = ServicesController(defaults: defaults())
        var i = ServicesModel.Inputs(); i.librarianReachable = true; i.navidromeCheck = .ok
        c.finish(i)
        #expect(c.expanded == [.librarian])
    }

    @Test func historySurvivesARelaunch() {
        let d = defaults()
        let c = ServicesController(defaults: d)
        var i = ServicesModel.Inputs(now: Date(timeIntervalSince1970: 1_794_427_200)); i.librarianReachable = true; i.navidromeCheck = .ok
        c.finish(i)
        let again = ServicesController(defaults: d)
        #expect(again.inputs.history.entries[.navidrome]?.word == "Connected")
        #expect(again.inputs.history.entries[.navidrome]?.lastGood == Date(timeIntervalSince1970: 1_794_427_200))
    }

    @Test func recordingATestUpdatesOneRowAndKeepsTheRest() {
        let c = ServicesController(defaults: defaults())
        var i = ServicesModel.Inputs(); i.librarianReachable = true; i.navidromeCheck = .ok
        i.slskdSettings = SlskdSettings(url: "http://nas:5030", apiKeyConfigured: true)
        c.finish(i)
        #expect(c.model.row(.slskd)?.state == .unknown)      // configured and not tested is not known to work
        c.record(test: ServiceTestResult(ok: true, status: "connected"), for: .slskd)
        #expect(c.model.row(.slskd)?.state == .connected && c.model.row(.navidrome)?.state == .connected)
    }

    @Test func editingStartsFromWhatTheServerHolds() {
        let c = ServicesController(defaults: defaults())
        var i = ServicesModel.Inputs(); i.librarianReachable = true
        i.slskdSettings = SlskdSettings(url: "http://nas:5030", apiKeyConfigured: true, downloadsPath: "/downloads", musicLibraryPath: "/music")
        i.lastFMSettings = LastFMSettings(apiKeyConfigured: true, username: "abc")
        c.finish(i)
        c.startEditing(.slskd)
        #expect(c.editing == .slskd && c.draft.address == "http://nas:5030" && c.draft.downloadsPath == "/downloads" && c.draft.libraryPath == "/music")
        #expect(c.draft.secret.isEmpty)                      // a secret is never held, so its field starts empty
        c.startEditing(.lastfm)
        #expect(c.draft.username == "abc" && c.draft.address.isEmpty)
        c.stopEditing()
        #expect(c.editing == nil && c.draft == ServiceDraft())
    }

    @Test func theSheetHasTheFieldsOfEachService() {
        #expect(ServiceEditSpec.fields(.slskd).map(\.label) == ["Address", "API key", "Folder slskd downloads into", "Music library folder"])
        #expect(ServiceEditSpec.fields(.lastfm).map(\.label) == ["Username", "API key"])
        #expect(ServiceEditSpec.fields(.discogs).map(\.label) == ["Token"])
        #expect(ServiceEditSpec.fields(.slskd).filter(\.secure).map(\.key) == [.secret])
        #expect(ServiceEditSpec.canEdit(.navidrome) && !ServiceEditSpec.canEdit(.musicbrainz) && !ServiceEditSpec.canEdit(.sonic))
        // The Librarian address and the music folder live elsewhere in Settings.
        #expect(ServiceEditSpec.settingsTab(for: .librarian) == .profiles && ServiceEditSpec.settingsTab(for: .smb) == .musicFolder)
        #expect(ServiceEditSpec.settingsTab(for: .slskd) == nil)
    }

    @Test func onlyWhatTheRoutesCanClearCanBeDisconnected() {
        #expect(ServiceEditSpec.canDisconnect(.discogs) && ServiceEditSpec.canDisconnect(.listenbrainz))
        #expect(!ServiceEditSpec.canDisconnect(.slskd) && !ServiceEditSpec.canDisconnect(.lastfm) && !ServiceEditSpec.canDisconnect(.navidrome))
        #expect(ServiceEditSpec.disconnectLabel(.listenbrainz, name: "ListenBrainz") == "Disconnect ListenBrainz")
        #expect(ServiceEditSpec.disconnectDetail(.listenbrainz, powers: ["Taste", "Popularity"]).hasPrefix("Taste, Popularity stop updating."))
    }

    @Test func testNoticesSayWhatHappenedInWords() {
        let pass = ServicesController.notice(for: ServiceTestResult(ok: true, status: "connected"), name: "slskd", noun: "Key")
        #expect(pass == .init(kind: .success, lead: "Test passed.", message: "slskd answered and the key was accepted."))
        let rejected = ServicesController.notice(for: ServiceTestResult(ok: false, status: "authentication_failed"), name: "ListenBrainz", noun: "Token")
        #expect(rejected.kind == .danger && rejected.message == "ListenBrainz did not accept the token.")
        let silent = ServicesController.notice(for: ServiceTestResult(ok: false, status: "connection_failed"), name: "slskd", noun: "Key")
        #expect(silent.message.contains("did not answer"))
        let server = ServicesController.notice(for: ServiceTestResult(ok: false, status: "connection_failed", message: "Connection refused"), name: "slskd", noun: "Key")
        #expect(server.message == "Connection refused")
    }

    @Test func timesReadAsTodayOrADate() {
        var cal = Calendar(identifier: .gregorian); cal.timeZone = TimeZone(identifier: "UTC")!
        let now = Date(timeIntervalSince1970: 1_794_427_200 + 3_600)       // 2026-11-11 21:00 UTC
        #expect(ServicesFormat.when(now.addingTimeInterval(-60), now: now, calendar: cal) == "Today, 20:59")
        #expect(ServicesFormat.when(now.addingTimeInterval(-2 * 86_400 - 3_600), now: now, calendar: cal) == "9 November, 20:00")
        #expect(ServicesFormat.day(now.addingTimeInterval(-2 * 86_400), calendar: cal) == "9 November")
    }

    @Test func addressesLoseTheirSchemeAndPortInTheDiagram() {
        #expect(ServicesFormat.bareAddress("http://100.92.14.7:8080") == "100.92.14.7")
        #expect(ServicesFormat.bareAddress("https://lib.example.ts.net/") == "lib.example.ts.net")
        #expect(ServicesFormat.bareAddress("192.168.1.87:4533") == "192.168.1.87")
    }

    @Test func tailscaleAddressesAreRecognised() {
        #expect(AppState.looksLikeTailscale(URL(string: "http://100.92.14.7:8080")!))
        #expect(AppState.looksLikeTailscale(URL(string: "https://lib.example.ts.net")!))
        #expect(!AppState.looksLikeTailscale(URL(string: "http://192.168.1.87:8686")!))
        #expect(!AppState.looksLikeTailscale(URL(string: "http://100.10.0.1")!))          // outside 100.64.0.0/10
        #expect(AppState.addressText(URL(string: "http://100.92.14.7:8080")!) == "100.92.14.7:8080")
        #expect(AppState.addressText(URL(string: "https://lib.example.ts.net")!) == "lib.example.ts.net")
    }

    @Test func fixServiceOpensTheRightPlace() {
        let state = AppState(themeID: .cupertino, screen: .home)
        state.fixService(.slskd)
        #expect(state.screen == .settings && state.settingsTab == .services)
        #expect(state.services.expanded.contains(.slskd) && state.services.editing == .slskd)
        state.services.stopEditing()
        state.fixService(.librarian)
        #expect(state.settingsTab == .profiles && state.services.editing == nil)
        state.fixService(.smb)
        #expect(state.settingsTab == .musicFolder)
    }

    @Test func toolbarWordsComeFromTheModel() {
        let state = AppState(themeID: .cupertino, screen: .home)
        #expect(state.services.model.toolbar.text == "Checking…")
        state.services.preview(ServicesModelTests.healthy())
        #expect(state.services.model.toolbar.text == "All working" && state.services.hasChecked)
    }

    @Test func settingsTabsAreTheFourOfTheMockups() {
        #expect(SettingsTab.allCases.map(\.rawValue) == ["Services", "Playback", "Music folder", "Profiles"])
        #expect(AppState(themeID: .cupertino, screen: .settings).settingsTab == .services)
    }
}
