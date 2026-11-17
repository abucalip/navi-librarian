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

/// The Booklet (docs/MACOS_PATHS_BOOKLET.md, section 5; D1 a: a sheet, closed by Done or Escape). A bar with the album title and the
/// Page/Spread switch; a sidebar of editions and extras (left out for one booklet with no extras); the spread on a dark stage
/// with turn arrows; a caption. Arrow keys turn; pinch zoom loads the full-resolution file on first use. A PDF booklet opens in
/// PDFKit (one page wide, continuous). Captions are the image's type, edition and the Cover Art Archive comment, as plain text.
/// No text recognition and no credit links.
struct BookletSheet: View {
    let title: String
    /// Every booklet the album has, best first. The sheet opens on the first.
    let booklets: [BookletView]
    let close: () -> Void
    @State private var current = 0
    @State private var mode: BookletMode = .spread
    @State private var index = 0
    @FocusState private var focused: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private var booklet: BookletView { booklets[min(current, booklets.count - 1)] }
    private var isPDF: Bool { booklet.pdf != nil && booklet.pages.allSatisfy(\.isPDF) && booklet.extras.allSatisfy(\.isPDF) }
    private var items: [BookletItem] { BookletLayout.items(booklet, mode: mode) }
    private var item: BookletItem? { items.indices.contains(index) ? items[index] : nil }
    private var pageCount: Int { BookletLayout.pageCount(booklet) }
    private var showsSidebar: Bool { BookletLayout.showsSidebar(booklets) }
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
                    .accessibilityAddTraits(.isHeader)
                if let item, !isPDF {
                    Text(BookletLayout.barDetail(edition: booklet.edition, item: item, pageCount: pageCount))
                        .font(CU.Font.body.font).foregroundStyle(CU.Booklet.ink2).lineLimit(1).truncationMode(.tail)
                } else if !booklet.edition.isEmpty {
                    Text("Booklet · \(booklet.edition)").font(CU.Font.body.font).foregroundStyle(CU.Booklet.ink2).lineLimit(1)
                }
            }
            Spacer(minLength: CU.Space.s)
            if !isPDF { modeSwitch }
            Button("Done", action: close).keyboardShortcut(.cancelAction).buttonStyle(BookletDoneStyle())
        }
        .padding(.horizontal, CU.Space.m)
        .frame(height: CU.Booklet.barHeight)
        .background(CU.Booklet.bar)
    }

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
            PDFBookletView(picture: pdf).id(pdf.imageID)
        } else if let item {
            VStack(spacing: 0) {
                HStack(spacing: 0) {
                    BookletArrow(systemImage: "chevron.left", label: "Previous \(unit)", help: "Previous \(unit) (left arrow)") { turn(-1) }
                        .disabled(index == 0).frame(width: CU.Booklet.arrowColumn)
                    ZStack { BookletSpreadView(item: item).id("\(current)|\(mode)|\(index)").transition(.opacity) }
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                    BookletArrow(systemImage: "chevron.right", label: "Next \(unit)", help: "Next \(unit) (right arrow)") { turn(1) }
                        .disabled(index >= items.count - 1).frame(width: CU.Booklet.arrowColumn)
                }
                .padding(.init(top: CU.Space.m, leading: CU.Space.s, bottom: CU.Space.s, trailing: CU.Space.s))
                caption(for: item)
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
        let text = BookletLayout.announcement(number: i + 1, of: booklets.count, edition: BookletLayout.editionName(booklets[i], number: i + 1))
        if let window = NSApp.keyWindow { NSAccessibility.post(element: window, notification: .announcementRequested, userInfo: [.announcement: text]) }
    }

    private func setMode(_ new: BookletMode) {
        guard new != mode else { return }
        let i = BookletLayout.index(after: new, from: mode, at: index, in: booklet)
        mode = new
        index = i
    }

    private func turn(_ by: Int) {
        if let next = BookletLayout.turned(index, by: by, count: items.count) { show(next) }
    }

    /// The turn is a 0.15 s cross-fade, none under Reduce Motion (section 5.3).
    private func show(_ i: Int) {
        withAnimation(reduceMotion ? nil : .easeOut(duration: 0.15)) { index = i }
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
