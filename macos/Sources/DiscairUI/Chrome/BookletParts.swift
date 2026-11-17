import AppKit
import DiscairLibrarian
import Observation
import PDFKit
import SwiftUI

/// The pieces of the Booklet sheet (docs/MACOS_PATHS_BOOKLET.md, section 5): the spread on the stage, one page of it, the turn
/// arrows, the edition rows and extras of the sidebar, and the PDF viewer.

/// One spread (one or two pages, or one extra) on the stage. Each page is as tall as fits and keeps its aspect; a pair sits
/// side by side with the gutter shade over the spine and the spread shadow under it. The sheet owns the zoom (its buttons and
/// shortcuts change it); spreading two fingers changes it too, loading each page's full-resolution file once the zoom is settled
/// past 1.25. A zoomed spread is dragged to move around it, and a double click puts it back. The sheet gives each spread its own
/// identity, so a turn resets the drag. While no page has arrived the stage says so; a page that is late or failed keeps its place.
struct BookletSpreadView: View {
    let item: BookletItem
    @Binding var zoom: Double
    /// The first page's fitted width at Fit, which the sheet needs for 1:1.
    @Binding var fittedWidth: CGFloat
    @GestureState private var pinch: CGFloat = 1
    @State private var offset: CGSize = .zero
    @GestureState private var drag: CGSize = .zero
    @State private var loads: [Int: BookletPageLoad] = [:]
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private var scale: CGFloat { min(max(CGFloat(zoom) * pinch, 1), CGFloat(BookletLayout.zoomRange.upperBound)) }
    private func load(_ picture: ArtworkPicture) -> BookletPageLoad { loads[picture.imageID] ?? .loading }
    private var stage: BookletStage { BookletLayout.stage(item.pictures.map(load)) }

    var body: some View {
        GeometryReader { g in
            let sizes = BookletLayout.fit(aspects: item.pictures.map(BookletLayout.aspect), in: g.size)
            let pair = item.pictures.count > 1
            let whole = stage != .pages
            ZStack {
                HStack(spacing: 0) {
                    ForEach(Array(item.pictures.enumerated()), id: \.element.imageID) { i, picture in
                        ZStack {
                            BookletPageImage(picture: picture, wantsFull: zoom > 1.25, load: Binding(
                                get: { load(picture) }, set: { loads[picture.imageID] = $0 }))
                            if !whole, load(picture) != .loaded { BookletPageMessage(failed: load(picture) == .failed, text: load(picture) == .failed ? BookletLayout.loadFailedText : nil) }
                        }
                        .frame(width: sizes[i].width, height: sizes[i].height)
                    }
                }
                .overlay(alignment: .leading) {
                    if pair, !whole { Gutter().frame(width: CU.Booklet.gutterWidth).offset(x: sizes[0].width - CU.Booklet.gutterWidth / 2).allowsHitTesting(false) }
                }
                .shadow(color: whole ? .clear : CU.Booklet.spreadShadow, radius: 40, y: 18)
                .opacity(whole ? 0 : 1)
                if whole { BookletPageMessage(failed: stage == .failed, text: stage == .failed ? BookletLayout.loadFailedText : BookletLayout.loadingText(item)) }
            }
            .scaleEffect(scale)
            .offset(x: (offset.width + drag.width) * (scale > 1 ? 1 : 0), y: (offset.height + drag.height) * (scale > 1 ? 1 : 0))
            .frame(width: g.size.width, height: g.size.height)
            // The shadow may spill past the stage until the spread is zoomed; then the spread is clipped to the stage.
            .mask { Rectangle().padding(scale > 1 ? 0 : -80) }
            .contentShape(Rectangle())
            .gesture(MagnifyGesture().updating($pinch) { v, state, _ in state = v.magnification }
                .onEnded { v in zoom = min(max(zoom * Double(v.magnification), BookletLayout.zoomRange.lowerBound), BookletLayout.zoomRange.upperBound) })
            .simultaneousGesture(DragGesture().updating($drag) { v, state, _ in if scale > 1 { state = v.translation } }
                .onEnded { v in if scale > 1 { offset.width += v.translation.width; offset.height += v.translation.height } })
            .onTapGesture(count: 2) { withAnimation(reduceMotion ? nil : .easeOut(duration: 0.2)) { zoom = 1 } }
            .onChange(of: zoom) { _, new in if new <= BookletLayout.zoomRange.lowerBound + 0.001 { offset = .zero } }
            .onAppear { fittedWidth = sizes.first?.width ?? 0 }
            .onChange(of: sizes.first?.width) { _, new in fittedWidth = new ?? 0 }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(item.pictures.map(\.label).joined(separator: ", "))
    }

    /// The shade over the spine: clear, 18 %, 28 % in the middle, 18 %, clear (tokens.json, booklet_colors.gutter).
    private struct Gutter: View {
        var body: some View {
            LinearGradient(stops: [.init(color: .clear, location: 0), .init(color: .black.opacity(0.18), location: 0.45),
                                   .init(color: .black.opacity(0.28), location: 0.5), .init(color: .black.opacity(0.18), location: 0.55),
                                   .init(color: .clear, location: 1)], startPoint: .leading, endPoint: .trailing)
        }
    }
}

/// A page's place while it is not drawn, in `ink2`: a spinner (with its text when it has one), or the failure sentence.
private struct BookletPageMessage: View {
    let failed: Bool
    var text: String?
    var body: some View {
        VStack(spacing: CU.Space.s) {
            if !failed { ProgressView().controlSize(.small) }
            if let text { Text(text).font(CU.Font.callout.font).multilineTextAlignment(.center) }
        }
        .foregroundStyle(CU.Booklet.ink2)
    }
}

/// One page at display size; its full-resolution file is fetched the first time `wantsFull` is set. Draws nothing until the image
/// arrives, inside the frame the spread gave it, so the spread does not jump; `load` tells the spread where it is.
private struct BookletPageImage: View {
    let picture: ArtworkPicture
    let wantsFull: Bool
    @Binding var load: BookletPageLoad
    @Environment(\.artwork) private var store
    @State private var image: NSImage?
    @State private var full: NSImage?

