import Foundation
import Testing
import DiscairCore
import DiscairLibrarian
@testable import DiscairUI

private struct AtlasTransport: HTTPTransport {
    let body: Data
    var status = 200
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        (body, HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!)
    }
}

private func place(_ id: String, _ lat: Double, _ lon: Double, owned: Int = 0) -> AtlasPlace {
    let json = #"{"entity":{"mbid":"\#(id)","canonical_name":"P \#(id)","type":"place"},"latitude":\#(lat),"longitude":\#(lon),"recordings":5,"owned_recordings":\#(owned)}"#
    return try! JSONDecoder().decode(AtlasPlace.self, from: Data(json.utf8))
}

@Suite("Atlas geometry") struct AtlasGeometryTests {
    @Test func pinGrowsWithOwnedRecordingsAndIsCapped() {
        #expect(AtlasGeometry.pinSize(owned: 0) == 14)
        #expect(AtlasGeometry.pinSize(owned: 4) > AtlasGeometry.pinSize(owned: 1))
        #expect(AtlasGeometry.pinSize(owned: 10_000) == 38)
    }

    @Test func regionHoldsEveryPlaceWithMargin() {
        let r = AtlasGeometry.region(for: [place("a", 48.85, 2.41), place("b", 9.0, 38.7)])
        #expect(abs(r.center.latitude - 28.925) < 1e-9)
        #expect(r.span.latitudeDelta >= (48.85 - 9.0) && r.span.longitudeDelta >= (38.7 - 2.41))
    }

    @Test func onePlaceGetsACitySizedViewAndNoPlacesTheWorld() {
        #expect(AtlasGeometry.region(for: [place("a", 10, 10)]).span.latitudeDelta == 2)
        #expect(AtlasGeometry.region(for: []).span.longitudeDelta > 100)
    }
}

@MainActor @Suite("Atlas model") struct AtlasModelTests {
    private func client(_ body: String, status: Int = 200) throws -> LibrarianClient {
        try LibrarianClient(baseURL: URL(string: "https://lib.example.ts.net")!, credential: Credential(username: "owner", password: "s3cret-pw-1234"),
                            transport: AtlasTransport(body: Data(body.utf8), status: status))
    }

    @Test func loadsPlacesAndExplainsAnEmptyAtlas() async throws {
        let model = AtlasModel()
        await model.load(librarian: try client(#"{"places":[],"truncated":false,"sources":{"musicbrainz_dump":{"coverage":"pending"}}}"#))
        #expect(model.loaded && model.places.isEmpty && model.note?.contains("not on the server") == true)
    }

    @Test func withoutALibrarianItSaysSo() async {
        let model = AtlasModel()
        await model.load(librarian: nil)
        #expect(!model.loaded && model.note != nil)
    }

    @Test func aFailedLoadKeepsNothingAndLeavesANote() async throws {
        let model = AtlasModel()
        await model.load(librarian: try client("{}", status: 502))
        #expect(!model.loaded && model.places.isEmpty && model.note?.contains("Could not") == true)
    }

    @Test func selectingAPinReadsItsPage() async throws {
        let model = AtlasModel()
        model.preview(places: [place("p1", 48.85, 2.41, owned: 2)])
        let page = #"{"place":{"mbid":"p1","canonical_name":"P p1","type":"place"},"facts":{"latitude":48.85,"longitude":2.41},"recordings":[],"not_loaded":["address"]}"#
        await model.select("p1", librarian: try client(page))
        #expect(model.selected?.id == "p1" && model.detail?.place.mbid == "p1" && model.detail?.notLoaded == ["address"])
        await model.select(nil, librarian: nil)
        #expect(model.selected == nil && model.detail == nil)
    }
}
