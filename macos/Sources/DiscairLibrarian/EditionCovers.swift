import Foundation

/// How many covers a Downloads row shows for the release group it fetches (docs/artwork.md, idea 13).
public let editionCoverLimit = 3

extension ArtworkIndex {
    /// The covers a Downloads row shows (docs/artwork.md, idea 13): the Front images of the release group, best first (the server's
    /// order), never a PDF, at most `editionCoverLimit`. Each carries its edition label. Chosen by type only; taste and play data
    /// play no part. Empty when the group has no Front image, so the row shows nothing extra.
    public var editionCovers: [ArtworkPicture] {
        Array(coverEditions.prefix(editionCoverLimit))
    }
}
