import AppKit
import DiscairLibrarian
import PDFKit
import SwiftUI

/// Presents the album's booklet (docs/artwork.md, idea 2). The index is asked for once the release group is known (the store keeps
/// a built one, so the cover's own lookup and this one share it); with no booklet this draws nothing: no button, no placeholder.
/// The theme draws its own button through `button`.
struct BookletOpener<Button: View>: View {
    let rgid: String?
    /// An index the caller already holds; used instead of asking by `rgid`.
    var index: ArtworkIndex?
    @ViewBuilder let button: (@escaping () -> Void) -> Button
    @Environment(\.artwork) private var store
    @State private var booklet: BookletView?
    @State private var showing = false

    var body: some View {
        Group {
            if booklet != nil { button { showing = true } }
        }
        .task(id: "\(rgid ?? "")|\(index?.faceKey ?? "")|\(store?.generation ?? 0)") {
            booklet = nil
            if let index { booklet = index.bookletView; return }
            guard let rgid, !rgid.isEmpty, let store else { return }
            if case .ready(let index) = await store.artworkIndex(rgid: rgid, release: nil), !Task.isCancelled { booklet = index.bookletView }
        }
        .sheet(isPresented: $showing) { if let booklet { BookletSheet(booklet: booklet) { showing = false } } }
    }
}

/// The booklet one page at a time, centred in the window. Arrow keys turn the pages; pinch zoom loads the full-resolution file
/// on first use. A PDF booklet opens in PDFKit (one page wide, continuous, zoom, arrow keys). Captions are the image's type,
/// edition and the Cover Art Archive comment, as plain text. No text recognition and no credit links.
struct BookletSheet: View {
    let booklet: BookletView
    let close: () -> Void
    @State private var page = 0
    @FocusState private var focused: Bool

    /// Every bitmap page and extra once, in the booklet's order.
    private var pages: [ArtworkPicture] { booklet.spreads.flatMap { $0 } }

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider()
            Group {
                if let pdf = booklet.pdf, pages.isEmpty { PDFBookletView(picture: pdf) } else { pageView }
            }
        }
        .frame(minWidth: 760, idealWidth: 980, minHeight: 600, idealHeight: 760)
        .background(Color(white: 0.09))
        .foregroundStyle(.white)
        .tint(CU.accent)
        .preferredColorScheme(.dark)
        .focusable()
        .focused($focused)
        .focusEffectDisabled()
        .onAppear { focused = true }
        .onKeyPress(.leftArrow) { turn(-1); return .handled }
        .onKeyPress(.rightArrow) { turn(1); return .handled }
        .onExitCommand { close() }
    }

    private var header: some View {
        HStack(spacing: 12) {
            Text(booklet.edition.isEmpty ? "Booklet" : "Booklet · \(booklet.edition)").font(.headline).accessibilityAddTraits(.isHeader)
            Spacer()
            if !pages.isEmpty {
                Text(position).font(.callout).foregroundStyle(.white.opacity(0.7)).monospacedDigit()
                Text("Pinch to zoom").font(.callout).foregroundStyle(.white.opacity(0.55))
            }
            Button("Close", action: close).keyboardShortcut(.cancelAction).buttonStyle(CapsuleButtonStyle(small: true))
        }
        .padding(.horizontal, 16).padding(.vertical, 10)
    }

    private var position: String {
        guard pages.indices.contains(page) else { return "" }
        let items = booklet.items
        let n = items.firstIndex { $0.imageID == pages[page].imageID }.map { $0 + 1 } ?? 0
        let span = n <= booklet.pages.count ? "Page \(n)" : "Image \(n)"
        return "\(span) of \(items.count)"
    }

    /// One picture, scaled to fit and centred, with the arrows at the window's edges.
    private var pageView: some View {
        HStack(spacing: 8) {
            Button { turn(-1) } label: { Image(systemName: "chevron.left") }
                .buttonStyle(.borderless).disabled(page == 0).accessibilityLabel("Previous page").help("Previous page (left arrow)")
            if pages.indices.contains(page) {
                BookletPage(picture: pages[page]).id(pages[page].imageID).frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            Button { turn(1) } label: { Image(systemName: "chevron.right") }
                .buttonStyle(.borderless).disabled(page >= pages.count - 1).accessibilityLabel("Next page").help("Next page (right arrow)")
        }
        .padding(12)
    }

    private func turn(_ by: Int) { page = min(max(page + by, 0), max(pages.count - 1, 0)) }
}

/// One page at display size with its caption. Spreading two fingers zooms in (loading the full-resolution file the first time),
/// pinching zooms out; a zoomed page is dragged to move around it, and a double click puts it back.
private struct BookletPage: View {
    let picture: ArtworkPicture
    @Environment(\.artwork) private var store
    @State private var image: NSImage?
    @State private var full: NSImage?
    @State private var zoom: CGFloat = 1
    @GestureState private var pinch: CGFloat = 1
    @State private var offset: CGSize = .zero
    @GestureState private var drag: CGSize = .zero

    private var scale: CGFloat { min(max(zoom * pinch, 1), 6) }

    var body: some View {
        VStack(spacing: 6) {
            GeometryReader { g in
                ZStack {
                    if let shown = full ?? image {
                        Image(nsImage: shown).resizable().scaledToFit()
                            .scaleEffect(scale)
                            .offset(x: (offset.width + drag.width) * (scale > 1 ? 1 : 0), y: (offset.height + drag.height) * (scale > 1 ? 1 : 0))
                    }
                }
                .frame(width: g.size.width, height: g.size.height)
                .clipped()
                .contentShape(Rectangle())
                .gesture(MagnifyGesture().updating($pinch) { v, state, _ in state = v.magnification }
                    .onEnded { v in zoom = min(max(zoom * v.magnification, 1), 6); if zoom == 1 { offset = .zero } })
                .simultaneousGesture(DragGesture().updating($drag) { v, state, _ in if scale > 1 { state = v.translation } }
                    .onEnded { v in if scale > 1 { offset.width += v.translation.width; offset.height += v.translation.height } })
                .onTapGesture(count: 2) { withAnimation(.easeOut(duration: 0.2)) { zoom = 1; offset = .zero } }
                .task(id: zoom > 1.25) {
                    // The original is asked for only once a zoom has been settled on (not while a pinch is under way, and not for a
                    // stray touch), never on a page that is shown whole: the 500 px display file is what an unzoomed page uses.
                    guard zoom > 1.25, full == nil, let store else { return }
                    full = await store.albumImage(picture, size: .full)
                }
            }
            Text(picture.label).font(.caption).foregroundStyle(.white.opacity(0.6)).lineLimit(2).multilineTextAlignment(.center)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(picture.label)
        .task(id: "\(picture.imageID)|\(store?.generation ?? 0)") {
            guard let store else { return }
            image = await store.albumImage(picture, size: .display)
        }
    }
}

/// A PDF booklet: downloaded whole when the sheet opens (cancelling closes the request), then shown by PDFKit one page wide.
private struct PDFBookletView: View {
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
