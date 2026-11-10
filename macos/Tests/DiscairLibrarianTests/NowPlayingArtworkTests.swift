import Foundation
import Testing
@testable import DiscairLibrarian

/// The disc and the slideshow (docs/artwork.md, ideas 3 and 4): what is picked, and the pure timing rules.
@Suite struct NowPlayingArtworkTests {
    private func index(_ images: [ArtworkPicture], slots: [String: Int] = [:], booklet: [Int] = []) -> ArtworkIndex {
        var slotJSON: [String: Any] = [:]
        for (type, id) in slots { slotJSON[type] = ["image_id": id, "release": "r", "edition": "e", "from_owned": true] }
        let body: [String: Any] = [
            "status": "ok", "rgid": "g", "slots": slotJSON,
            "booklet": booklet.isEmpty ? NSNull() : ["release": "r", "edition": "1999 JP CD", "image_ids": booklet] as [String: Any],
            "images": images.map { p in
                ["image_id": p.imageID, "types": p.types, "comment": p.comment, "edition": p.edition, "format": p.format,
                 "width": p.width as Any, "height": p.height as Any]
            },
        ]
        let data = try! JSONSerialization.data(withJSONObject: body)
        guard case .ready(let result) = ArtworkIndexResult.decode(data) else { fatalError("index did not decode") }
        return result
    }

    private func pic(_ id: Int, _ types: [String], comment: String = "", edition: String = "", format: String = "jpg",
                     size: Int? = 1200) -> ArtworkPicture {
        ArtworkPicture(imageID: id, edition: edition, types: types, comment: comment, width: size, height: size, format: format)
    }

    @Test func discNumbersAreReadFromText() {
        #expect(namedDisc("Disc 2") == 2)
        #expect(namedDisc("CD2 label") == 2)
        #expect(namedDisc("disk 02, side B") == 2)
        #expect(namedDisc("Disc No. 1") == 1)
        #expect(namedDisc("Side A label") == nil)
        #expect(namedDisc("") == nil)
        #expect(namedDisc("1999 JP CD") == nil)
        #expect(namedDisc("Discovery") == nil)
    }

    @Test func theDiscNamedByTheSongsDiscWins() {
        let i = index([pic(1, ["Medium"], comment: "Disc 1"), pic(2, ["Medium"], comment: "Disc 2")], slots: ["Medium": 1])
        #expect(i.discImage(disc: 2)?.imageID == 2)
        #expect(i.discImage(disc: 1)?.imageID == 1)
    }

    @Test func withoutANamedMatchTheMediumSlotThenTheFirstMediumIsUsed() {
        let slotted = index([pic(1, ["Medium"]), pic(2, ["Medium"])], slots: ["Medium": 2])
        #expect(slotted.discImage(disc: nil)?.imageID == 2)
        #expect(slotted.discImage(disc: 3)?.imageID == 2)
        let plain = index([pic(5, ["Medium"]), pic(6, ["Medium"])])
        #expect(plain.discImage(disc: 1)?.imageID == 5)
    }

    @Test func aLabelThatNamesAnotherDiscIsNotShown() {
        let i = index([pic(1, ["Medium"], comment: "Disc 1")], slots: ["Medium": 1])
        #expect(i.discImage(disc: 2) == nil)
        #expect(i.discImage(disc: nil)?.imageID == 1)
    }

    @Test func noMediumImageMeansNoDisc() {
        #expect(index([pic(1, ["Front"]), pic(2, ["Booklet"])]).discImage(disc: 1) == nil)
        #expect(index([pic(3, ["Medium"], format: "pdf")]).discImage(disc: nil) == nil)
    }

    @Test func theSlideshowTakesBookletPagesThenOtherLinerAndPosterOnce() {
        let i = index([pic(1, ["Front"]), pic(2, ["Booklet"]), pic(3, ["Booklet"]), pic(4, ["Other"]), pic(5, ["Liner"]),
                       pic(6, ["Poster", "Other"]), pic(7, ["Back"]), pic(8, ["Medium"]), pic(9, ["Raw/Unedited"])], booklet: [2, 3])
        #expect(i.slideshowImages.map(\.imageID) == [2, 3, 4, 5, 6])
    }

    @Test func pdfsAndSmallImagesAreLeftOut() {
        let i = index([pic(1, ["Booklet"], format: "pdf"), pic(2, ["Booklet"]), pic(3, ["Other"], size: 250), pic(4, ["Other"], size: nil),
                       pic(5, ["Other"])], booklet: [1, 2])
        #expect(i.slideshowImages.map(\.imageID) == [2, 4, 5])
    }

    @Test func fewerThanTwoImagesIsNotASlideshow() {
        #expect(index([pic(1, ["Other"])]).slideshowImages.isEmpty)
        #expect(index([pic(1, ["Front"])]).slideshowImages.isEmpty)
    }

    @Test func theSlideshowIsCapped() {
        let many = (1...30).map { pic($0, ["Other"]) }
        #expect(index(many).slideshowImages.count == ArtworkIndex.slideshowLimit)
    }

    @Test func slideshowTimingHoldsThenFadesIntoTheNextSlide() throws {
        let start = try #require(slideshowFrame(elapsed: 0, count: 3))
        #expect(start.index == 0 && start.next == 1 && start.mix == 0 && start.progress == 0)
        let held = try #require(slideshowFrame(elapsed: 10, count: 3))
        #expect(held.index == 0 && held.mix == 0)
        let fading = try #require(slideshowFrame(elapsed: 12.5, count: 3))
        #expect(fading.index == 0 && fading.next == 1 && abs(fading.mix - 0.5) < 0.0001)
        let second = try #require(slideshowFrame(elapsed: 14, count: 3))
        #expect(second.index == 1 && second.mix == 0)
        let wrapped = try #require(slideshowFrame(elapsed: 14 * 3 + 1, count: 3))
        #expect(wrapped.index == 0 && wrapped.next == 1)
        let last = try #require(slideshowFrame(elapsed: 14 * 2 + 13, count: 3))
        #expect(last.index == 2 && last.next == 0)
    }

    @Test func slideshowTimingHandlesEmptyAndNegative() {
        #expect(slideshowFrame(elapsed: 5, count: 0) == nil)
        #expect(slideshowFrame(elapsed: -3, count: 2)?.index == 0)
    }

    @Test func theDiscTurnsOnlyWhileRunning() {
        #expect(discAngle(base: 40, since: nil, now: 100, rpm: 10) == 40)
        #expect(discAngle(base: 0, since: 100, now: 101, rpm: 10) == 60)
        #expect(abs(discAngle(base: 350, since: 0, now: 1, rpm: 10) - 50) < 0.0001)
        #expect(discAngle(base: 0, since: 100, now: 90, rpm: 10) == 0)
    }
}
