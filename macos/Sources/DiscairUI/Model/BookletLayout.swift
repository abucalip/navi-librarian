import CoreGraphics
import DiscairLibrarian
import Foundation

/// The Booklet sheet's pure rules (docs/MACOS_PATHS_BOOKLET.md, section 5): what each spread or page shows, its label, the position
/// and caption text, the edition rows, and the zoom steps. No view code here, so each rule is tested on its own.
enum BookletMode: Equatable, Sendable { case spread, page }

/// One turn of the booklet: a spread (one or two pages), one page, or one extra.
struct BookletItem: Equatable, Sendable {
    let pictures: [ArtworkPicture]
    /// 1-based page numbers of `pictures`. Empty for an extra, which is not counted as a page.
    let numbers: [Int]
    var isExtra: Bool { numbers.isEmpty }
}

struct BookletCaption: Equatable, Sendable {
    let headline: String
    /// The Cover Art Archive comment in “ ”, nil when the page has none.
    let quote: String?
    let detail: String
}

/// Where one page of the spread is in its loading.
enum BookletPageLoad: Equatable, Sendable { case loading, loaded, failed }

/// What the stage draws for a spread (section 5.9): the pages (each unresolved one keeps its place), or one message for the
/// whole stage while no page has arrived.
enum BookletStage: Equatable, Sendable { case pages, loading, failed }

enum BookletLayout {
    static let loadFailedText = "This page could not be loaded."
    static let zoomRange: ClosedRange<Double> = 1...6
    static let zoomStep = 1.25
    static let keysHint = "← → turn · pinch to zoom · double-click to fit"

    // MARK: Items

    /// Spread mode walks `view.spreads`; Page mode walks the same pictures one by one (section 5.3).
    static func items(_ view: BookletView, mode: BookletMode) -> [BookletItem] {
        let numbers = Dictionary(uniqueKeysWithValues: view.pages.filter { !$0.isPDF }.enumerated().map { ($1.imageID, $0 + 1) })
        let groups = mode == .spread ? view.spreads : view.spreads.flatMap { $0 }.map { [$0] }
        return groups.map { group in BookletItem(pictures: group, numbers: group.compactMap { numbers[$0.imageID] }) }
    }

    /// The number of pages, not counting extras or a PDF.
    static func pageCount(_ view: BookletView) -> Int { view.pages.filter { !$0.isPDF }.count }

    /// Where the current item lands after the mode changes: the item that holds the first page now in view (section 5.3).
    static func index(after mode: BookletMode, from old: BookletMode, at index: Int, in view: BookletView) -> Int {
        let before = items(view, mode: old)
        guard mode != old, before.indices.contains(index), let anchor = before[index].pictures.first?.imageID else { return 0 }
        return items(view, mode: mode).firstIndex { $0.pictures.contains { $0.imageID == anchor } } ?? 0
    }

    /// The index after a turn of `step`, or nil at the ends (the arrows are disabled there).
    static func turned(_ index: Int, by step: Int, count: Int) -> Int? {
        let next = index + step
        return (0..<count).contains(next) ? next : nil
    }

    // MARK: Text

    /// The filmstrip label: "1", "2–3", "16"; an extra reads as its type.
    static func label(_ item: BookletItem) -> String {
        guard let first = item.numbers.first, let last = item.numbers.last else { return extraName(item) }
        return first == last ? "\(first)" : "\(first)–\(last)"
    }

    /// VoiceOver for a filmstrip item: "Pages 2 to 3", "Page 1", or the extra's type.
    static func accessibilityLabel(_ item: BookletItem) -> String {
        guard let first = item.numbers.first, let last = item.numbers.last else { return extraName(item) }
        return first == last ? "Page \(first)" : "Pages \(first) to \(last)"
    }

    /// "Pages 4–5 of 16", "Page 4 of 16", or the extra's type (section 5.3).
    static func position(_ item: BookletItem, pageCount: Int) -> String {
        guard let first = item.numbers.first, let last = item.numbers.last else { return extraName(item) }
        return first == last ? "Page \(first) of \(pageCount)" : "Pages \(first)–\(last) of \(pageCount)"
    }

