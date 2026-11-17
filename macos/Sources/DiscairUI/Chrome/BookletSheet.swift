import AppKit
import DiscairLibrarian
import PDFKit
import SwiftUI

/// Presents the album's booklet (docs/artwork.md, idea 2). The index is asked for once the release group is known (the store keeps
/// a built one, so the cover's own lookup and this one share it); with no booklet this draws nothing: no button, no placeholder.
/// The theme draws its own button through `button`.
struct BookletOpener<Button: View>: View {
    /// The album's title, shown in the sheet's bar.
    let title: String
    let rgid: String?
    /// An index the caller already holds; used instead of asking by `rgid`.
    var index: ArtworkIndex?
    @ViewBuilder let button: (@escaping () -> Void) -> Button
    @Environment(\.artwork) private var store
    @State private var booklets: [BookletView] = []
    @State private var showing = false

    var body: some View {
        Group {
            if !booklets.isEmpty { button { showing = true } }
        }
        .task(id: "\(rgid ?? "")|\(index?.faceKey ?? "")|\(store?.generation ?? 0)") {
            booklets = []
            if let index { booklets = index.bookletViews; return }
            guard let rgid, !rgid.isEmpty, let store else { return }
            if case .ready(let index) = await store.artworkIndex(rgid: rgid, release: nil), !Task.isCancelled { booklets = index.bookletViews }
        }
        .sheet(isPresented: $showing) { if !booklets.isEmpty { BookletSheet(title: title, booklets: booklets) { showing = false } } }
    }
}

/// The Booklet (docs/MACOS_PATHS_BOOKLET.md, section 5; D1 a: a sheet, closed by Done or Escape). A bar with the album title, the
/// Page/Spread switch and the zoom buttons; a sidebar of editions and extras (left out for one booklet with no extras, and below
/// 900 wide replaced by an edition pop-up in the bar); the spread on a dark stage with turn arrows; a caption; a filmstrip. Arrow
/// keys turn; ⌘+ ⌘− ⌘0 and pinch zoom, and a zoom past 1.25 loads the full-resolution file. A PDF booklet opens in
/// PDFKit (one page wide, continuous), driven by the same buttons. Captions are the image's type, edition and the Cover Art Archive comment, as plain text.
/// No text recognition and no credit links.
struct BookletSheet: View {
    let title: String
    /// Every booklet the album has, best first. The sheet opens on the first.
    let booklets: [BookletView]
    let close: () -> Void
    @State private var current = 0
    @State private var mode: BookletMode
    @State private var index: Int
    @State private var zoom = 1.0
    @State private var fittedWidth: CGFloat = 0
    @State private var pdfZoom = PDFZoomController()
    @FocusState private var focused: Bool
    @State private var narrow = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// `startIndex` and `startMode` are for the render tests; the app opens on the cover in Spread mode.
    init(title: String, booklets: [BookletView], startIndex: Int = 0, startMode: BookletMode = .spread, close: @escaping () -> Void) {
        self.title = title; self.booklets = booklets; self.close = close
        _index = State(initialValue: startIndex); _mode = State(initialValue: startMode)
    }

    private var booklet: BookletView { booklets[min(current, booklets.count - 1)] }
    private var isPDF: Bool { booklet.pdf != nil && booklet.pages.allSatisfy(\.isPDF) && booklet.extras.allSatisfy(\.isPDF) }
    private var items: [BookletItem] { BookletLayout.items(booklet, mode: mode) }
    private var item: BookletItem? { items.indices.contains(index) ? items[index] : nil }
    private var pageCount: Int { BookletLayout.pageCount(booklet) }
    private var showsSidebar: Bool { BookletLayout.showsSidebar(booklets) && !narrow }
    private var extras: [ArtworkPicture] { booklet.extras.filter { !$0.isPDF } }
    private var unit: String { mode == .spread ? "spread" : "page" }

