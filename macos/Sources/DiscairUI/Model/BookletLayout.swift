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

enum BookletLayout {
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

    static func editionsHeading(count: Int) -> String { "Editions · \(count) \(count == 1 ? "booklet" : "booklets")" }

    /// The VoiceOver announcement when a row is chosen (section 5.2).
    static func announcement(number: Int, of count: Int, edition: String) -> String { "Booklet \(number) of \(count) · \(edition)." }

    // MARK: Zoom

    static func zoomedIn(_ zoom: Double) -> Double { min(zoom * zoomStep, zoomRange.upperBound) }
    static func zoomedOut(_ zoom: Double) -> Double { max(zoom / zoomStep, zoomRange.lowerBound) }

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