    /// The three caption lines under the spread (section 5.5).
    static func caption(_ item: BookletItem, edition: String, pageCount: Int) -> BookletCaption {
        let name = edition.trimmingCharacters(in: .whitespacesAndNewlines)
        let head = item.isExtra ? extraName(item) : "\(position(item, pageCount: pageCount)) · Booklet"
        let comments = item.pictures.map { $0.comment.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
        let parts = [size(item), keysHint].compactMap { $0 }
        return BookletCaption(headline: name.isEmpty ? head : item.isExtra ? "\(head) · \(name)" : "\(head), \(name)",
                              quote: comments.isEmpty ? nil : "“\(comments.joined(separator: " / "))”",
                              detail: parts.joined(separator: " · "))
    }

    /// "{w} × {h} px", with " each" for a pair of equal size; nil when unknown, or when a pair differs.
    private static func size(_ item: BookletItem) -> String? {
        let sizes = item.pictures.map { p -> [Int]? in p.width.flatMap { w in p.height.map { [w, $0] } } }
        guard let first = sizes.first, let s = first, sizes.allSatisfy({ $0 == s }) else { return nil }
        return "\(s[0]) × \(s[1]) px" + (sizes.count > 1 ? " each" : "")
    }

    private static func extraName(_ item: BookletItem) -> String { item.pictures.first?.types.first ?? "Image" }

    /// The bar's detail line: "Booklet · 2001 US CD · Pages 4–5 of 16" (section 5.1); the edition is left out when empty.
    static func barDetail(edition: String, item: BookletItem, pageCount: Int) -> String {
        let name = edition.trimmingCharacters(in: .whitespacesAndNewlines)
        return ["Booklet", name.isEmpty ? nil : name, position(item, pageCount: pageCount)].compactMap { $0 }.joined(separator: " · ")
    }

    /// The bar's detail line when the sidebar is replaced by the edition pop-up: the pop-up names the edition (section 5.1).
    static func narrowBarDetail(item: BookletItem, pageCount: Int) -> String { position(item, pageCount: pageCount) }

    /// The bar's detail line for a PDF booklet, "Booklet · 1999 EU CD · PDF, 12 pages"; "PDF, n pages" only once the document is loaded.
    static func pdfBarDetail(edition: String, pages: Int?) -> String {
        let name = edition.trimmingCharacters(in: .whitespacesAndNewlines)
        let count = pages.map { "PDF, \($0) \($0 == 1 ? "page" : "pages")" }
        return ["Booklet", name.isEmpty ? nil : name, count].compactMap { $0 }.joined(separator: " · ")
    }

    // MARK: Stage

    /// Below 900 wide the sidebar gives way to the edition pop-up (section 5.1).
    static func isNarrow(width: CGFloat) -> Bool { width < CU.Booklet.sidebarCollapsesBelow }

    /// The pop-up is only offered when there is more than one edition to choose from.
    static func showsEditionMenu(_ booklets: [BookletView], narrow: Bool) -> Bool { narrow && booklets.count > 1 }

    /// "Loading pages 4–5…", "Loading page 4…", "Loading Obi…".
    static func loadingText(_ item: BookletItem) -> String {
        guard let first = item.numbers.first, let last = item.numbers.last else { return "Loading \(extraName(item))…" }
        return first == last ? "Loading page \(first)…" : "Loading pages \(first)–\(last)…"
    }

    /// One message over the whole stage while no page of the spread has arrived (loading, or all of them failed); otherwise each
    /// page draws its own state in its own place.
    static func stage(_ loads: [BookletPageLoad]) -> BookletStage {
        guard !loads.isEmpty, !loads.contains(.loaded) else { return .pages }
        return loads.contains(.loading) ? .loading : .failed
    }

    /// The filmstrip's items: the pages' (or spreads') indices, then the extras' (they come after a separator).
    static func filmstrip(_ items: [BookletItem]) -> (pages: [Int], extras: [Int]) {
        (items.indices.filter { !items[$0].isExtra }, items.indices.filter { items[$0].isExtra })
    }

    /// The sidebar is drawn unless there is one booklet and no extras (section 5.1).
    static func showsSidebar(_ booklets: [BookletView]) -> Bool {
        booklets.count > 1 || booklets.contains { !$0.extras.isEmpty }
    }

    /// width / height of a page; 1 when the server did not give the size, so a page that is still loading keeps a place.
    static func aspect(_ picture: ArtworkPicture) -> CGFloat {
        guard let w = picture.width, let h = picture.height, w > 0, h > 0 else { return 1 }
        return CGFloat(w) / CGFloat(h)
    }

    /// Each page's size on a stage of `size`: every page has the same height, as tall as fits, and keeps its own aspect (section 5.3).
    static func fit(aspects: [CGFloat], in size: CGSize) -> [CGSize] {
        let total = aspects.reduce(0, +)
        guard total > 0, size.width > 0, size.height > 0 else { return aspects.map { _ in .zero } }
        let height = min(size.height, size.width / total)
        return aspects.map { CGSize(width: $0 * height, height: height) }
    }

    /// The item that shows `picture` first, so choosing an extra jumps to it.
    static func index(of picture: ArtworkPicture, in items: [BookletItem]) -> Int? {
        items.firstIndex { $0.pictures.first?.imageID == picture.imageID }
    }

    // MARK: Editions

    /// The row name: the edition, or "Booklet {n}" (1-based) when it is empty.
    static func editionName(_ view: BookletView, number: Int) -> String {
        let name = view.edition.trimmingCharacters(in: .whitespacesAndNewlines)
        return name.isEmpty ? "Booklet \(number)" : name
    }

    /// "{n} pages · {w} px"; the width is left out when unknown, a PDF booklet reads "PDF" (section 5.2).
    static func editionDetail(_ view: BookletView) -> String {
        if view.pdf != nil, view.pages.allSatisfy(\.isPDF) { return "PDF" }
        let n = pageCount(view)
        let pages = n == 1 ? "1 page" : "\(n) pages"
        guard let w = view.pages.first(where: { !$0.isPDF })?.width else { return pages }
        return "\(pages) · \(w) px"
    }

    /// The row's tag: "Your edition" only for the owned release's booklet (section 5.2, D3); a language tag is D4 and not built.
    static func editionTag(_ view: BookletView) -> String? { view.fromOwned ? "Your edition" : nil }

    static func editionsHeading(count: Int) -> String { "Editions · \(count) \(count == 1 ? "booklet" : "booklets")" }

    /// The VoiceOver announcement when a row is chosen (section 5.2).
    static func announcement(number: Int, of count: Int, edition: String) -> String { "Booklet \(number) of \(count) · \(edition)." }

    // MARK: Zoom

    static func zoomedIn(_ zoom: Double) -> Double { min(zoom * zoomStep, zoomRange.upperBound) }
    static func zoomedOut(_ zoom: Double) -> Double { max(zoom / zoomStep, zoomRange.lowerBound) }

    static func canZoomIn(_ zoom: Double) -> Bool { zoom < zoomRange.upperBound - 0.001 }
    static func canZoomOut(_ zoom: Double) -> Bool { zoom > zoomRange.lowerBound + 0.001 }

    /// The PDF viewer's value: "Fit" while it fits the width itself, otherwise its scale as a percentage (section 5.8).
    static func pdfZoomLabel(scale: Double, autoScales: Bool) -> String { autoScales ? "Fit" : "\(Int((scale * 100).rounded())) %" }

    /// "Fit" at 1, otherwise "{n} %".
    static func zoomLabel(_ zoom: Double) -> String {
        zoom <= zoomRange.lowerBound + 0.001 ? "Fit" : "\(Int((zoom * 100).rounded())) %"
    }

    /// The zoom at which one image pixel is one point: the first page's width over its fitted width, within 1...6.
    /// nil when the width is unknown, so the 1:1 button is disabled.
    static func oneToOne(imageWidth: Int?, fittedWidth: CGFloat) -> Double? {
        guard let imageWidth, imageWidth > 0, fittedWidth > 0 else { return nil }
        return min(max(Double(imageWidth) / Double(fittedWidth), zoomRange.lowerBound), zoomRange.upperBound)
    }
}
