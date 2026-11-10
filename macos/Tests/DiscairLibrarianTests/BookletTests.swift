import CoreGraphics
import Foundation
import Testing
@testable import DiscairLibrarian

/// What the Booklet sheet shows and how its spreads and zoom lens are laid out (docs/artwork.md, idea 2).
@Suite struct BookletTests {
    private func pic(_ id: Int, _ type: String, format: String = "jpg") -> ArtworkPicture {
        ArtworkPicture(imageID: id, release: "r", releases: ["r"], edition: "1999 JP CD", types: [type], format: format)
    }

    private func index(pages: [ArtworkPicture], extras: [ArtworkPicture] = [], booklet: Bool = true) throws -> ArtworkIndex {
        let all = pages + extras
        let slots = Dictionary(uniqueKeysWithValues: extras.map { ($0.types[0], ["image_id": $0.imageID, "release": "r", "edition": "", "from_owned": true] as [String: Any]) })
        var object: [String: Any] = ["status": "ok", "rgid": "rg", "slots": slots, "images": all.map { p in
            ["image_id": p.imageID, "release": "r", "releases": ["r"], "edition": "1999 JP CD", "types": p.types, "format": p.format, "approved": true] as [String: Any]
        }]
        if booklet { object["booklet"] = ["release": "r", "edition": "1999 JP CD", "image_ids": pages.map(\.imageID)] }
        return try JSONDecoder().decode(ArtworkIndex.self, from: JSONSerialization.data(withJSONObject: object))
    }

    @Test func noBookletMeansNoSheetEvenWithAPoster() throws {
        #expect(try index(pages: [], extras: [pic(5, "Poster")], booklet: false).bookletView == nil)
    }

    @Test func pagesKeepServerOrderThenStickerObiPoster() throws {
        let view = try index(pages: [pic(3, "Booklet"), pic(1, "Booklet"), pic(2, "Booklet")],
                             extras: [pic(9, "Poster"), pic(8, "Obi"), pic(7, "Sticker")]).bookletView
        #expect(view?.items.map(\.imageID) == [3, 1, 2, 7, 8, 9])
        #expect(view?.pages.count == 3)
        #expect(view?.edition == "1999 JP CD")
    }

    @Test func spreadsStartWithTheCoverAloneThenPairs() {
        #expect(bookletSpreads([1, 2, 3, 4, 5]) == [[1], [2, 3], [4, 5]])
        #expect(bookletSpreads([1, 2, 3, 4]) == [[1], [2, 3], [4]])
        #expect(bookletSpreads([1]) == [[1]])
        #expect(bookletSpreads([Int]()).isEmpty)
    }

    @Test func extrasStandAloneAfterThePageSpreads() throws {
        let view = try #require(try index(pages: [pic(1, "Booklet"), pic(2, "Booklet"), pic(3, "Booklet")], extras: [pic(9, "Poster")]).bookletView)
        #expect(view.spreads.map { $0.map(\.imageID) } == [[1], [2, 3], [9]])
    }

    @Test func aPdfBookletOpensInTheViewerAndNotInASpread() throws {
        let view = try #require(try index(pages: [pic(4, "Booklet", format: "pdf")], extras: [pic(9, "Poster")]).bookletView)
        #expect(view.pdf?.imageID == 4)
        #expect(view.spreads.map { $0.map(\.imageID) } == [[9]])
    }

    @Test func fittedRectCentresThePictureInItsFrame() {
        let r = fittedRect(image: CGSize(width: 100, height: 200), in: CGSize(width: 400, height: 400))
        #expect(r == CGRect(x: 100, y: 0, width: 200, height: 400))
        #expect(fittedRect(image: .zero, in: CGSize(width: 10, height: 10)) == .zero)
    }

    @Test func lensPointIsClampedToThePicture() {
        let frame = CGRect(x: 100, y: 0, width: 200, height: 400)
        #expect(lensUnitPoint(CGPoint(x: 200, y: 200), in: frame) == CGPoint(x: 0.5, y: 0.5))
        #expect(lensUnitPoint(CGPoint(x: 0, y: 900), in: frame) == CGPoint(x: 0, y: 1))
        #expect(lensUnitPoint(CGPoint(x: 5, y: 5), in: .zero) == nil)
    }

    @Test func badgeTextIsThePageCountOrPdf() throws {
        #expect(try index(pages: [pic(1, "Booklet")]).bookletView?.badgeText == "1 page")
        #expect(try index(pages: [pic(1, "Booklet"), pic(2, "Booklet"), pic(3, "Booklet")], extras: [pic(9, "Poster")]).bookletView?.badgeText == "3 pages")
        #expect(try index(pages: [pic(4, "Booklet", format: "pdf")]).bookletView?.badgeText == "PDF")
    }

    @Test func faceKeyChangesWithTheAlbumAndItsImages() throws {
        let a = try index(pages: [pic(1, "Booklet")])
        let b = try index(pages: [pic(1, "Booklet"), pic(2, "Booklet")])
        #expect(a.faceKey != b.faceKey)
    }
}
