import Foundation
import Testing
@testable import DiscairLibrarian

/// The artwork index (`GET /api/artwork/index`): the recorded fixtures decode into what the screens will show.
@Suite struct ArtworkTests {
    private func body(_ name: String, file: String = #filePath) throws -> Data {
        let url = URL(fileURLWithPath: file).deletingLastPathComponent().appending(path: "Fixtures/\(name).json")
        let object = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
        return try JSONSerialization.data(withJSONObject: (object["response"] as! [String: Any])["body"]!)
    }

    private func ready(_ name: String) throws -> ArtworkIndex {
        guard case .ready(let index) = ArtworkIndexResult.decode(try body(name)) else { throw TestFailure() }
        return index
    }
    private struct TestFailure: Error {}

    @Test func okFixtureReadsSlotsBookletAndImages() throws {
        let index = try ready("artwork_index")
        #expect(index.bestFront == 2001 && index.truncatedReason == nil)
        #expect(!index.images.isEmpty)
        #expect(Set(index.images.map(\.imageID)).count == index.images.count)
        for (type, slot) in index.slots { #expect(index.slotImage(type) != nil && slot.imageID > 0, "\(type) slot resolves") }
        #expect(index.booklet.map(\.imageIDs) == index.bookletImages.map(\.imageID))
        #expect(index.images.allSatisfy { ["jpg", "png", "gif", "webp", "pdf"].contains($0.format) })
    }

    @Test func editionsAreLabelledAndOwnedFlagIsRead() throws {
        let index = try ready("artwork_index")
        #expect(index.slots.values.contains { $0.fromOwned })
        #expect(index.images.allSatisfy { !$0.edition.isEmpty })
        let back = try #require(index.slotImage("Back"))
        let note = back.comment.trimmingCharacters(in: .whitespacesAndNewlines)
        #expect(back.label == "Back cover, \(back.edition)" + (note.isEmpty ? "" : ": \(note)"))
    }

    @Test func emptyUnavailableAndNotLoaded() throws {
        #expect(ArtworkIndexResult.decode(try body("artwork_index_empty")) == .empty)
        #expect(ArtworkIndexResult.decode(try body("artwork_index_unavailable")) == .unavailable)
        #expect(ArtworkIndexResult.decode(Data("not json".utf8)) == .unavailable)
        #expect(ArtworkIndexResult.decode(Data(#"{"status":"something_new"}"#.utf8)) == .unavailable)
        #expect(ArtworkIndexResult.decode(try body("artwork_index_error_bad_rgid")) == .unavailable)
        guard case .notLoaded(let seconds) = ArtworkIndexResult.decode(try body("artwork_index_not_loaded")) else { throw TestFailure() }
        #expect((1...60).contains(seconds))
    }

    @Test func pendingIsReadAsNotLoaded() {
        #expect(ArtworkIndexResult.decode(Data(#"{"status":"pending"}"#.utf8)) == .notLoaded(retryAfter: 5))
    }

    @Test func truncatedFixturesStillShowWhatWasServedAndSayWhy() throws {
        #expect(try ready("artwork_index_truncated").truncatedReason == "partial")
        #expect(try ready("artwork_index_truncated_release_cap").truncatedReason == "release_cap")
        #expect(try ready("artwork_index_truncated_served_cap").truncatedReason == "served_cap")
    }

    @Test func oneBadImageEntryDoesNotDropTheRest() throws {
        let json = #"{"status":"ok","rgid":"x","images":[{"types":["Front"]},{"image_id":7,"types":["Front"],"comment":"<b>hi</b>","format":"PDF"},{"image_id":0}]}"#
        guard case .ready(let index) = ArtworkIndexResult.decode(Data(json.utf8)) else { throw TestFailure() }
        #expect(index.images.map(\.imageID) == [7])
        #expect(index.images[0].isPDF && index.images[0].comment == "<b>hi</b>")
    }

    @Test func untypedImagesAreInNoSlotAndLabelledImage() {
        let image = ArtworkPicture(imageID: 1)
        #expect(image.isUntyped && image.label == "Image" && !image.isPDF)
    }

    @Test func loadAsksAgainOnNotLoadedThenGivesUp() async {
        final class Box: @unchecked Sendable { var calls = 0; var waits: [Duration] = [] }
        let box = Box()
        let done = await ArtworkIndexResult.load(wait: { box.waits.append($0) }) {
            box.calls += 1
            return box.calls < 3 ? .notLoaded(retryAfter: 2) : .empty
        }
        #expect(done == .empty && box.waits == [.seconds(2), .seconds(2)])
        let never = await ArtworkIndexResult.load(tries: 3, wait: { _ in }) { .notLoaded(retryAfter: 1) }
        #expect(never == .unavailable)
        struct Offline: Error {}
        let failed = await ArtworkIndexResult.load(wait: { _ in }) { throw Offline() }
        #expect(failed == .unavailable)
    }

    // MARK: Flip cover faces

    private func picture(_ id: Int, _ type: String) -> ArtworkPicture { ArtworkPicture(imageID: id, types: [type]) }
    private func index(_ types: [String]) throws -> ArtworkIndex {
        let pics = types.enumerated().map { picture(10 + $0.offset, $0.element) }
        let slots = Dictionary(uniqueKeysWithValues: pics.map { ($0.types[0], ["image_id": $0.imageID, "release": "r", "edition": "", "from_owned": true] as [String: Any]) })
        let json: [String: Any] = ["status": "ok", "rgid": "rg", "releases": ["total": 1, "fetched": 1, "empty": 0, "failed": 0], "slots": slots,
                                   "images": pics.map { ["image_id": $0.imageID, "types": $0.types, "format": "jpg"] as [String: Any] }]
        return try JSONDecoder().decode(ArtworkIndex.self, from: JSONSerialization.data(withJSONObject: json))
    }

    @Test func noBackMeansNoFlip() throws {
        #expect(try index(["Front"]).coverBackFaces.isEmpty)
        #expect(try index(["Front", "Spine", "Tray"]).coverBackFaces.isEmpty, "a spine alone is not a reason to flip")
    }

    @Test func backThenTrayThenSpine() throws {
        #expect(try index(["Back", "Front"]).coverBackFaces.map(\.imageID) == [10])
        #expect(try index(["Back", "Spine", "Tray"]).coverBackFaces.map(\.imageID) == [10, 12, 11])
    }

    @Test func flipsWrapInBothDirections() {
        #expect(coverFace(afterSteps: 5, backs: 0) == 0)
        #expect(coverFace(afterSteps: 1, backs: 1) == 1 && coverFace(afterSteps: 2, backs: 1) == 0 && coverFace(afterSteps: -1, backs: 1) == 1)
        #expect(coverFace(afterSteps: -1, backs: 3) == 3 && coverFace(afterSteps: 4, backs: 3) == 0)
    }

    @Test func recordedFixtureFlipsOnlyWithABack() throws {
        let index = try ready("artwork_index")
        #expect(index.coverBackFaces.isEmpty == (index.slotImage("Back") == nil))
    }

    // MARK: Discover peek (idea 9)

    private func peekIndex(images: [(id: Int, types: [String], format: String)], slots: [String: Int], booklet: [Int]?) throws -> ArtworkIndex {
        var json: [String: Any] = [
            "status": "ok", "rgid": "rg", "releases": ["total": 1, "fetched": 1, "empty": 0, "failed": 0],
            "slots": slots.mapValues { ["image_id": $0, "release": "r", "edition": "", "from_owned": true] as [String: Any] },
            "images": images.map { ["image_id": $0.id, "types": $0.types, "format": $0.format] as [String: Any] },
        ]
        if let booklet { json["booklet"] = ["release": "r", "edition": "", "image_ids": booklet] as [String: Any] }
        return try JSONDecoder().decode(ArtworkIndex.self, from: JSONSerialization.data(withJSONObject: json))
    }

    @Test func discoverPeekIsBackThenFirstPageThenMedium() throws {
        let index = try peekIndex(
            images: [(1, ["Front"], "jpg"), (2, ["Back"], "jpg"), (3, ["Booklet"], "jpg"), (4, ["Medium"], "jpg")],
            slots: ["Front": 1, "Back": 2, "Medium": 4], booklet: [3])
        #expect(index.discoverPeek.map(\.imageID) == [2, 3, 4])
    }

    @Test func discoverPeekSkipsPDFPagesAndMissingTypes() throws {
        let index = try peekIndex(
            images: [(5, ["Booklet"], "pdf"), (6, ["Medium"], "jpg")],
            slots: ["Medium": 6], booklet: [5])
        #expect(index.discoverPeek.map(\.imageID) == [6])
        #expect(try peekIndex(images: [(7, ["Front"], "jpg")], slots: ["Front": 7], booklet: nil).discoverPeek.isEmpty)
    }

    @Test func pathCoversAreFrontImagesWithoutPDFsAndNeedTwo() throws {
        let two = try peekIndex(images: [(1, ["Front"], "jpg"), (2, ["Back"], "jpg"), (3, ["Front"], "jpg"), (4, ["Front"], "pdf")], slots: [:], booklet: nil)
        #expect(two.pathCoverFaces.map(\.imageID) == [1, 3])
        let one = try peekIndex(images: [(1, ["Front"], "jpg"), (2, ["Back"], "jpg")], slots: [:], booklet: nil)
        #expect(one.pathCoverFaces.isEmpty)
    }

    @Test func pathCoverCyclingWraps() {
        #expect(nextPathCover(after: 0, count: 3) == 1)
        #expect(nextPathCover(after: 2, count: 3) == 0)
        #expect(nextPathCover(after: 4, count: 0) == 0)
    }

    @Test func roomPhotosAreSessionPicturesOnlyAndCapped() throws {
        let index = try peekIndex(
            images: [(1, ["Front"], "jpg"), (2, ["Other"], "jpg"), (3, ["Liner"], "jpg"), (4, ["Poster"], "jpg"), (5, ["Raw/Unedited"], "jpg"), (6, ["Poster"], "pdf")],
            slots: [:], booklet: nil)
        #expect(index.roomPhotos.map(\.imageID) == [2, 3, 4])
        #expect(roomPhotoLimit == 3)
    }

    @Test func sameRoomNeedsAPhotoOnEitherSide() throws {
        let one = try peekIndex(images: [(2, ["Other"], "jpg")], slots: [:], booklet: nil).roomPhotos
        #expect(hasRoomPhotos(one, []))
        #expect(hasRoomPhotos([], one))
        #expect(!hasRoomPhotos([], []))
    }
}
