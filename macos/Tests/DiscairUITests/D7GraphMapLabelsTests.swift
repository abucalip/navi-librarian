import AppKit
import CoreGraphics
import DiscairLibrarian
import MapKit
import SwiftUI
import Testing
@testable import DiscairUI

/// Slice D7 (`docs/plans/MACOS_DESIGN_DETAILS.md`):
/// - D7.1: Connections graph labels sit on a rounded `CU.content` 80% halo (4 pt padding) above edges;
///   sector eyebrows sit in gaps between edges and drop when a cluster has fewer than 2 step-1 nodes.
/// - D7.2: Atlas map enables native MapKit clustering (`clusteringIdentifier`), priority-ordered pin/label
///   collision (`displayPriority` + `AtlasLabelLayout`), and in-bounds label clamping.
/// - D7.3: Atlas inspector recording rows collapse the album line when a recording has no albums.
/// - D7.4: Atlas and Timeline footers wrap their legend as one block with the "Showing the first … only." note on its own line.
@MainActor
@Suite(.serialized)
struct D7GraphMapLabelsTests {
    // MARK: - D7.1 Connections graph labels & sector gaps

    @Test func sectorLabelAnglesDropSmallClustersAndSitInEdgeGaps() {
        // 3 people (odd), 2 albums (even), 1 label (single -> dropped), 1 place (single -> dropped).
        let items: [GraphLayout.Item] = [
            .init(id: "p1", depth: 1, via: "c", kind: "artist"),
            .init(id: "p2", depth: 1, via: "c", kind: "person"),
            .init(id: "p3", depth: 1, via: "c", kind: "group"),
            .init(id: "a1", depth: 1, via: "c", kind: "release"),
            .init(id: "a2", depth: 1, via: "c", kind: "release_group"),
            .init(id: "l1", depth: 1, via: "c", kind: "label"),
            .init(id: "pl1", depth: 1, via: "c", kind: "place"),
        ]
        let labelAngles = GraphLayout.sectorLabelAngles(items)
        #expect(Set(labelAngles.keys) == [.people, .albums])

        let placed = GraphLayout.place(centre: "c", items: items, style: .sectors)
        let edgeAngles = items.compactMap { placed[$0.id] }.map { atan2($0.y, $0.x) }

        for (sector, angle) in labelAngles {
            let minGap = edgeAngles.map { circularDistance(angle, $0) }.min() ?? 0
            #expect(minGap > 0.15, "sector \(sector) label angle \(angle) sits too close to an edge (gap \(minGap))")
        }
    }

    @Test func connectionsLabelHaloConstantsMatchSpec() {
        #expect(CupertinoConnections.labelHaloOpacity == 0.8)
        #expect(CupertinoConnections.labelHaloPadding == 4)
        #expect(CupertinoConnections.labelHaloCornerRadius == 6)
    }

    // MARK: - D7.2 Atlas clustering, priority & label layout

    @Test func displayPriorityRanksSelectedThenOwnedThenUnowned() {
        let selected = AtlasGeometry.displayPriority(owned: 0, recordings: 1, selected: true)
        let highOwned = AtlasGeometry.displayPriority(owned: 12, recordings: 15)
        let lowOwned = AtlasGeometry.displayPriority(owned: 1, recordings: 20)
        let highUnowned = AtlasGeometry.displayPriority(owned: 0, recordings: 10)
        let lowUnowned = AtlasGeometry.displayPriority(owned: 0, recordings: 1)

        #expect(selected == .required)
        #expect(selected.rawValue > highOwned.rawValue)
        #expect(highOwned.rawValue > lowOwned.rawValue)
        #expect(lowOwned.rawValue > highUnowned.rawValue)
        #expect(highUnowned.rawValue > lowUnowned.rawValue)
    }

    @Test func clusterBadgeSizeGrowsGentlyAndStaysBounded() {
        #expect(AtlasGeometry.clusterBadgeSize(count: 2) >= 28)
        #expect(AtlasGeometry.clusterBadgeSize(count: 10) > AtlasGeometry.clusterBadgeSize(count: 2))
        #expect(AtlasGeometry.clusterBadgeSize(count: 500) <= 42)
    }

