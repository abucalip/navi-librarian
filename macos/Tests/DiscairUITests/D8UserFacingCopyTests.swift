import AppKit
import DiscairAudio
import DiscairLibrarian
import SwiftUI
import Testing
@testable import DiscairUI

@MainActor
@Suite("D8 user-facing copy", .serialized)
struct D8UserFacingCopyTests {

    // MARK: - D8.1 Internal source codes mapped to plain words

    @Test func provenanceLineMapsInternalCodesToPlainWords() {
        #expect(
            GraphWording.provenanceLine(
                source: "musicbrainz_dump",
                evidenceClass: "source_explicit",
                matchQuality: "exact_mbid",
                explicitLabel: "stated place"
            ) == "MusicBrainz · stated place · exact match"
        )
        #expect(
            GraphWording.provenanceLine(
                source: "musicbrainz_dump",
                evidenceClass: "source_explicit",
                matchQuality: "exact_mbid"
            ) == "MusicBrainz · stated · exact match"
        )
        #expect(
            GraphWording.provenanceLine(
                source: "wikidata",
                evidenceClass: "derived",
                matchQuality: "fuzzy_confirmed"
            ) == "Wikidata · derived · name match, confirmed"
        )
        #expect(
            GraphWording.provenanceLine(
                source: "discogs",
                evidenceClass: "library_tag",
                matchQuality: "isrc"
            ) == "Discogs · library tag · ISRC match"
        )
        // Unknown codes fall back to readable words, never raw snake_case.
        let fallback = GraphWording.provenanceLine(
            source: "custom_feed",
            evidenceClass: "manual_entry",
            matchQuality: "custom_check"
        )
        #expect(fallback == "Custom feed · manual entry · custom check")
        #expect(!fallback.contains("_"))
    }

    // MARK: - D8.2 Raw acquisition status text

    @Test func destinationExistsUsesPlainSentenceAndOffersOnlyDismiss() throws {
        let json = #"{"artist":"John Coltrane","album":"Blue Train","status":"destination_exists"}"#
        let job = try JSONDecoder().decode(Acquisition.self, from: Data(json.utf8))
        let model = AcquisitionModel()

        #expect(AcquisitionModel.statusText(job) == "Already in your library folder; nothing was copied")
        #expect(model.statusLine(job) == "Already in your library folder; nothing was copied")
        #expect(job.phase == .other)
        #expect(model.canRetry(job) == false)
        #expect(model.canSkip(job) == false)
        #expect(HomeDashboard.stage(of: job) == .importing)
    }

    @Test func knownAndUnknownAcquisitionStatusesAvoidRawTitleCase() throws {
        func status(_ code: String) throws -> String {
            let json = #"{"artist":"A","album":"B","status":"\#(code)"}"#
            let job = try JSONDecoder().decode(Acquisition.self, from: Data(json.utf8))
            return AcquisitionModel.statusText(job)
        }

        #expect(try status("download_complete_move_failed") == "Could not move download into your library")
        #expect(try status("download_complete_waiting_for_folder") == "Waiting for download folder")
        #expect(try status("review_required") == "Needs review")
        #expect(try status("brand_new_code") == "Brand new code")
    }

    // MARK: - D8.3 Connections truncated notice

    @Test func connectionsTruncatedNoticeOmitsDeveloperWording() throws {
        let m = GraphExplorerModel()
        let singleNode = [ConnectionsServicesRenderTests.nodes[0]]
        m.preview(centre: ConnectionsServicesRenderTests.centre, nodes: singleNode, truncated: "rows")
        let one = try #require(m.truncatedNotice)
        #expect(one.lead == "Showing the first 1 connection.")
        #expect(one.message == "Turn on Credits only, lower the reach, or use List to see them all.")

        let eightNodes = Array(ConnectionsServicesRenderTests.nodes.prefix(8))
        m.preview(centre: ConnectionsServicesRenderTests.centre, nodes: eightNodes, truncated: "time")
        let eight = try #require(m.truncatedNotice)
        #expect(eight.lead == "Showing the first 8 connections.")
        #expect(eight.message == "Turn on Credits only, lower the reach, or use List to see them all.")
        #expect(!eight.message.contains("200 rows"))
        #expect(!eight.message.contains("2 seconds"))
    }

    // MARK: - D8.4 Player bar title block width up to 40%

    @Test func playerBarTitleBlockAllowsUpToFortyPercentOfBarWidth() {
        #expect(CupertinoPlayerBar.titleBlockMaxWidthFraction == 0.40)
        #expect(CupertinoPlayerBar.titleBlockMaxWidth(forBarWidth: 1200) == 480)
        #expect(CupertinoPlayerBar.titleBlockMaxWidth(forBarWidth: 1000) == 400)
        // Narrow bars still respect the minimum width.
        #expect(CupertinoPlayerBar.titleBlockMaxWidth(forBarWidth: 300) == CupertinoPlayerBar.titleBlockMinWidth)
    }

    // MARK: - Offscreen renders (Day and Night)

    @Test(arguments: AppearanceMode.allCases)
    func rendersD8Views(_ mode: AppearanceMode) throws {
        // D8.1 Atlas inspector with mapped provenance line
        let atlasState = AppState(themeID: .cupertino, screen: .atlas)
        let placeJSON = #"{"entity":{"mbid":"p1","canonical_name":"Wessex Studios","type":"place"},"latitude":51.55,"longitude":-0.09,"recordings":2,"owned_recordings":1}"#
        let detailJSON = """
        {
          "place": {"mbid": "p1", "canonical_name": "Wessex Studios", "type": "place"},
          "facts": {"latitude": 51.55, "longitude": -0.09},
          "recordings": [
            {
              "recording": {"mbid": "r1", "canonical_name": "Spirit of Eden", "type": "recording"},
              "owned": true,
              "albums": [{"album": {"mbid": "rg1", "canonical_name": "Spirit of Eden", "type": "release_group"}, "owned": true}],
              "relations": [{"relation": "recorded in", "source": "musicbrainz_dump", "evidence_class": "source_explicit", "match_quality": "exact_mbid"}]
            }
          ],
          "not_loaded": []
        }
        """
        let place = try JSONDecoder().decode(AtlasPlace.self, from: Data(placeJSON.utf8))
        let detail = try JSONDecoder().decode(KnowledgePlace.self, from: Data(detailJSON.utf8))
        atlasState.atlas.preview(places: [place], detail: detail, truncated: false)
        atlasState.atlas.selectedID = "p1"
        try render(AtlasInspector(state: atlasState, style: .cupertino), size: NSSize(width: AtlasView.inspectorWidth, height: 520), mode: mode, name: "d8-atlas-inspector-\(mode)")

        // D8.2 Downloads with destination_exists row
        let dlState = AppState(themeID: .cupertino, screen: .downloads)
        let jobJSON = #"[{"artist":"John Coltrane","album":"Blue Train","status":"destination_exists","updated_at":1700000000}]"#
        let jobs = try JSONDecoder().decode([Acquisition].self, from: Data(jobJSON.utf8))
        dlState.acquisition.showJobs(jobs)
        try render(CupertinoDownloads(state: dlState), size: NSSize(width: 1080, height: 420), mode: mode, name: "d8-downloads-\(mode)")

        // D8.3 Connections with truncated notice
        let connState = AppState(themeID: .cupertino, screen: .connections)
        connState.graph.preview(centre: ConnectionsServicesRenderTests.centre, nodes: Array(ConnectionsServicesRenderTests.nodes.prefix(8)), truncated: "rows")
        try render(CupertinoConnections(state: connState), size: NSSize(width: 1100, height: 640), mode: mode, name: "d8-connections-\(mode)")

        // D8.4 Player bar with long artist + album name
        let barState = AppState(themeID: .cupertino, screen: .home)
        let track = QueueItem(
            songID: "s-aretha",
            title: "You Send Me",
            artist: "Aretha Franklin",
            album: "The Electrifying Aretha Franklin",
            albumID: "al-aretha",
            coverArt: nil,
            duration: 147,
            suffix: "mp3",
            quality: "MP3 320"
        )
        barState.player.play([track], startAt: 0)
        barState.player.phase = .paused
        try render(CupertinoPlayerBar(state: barState), size: NSSize(width: 1460, height: CupertinoPlayerBar.height), mode: mode, name: "d8-player-bar-\(mode)")
    }

    private func render<V: View>(_ view: V, size: NSSize, mode: AppearanceMode, name: String) throws {
        RenderMode.offscreenScreenshot = true
        let saved = CUPalette.current
        CUPalette.current = mode == .night ? .night : .day
        defer { CUPalette.current = saved }

        let host = NSHostingView(
            rootView: view
                .frame(width: size.width, height: size.height)
                .background(CU.content)
                .environment(\.colorScheme, mode == .night ? .dark : .light)
        )
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.3))

        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)

        var colours = Set<Int>()
        for ix in 0..<48 {
            for iy in 0..<48 {
                guard let c = rep.colorAt(x: (rep.pixelsWide - 1) * ix / 47, y: (rep.pixelsHigh - 1) * iy / 47)?.usingColorSpace(.sRGB) else { continue }
                colours.insert(Int(c.redComponent * 15) << 8 | Int(c.greenComponent * 15) << 4 | Int(c.blueComponent * 15))
            }
        }
        #expect(colours.count >= 4, "\(name) render looks blank (\(colours.count) distinct colours)")

        if let dirPath = ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] {
            let dir = URL(fileURLWithPath: dirPath)
            try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            let png = try #require(rep.representation(using: .png, properties: [:]))
            try png.write(to: dir.appendingPathComponent("\(name).png"))
        }
    }
}
