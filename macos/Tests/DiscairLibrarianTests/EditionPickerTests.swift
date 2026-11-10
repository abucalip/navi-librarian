@testable import DiscairLibrarian
import Foundation
import Testing

/// Which covers the edition picker offers (docs/artwork.md, idea 7).
@Suite struct EditionPickerTests {
    private func index(_ pictures: [ArtworkPicture]) -> ArtworkIndex {
        let body: [String: Any] = ["status": "ok", "rgid": "r", "best_front": NSNull(), "slots": [:], "booklet": NSNull(), "images": pictures.map {
            ["image_id": $0.imageID, "release": "r", "releases": ["r"], "edition": $0.edition, "types": $0.types, "comment": "", "approved": true, "format": $0.format] as [String: Any]
        }]
        let data = try! JSONSerialization.data(withJSONObject: body)
        guard case .ready(let found) = ArtworkIndexResult.decode(data) else { fatalError("index did not decode") }
        return found
    }

    @Test func onlyFrontImagesAreOffered_neverAPdf() {
        let found = index([
            ArtworkPicture(imageID: 1, edition: "1999 JP CD", types: ["Front"], format: "jpg"),
            ArtworkPicture(imageID: 2, types: ["Back"], format: "jpg"),
            ArtworkPicture(imageID: 3, types: ["Front"], format: "pdf"),
            ArtworkPicture(imageID: 4, edition: "2010 US CD", types: ["Front"], format: "png"),
        ])
        #expect(found.coverEditions.map(\.imageID) == [1, 4])
    }

    @Test func aChoiceNeedsAtLeastTwoCovers() {
        #expect(!hasEditionChoice([]))
        #expect(!hasEditionChoice([ArtworkPicture(imageID: 1, types: ["Front"])]))
        #expect(hasEditionChoice([ArtworkPicture(imageID: 1, types: ["Front"]), ArtworkPicture(imageID: 2, types: ["Front"])]))
    }
}
