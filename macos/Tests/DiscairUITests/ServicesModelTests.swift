import Foundation
import Testing
import DiscairLibrarian
@testable import DiscairUI

@Suite("Services model") struct ServicesModelTests {
    typealias M = ServicesModel
    static let now = Date(timeIntervalSince1970: 1_794_427_200)   // 2026-11-11 20:00 UTC
    static var cal: Calendar { var c = Calendar(identifier: .gregorian); c.timeZone = TimeZone(identifier: "UTC")!; return c }
    static let ok = ServiceTestResult(ok: true, status: "connected")

    /// Everything configured and every test passing.
    static func healthy(_ tweak: (inout M.Inputs) -> Void = { _ in }) -> M {
        var i = M.Inputs(librarianReachable: true, librarianAddress: "100.92.14.7:8080", navidromeCheck: .ok,
                         navidromeSettings: NavidromeSettings(url: "http://192.168.1.87:4533", username: "the-owner", passwordConfigured: true),
                         slskdSettings: SlskdSettings(url: "http://nas:5030", apiKeyConfigured: true),
                         lastFMSettings: LastFMSettings(apiKeyConfigured: true, username: "abc"),
                         listenBrainzSettings: ListenBrainzSettings(username: "abc", tokenConfigured: true),
                         discogsSettings: DiscogsSettings(tokenConfigured: true, source: "settings"),
                         tests: [.slskd: ok, .lastfm: ok, .listenbrainz: ok, .discogs: ok],
                         capabilities: ServerCapabilities(graphCoverage: "broad", sonicAvailable: true, listenBrainzConnected: true),
                         share: .mounted, shareAddress: "smb://nas/media", now: now, calendar: cal)
        tweak(&i)
        return M.build(i)
    }

    // MARK: Healthy

    @Test func healthyIsEverythingWorking() {
        let m = Self.healthy()
        #expect(m.summary.title == "Everything is working" && m.summary.tone == .success)
        #expect(m.toolbar == M.Toolbar(kind: .ok, text: "All working"))
        #expect(m.attention.isEmpty)
        #expect(m.row(.musicbrainz)?.state.word == "Loaded · broad")
        #expect(m.row(.sonic)?.state.word == "Available")
        #expect(m.row(.librarian)?.state.word == "Connected")
    }

    @Test func rowsFollowTheMockupGroups() {
        let m = Self.healthy()
        #expect(m.rows(in: .core).map(\.id) == [.librarian, .navidrome])
        #expect(m.rows(in: .gettingMusic).map(\.id) == [.slskd])
        #expect(m.rows(in: .listeningHistory).map(\.id) == [.lastfm, .listenbrainz])
        #expect(m.rows(in: .knowledge).map(\.id) == [.musicbrainz, .sonic, .discogs])
        #expect(m.rows(in: .onThisMac).map(\.id) == [.smb])
        #expect(m.row(.listenbrainz)?.powers == ["Taste", "Popularity", "Lenses"])
        #expect(m.row(.librarian)?.powers == ["Home", "Discover", "Insights", "Downloads"])
    }

    @Test func healthyDiagramIsAllSolid() {
        let m = Self.healthy()
        #expect(m.edges.count == 8)
        #expect(m.edges.allSatisfy { $0.style == .working })
    }

    // MARK: One failing

    @Test func aRejectedTokenNeedsAttentionAndTheSentenceNamesWhatIsNotAffected() {
        let m = Self.healthy { $0.tests[.listenbrainz] = ServiceTestResult(ok: false, status: "authentication_failed", message: "") ; $0.discogsSettings = DiscogsSettings(tokenConfigured: false) }
        #expect(m.row(.listenbrainz)?.state == .rejected("Token"))
        #expect(m.row(.listenbrainz)?.state.word == "Token rejected")
        #expect(m.summary.title == "One service needs attention" && m.summary.tone == .warning)
        #expect(m.summary.detail == "ListenBrainz rejected the saved token. Playback, picks and Get are not affected · checked at 20:00")
        #expect(m.toolbar == M.Toolbar(kind: .attention, text: "1 needs attention"))
        #expect(m.row(.listenbrainz)?.actions == [.replace("token"), .testAgain, .disconnect])
        #expect(m.row(.listenbrainz)?.notice?.contains("did not accept the token") == true)
        // Discogs is optional: not set up, and not a problem.
        #expect(m.row(.discogs)?.state == .notSetUp && m.row(.discogs)?.needsAttention == false)
        #expect(m.row(.discogs)?.actions == [.setUp])
        #expect(m.attention.map(\.id) == [.listenbrainz])
    }

