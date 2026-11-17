import AppKit
import DiscairLibrarian
import PDFKit
import SwiftUI

/// The pieces of the Booklet sheet (docs/MACOS_PATHS_BOOKLET.md, section 5): the spread on the stage, one page of it, the turn
/// arrows, the edition rows and extras of the sidebar, and the PDF viewer.

/// One spread (one or two pages, or one extra) on the stage. Each page is as tall as fits and keeps its aspect; a pair sits
/// side by side with the gutter shade over the spine and the spread shadow under it. Spreading two fingers zooms the whole spread
/// (loading each page's full-resolution file once the zoom is settled past 1.25), a zoomed spread is dragged to move around it,
/// and a double click puts it back. The zoom is per spread: the sheet gives each spread its own identity, so a turn resets it.
struct BookletSpreadView: View {
    let item: BookletItem
    @State private var zoom: CGFloat = 1
    @GestureState private var pinch: CGFloat = 1
    @State private var offset: CGSize = .zero
    @GestureState private var drag: CGSize = .zero

    private var scale: CGFloat { min(max(zoom * pinch, 1), 6) }

    var body: some View {
        GeometryReader { g in
            let sizes = BookletLayout.fit(aspects: item.pictures.map(BookletLayout.aspect), in: g.size)
            let pair = item.pictures.count > 1
            HStack(spacing: 0) {
                ForEach(Array(item.pictures.enumerated()), id: \.element.imageID) { i, picture in
                    BookletPageImage(picture: picture, wantsFull: zoom > 1.25).frame(width: sizes[i].width, height: sizes[i].height)
                }
            }
            .overlay(alignment: .leading) {
                if pair { Gutter().frame(width: CU.Booklet.gutterWidth).offset(x: sizes[0].width - CU.Booklet.gutterWidth / 2).allowsHitTesting(false) }
            }
            .shadow(color: CU.Booklet.spreadShadow, radius: 40, y: 18)
            .scaleEffect(scale)
            .offset(x: (offset.width + drag.width) * (scale > 1 ? 1 : 0), y: (offset.height + drag.height) * (scale > 1 ? 1 : 0))
            .frame(width: g.size.width, height: g.size.height)
            // The shadow may spill past the stage until the spread is zoomed; then the spread is clipped to the stage.
            .mask { Rectangle().padding(scale > 1 ? 0 : -80) }
            .contentShape(Rectangle())
            .gesture(MagnifyGesture().updating($pinch) { v, state, _ in state = v.magnification }
                .onEnded { v in zoom = min(max(zoom * v.magnification, 1), 6); if zoom == 1 { offset = .zero } })
            .simultaneousGesture(DragGesture().updating($drag) { v, state, _ in if scale > 1 { state = v.translation } }
                .onEnded { v in if scale > 1 { offset.width += v.translation.width; offset.height += v.translation.height } })
            .onTapGesture(count: 2) { withAnimation(.easeOut(duration: 0.2)) { zoom = 1; offset = .zero } }
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

/// One page at display size; its full-resolution file is fetched the first time `wantsFull` is set. Draws nothing until the image
/// arrives, inside the frame the spread gave it, so the spread does not jump.
private struct BookletPageImage: View {
    let picture: ArtworkPicture
    let wantsFull: Bool
    @Environment(\.artwork) private var store
    @State private var image: NSImage?
    @State private var full: NSImage?

    var body: some View {
        ZStack {
            if let shown = full ?? image { Image(nsImage: shown).resizable().scaledToFit() }
        }
        .task(id: "\(picture.imageID)|\(store?.generation ?? 0)") {
            guard let store else { return }
            image = await store.albumImage(picture, size: .display)
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

/// A PDF booklet: downloaded whole when the sheet opens (cancelling closes the request), then shown by PDFKit one page wide.
struct PDFBookletView: View {
    let picture: ArtworkPicture
    @Environment(\.artwork) private var store
    @State private var data: Data?
    @State private var failed = false

    var body: some View {
        ZStack {
            if let data { PDFKitView(data: data) } else if failed {
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

    func makeNSView(context: Context) -> PDFView {
        let view = PDFView()
        view.displayMode = .singlePageContinuous
        view.autoScales = true
        view.delegate = context.coordinator
        view.document = PDFDocument(data: data)
        view.setAccessibilityLabel("PDF booklet")
        return view
    }

    func updateNSView(_ view: PDFView, context: Context) {}
    func makeCoordinator() -> Coordinator { Coordinator() }

    /// A link inside a third-party PDF is never opened from here.
    final class Coordinator: NSObject, PDFViewDelegate {
        func pdfViewWillClick(onLink sender: PDFView, with url: URL) {}
    }
}