    @Test func pinViewEnablesClusteringAndCollisionPriority() {
        let p = makePlace(id: "abbey", name: "Abbey Road", lat: 51.532, lon: -0.177, recordings: 20, owned: 8)
        let annotation = AtlasPlaceAnnotation(place: p)
        let view = AtlasPinView(annotation: annotation, reuseIdentifier: AtlasPinView.reuseIdentifier)
        view.configure(place: p, selected: false, accent: .systemPink, ink: .labelColor)

        #expect(view.clusteringIdentifier == AtlasMapView.clusterIdentifier)
        #expect(view.collisionMode == .circle)
        #expect(view.displayPriority == AtlasGeometry.displayPriority(owned: 8, recordings: 20, selected: false))
    }

    @Test func labelLayoutHidesLowerPriorityLabelOnCollision() {
        let bounds = CGRect(x: 0, y: 0, width: 600, height: 420)
        let high = AtlasLabelCandidate(
            id: "high",
            pinCenter: CGPoint(x: 300, y: 200),
            pinSize: 24,
            labelSize: CGSize(width: 110, height: 18),
            priority: AtlasGeometry.displayPriority(owned: 10, recordings: 12).rawValue
        )
        let low = AtlasLabelCandidate(
            id: "low",
            pinCenter: CGPoint(x: 312, y: 206),
            pinSize: 14,
            labelSize: CGSize(width: 110, height: 18),
            priority: AtlasGeometry.displayPriority(owned: 0, recordings: 2).rawValue
        )

        let placed = AtlasLabelLayout.place([low, high], in: bounds)
        #expect(placed["high"]?.visible == true)
        #expect(placed["low"]?.visible == false)
    }

    @Test func labelLayoutKeepsEdgeLabelsInsideMapBounds() {
        let bounds = CGRect(x: 0, y: 0, width: 600, height: 420)
        let safe = bounds.insetBy(dx: AtlasLabelLayout.edgeInset, dy: AtlasLabelLayout.edgeInset)
        let candidates = [
            // Near top edge (like "Studios, Studios, Studio 2" in screenshot 02.27.57)
            AtlasLabelCandidate(id: "top", pinCenter: CGPoint(x: 220, y: 16), pinSize: 16, labelSize: CGSize(width: 140, height: 18), priority: 700),
            // Near bottom edge -> should flip above the pin
            AtlasLabelCandidate(id: "bottom", pinCenter: CGPoint(x: 220, y: 404), pinSize: 16, labelSize: CGSize(width: 120, height: 18), priority: 680),
            // Near left edge -> should clamp right
            AtlasLabelCandidate(id: "left", pinCenter: CGPoint(x: 16, y: 200), pinSize: 16, labelSize: CGSize(width: 120, height: 18), priority: 660),
            // Near right edge -> should clamp left
            AtlasLabelCandidate(id: "right", pinCenter: CGPoint(x: 584, y: 200), pinSize: 16, labelSize: CGSize(width: 120, height: 18), priority: 640),
        ]

        let placed = AtlasLabelLayout.place(candidates, in: bounds)
        for c in candidates {
            let p = try! #require(placed[c.id])
            #expect(p.visible, "edge candidate \(c.id) should stay visible inside safe bounds")
            #expect(safe.contains(p.frame), "label \(c.id) frame \(p.frame) escaped safe bounds \(safe)")
        }
        // Bottom pin flipped above its pin centre.
        #expect(placed["bottom"]!.frame.maxY < 404)
        // Top pin placed below its pin centre.
        #expect(placed["top"]!.frame.minY > 16)
    }

    // MARK: - D7.3 Atlas inspector empty album line

    @Test func atlasInspectorCollapsesEmptyAlbumLine() {
        #expect(AtlasInspector.albumLine(for: []) == nil)
        #expect(AtlasInspector.albumLine(for: [makeAlbumLink("   ")]) == nil)
        #expect(AtlasInspector.albumLine(for: [makeAlbumLink("Blue Train")]) == "Blue Train")
        #expect(AtlasInspector.albumLine(for: [makeAlbumLink("Blue Train"), makeAlbumLink("Giant Steps")]) == "Blue Train · Giant Steps")
    }

    // MARK: - D7.4 Footer legends & offscreen renders

    @Test func footerLayoutSpacingConstantsMatch() {
        #expect(AtlasView.footerItemSpacing == 14)
        #expect(AtlasView.footerLineSpacing == 4)
        #expect(TimelineView.footerItemSpacing == 14)
        #expect(TimelineView.footerLineSpacing == 4)
    }

