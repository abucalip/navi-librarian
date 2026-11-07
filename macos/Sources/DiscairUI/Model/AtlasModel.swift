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

    public init() {}

    /// Shows a finished load without a server: screenshots and tests.
    func preview(places: [AtlasPlace], detail: KnowledgePlace? = nil) { self.places = places; self.detail = detail; loaded = true; coverage = "loaded" }

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
