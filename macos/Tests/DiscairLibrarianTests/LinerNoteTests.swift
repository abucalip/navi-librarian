import Foundation
import Testing
@testable import DiscairLibrarian

/// The liner note of the day (docs/artwork.md, idea 12): a stable day key, a stable album order and a picture chosen by type only.
@Suite struct LinerNoteTests {
    private let a = "1edd139d-4779-4057-8e12-13c783674f0d"
    private let b = "9b7e1f2c-3d4a-4b5c-8d6e-7f8091a2b3c4"
    private let c = "2c3d4e5f-6a7b-4c8d-9e0f-1a2b3c4d5e6f"

    private func index(_ images: [ArtworkPicture], slots: [String: Any] = [:]) -> ArtworkIndex {
        let body: [String: Any] = [
            "status": "ok", "rgid": "g", "slots": slots, "booklet": NSNull(),
            "images": images.map { p in
                ["image_id": p.imageID, "types": p.types, "comment": p.comment, "edition": p.edition, "format": p.format,
                 "width": p.width as Any, "height": p.height as Any]
            },
        ]
        let data = try! JSONSerialization.data(withJSONObject: body)
        guard case .ready(let result) = ArtworkIndexResult.decode(data) else { fatalError("index did not decode") }
        return result
    }

    private func pic(_ id: Int, _ types: [String], comment: String = "", format: String = "jpg") -> ArtworkPicture {
        ArtworkPicture(imageID: id, edition: "1999 JP CD", types: types, comment: comment, width: 1200, height: 1200, format: format)
    }

    @Test func theSeedIsStableAndDependsOnTheKey() {
        #expect(linerNoteSeed("2026-11-10") == linerNoteSeed("2026-11-10"))
        #expect(linerNoteSeed("2026-11-10") != linerNoteSeed("2026-11-11"))
    }

    @Test func dayIsTheLocalCalendarDate() {
        var parts = DateComponents(); parts.year = 2026; parts.month = 3; parts.day = 7; parts.hour = 12
        let calendar = Calendar(identifier: .gregorian)
        #expect(linerNoteDay(calendar.date(from: parts)!, calendar: calendar) == "2026-03-07")
    }

    @Test func orderIgnoresArrivalOrderAndDropsBadAndRepeatedIds() {
        let one = linerNoteOrder([a, b, c], day: "2026-11-10")
        #expect(Set(one) == Set([a, b, c]) && one.count == 3)
        #expect(linerNoteOrder([c, a, b], day: "2026-11-10") == one)
        #expect(linerNoteOrder(["not-an-id", a, a.uppercased()], day: "2026-11-10") == [a])
        #expect(linerNoteOrder([], day: "2026-11-10").isEmpty)
    }

    @Test func pictureIsBookletSessionOrLabelNeverACoverOrPDF() {
        let idx = index([pic(1, ["Front"]), pic(2, ["Back"]), pic(3, ["Booklet"], format: "pdf"),
                         pic(4, ["Booklet"]), pic(5, ["Other"]), pic(6, ["Medium"])])
        for day in ["2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"] {
            let picked = idx.linerNotePicture(day: day)
            #expect([4, 5, 6].contains(picked?.imageID ?? -1), "\(day) picked \(String(describing: picked?.imageID))")
        }
        #expect(idx.linerNotePicture(day: "2026-11-10") == idx.linerNotePicture(day: "2026-11-10"))
    }

    @Test func noQualifyingPictureMeansNoNote() {
        #expect(index([pic(1, ["Front"]), pic(2, ["Back"]), pic(3, [])]).linerNotePicture(day: "2026-11-10") == nil)
    }
}