    var body: some View {
        VStack(spacing: 0) {
            bar
            Rectangle().fill(CU.Booklet.rule).frame(height: 1)
            HStack(spacing: 0) {
                if showsSidebar {
                    sidebar
                    Rectangle().fill(CU.Booklet.rule).frame(width: 1)
                }
                main
            }
        }
        .frame(minWidth: CU.Booklet.minSize.width, idealWidth: ideal(CU.Booklet.idealSize.width, along: \.width),
               minHeight: CU.Booklet.minSize.height, idealHeight: ideal(CU.Booklet.idealSize.height, along: \.height))
        .background(CU.Booklet.ground)
        .background { GeometryReader { g in Color.clear.onChange(of: g.size.width, initial: true) { _, w in narrow = BookletLayout.isNarrow(width: w) } } }
        .foregroundStyle(CU.Booklet.ink)
        .tint(CU.Booklet.stageAccent)
        .preferredColorScheme(.dark)
        .focusable()
        .focused($focused)
        .focusEffectDisabled()
        .onAppear { focused = true }
        .onKeyPress(.leftArrow) { turn(-1); return .handled }
        .onKeyPress(.rightArrow) { turn(1); return .handled }
        .onExitCommand { close() }
    }

    /// The ideal size, kept 40 short of the parent window on each axis (section 5.9).
    private func ideal(_ value: CGFloat, along side: KeyPath<CGSize, CGFloat>) -> CGFloat {
        guard let window = NSApp.keyWindow else { return value }
        return min(value, max(window.frame.size[keyPath: side] - 40, 0))
    }

    // MARK: Bar

    private var bar: some View {
        HStack(spacing: CU.Space.s) {
            // With the sidebar, the title starts above the main column, as in the mockup.
            if showsSidebar { Color.clear.frame(width: CU.Booklet.sidebar - CU.Space.m + 1, height: 1) }
            HStack(alignment: .firstTextBaseline, spacing: CU.Space.s) {
                Text(title).font(CU.Font.headline.font).foregroundStyle(CU.Booklet.ink).lineLimit(1)
                    .layoutPriority(1).accessibilityAddTraits(.isHeader)
                if let detail = barDetail {
                    Text(detail).font(CU.Font.body.font).foregroundStyle(CU.Booklet.ink2).lineLimit(1).truncationMode(.tail)
                }
            }
            Spacer(minLength: CU.Space.s)
            // The tools sit 4 apart; the switch and the pop-up keep 8 more after them, and Done 8 before it (components.css .b-tools).
            HStack(spacing: 4) {
                if BookletLayout.showsEditionMenu(booklets, narrow: narrow) { editionMenu }
                if !isPDF { modeSwitch }
                zoomControls
                Button("Done", action: close).keyboardShortcut(.cancelAction).buttonStyle(BookletDoneStyle()).padding(.leading, CU.Space.s)
            }
            .layoutPriority(2)
        }
        .padding(.horizontal, CU.Space.m)
        .frame(height: CU.Booklet.barHeight)
        .background(CU.Booklet.bar)
    }

    /// The bar's detail: with the edition pop-up the edition is named there, so only the position stays.
    private var barDetail: String? {
        if isPDF { return BookletLayout.pdfBarDetail(edition: booklet.edition, pages: pdfZoom.pages) }
        guard let item else { return booklet.edition.isEmpty ? nil : "Booklet · \(booklet.edition)" }
        return BookletLayout.showsEditionMenu(booklets, narrow: narrow) ? BookletLayout.narrowBarDetail(item: item, pageCount: pageCount)
            : BookletLayout.barDetail(edition: booklet.edition, item: item, pageCount: pageCount)
    }

    /// Narrow layout: the editions as a pop-up button in the bar, in place of the sidebar (section 5.1).
    private var editionMenu: some View {
        Menu {
            ForEach(booklets.indices, id: \.self) { i in
                Button { choose(i) } label: {
                    if i == current { Label(BookletLayout.editionName(booklets[i], number: i + 1), systemImage: "checkmark") }
                    else { Text(BookletLayout.editionName(booklets[i], number: i + 1)) }
                }
            }
        } label: {
            HStack(spacing: 4) {
                Text(BookletLayout.editionName(booklet, number: current + 1)).font(CU.Font.callout.font.weight(.semibold)).lineLimit(1)
                Image(systemName: "chevron.down").font(.system(size: 8, weight: .semibold))
            }
            .foregroundStyle(CU.Booklet.ink).padding(.horizontal, 10).frame(height: 26)
            .background(CU.Booklet.control, in: RoundedRectangle(cornerRadius: 7, style: .continuous))
        }
        .menuStyle(.button).buttonStyle(.plain).menuIndicator(.hidden).fixedSize()
        .padding(.trailing, CU.Space.s)
        .accessibilityLabel("Edition")
        .accessibilityValue(BookletLayout.editionName(booklet, number: current + 1))
    }

    // MARK: Zoom

