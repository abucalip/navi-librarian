import CoreGraphics
import Testing
@testable import DiscairLibrarian
@testable import DiscairUI

/// The Booklet sheet's pure rules (docs/MACOS_PATHS_BOOKLET.md, section 5).
@Suite struct BookletLayoutTests {
    private func pic(_ id: Int, _ type: String = "Booklet", w: Int? = 1200, h: Int? = 1200, comment: String = "", format: String = "jpg") -> ArtworkPicture {
        ArtworkPicture(imageID: id, release: "r", releases: ["r"], edition: "1999 JP CD", types: [type], comment: comment, width: w, height: h, format: format)
    }

    private func view(pages: Int, extras: [String] = [], edition: String = "1999 JP CD") -> BookletView {
        BookletView(edition: edition, pages: (1...max(pages, 1)).prefix(pages).map { pic($0) },
                    extras: extras.enumerated().map { pic(100 + $0, $1) })
    }

    // MARK: Items and labels

    @Test func spreadItemsAreCoverPairsThenOddLastThenExtras() {
        let items = BookletLayout.items(view(pages: 6, extras: ["Obi"]), mode: .spread)
        #expect(items.map(\.numbers) == [[1], [2, 3], [4, 5], [6], []])
        #expect(items.map(BookletLayout.label) == ["1", "2–3", "4–5", "6", "Obi"])
        #expect(items.last?.isExtra == true)
    }

    @Test func pageItemsAreOneEachInTodaysOrder() {
        let items = BookletLayout.items(view(pages: 3, extras: ["Sticker", "Poster"]), mode: .page)
        #expect(items.map(\.numbers) == [[1], [2], [3], [], []])
        #expect(items.map(BookletLayout.label) == ["1", "2", "3", "Sticker", "Poster"])
    }

    @Test func aPdfIsNotAPageAndExtrasAreNotCounted() {
        let v = BookletView(edition: "", pages: [pic(1), pic(2, format: "pdf"), pic(3)], extras: [pic(9, "Obi")])
        #expect(BookletLayout.pageCount(v) == 2)
        #expect(BookletLayout.items(v, mode: .spread).map(\.numbers) == [[1], [2], []])
    }

    @Test func accessibilityLabelsNamePagesOrTheExtra() {
        let items = BookletLayout.items(view(pages: 3, extras: ["Obi"]), mode: .spread)
        #expect(items.map(BookletLayout.accessibilityLabel) == ["Page 1", "Pages 2 to 3", "Obi"])
    }

    // MARK: Position and caption

    @Test func positionTextByModeAndExtra() {
        let v = view(pages: 16, extras: ["Obi"])
        let spreads = BookletLayout.items(v, mode: .spread), pages = BookletLayout.items(v, mode: .page)
        #expect(BookletLayout.position(spreads[2], pageCount: 16) == "Pages 4–5 of 16")
        #expect(BookletLayout.position(pages[3], pageCount: 16) == "Page 4 of 16")
        #expect(BookletLayout.position(spreads[0], pageCount: 16) == "Page 1 of 16")
        #expect(BookletLayout.position(spreads.last!, pageCount: 16) == "Obi")
    }

    @Test func captionForAPairWithCommentsJoinsThemAndSaysEach() {
        let v = BookletView(edition: "1999 JP CD", pages: [pic(1), pic(2, comment: " Inside left "), pic(3, comment: "Inside right")], extras: [])
        let c = BookletLayout.caption(BookletLayout.items(v, mode: .spread)[1], edition: v.edition, pageCount: 3)
        #expect(c.headline == "Pages 2–3 of 3 · Booklet, 1999 JP CD")
        #expect(c.quote == "“Inside left / Inside right”")
        #expect(c.detail == "1200 × 1200 px each · ← → turn · pinch to zoom · double-click to fit")
    }

    @Test func captionWithoutCommentsOrSizeKeepsOnlyTheHint() {
        let v = BookletView(edition: "1999 JP CD", pages: [pic(1, w: nil, h: nil)], extras: [])
        let c = BookletLayout.caption(BookletLayout.items(v, mode: .spread)[0], edition: v.edition, pageCount: 1)
        #expect(c.quote == nil)
        #expect(c.detail == BookletLayout.keysHint)
    }

