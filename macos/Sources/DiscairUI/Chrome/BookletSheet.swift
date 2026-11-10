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

/// The booklet as a two-page spread. Arrow keys turn the pages; a zoom lens follows the pointer and loads the full-resolution file
/// on first use. A PDF booklet opens in PDFKit (two-up, continuous, zoom, arrow keys). Captions are the image's type, edition and
/// the Cover Art Archive comment, as plain text. No text recognition and no credit links.
struct BookletSheet: View {
    let booklet: BookletView
    let close: () -> Void
    @State private var spread = 0
    @State private var lens = true
    @FocusState private var focused: Bool

    private var spreads: [[ArtworkPicture]] { booklet.spreads }

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider()
            Group {
                if let pdf = booklet.pdf, spreads.isEmpty { PDFBookletView(picture: pdf) } else { spreadView }
            }
        }
        .frame(minWidth: 760, idealWidth: 980, minHeight: 600, idealHeight: 760)
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
            if !spreads.isEmpty {
                Text(position).font(.callout).foregroundStyle(.secondary).monospacedDigit()
                Toggle("Zoom lens", isOn: $lens).toggleStyle(.checkbox).help("Hover a page to magnify it")
            }
            Button("Close", action: close).keyboardShortcut(.cancelAction)
        }
        .padding(.horizontal, 16).padding(.vertical, 10)
    }

    private var position: String {
        guard spreads.indices.contains(spread) else { return "" }
        let items = booklet.items
        let ids = spreads[spread].compactMap { p in items.firstIndex { $0.imageID == p.imageID } }.map { $0 + 1 }
        let span = ids.count == 2 ? "Pages \(ids[0])–\(ids[1])" : (ids.first.map { $0 <= booklet.pages.count ? "Page \($0)" : "Image \($0)" } ?? "")
        return "\(span) of \(items.count)"
    }

    private var spreadView: some View {
        HStack(spacing: 8) {
            Button { turn(-1) } label: { Image(systemName: "chevron.left") }
                .buttonStyle(.borderless).disabled(spread == 0).accessibilityLabel("Previous pages").help("Previous pages (left arrow)")
            if spreads.indices.contains(spread) {
                HStack(alignment: .top, spacing: 2) {
                    ForEach(spreads[spread]) { BookletPage(picture: $0, lens: lens) }
                }
            }
            Button { turn(1) } label: { Image(systemName: "chevron.right") }
                .buttonStyle(.borderless).disabled(spread >= spreads.count - 1).accessibilityLabel("Next pages").help("Next pages (right arrow)")
        }
        .padding(12)
    }

    private func turn(_ by: Int) { spread = min(max(spread + by, 0), max(spreads.count - 1, 0)) }
}

/// One page at display size with its caption and the zoom lens.
private struct BookletPage: View {
    let picture: ArtworkPicture
    let lens: Bool
    static let lensRadius: CGFloat = 110
    static let lensZoom: CGFloat = 3
    @Environment(\.artwork) private var store
    @State private var image: NSImage?
    @State private var full: NSImage?
    @State private var hover: CGPoint?

    var body: some View {
        VStack(spacing: 6) {
            GeometryReader { g in
                let box = image.map { fittedRect(image: $0.size, in: g.size) } ?? .zero
                ZStack {
                    if let image { Image(nsImage: image).resizable().scaledToFit() }
                    if lens, let image, let hover, let u = lensUnitPoint(hover, in: box), box.contains(hover) {
                        lensView(image: full ?? image, unit: u, box: box).position(hover).allowsHitTesting(false)
                    }
                }
                .frame(width: g.size.width, height: g.size.height)
                .contentShape(Rectangle())
                .onContinuousHover { phase in
                    switch phase {
                    case .active(let p): hover = p
                    case .ended: hover = nil
                    }
                }
                .task(id: hover != nil && lens) {
                    // The original is asked for the first time the lens is used, never before.
                    guard hover != nil, lens, full == nil, let store else { return }
                    full = await store.albumImage(picture, size: .full)
                }
            }
            Text(picture.label).font(.caption).foregroundStyle(.secondary).lineLimit(2).multilineTextAlignment(.center)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(picture.label)
        .task(id: "\(picture.imageID)|\(store?.generation ?? 0)") {
            guard let store else { return }
            image = await store.albumImage(picture, size: .display)
        }
    }

    private func lensView(image: NSImage, unit: CGPoint, box: CGRect) -> some View {
        let r = Self.lensRadius, z = Self.lensZoom
        return Image(nsImage: image).resizable()
            .frame(width: box.width * z, height: box.height * z)
            .offset(x: r - unit.x * box.width * z, y: r - unit.y * box.height * z)
            .frame(width: r * 2, height: r * 2, alignment: .topLeading)
            .clipShape(Circle())
            .overlay(Circle().stroke(.white.opacity(0.9), lineWidth: 2))
            .shadow(radius: 6)
    }
}

/// A PDF booklet: downloaded whole when the sheet opens (cancelling closes the request), then shown by PDFKit.
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
        view.displayMode = .twoUpContinuous
        view.displaysAsBook = true
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