    private var zoomLabel: String { isPDF ? pdfZoom.label : BookletLayout.zoomLabel(zoom) }
    private var canZoomIn: Bool { isPDF ? pdfZoom.canZoomIn : BookletLayout.canZoomIn(zoom) }
    private var canZoomOut: Bool { isPDF ? pdfZoom.canZoomOut : BookletLayout.canZoomOut(zoom) }
    private var oneToOne: Double? {
        guard !isPDF else { return 1 }
        return BookletLayout.oneToOne(imageWidth: item?.pictures.first?.width, fittedWidth: fittedWidth)
    }

    /// − / value / + / 1:1. ⌘+ ⌘− ⌘0 do the same; ⌘= is the unshifted ⌘+ and ⌘0 is Fit, which has no button of its own.
    private var zoomControls: some View {
        HStack(spacing: 4) {
            Button { zoomOutAction() } label: { Image(systemName: "minus").font(CU.Icon.small(.semibold)) }
                .buttonStyle(BookletZoomButtonStyle()).disabled(!canZoomOut)
                .keyboardShortcut("-", modifiers: .command).help("Zoom out (⌘−)").accessibilityLabel("Zoom out")
            Text(zoomLabel).font(CU.Font.callout.font.monospaced()).foregroundStyle(CU.Booklet.ink2)
                .frame(width: CU.Booklet.zoomValueWidth).accessibilityLabel("Zoom").accessibilityValue(zoomLabel)
            Button { zoomInAction() } label: { Image(systemName: "plus").font(CU.Icon.small(.semibold)) }
                .buttonStyle(BookletZoomButtonStyle()).disabled(!canZoomIn)
                .keyboardShortcut("+", modifiers: .command).help("Zoom in (⌘+)").accessibilityLabel("Zoom in")
            Button("1:1") { oneToOneAction() }
                .buttonStyle(BookletZoomButtonStyle()).disabled(oneToOne == nil)
                .help("Actual size: one image pixel to one point").accessibilityLabel("Actual size")
        }
        .background {
            Group {
                Button("Zoom in") { zoomInAction() }.keyboardShortcut("=", modifiers: .command).disabled(!canZoomIn)
                Button("Fit") { fitAction() }.keyboardShortcut("0", modifiers: .command)
            }
            .opacity(0).allowsHitTesting(false).accessibilityHidden(true)
        }
    }

    private func zoomInAction() { if isPDF { pdfZoom.zoomIn() } else { zoom = BookletLayout.zoomedIn(zoom) } }
    private func zoomOutAction() { if isPDF { pdfZoom.zoomOut() } else { zoom = BookletLayout.zoomedOut(zoom) } }
    private func fitAction() { if isPDF { pdfZoom.fit() } else { zoom = 1 } }
    private func oneToOneAction() { if isPDF { pdfZoom.actualSize() } else if let z = oneToOne { zoom = z } }

    /// The Page / Spread segmented switch: a `control` track with the chosen segment on `controlOn`.
    private var modeSwitch: some View {
        HStack(spacing: 0) {
            segment("Page", .page)
            segment("Spread", .spread)
        }
        .padding(2)
        .background(CU.Booklet.control, in: RoundedRectangle(cornerRadius: 7, style: .continuous))
        .padding(.trailing, CU.Space.s)
    }