    @Test func aPairOfDifferentSizesLeavesTheSizeOut() {
        let v = BookletView(edition: "x", pages: [pic(1), pic(2, w: 800), pic(3)], extras: [])
        #expect(BookletLayout.caption(BookletLayout.items(v, mode: .spread)[1], edition: "x", pageCount: 3).detail == BookletLayout.keysHint)
    }

    @Test func aSinglePageSaysItsSizeWithoutEach() {
        let v = BookletView(edition: "x", pages: [pic(1, w: 900, h: 1100)], extras: [])
        #expect(BookletLayout.caption(BookletLayout.items(v, mode: .page)[0], edition: "x", pageCount: 1).detail.hasPrefix("900 × 1100 px · ← →"))
    }

    @Test func extraCaptionReadsTypeThenEdition() {
        let v = view(pages: 2, extras: ["Obi"])
        let c = BookletLayout.caption(BookletLayout.items(v, mode: .spread).last!, edition: v.edition, pageCount: 2)
        #expect(c.headline == "Obi · 1999 JP CD")
    }

    @Test func emptyEditionDropsTheSuffix() {
        let v = view(pages: 2, extras: ["Obi"], edition: "")
        let items = BookletLayout.items(v, mode: .spread)
        #expect(BookletLayout.caption(items[0], edition: "", pageCount: 2).headline == "Page 1 of 2 · Booklet")
        #expect(BookletLayout.caption(items.last!, edition: "", pageCount: 2).headline == "Obi")
    }

    // MARK: Editions

    @Test func onlyTheOwnedEditionGetsTheYourEditionTag() {
        #expect(BookletLayout.editionTag(view(pages: 3)) == nil)
        var owned = view(pages: 3)
        owned.fromOwned = true
        #expect(BookletLayout.editionTag(owned) == "Your edition")
    }

    @Test func editionDetailCoversPagesWidthUnknownWidthAndPdf() {
        #expect(BookletLayout.editionDetail(view(pages: 16)) == "16 pages · 1200 px")
        #expect(BookletLayout.editionDetail(view(pages: 1)) == "1 page · 1200 px")
        #expect(BookletLayout.editionDetail(BookletView(edition: "", pages: [pic(1, w: nil), pic(2, w: nil)], extras: [])) == "2 pages")
        #expect(BookletLayout.editionDetail(BookletView(edition: "", pages: [pic(1, format: "pdf")], extras: [])) == "PDF")
    }

    @Test func editionNameFallsBackToBookletNumber() {
        #expect(BookletLayout.editionName(view(pages: 2, edition: "  "), number: 2) == "Booklet 2")
        #expect(BookletLayout.editionName(view(pages: 2), number: 1) == "1999 JP CD")
    }

    @Test func headingAndAnnouncement() {
        #expect(BookletLayout.editionsHeading(count: 1) == "Editions · 1 booklet")
        #expect(BookletLayout.editionsHeading(count: 3) == "Editions · 3 booklets")
        #expect(BookletLayout.announcement(number: 2, of: 3, edition: "2004 DE CD") == "Booklet 2 of 3 · 2004 DE CD.")
    }

    // MARK: Zoom

    @Test func zoomStepsStayInRangeAndLabelFit() {
        #expect(BookletLayout.zoomedIn(1) == 1.25)
        #expect(BookletLayout.zoomedIn(5.5) == 6)
        #expect(BookletLayout.zoomedOut(1.25) == 1)
        #expect(BookletLayout.zoomedOut(1) == 1)
        #expect(BookletLayout.zoomLabel(1) == "Fit")
        #expect(BookletLayout.zoomLabel(1.25) == "125 %")
        #expect(BookletLayout.zoomLabel(BookletLayout.zoomedIn(1.25)) == "156 %")
    }

