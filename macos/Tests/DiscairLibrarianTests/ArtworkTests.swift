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
}
