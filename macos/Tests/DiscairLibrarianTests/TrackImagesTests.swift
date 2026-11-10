import Foundation
import Testing
@testable import DiscairLibrarian

/// The queue's Track cards (docs/artwork.md, idea 6): only Track images, never a PDF, at most three, none when there are none.
@Suite struct TrackImagesTests {
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

    @Test func noTrackImageMeansNoCard() {
        #expect(index([pic(1, ["Front"]), pic(2, ["Back"])]).trackImages.isEmpty)
        #expect(index([pic(3, [])]).trackImages.isEmpty, "an untyped image is not a track sheet")
    }

    @Test func keepsTrackImagesInServerOrder() {
        let got = index([pic(1, ["Front"]), pic(5, ["Track"]), pic(2, ["Track", "Medium"]), pic(7, ["Booklet"])]).trackImages
        #expect(got.map(\.imageID) == [5, 2])
    }

    @Test func leavesOutPdfsAndCapsTheCount() {
        #expect(index([pic(9, ["Track"], format: "pdf"), pic(4, ["Track"])]).trackImages.map(\.imageID) == [4])
        let many = index((1...10).map { pic($0, ["Track"]) })
        #expect(many.trackImages.count == trackImageLimit)
    }
}