    var body: some View {
        ZStack {
            if let shown = full ?? image { Image(nsImage: shown).resizable().scaledToFit() }
        }
        .task(id: "\(picture.imageID)|\(store?.generation ?? 0)") {
            guard let store else { load = .failed; return }
            load = image == nil ? .loading : .loaded
            let got = await store.albumImage(picture, size: .display)
            if Task.isCancelled { return }
            image = got
            load = got == nil ? .failed : .loaded
        }
        .task(id: wantsFull) {
            // The original is asked for only once a zoom has been settled on (not while a pinch is under way, and not for a
            // stray touch), never on a page that is shown whole: the 500 px display file is what an unzoomed page uses.
            guard wantsFull, full == nil, let store else { return }
            full = await store.albumImage(picture, size: .full)
        }
    }
}

/// A turn arrow at the stage's edge: 32 × 56, `ink2` at rest, a hover ground under the pointer, dimmed when disabled.
struct BookletArrow: View {
    let systemImage: String
    let label: String
    let help: String
    let action: () -> Void
    @Environment(\.isEnabled) private var isEnabled
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var hovering = false

    var body: some View {
        Button(action: action) {
            Image(systemName: systemImage).font(.system(size: 17, weight: .semibold))
                .foregroundStyle(hovering && isEnabled ? CU.Booklet.ink : CU.Booklet.ink2)
                .frame(width: CU.Booklet.arrow.width, height: CU.Booklet.arrow.height)
                .background(hovering && isEnabled ? CU.Booklet.arrowHover : .clear, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .opacity(isEnabled ? 1 : 0.35)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { h in withAnimation(reduceMotion ? nil : .easeOut(duration: 0.12)) { hovering = h } }
        .accessibilityLabel(label)
        .help(help)
    }
}

/// One edition of the sidebar: the first page as a 40 pt mini (`doc.richtext` for a PDF), the name, "{n} pages · {w} px".
struct BookletEditionRow: View {
    let booklet: BookletView
    let number: Int
    let selected: Bool
    let action: () -> Void
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var hovering = false

    private var name: String { BookletLayout.editionName(booklet, number: number) }
    private var detail: String { BookletLayout.editionDetail(booklet) }

    var body: some View {
        Button(action: action) {
            HStack(spacing: CU.Space.s) {
                mini.frame(width: CU.Booklet.editionMini, height: CU.Booklet.editionMini)
                    .clipShape(RoundedRectangle(cornerRadius: 3, style: .continuous))
                VStack(alignment: .leading, spacing: 0) {
                    Text(name).font(CU.Font.headline.font).foregroundStyle(CU.Booklet.ink).lineLimit(1)
                    Text(detail).font(CU.Font.caption.font).monospacedDigit()
                        .foregroundStyle(selected ? CU.Booklet.selectedInk2 : CU.Booklet.ink2).lineLimit(1)
                }
                Spacer(minLength: 0)
            }
            .padding(CU.Space.s)
            .background(selected ? CU.Booklet.selectedRow : hovering ? CU.Booklet.hover : .clear, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay { if selected { RoundedRectangle(cornerRadius: 8, style: .continuous).strokeBorder(CU.Booklet.stageAccent.opacity(0.6), lineWidth: 1) } }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { h in withAnimation(reduceMotion ? nil : .easeOut(duration: 0.12)) { hovering = h } }
        .accessibilityLabel("\(name), \(detail)")
        .accessibilityAddTraits(selected ? .isSelected : [])
    }

    @ViewBuilder private var mini: some View {
        if let first = booklet.pages.first(where: { !$0.isPDF }) {
            AlbumPictureView(picture: first, size: .thumb, fill: true)
        } else {
            Image(systemName: "doc.richtext").font(.system(size: 18)).foregroundStyle(CU.Booklet.ink2)
        }
    }
}

/// One extra (Sticker, Obi, Poster) in the sidebar's grid: a 56 pt thumbnail with its type under it; the chosen one has the ring.
struct BookletExtraButton: View {
    let picture: ArtworkPicture
    let selected: Bool
    let action: () -> Void
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var hovering = false

    private var name: String { picture.types.first ?? "Image" }

    var body: some View {
        Button(action: action) {
            VStack(spacing: 4) {
                AlbumPictureView(picture: picture, size: .thumb, fill: true)
                    .frame(width: CU.Booklet.extraThumb, height: CU.Booklet.extraThumb)
                    .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                    .overlay { if selected { RoundedRectangle(cornerRadius: 4, style: .continuous).strokeBorder(CU.Booklet.stageAccent, lineWidth: CU.Booklet.thumbRing) } }
                Text(name).font(CU.Font.caption.font).foregroundStyle(selected ? CU.Booklet.ink : CU.Booklet.ink2).lineLimit(1)
            }
            .padding(4)
            .frame(maxWidth: .infinity)
            .background(hovering ? CU.Booklet.hover : .clear, in: RoundedRectangle(cornerRadius: 6, style: .continuous))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { h in withAnimation(reduceMotion ? nil : .easeOut(duration: 0.12)) { hovering = h } }
        .accessibilityLabel(name)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }
}

/// Drives the PDF booklet's PDFView from the bar's zoom buttons, and tells the bar the page count and the scale. The view reports
/// itself when PDFKit makes it; nothing is kept once the sheet closes.
@MainActor @Observable
final class PDFZoomController {
    private(set) var pages: Int?
    private(set) var label = "Fit"
    private(set) var canZoomIn = true
    private(set) var canZoomOut = true
    @ObservationIgnored private weak var view: PDFView?
    @ObservationIgnored private var observer: (any NSObjectProtocol)?

    func attach(_ view: PDFView) {
        self.view = view
        pages = view.document?.pageCount
        if let old = observer { NotificationCenter.default.removeObserver(old) }
        observer = NotificationCenter.default.addObserver(forName: .PDFViewScaleChanged, object: view, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated { self?.refresh() }
        }
        refresh()
    }

    func zoomIn() { view?.zoomIn(nil); refresh() }
    func zoomOut() { view?.zoomOut(nil); refresh() }
    func fit() { view?.autoScales = true; refresh() }
    /// 1:1 for a PDF is a scale factor of 1 (section 5.8).
    func actualSize() { view?.autoScales = false; view?.scaleFactor = 1; refresh() }

    private func refresh() {
        guard let view else { return }
        label = BookletLayout.pdfZoomLabel(scale: Double(view.scaleFactor), autoScales: view.autoScales)
        canZoomIn = view.canZoomIn
        canZoomOut = view.canZoomOut
    }
}

/// A PDF booklet: downloaded whole when the sheet opens (cancelling closes the request), then shown by PDFKit one page wide.
struct PDFBookletView: View {
    let picture: ArtworkPicture
    let zoom: PDFZoomController
    @Environment(\.artwork) private var store
    @State private var data: Data?
    @State private var failed = false

    var body: some View {
        ZStack {
            if let data { PDFKitView(data: data, zoom: zoom) } else if failed {
                Text("The booklet could not be opened.").foregroundStyle(.secondary)
            } else {
                VStack(spacing: 8) { ProgressView(); Text("Downloading the booklet…").font(.callout).foregroundStyle(.secondary) }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .task(id: picture.imageID) {
            guard let store else { failed = true; return }
            let got = await store.albumPDF(picture)
            if Task.isCancelled { return }
            if let got { data = got } else { failed = true }
        }
    }
}

private struct PDFKitView: NSViewRepresentable {
    let data: Data
    let zoom: PDFZoomController

    func makeNSView(context: Context) -> PDFView {
        let view = PDFView()
        view.displayMode = .singlePageContinuous
        view.autoScales = true
        view.delegate = context.coordinator
        view.document = PDFDocument(data: data)
        view.setAccessibilityLabel("PDF booklet")
        zoom.attach(view)
        return view
    }

    func updateNSView(_ view: PDFView, context: Context) {}
    func makeCoordinator() -> Coordinator { Coordinator() }

    /// A link inside a third-party PDF is never opened from here.
    final class Coordinator: NSObject, PDFViewDelegate {
        func pdfViewWillClick(onLink sender: PDFView, with url: URL) {}
    }
}

/// One item of the filmstrip: its pages at 30 × 38 side by side (a 1 pt gap), the number or type under them. The current item has
/// the 2 pt `stageAccent` ring and the primary ink.
struct BookletFilmstripItem: View {
    let item: BookletItem
    let current: Bool
    let action: () -> Void
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var hovering = false

    var body: some View {
        Button(action: action) {
            VStack(spacing: 4) {
                HStack(spacing: 1) {
                    ForEach(item.pictures) { picture in
                        AlbumPictureView(picture: picture, size: .thumb, fill: true)
                            .frame(width: CU.Booklet.thumbPage.width, height: CU.Booklet.thumbPage.height).clipped()
                    }
                }
                .padding(2)
                .overlay { if current { RoundedRectangle(cornerRadius: 3, style: .continuous).strokeBorder(CU.Booklet.stageAccent, lineWidth: CU.Booklet.thumbRing) } }
                Text(BookletLayout.label(item)).font(CU.Font.caption.font).monospacedDigit()
                    .foregroundStyle(current ? CU.Booklet.ink : CU.Booklet.ink2).lineLimit(1)
            }
            .padding(4)
            .background(hovering ? CU.Booklet.hover : .clear, in: RoundedRectangle(cornerRadius: 6, style: .continuous))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { h in withAnimation(reduceMotion ? nil : .easeOut(duration: 0.12)) { hovering = h } }
        .accessibilityLabel(BookletLayout.accessibilityLabel(item))
        .accessibilityAddTraits(current ? .isSelected : [])
    }
}

/// The filmstrip under the caption: every spread (or page), then a separator and the extras. The current item is kept in view
/// with a one-shot scroll (none under Reduce Motion); clicking one jumps to it.
struct BookletFilmstrip: View {
    let items: [BookletItem]
    let index: Int
    let jump: (Int) -> Void
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        let parts = BookletLayout.filmstrip(items)
        ScrollViewReader { proxy in
            ScrollView(.horizontal, showsIndicators: false) {
                LazyHStack(alignment: .bottom, spacing: CU.Space.s) {
                    ForEach(parts.pages, id: \.self) { i in BookletFilmstripItem(item: items[i], current: i == index) { jump(i) }.id(i) }
                    if !parts.extras.isEmpty {
                        Rectangle().fill(CU.Booklet.rule).frame(width: 1).padding(.horizontal, 4)
                        ForEach(parts.extras, id: \.self) { i in BookletFilmstripItem(item: items[i], current: i == index) { jump(i) }.id(i) }
                    }
                }
                .padding(.horizontal, CU.Space.m)
                .padding(.top, CU.Space.s).padding(.bottom, CU.Space.m)
            }
            .onAppear { proxy.scrollTo(index, anchor: .center) }
            .onChange(of: index) { _, new in withAnimation(reduceMotion ? nil : .easeOut(duration: 0.12)) { proxy.scrollTo(new, anchor: .center) } }
            .frame(height: CU.Booklet.thumbPage.height + 60)
            .overlay(alignment: .top) { Rectangle().fill(CU.Booklet.rule).frame(height: 1) }
        }
    }
}

/// A zoom button of the bar: `control` ground, 28 × 26, radius 7 (a label of "1:1" is wider text in the same box).
struct BookletZoomButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.font(CU.Font.callout.font.weight(.semibold)).foregroundStyle(CU.Booklet.ink)
            .frame(minWidth: 28).frame(height: 26)
            .background(CU.Booklet.control.opacity(configuration.isPressed ? 0.7 : 1), in: RoundedRectangle(cornerRadius: 7, style: .continuous))
            .opacity(isEnabled ? 1 : 0.4)
    }
}
