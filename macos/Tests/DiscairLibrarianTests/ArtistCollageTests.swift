import Foundation
import Testing
@testable import DiscairLibrarian

/// Which album images make the artist collage and in what order (docs/artwork.md, idea 8).
@Suite struct ArtistCollageTests {
    private func pic(_ id: Int, _ types: [String], comment: String = "", format: String = "jpg") -> ArtworkPicture {
        ArtworkPicture(imageID: id, release: "r", types: types, comment: comment, format: format)
    }

    private func index(_ pictures: [ArtworkPicture]) throws -> ArtworkIndex {
        let object: [String: Any] = ["status": "ok", "rgid": "rg", "images": pictures.map { p in
            ["image_id": p.imageID, "release": "r", "releases": ["r"], "edition": "", "types": p.types, "comment": p.comment,
             "format": p.format, "approved": true] as [String: Any]
        }]
        return try JSONDecoder().decode(ArtworkIndex.self, from: JSONSerialization.data(withJSONObject: object))
    }

    @Test func typesAndCommentWordsQualify() {
        #expect(pic(1, ["Other"]).qualifiesForCollage)
        #expect(pic(2, ["Raw/Unedited"]).qualifiesForCollage)
        #expect(pic(3, ["Liner"]).qualifiesForCollage)
        #expect(pic(4, ["Poster"]).qualifiesForCollage)
        #expect(pic(5, [], comment: "Studio session, 1971").qualifiesForCollage)
        #expect(pic(6, ["Booklet"], comment: "band photo").qualifiesForCollage == false)
        #expect(pic(7, [], comment: "The BAND on stage").qualifiesForCollage)
    }

    @Test func packagingAndPDFsNeverQualifyThroughAComment() {
        #expect(pic(1, ["Front"], comment: "studio version").qualifiesForCollage == false)
        #expect(pic(2, ["Medium"], comment: "band label").qualifiesForCollage == false)
        #expect(pic(3, ["Other"], format: "pdf").qualifiesForCollage == false)
        #expect(pic(4, [], comment: "scan of the back").qualifiesForCollage == false)
    }

    @Test func albumsTakeTurnsAndTheSameImageIsOnce() throws {
        let a = try index([pic(1, ["Other"]), pic(2, ["Other"]), pic(3, ["Other"]), pic(4, ["Other"])])
        let b = try index([pic(10, ["Poster"]), pic(1, ["Other"]), pic(11, ["Liner"])])
        let c = artistCollage(from: [("A", "ga", a), ("B", "gb", b)], limit: 12, perAlbum: 3)
        #expect(c.map(\.picture.imageID) == [1, 10, 2, 11, 3])
        #expect(c.map(\.albumTitle) == ["A", "B", "A", "B", "A"])
    }

    @Test func perAlbumAndTotalLimitsHold() throws {
        let a = try index((1...9).map { pic($0, ["Other"]) })
        let b = try index((20...28).map { pic($0, ["Other"]) })
        let c = artistCollage(from: [("A", "ga", a), ("B", "gb", b)], limit: 5, perAlbum: 3)
        #expect(c.map(\.picture.imageID) == [1, 20, 2, 21, 3])
    }

    @Test func tooFewPicturesGiveNoCollage() throws {
        let a = try index([pic(1, ["Other"]), pic(2, ["Other"]), pic(3, ["Other"])])
        #expect(artistCollage(from: [("A", "ga", a)]).isEmpty)
        #expect(artistCollage(from: []).isEmpty)
    }

    @Test func labelNamesTheAlbum() {
        let e = CollageEntry(picture: pic(1, ["Other"], comment: "session"), albumTitle: "Kid A", rgid: "g")
        #expect(e.label == "Other: session, from Kid A")
    }

    @Test func artistAlbumEntryReadsIdAndReleaseGroup() throws {
        let data = Data(#"{"name":"Kid A","key":"radiohead/kid a","year":2000,"owned":true,"id":"al1","release_group_mbid":"b1a9c0e9"}"#.utf8)
        let e = try JSONDecoder().decode(ArtistAlbumEntry.self, from: data)
        #expect(e.albumID == "al1" && e.releaseGroupMBID == "b1a9c0e9")
        let bare = try JSONDecoder().decode(ArtistAlbumEntry.self, from: Data(#"{"name":"X","owned":false,"id":null}"#.utf8))
        #expect(bare.albumID == nil && bare.releaseGroupMBID == nil)
    }
}