    @Test func oneToOneIsImageOverFittedClampedAndNilWhenUnknown() {
        #expect(BookletLayout.oneToOne(imageWidth: 1200, fittedWidth: 400) == 3)
        #expect(BookletLayout.oneToOne(imageWidth: 5000, fittedWidth: 400) == 6)
        #expect(BookletLayout.oneToOne(imageWidth: 300, fittedWidth: 400) == 1)
        #expect(BookletLayout.oneToOne(imageWidth: nil, fittedWidth: 400) == nil)
        #expect(BookletLayout.oneToOne(imageWidth: 1200, fittedWidth: 0) == nil)
    }

    // MARK: Turning and mode switch

    @Test func turnsStopAtTheEnds() {
        #expect(BookletLayout.turned(0, by: -1, count: 4) == nil)
        #expect(BookletLayout.turned(3, by: 1, count: 4) == nil)
        #expect(BookletLayout.turned(1, by: 1, count: 4) == 2)
    }

    @Test func switchingModeKeepsThePageInView() {
        let v = view(pages: 6, extras: ["Obi"])
        // page 5 is page-item 4; its spread (4–5) is spread-item 2
        #expect(BookletLayout.index(after: .spread, from: .page, at: 4, in: v) == 2)
        // spread 4–5 (item 2) goes back to its first page, page-item 3
        #expect(BookletLayout.index(after: .page, from: .spread, at: 2, in: v) == 3)
        // the extra stays the extra
        #expect(BookletLayout.index(after: .page, from: .spread, at: 4, in: v) == 6)
        #expect(BookletLayout.index(after: .spread, from: .page, at: 6, in: v) == 4)
        #expect(BookletLayout.index(after: .spread, from: .spread, at: 2, in: v) == 0)
    }

    // MARK: Bar, sidebar and stage (B2)

    @Test func barDetailNamesEditionAndPosition() {
        let v = view(pages: 16, extras: ["Obi"])
        let items = BookletLayout.items(v, mode: .spread)
        #expect(BookletLayout.barDetail(edition: "2001 US CD", item: items[2], pageCount: 16) == "Booklet · 2001 US CD · Pages 4–5 of 16")
        #expect(BookletLayout.barDetail(edition: " ", item: items[0], pageCount: 16) == "Booklet · Page 1 of 16")
        #expect(BookletLayout.barDetail(edition: "2001 US CD", item: items.last!, pageCount: 16) == "Booklet · 2001 US CD · Obi")
    }

    @Test func sidebarIsDrawnUnlessOneBookletAndNoExtras() {
        #expect(!BookletLayout.showsSidebar([view(pages: 4)]))
        #expect(BookletLayout.showsSidebar([view(pages: 4, extras: ["Obi"])]))
        #expect(BookletLayout.showsSidebar([view(pages: 4), view(pages: 2)]))
    }

    @Test func pagesShareTheStageHeightAndKeepTheirAspect() {
        // two square pages on a wide stage: limited by height
        let wide = BookletLayout.fit(aspects: [1, 1], in: CGSize(width: 1000, height: 400))
        #expect(wide == [CGSize(width: 400, height: 400), CGSize(width: 400, height: 400)])
        // on a narrow stage: limited by width, height shrinks to match
        let narrow = BookletLayout.fit(aspects: [1, 1], in: CGSize(width: 400, height: 400))
        #expect(narrow == [CGSize(width: 200, height: 200), CGSize(width: 200, height: 200)])
        // unequal pages keep their own widths at one height
        let mixed = BookletLayout.fit(aspects: [0.5, 1], in: CGSize(width: 600, height: 300))
        #expect(mixed == [CGSize(width: 150, height: 300), CGSize(width: 300, height: 300)])
        #expect(BookletLayout.fit(aspects: [1], in: .zero) == [.zero])
    }

    @Test func aspectFallsBackToSquareWhenTheSizeIsUnknown() {
        #expect(BookletLayout.aspect(pic(1, w: 900, h: 600)) == 1.5)
        #expect(BookletLayout.aspect(pic(1, w: nil, h: nil)) == 1)
        #expect(BookletLayout.aspect(pic(1, w: 0, h: 10)) == 1)
    }

