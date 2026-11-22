import DiscairLibrarian
import Foundation
import MapKit
import Observation

/// Pure map maths for the atlas, so a test can drive it without a window.
public enum AtlasGeometry {
    /// A pin grows with the recordings the library owns made there: 14 pt for none, up to 38 pt.
    public static func pinSize(owned: Int) -> Double { owned <= 0 ? 14 : min(38, 14 + 6 * Double(owned).squareRoot()) }

    /// The region that holds every place with some margin, or the world when there are none. One place gets a city-sized view.
    public static func region(for places: [AtlasPlace]) -> MKCoordinateRegion {
        guard let first = places.first else {
            return MKCoordinateRegion(center: .init(latitude: 25, longitude: 10), span: .init(latitudeDelta: 120, longitudeDelta: 200))
        }
        var minLat = first.latitude, maxLat = first.latitude, minLon = first.longitude, maxLon = first.longitude
        for p in places {
            minLat = min(minLat, p.latitude); maxLat = max(maxLat, p.latitude)
            minLon = min(minLon, p.longitude); maxLon = max(maxLon, p.longitude)
        }
        let latSpan = min(max((maxLat - minLat) * 1.4, 2), 170), lonSpan = min(max((maxLon - minLon) * 1.4, 2), 350)
        return MKCoordinateRegion(center: .init(latitude: (minLat + maxLat) / 2, longitude: (minLon + maxLon) / 2),
                                  span: .init(latitudeDelta: latSpan, longitudeDelta: lonSpan))
    }

    /// MapKit display priority for a place pin (D7.2): selected pins win first, then owned places ordered by owned
    /// recording count, then unowned places ordered by total recordings, so lower-count pins and labels hide first.
    public static func displayPriority(owned: Int, recordings: Int, selected: Bool = false) -> MKFeatureDisplayPriority {
        if selected { return .required }
        if owned > 0 {
            return MKFeatureDisplayPriority(rawValue: Float(min(950, 500 + owned * 20)))
        }
        return MKFeatureDisplayPriority(rawValue: Float(min(450, 200 + max(recordings, 0) * 10)))
    }

    /// Diameter of a numbered MapKit cluster badge, growing gently with member count (28..42 pt).
    public static func clusterBadgeSize(count: Int) -> Double {
        min(42, max(28, 24 + 4.5 * Double(max(count, 2)).squareRoot()))
    }
}

/// One pin's label candidate for collision-free, in-bounds placement on the Atlas map (D7.2).
public struct AtlasLabelCandidate: Equatable, Sendable {
    public let id: String
    public let pinCenter: CGPoint
    public let pinSize: CGFloat
    public let labelSize: CGSize
    public let priority: Float

    public init(id: String, pinCenter: CGPoint, pinSize: CGFloat, labelSize: CGSize, priority: Float) {
        self.id = id
        self.pinCenter = pinCenter
        self.pinSize = pinSize
        self.labelSize = labelSize
        self.priority = priority
    }
}

/// Placed label frame and visibility decision for one Atlas pin (D7.2).
public struct AtlasLabelPlacement: Equatable, Sendable {
    public let id: String
    public let frame: CGRect
    public let visible: Bool
}

/// Pure collision and map-bounds clamping for Atlas pin labels (D7.2). Higher-priority labels win; lower-count
/// labels hide when they would overlap another label or pin, and labels stay strictly inside the map's safe bounds.
public enum AtlasLabelLayout {
    public static let edgeInset: CGFloat = 8
    public static let pinGap: CGFloat = 4
    public static let collisionPadding: CGFloat = 3