    private func segment(_ label: String, _ value: BookletMode) -> some View {
        Button { setMode(value) } label: {
            Text(label).font(CU.Font.callout.font).foregroundStyle(mode == value ? CU.Booklet.ink : CU.Booklet.ink2)
                .padding(.horizontal, 10).padding(.vertical, 3)
                .background(mode == value ? CU.Booklet.controlOn : .clear, in: RoundedRectangle(cornerRadius: 5, style: .continuous))
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
        .accessibilityAddTraits(mode == value ? .isSelected : [])
    }

    // MARK: Sidebar

    private var sidebar: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: CU.Space.m) {
                VStack(alignment: .leading, spacing: CU.Space.s) {
                    heading(BookletLayout.editionsHeading(count: booklets.count))
                    VStack(spacing: CU.Booklet.editionRowGap) {
                        ForEach(booklets.indices, id: \.self) { i in
                            BookletEditionRow(booklet: booklets[i], number: i + 1, selected: i == current) { choose(i) }
                        }
                    }
                }
                if !extras.isEmpty {
                    VStack(alignment: .leading, spacing: CU.Space.s) {
                        heading("Extras")
                        LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: CU.Space.s), count: 3), spacing: CU.Space.s) {
                            ForEach(extras) { extra in
                                BookletExtraButton(picture: extra, selected: item?.isExtra == true && item?.pictures.first?.imageID == extra.imageID) {
                                    if let i = BookletLayout.index(of: extra, in: items) { show(i) }
                                }
                            }
                        }
                    }
                }
            }
            .padding(.vertical, CU.Space.m).padding(.horizontal, CU.Space.s)
        }
        .frame(width: CU.Booklet.sidebar)
        .background(CU.Booklet.panel)
    }

    private func heading(_ text: String) -> some View {
        Text(text).font(CU.Font.eyebrow.font).tracking(CU.Font.eyebrow.tracking).textCase(.uppercase)
            .foregroundStyle(CU.Booklet.ink2).padding(.horizontal, CU.Space.s)
            .accessibilityAddTraits(.isHeader)
    }

    // MARK: Main

    @ViewBuilder private var main: some View {
        if let pdf = booklet.pdf, isPDF {
            PDFBookletView(picture: pdf, zoom: pdfZoom).id(pdf.imageID)
        } else if let item {
            VStack(spacing: 0) {
                HStack(spacing: 0) {
                    BookletArrow(systemImage: "chevron.left", label: "Previous \(unit)", help: "Previous \(unit) (left arrow)") { turn(-1) }
                        .disabled(index == 0).frame(width: CU.Booklet.arrowColumn)
                    ZStack { BookletSpreadView(item: item, zoom: $zoom, fittedWidth: $fittedWidth).id("\(current)|\(mode)|\(index)").transition(.opacity) }
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                    BookletArrow(systemImage: "chevron.right", label: "Next \(unit)", help: "Next \(unit) (right arrow)") { turn(1) }
                        .disabled(index >= items.count - 1).frame(width: CU.Booklet.arrowColumn)
                }
                .padding(.init(top: CU.Space.m, leading: CU.Space.s, bottom: CU.Space.s, trailing: CU.Space.s))
                caption(for: item)
                BookletFilmstrip(items: items, index: index) { show($0) }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else {
            Color.clear.frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private func caption(for item: BookletItem) -> some View {
        let c = BookletLayout.caption(item, edition: booklet.edition, pageCount: pageCount)
        return VStack(spacing: 2) {
            Text(c.headline).font(CU.Font.headline.font).foregroundStyle(CU.Booklet.ink)
            if let quote = c.quote { Text(quote).font(CU.Font.callout.font).foregroundStyle(CU.Booklet.quote) }
            Text(c.detail).font(CU.Font.callout.font).foregroundStyle(CU.Booklet.ink2)
        }
        .multilineTextAlignment(.center)
        .padding(.init(top: CU.Space.s, leading: 56, bottom: CU.Space.m, trailing: 56))
        .frame(maxWidth: .infinity)
        .accessibilityElement(children: .combine)
    }

    // MARK: Actions

    /// Chooses an edition: back to the first spread (or page) at Fit, and said to VoiceOver (there is no visual notice).
    private func choose(_ i: Int) {
        guard i != current else { return }
        current = i
        index = 0
        zoom = 1
        let text = BookletLayout.announcement(number: i + 1, of: booklets.count, edition: BookletLayout.editionName(booklets[i], number: i + 1))
        if let window = NSApp.keyWindow { NSAccessibility.post(element: window, notification: .announcementRequested, userInfo: [.announcement: text]) }
    }

    private func setMode(_ new: BookletMode) {
        guard new != mode else { return }
        let i = BookletLayout.index(after: new, from: mode, at: index, in: booklet)
        mode = new
        index = i
        zoom = 1
    }

    private func turn(_ by: Int) {
        if let next = BookletLayout.turned(index, by: by, count: items.count) { show(next) }
    }

    /// The turn is a 0.15 s cross-fade, none under Reduce Motion (section 5.3).
    private func show(_ i: Int) {
        withAnimation(reduceMotion ? nil : .easeOut(duration: 0.15)) { index = i; zoom = 1 }
    }
}

/// The bar's Done button: `controlOn` ground, `ink` text.
private struct BookletDoneStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.font(CU.Font.headline.font).foregroundStyle(CU.Booklet.ink)
            .padding(.horizontal, 12).frame(height: 26)
            .background(CU.Booklet.controlOn.opacity(configuration.isPressed ? 0.8 : 1), in: RoundedRectangle(cornerRadius: 7, style: .continuous))
    }
}