    @Test func choosingAnExtraJumpsToItsItem() {
        let v = view(pages: 4, extras: ["Obi", "Poster"])
        let spreads = BookletLayout.items(v, mode: .spread), pages = BookletLayout.items(v, mode: .page)
        #expect(BookletLayout.index(of: v.extras[1], in: spreads) == 4)
        #expect(BookletLayout.index(of: v.extras[0], in: pages) == 4)
        #expect(BookletLayout.index(of: pic(999), in: spreads) == nil)
    }

    // MARK: B3: filmstrip, narrow layout, loading, PDF, zoom limits

    @Test func theFilmstripPutsExtrasAfterThePages() {
        let v = view(pages: 4, extras: ["Obi", "Sticker"])
        let spreads = BookletLayout.filmstrip(BookletLayout.items(v, mode: .spread))
        #expect(spreads.pages == [0, 1, 2] && spreads.extras == [3, 4])
        let pages = BookletLayout.filmstrip(BookletLayout.items(v, mode: .page))
        #expect(pages.pages == [0, 1, 2, 3] && pages.extras == [4, 5])
        #expect(BookletLayout.filmstrip(BookletLayout.items(view(pages: 2), mode: .spread)).extras.isEmpty)
    }

    @Test func theSidebarGivesWayBelowNineHundredAndOnlyMoreThanOneEditionGetsAPopUp() {
        #expect(BookletLayout.isNarrow(width: 899) && !BookletLayout.isNarrow(width: 900))
        #expect(BookletLayout.showsEditionMenu([view(pages: 4), view(pages: 2)], narrow: true))
        #expect(!BookletLayout.showsEditionMenu([view(pages: 4), view(pages: 2)], narrow: false))
        #expect(!BookletLayout.showsEditionMenu([view(pages: 4, extras: ["Obi"])], narrow: true))
        let item = BookletLayout.items(view(pages: 16), mode: .spread)[2]
        #expect(BookletLayout.narrowBarDetail(item: item, pageCount: 16) == "Pages 4–5 of 16")
    }

    @Test func loadingTextNamesTheSpreadOrExtra() {
        let items = BookletLayout.items(view(pages: 6, extras: ["Obi"]), mode: .spread)
        #expect(BookletLayout.loadingText(items[2]) == "Loading pages 4–5…")
        #expect(BookletLayout.loadingText(items[0]) == "Loading page 1…")
        #expect(BookletLayout.loadingText(items[4]) == "Loading Obi…")
    }

    @Test func theStageSaysLoadingOrFailedOnlyWhileNoPageHasArrived() {
        #expect(BookletLayout.stage([.loading, .loading]) == .loading)
        #expect(BookletLayout.stage([.loading, .failed]) == .loading)
        #expect(BookletLayout.stage([.failed, .failed]) == .failed)
        #expect(BookletLayout.stage([.loaded, .loading]) == .pages)
        #expect(BookletLayout.stage([.loaded, .failed]) == .pages)
        #expect(BookletLayout.stage([.failed]) == .failed)
        #expect(BookletLayout.stage([]) == .pages)
        #expect(BookletLayout.loadFailedText == "This page could not be loaded.")
    }

    @Test func pdfBarDetailCountsPagesOnlyOnceLoaded() {
        #expect(BookletLayout.pdfBarDetail(edition: "1999 EU CD", pages: nil) == "Booklet · 1999 EU CD")
        #expect(BookletLayout.pdfBarDetail(edition: "1999 EU CD", pages: 12) == "Booklet · 1999 EU CD · PDF, 12 pages")
        #expect(BookletLayout.pdfBarDetail(edition: " ", pages: 1) == "Booklet · PDF, 1 page")
    }

    @Test func pdfZoomLabelIsFitUntilTheScaleIsSet() {
        #expect(BookletLayout.pdfZoomLabel(scale: 0.83, autoScales: true) == "Fit")
        #expect(BookletLayout.pdfZoomLabel(scale: 1.25, autoScales: false) == "125 %")
    }

    @Test func zoomButtonsStopAtTheEnds() {
        #expect(!BookletLayout.canZoomOut(1) && BookletLayout.canZoomOut(1.25))
        #expect(BookletLayout.canZoomIn(5) && !BookletLayout.canZoomIn(6))
        #expect(BookletLayout.canZoomIn(BookletLayout.zoomedOut(1)))
    }
}
