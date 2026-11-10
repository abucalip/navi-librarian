@testable import DiscairLibrarian
import Foundation
import Testing
@testable import DiscairUI

/// The album page carries the release group that keys the cover's artwork index (docs/artwork.md, idea 1).
@Suite struct FlipCoverTests {
    private func related(_ json: String) throws -> AlbumPageRelated {
        try JSONDecoder().decode(AlbumPageEnvelope.self, from: Data(json.utf8)).related
    }

    @Test func releaseGroupIsReadFromTheAlbumSection() throws {
        let page = try related(#"{"sections":{"album":{"available":true,"album":{"name":"A","release_group_mbid":"1edd139d-4779-4057-8e12-13c783674f0d"}}},"done":{}}"#)
        #expect(page.releaseGroupMBID == "1edd139d-4779-4057-8e12-13c783674f0d")
    }

    @Test func missingOrEmptyReleaseGroupIsNilAndNothingElseBreaks() throws {
        #expect(try related(#"{"sections":{"album":{"album":{"release_group_mbid":""}}}}"#).releaseGroupMBID == nil)
        #expect(try related(#"{"sections":{"album":{"album":{"release_group_mbid":7}}}}"#).releaseGroupMBID == nil)
        #expect(try related(#"{"sections":{}}"#).releaseGroupMBID == nil)
    }
}