    @Test func aFailingServiceDrawsItsLineDashedAndOnlyThat() {
        let m = Self.healthy { $0.tests[.listenbrainz] = ServiceTestResult(ok: false, status: "authentication_failed"); $0.discogsSettings = DiscogsSettings(tokenConfigured: false) }
        func style(_ to: String) -> M.EdgeStyle { m.edges.first { $0.from == "librarian" && $0.to == to }!.style }
        #expect(style("listenbrainz") == .failing)
        #expect(style("discogs") == .dim)
        #expect(style("lastfm") == .working && style("slskd") == .working && style("musicbrainz") == .working)
        #expect(m.edges.first { $0.from == "librarian" && $0.to == "navidrome" }?.style == .working)
    }

    @Test func testStatusesMapToWords() {
        func state(_ status: String) -> M.State? { Self.healthy { $0.tests[.lastfm] = ServiceTestResult(ok: false, status: status) }.row(.lastfm)?.state }
        #expect(state("authentication_failed") == .rejected("Key"))
        #expect(state("connection_failed") == .noAnswer)
        #expect(state("not_configured") == .notSetUp)
        #expect(state("not_found") == .rejected("Username"))
    }

    @Test func twoFailuresAreCounted() {
        let m = Self.healthy {
            $0.tests[.lastfm] = ServiceTestResult(ok: false, status: "connection_failed")
            $0.tests[.slskd] = ServiceTestResult(ok: false, status: "connection_failed")
        }
        #expect(m.summary.title == "2 services need attention")
        #expect(m.summary.detail.hasPrefix("slskd did not answer. Last.fm also needs attention."))
        #expect(m.summary.detail.contains("Playback and picks are not affected"))   // Get needs slskd
        #expect(m.toolbar.text == "2 needs attention")
    }

    @Test func aRequiredServiceThatIsNotSetUpIsAProblem() {
        let m = Self.healthy { $0.slskdSettings = SlskdSettings(url: "", apiKeyConfigured: false); $0.tests[.slskd] = nil }
        #expect(m.row(.slskd)?.state == .notSetUp && m.row(.slskd)?.needsAttention == true)
        #expect(m.summary.title == "One service needs attention")
    }

    @Test func onlyOptionalServicesNotSetUpIsNotAProblem() {
        let m = Self.healthy { $0.discogsSettings = DiscogsSettings(tokenConfigured: false); $0.share = .off; $0.sonicAvailable = false }
        #expect(m.attention.isEmpty)
        #expect(m.toolbar == M.Toolbar(kind: .notSetUp, text: "2 not set up"))
        #expect(m.summary.title == "Everything is working")
        #expect(m.summary.detail.contains("optional and not set up"))
        #expect(m.row(.smb)?.state.word == "Off" && m.row(.smb)?.actions == [.setUp])
    }

    // MARK: Librarian down

    static func down(_ tweak: (inout M.Inputs) -> Void = { _ in }) -> M {
        var history = M.History()
        history.entries[.librarian] = .init(word: "No answer", since: Date(timeIntervalSince1970: 1_794_427_200 - 3720), lastGood: nil)   // 18:58
        return healthy {
            $0.librarianReachable = false; $0.tailscaleHint = true; $0.history = history
            $0.slskdSettings = nil; $0.lastFMSettings = nil; $0.listenBrainzSettings = nil; $0.discogsSettings = nil
            $0.tests = [:]; $0.capabilities = nil; $0.sonicAvailable = true       // read from Navidrome directly
            tweak(&$0)
        }
    }

