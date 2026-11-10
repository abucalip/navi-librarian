import Foundation
import Testing
@testable import DiscairLibrarian

/// The Downloads row's covers (docs/artwork.md, idea 13): Front images only, never a PDF, at most three, and the release group a Get
/// carries back from the server.
@Suite struct EditionCoversTests {
    private func index(_ images: [ArtworkPicture]) -> ArtworkIndex {
        let body: [String: Any] = [
            "status": "ok", "rgid": "g", "slots": [String: Any](), "booklet": NSNull(),
            "images": images.map { p in
                ["image_id": p.imageID, "types": p.types, "comment": p.comment, "edition": p.edition, "format": p.format,
                 "width": p.width as Any, "height": p.height as Any]
            },
        ]
        let data = try! JSONSerialization.data(withJSONObject: body)
        guard case .ready(let result) = ArtworkIndexResult.decode(data) else { fatalError("index did not decode") }
        return result
    }

    private func pic(_ id: Int, _ types: [String], format: String = "jpg") -> ArtworkPicture {
        ArtworkPicture(imageID: id, edition: "1999 JP CD", types: types, comment: "", width: 1200, height: 1200, format: format)
    }

    @Test func onlyFrontImagesInServerOrder() {
        let got = index([pic(1, ["Back"]), pic(5, ["Front"]), pic(2, ["Front", "Back"]), pic(7, ["Booklet"])]).editionCovers
        #expect(got.map(\.imageID) == [5, 2])
    }

    @Test func noFrontMeansNoCovers() {
        #expect(index([pic(1, ["Back"]), pic(2, [])]).editionCovers.isEmpty)
    }

    @Test func leavesOutPdfsAndCapsTheCount() {
        #expect(index([pic(9, ["Front"], format: "pdf"), pic(4, ["Front"])]).editionCovers.map(\.imageID) == [4])
        let many = index((1...10).map { pic($0, ["Front"]) })
        #expect(many.editionCovers.count == editionCoverLimit)
    }

    @Test func jobReadsTheReleaseGroupFromItsMetadata() throws {
        func job(_ metadata: String) throws -> Acquisition {
            let json = #"{"artist":"A","album":"B","status":"queued","details":{"metadata":\#(metadata)}}"#
            return try JSONDecoder().decode(Acquisition.self, from: Data(json.utf8))
        }
        let rgid = "1edd139d-4779-4057-8e12-13c783674f0d"
        #expect(try job(#"{"release_group_mbid":"\#(rgid)","year":1999}"#).details?.releaseGroupMBID == rgid)
        #expect(try job(#"{"release_group_mbid":"not-an-id"}"#).details?.releaseGroupMBID == nil)
        #expect(try job(#"{"year":1999}"#).details?.releaseGroupMBID == nil)
        #expect(try job(#"[1,2]"#).details?.releaseGroupMBID == nil, "a metadata value of the wrong shape must not fail the job list")
    }
}
