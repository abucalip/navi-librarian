import Foundation

/// How many Track images the queue shows at most (docs/artwork.md, idea 6).
public let trackImageLimit = 3

extension ArtworkIndex {
    /// The Track images of the playing album (idea 6): session sheets and studio track lists, shown as cards in the queue while that
    /// album plays. Only images typed Track, in the server's quality order, each once, never a PDF (its preview is not the sheet), at
    /// most `trackImageLimit`. Empty when the album has none, so no card is drawn. Chosen by type only, never by taste or play data.
    public var trackImages: [ArtworkPicture] {
        var seen = Set<Int>()
        let found = images.filter { $0.types.contains("Track") && !$0.isPDF && seen.insert($0.imageID).inserted }
        return Array(found.prefix(trackImageLimit))
    }
}
