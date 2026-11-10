import DiscairLibrarian
import Testing
@testable import DiscairUI

/// A Get carries the album's release group so its Downloads row can show the covers (docs/artwork.md, idea 13). Feedback does not.
@MainActor
@Suite struct EditionCoverGetTests {
    private func album(_ rgid: String?) -> AlbumItem {
        var a = AlbumItem(id: 1, title: "Somethin' Else", artist: "Cannonball Adderley", year: 1958, genre: "", format: "", owned: false, hue: 0)
        a.releaseGroupMBID = rgid
        return a
    }

    @Test func getCarriesAKnownReleaseGroup() {
        let rgid = "1edd139d-4779-4057-8e12-13c783674f0d"
        #expect(AcquisitionModel.getMetadata(album(rgid))["release_group_mbid"] == rgid)
        #expect(AcquisitionModel.metadata(album(rgid))["release_group_mbid"] == nil, "feedback keeps the plain metadata")
    }

    @Test func getOmitsAMissingOrMalformedReleaseGroup() {
        #expect(AcquisitionModel.getMetadata(album(nil))["release_group_mbid"] == nil)
        #expect(AcquisitionModel.getMetadata(album("nope"))["release_group_mbid"] == nil)
    }
}