    @Test func whenTheLibrarianIsDownEverythingItReportsIsUnknownNotFailed() {
        let m = Self.down()
        for id in [M.ServiceID.slskd, .lastfm, .listenbrainz, .discogs, .musicbrainz] {
            #expect(m.row(id)?.state == .unknown, "\(id)")
            #expect(m.row(id)?.needsAttention == false)
        }
        #expect(m.row(.librarian)?.state == .noAnswer)
        #expect(m.row(.navidrome)?.state == .connected)
        #expect(m.row(.sonic)?.state == .available)
        #expect(m.row(.smb)?.state == .connected)
    }

    @Test func staleTestsAndCachedSettingsDoNotCountWhileTheLibrarianIsDown() {
        // Tests and capabilities from before the outage must not make a service look connected.
        let m = Self.down { $0.tests = [.lastfm: Self.ok]; $0.lastFMSettings = LastFMSettings(apiKeyConfigured: true); $0.capabilities = ServerCapabilities(graphCoverage: "broad") }
        #expect(m.row(.lastfm)?.state == .unknown)
        #expect(m.row(.musicbrainz)?.state == .unknown)
    }

    @Test func theUnreachableSummaryAndToolbarMatchTheMockup() {
        let m = Self.down()
        #expect(m.summary.title == "Can’t reach Librarian" && m.summary.tone == .danger)
        #expect(m.summary.detail == "No answer from 100.92.14.7:8080 since 18:58. Check that Tailscale is connected on this Mac. Your library still plays from Navidrome.")
        #expect(m.toolbar == M.Toolbar(kind: .unreachable, text: "Librarian unreachable"))
        #expect(m.row(.librarian)?.actions == [.testAgain, .editAddress])
    }

    @Test func theTailscaleSentenceNeedsTheHint() {
        #expect(!Self.down { $0.tailscaleHint = false }.summary.detail.contains("Tailscale"))
    }

    @Test func theUnreachableDiagramFailsOnlyTheMacToLibrarianLine() {
        let m = Self.down()
        #expect(m.edges.first { $0.from == "mac" && $0.to == "librarian" }?.style == .failing)
        #expect(m.edges.first { $0.from == "mac" && $0.to == "navidrome" }?.style == .working)
        #expect(m.edges.filter { $0.from == "librarian" }.allSatisfy { $0.style == .dim })
    }

    @Test func navidromeFailingDirectlyIsItsOwnProblemEvenWithTheLibrarianUp() {
        let m = Self.healthy { $0.navidromeCheck = .noAnswer }
        #expect(m.row(.navidrome)?.state == .noAnswer)
        #expect(m.summary.detail.contains("Navidrome did not answer."))
        #expect(!m.summary.detail.contains("Playback"))
        #expect(m.edges.first { $0.from == "librarian" && $0.to == "navidrome" }?.style == .failing)
    }

    // MARK: Before the first check

    @Test func beforeTheFirstCheckEverythingIsCheckingNotZero() {
        let m = M.build(M.Inputs(now: Self.now, calendar: Self.cal))
        #expect(m.toolbar == M.Toolbar(kind: .checking, text: "Checking…"))
        #expect(m.summary.title == "Checking services…")
        #expect(m.attention.isEmpty)
        #expect(m.row(.librarian)?.state == .unknown)
        #expect(m.row(.librarian)?.checked == nil)
    }

    @Test func aConfiguredServiceThatWasNotTestedIsUnknownNotConnected() {
        let m = Self.healthy { $0.tests[.lastfm] = nil }
        #expect(m.row(.lastfm)?.state == .unknown)
        #expect(m.summary.title == "Some services are not checked yet")
    }

    // MARK: MusicBrainz and Sonic