    public static func place(_ candidates: [AtlasLabelCandidate], in bounds: CGRect) -> [String: AtlasLabelPlacement] {
        let safe = bounds.insetBy(dx: edgeInset, dy: edgeInset)
        guard safe.width > 0, safe.height > 0 else {
            return Dictionary(uniqueKeysWithValues: candidates.map { ($0.id, AtlasLabelPlacement(id: $0.id, frame: .zero, visible: false)) })
        }

        let ordered = candidates.sorted { a, b in
            if a.priority != b.priority { return a.priority > b.priority }
            return a.id < b.id
        }
        let pinRects: [(id: String, rect: CGRect)] = candidates.map { c in
            let r = CGRect(x: c.pinCenter.x - c.pinSize / 2, y: c.pinCenter.y - c.pinSize / 2, width: c.pinSize, height: c.pinSize)
            return (c.id, r)
        }

        var accepted: [CGRect] = []
        var out: [String: AtlasLabelPlacement] = [:]

        for c in ordered {
            let w = c.labelSize.width, h = c.labelSize.height
            guard w > 0, h > 0, w <= safe.width, h <= safe.height else {
                out[c.id] = AtlasLabelPlacement(id: c.id, frame: .zero, visible: false)
                continue
            }
            let clampedX = min(max(c.pinCenter.x - w / 2, safe.minX), safe.maxX - w)
            let below = CGRect(x: clampedX, y: c.pinCenter.y + c.pinSize / 2 + pinGap, width: w, height: h)
            let above = CGRect(x: clampedX, y: c.pinCenter.y - c.pinSize / 2 - pinGap - h, width: w, height: h)

            var chosen: CGRect?
            for candidateRect in [below, above] {
                guard safe.contains(candidateRect) else { continue }
                let padded = candidateRect.insetBy(dx: -collisionPadding, dy: -collisionPadding)
                let hitsLabel = accepted.contains { $0.intersects(padded) }
                let hitsPin = pinRects.contains { $0.id != c.id && $0.rect.intersects(candidateRect) }
                if !hitsLabel && !hitsPin {
                    chosen = candidateRect
                    break
                }
            }

            if let frame = chosen {
                accepted.append(frame)
                out[c.id] = AtlasLabelPlacement(id: c.id, frame: frame, visible: true)
            } else {
                out[c.id] = AtlasLabelPlacement(id: c.id, frame: .zero, visible: false)
            }
        }
        return out
    }
}

extension AtlasGeometry {
    /// The release group whose disc stands for a recording: the first album that is a release group with a valid id.
    public static func discGroup(_ albums: [KnowledgeAlbumLink]) -> String? {
        albums.lazy.filter { $0.album.type == "release_group" }.compactMap { artworkGroupID($0.album.mbid) }.first
    }
}

/// State of the atlas (Server V2 Phase 7 client gate): places with stated coordinates and the place on show. It only
/// reads `GET /api/knowledge/atlas` and `/place`; nothing is geocoded or inferred on the Mac.
@MainActor
@Observable
public final class AtlasModel {
    public private(set) var places: [AtlasPlace] = []
    public private(set) var loading = false
    public private(set) var loaded = false
    public private(set) var note: String?
    public private(set) var truncated = false
    public private(set) var coverage: String?
    public private(set) var detail: KnowledgePlace?
    public private(set) var detailLoading = false
    public private(set) var detailNote: String?
    public var selectedID: String?
    public var showsList = false
    /// Off until the owner turns it on: discs ask the server for one artwork index per album.
    public var showsDiscs = false

    public init() {}

    /// Shows a finished load without a server: screenshots and tests.
    func preview(places: [AtlasPlace], detail: KnowledgePlace? = nil, truncated: Bool = false) {
        self.places = places; self.detail = detail; self.truncated = truncated; loaded = true; coverage = "loaded"
    }

    public var selected: AtlasPlace? { places.first { $0.id == selectedID } }
    public var region: MKCoordinateRegion { AtlasGeometry.region(for: places) }

    /// Reads the places once; call again with `force` to refresh.
    public func load(librarian: LibrarianClient?, force: Bool = false) async {
        guard let librarian else { note = "Connect to your Librarian to see where your music was made."; return }
        guard force || !loaded, !loading else { return }
        loading = true; note = nil
        defer { loading = false }
        do {
            let atlas = try await librarian.knowledgeAtlas()
            places = atlas.places; truncated = atlas.truncated
            coverage = atlas.sources["musicbrainz_dump"]?.coverage
            loaded = true
            if places.isEmpty {
                note = coverage == "pending" ? "MusicBrainz data is not on the server yet, so there are no places to pin."
                                             : "No place with stated coordinates is linked to a recording yet."
            }
        } catch {
            note = "Could not read the atlas from the Librarian."
        }
    }

    /// Selects a pin and reads its page (recordings, albums, events and the stated area chain).
    public func select(_ id: String?, librarian: LibrarianClient?) async {
        selectedID = id
        detail = nil; detailNote = nil
        guard let id, let librarian else { return }
        detailLoading = true
        defer { detailLoading = false }
        do {
            let page = try await librarian.knowledgePlace(mbid: id)
            if selectedID == id { detail = page }
        } catch {
            if selectedID == id { detailNote = "Could not read this place." }
        }
    }
}