    @Test(arguments: AppearanceMode.allCases)
    func rendersConnectionsAtlasAndTimeline(_ mode: AppearanceMode) throws {
        // D7.1 Connections graph
        let connState = AppState(themeID: .cupertino, screen: .connections)
        connState.graph.preview(centre: ConnectionsServicesRenderTests.centre, nodes: ConnectionsServicesRenderTests.nodes, more: true)
        try render(CupertinoConnections(state: connState), size: NSSize(width: 1100, height: 760), mode: mode, name: "d7-connections-\(mode)")

        // D7.2 + D7.3 + D7.4 Atlas with truncated footer and inspector detail containing a recording without an album
        let atlasState = AppState(themeID: .cupertino, screen: .atlas)
        let detail = makePlaceDetailWithAndWithoutAlbums()
        let places = [
            makePlace(id: "p1", name: "Wessex Studios", lat: 51.55, lon: -0.09, recordings: 12, owned: 5),
            makePlace(id: "p2", name: "Abbey Road Studios", lat: 51.532, lon: -0.177, recordings: 8, owned: 3),
            makePlace(id: "p3", name: "Studios, Studios, Studio 2", lat: 55.95, lon: -3.19, recordings: 2, owned: 0),
        ]
        atlasState.atlas.preview(places: places, detail: detail, truncated: true)
        atlasState.atlas.selectedID = "p1"
        try render(AtlasView(state: atlasState, style: .cupertino), size: NSSize(width: 1020, height: 680), mode: mode, name: "d7-atlas-\(mode)")

        // D7.4 Timeline with truncated footer
        let timelineState = AppState(themeID: .cupertino, screen: .timeline)
        timelineState.timeline.preview(person: TimelinePreview.person, items: TimelinePreview.items, undated: 1, truncated: true)
        try render(TimelineView(state: timelineState, style: .cupertino), size: NSSize(width: 960, height: 640), mode: mode, name: "d7-timeline-\(mode)")
    }

    // MARK: - Helpers

    private func circularDistance(_ a: Double, _ b: Double) -> Double {
        let d = abs(a - b).truncatingRemainder(dividingBy: 2 * Double.pi)
        return min(d, 2 * Double.pi - d)
    }

    private func makePlace(id: String, name: String, lat: Double, lon: Double, recordings: Int, owned: Int) -> AtlasPlace {
        let json = #"{"entity":{"mbid":"\#(id)","canonical_name":"\#(name)","type":"place"},"latitude":\#(lat),"longitude":\#(lon),"recordings":\#(recordings),"owned_recordings":\#(owned)}"#
        return try! JSONDecoder().decode(AtlasPlace.self, from: Data(json.utf8))
    }

    private func makeAlbumLink(_ name: String) -> KnowledgeAlbumLink {
        let json = #"{"album":{"mbid":"a1","canonical_name":"\#(name)","type":"release_group"},"owned":true}"#
        return try! JSONDecoder().decode(KnowledgeAlbumLink.self, from: Data(json.utf8))
    }

    private func makePlaceDetailWithAndWithoutAlbums() -> KnowledgePlace {
        let json = """
        {
          "place": {"mbid": "p1", "canonical_name": "Wessex Studios", "type": "place"},
          "facts": {"latitude": 51.55, "longitude": -0.09},
          "recordings": [
            {
              "recording": {"mbid": "r1", "canonical_name": "! (foreword)", "type": "recording"},
              "owned": false,
              "albums": [],
              "credits": [{"relation": "recorded in", "source": "musicbrainz_dump", "evidence_class": "source_explicit", "match_quality": "exact_mbid"}]
            },
            {
              "recording": {"mbid": "r2", "canonical_name": "Spirit of Eden", "type": "recording"},
              "owned": true,
              "albums": [{"album": {"mbid": "rg1", "canonical_name": "Spirit of Eden", "type": "release_group"}, "owned": true}],
              "credits": [{"relation": "recorded in", "source": "musicbrainz_dump", "evidence_class": "source_explicit", "match_quality": "exact_mbid"}]
            }
          ],
          "not_loaded": []
        }
        """
        return try! JSONDecoder().decode(KnowledgePlace.self, from: Data(json.utf8))
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
        RunLoop.current.run(until: Date().addingTimeInterval(0.35))

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