    @Test func musicBrainzCoverageStates() {
        #expect(Self.healthy { $0.capabilities = ServerCapabilities(graphCoverage: "partial") }.row(.musicbrainz)?.state.word == "Loaded · partial")
        let none = Self.healthy { $0.capabilities = ServerCapabilities(graphCoverage: "none") }.row(.musicbrainz)
        #expect(none?.state == .notLoaded && none?.state.tone == .info && none?.needsAttention == false)
    }

    @Test func sonicComesFromCapabilitiesUnlessReadDirectly() {
        #expect(Self.healthy { $0.capabilities = ServerCapabilities(sonicAvailable: false) }.row(.sonic)?.state == .notSetUp)
        #expect(Self.healthy { $0.sonicAvailable = true; $0.capabilities = ServerCapabilities(sonicAvailable: false) }.row(.sonic)?.state == .available)
    }

    // MARK: Setup column

    @Test func theSetupColumnNeverCarriesASecret() {
        let m = Self.healthy()
        let lb = m.row(.listenbrainz)!
        #expect(lb.setup == [.init(label: "Username", value: "abc"), .init(label: "Token", value: "Saved on the server, never shown"),
                             .init(label: "Used by", value: "Taste, Popularity, Lenses")])
        #expect(m.row(.navidrome)?.setup.map(\.label) == ["Address", "Username", "Password", "Used by"])
        #expect(m.row(.discogs)?.setup.first == .init(label: "Token", value: "Saved on the server, never shown"))
        #expect(Self.healthy { $0.discogsSettings = DiscogsSettings(tokenConfigured: true, source: "environment") }.row(.discogs)?.setup.first?.value.contains("environment") == true)
    }

    // MARK: Local history

    @Test func historyRecordsSinceAndLastGoodAndKeepsThemAcrossBuilds() {
        let t0 = Self.now, t1 = t0.addingTimeInterval(3600), t2 = t0.addingTimeInterval(7200)
        let first = Self.healthy { $0.now = t0 }
        #expect(first.row(.lastfm)?.since == t0 && first.row(.lastfm)?.lastGood == t0)

        let failing = Self.healthy { $0.now = t1; $0.history = first.history; $0.tests[.lastfm] = ServiceTestResult(ok: false, status: "connection_failed") }
        #expect(failing.row(.lastfm)?.since == t1)          // state changed
        #expect(failing.row(.lastfm)?.lastGood == t0)       // last time it worked

        let still = Self.healthy { $0.now = t2; $0.history = failing.history; $0.tests[.lastfm] = ServiceTestResult(ok: false, status: "connection_failed") }
        #expect(still.row(.lastfm)?.since == t1)            // unchanged state keeps its since
        #expect(still.row(.lastfm)?.lastGood == t0)
        #expect(still.row(.lastfm)?.checked == t2)
    }

    @Test func anUnknownStateChangesNothingInTheHistory() {
        let first = Self.healthy()
        let later = Self.down { $0.now = Self.now.addingTimeInterval(600); $0.history = first.history }
        #expect(later.row(.lastfm)?.state == .unknown)
        #expect(later.row(.lastfm)?.lastGood == Self.now)    // the earlier good read is kept
        #expect(later.row(.lastfm)?.since == Self.now)
    }

    @Test func historyRoundTripsThroughJSON() throws {
        let h = Self.healthy().history
        #expect(try JSONDecoder().decode(M.History.self, from: JSONEncoder().encode(h)) == h)
    }

    // MARK: Vocabulary

    @Test func everyStateHasAWordAndStatusIsNeverColourOnly() {
        let states: [M.State] = [.connected, .available, .loaded("broad"), .notLoaded, .notSetUp, .off, .unknown, .rejected("Key"), .noAnswer]
        #expect(states.map(\.word) == ["Connected", "Available", "Loaded · broad", "Not loaded", "Not set up", "Off", "Unknown", "Key rejected", "No answer"])
        #expect(states.allSatisfy { !$0.word.isEmpty })
    }
}
