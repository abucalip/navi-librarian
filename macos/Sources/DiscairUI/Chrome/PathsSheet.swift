import DiscairLibrarian
import SwiftUI

/// The Paths sheet of an album or an artist (docs/MACOS_PATHS_BOOKLET.md, section 4): a header, text tabs, the summary with a
/// filter, the Trail of steps grouped under what links them to the start, and a detail bar for the selected step. It can be
/// resized, and every colour is a CU role, so it follows the theme, Night and the owner's accent.
struct PathsSheet: View {
    let state: AppState
    @Bindable var model: PathsSheetModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private var lookup: PathStepLookup { PathStepLookup(state: state) }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            tabBar
            content.frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(minWidth: CU.PathsSheet.minSize.width, idealWidth: CU.PathsSheet.idealSize.width, maxWidth: .infinity,
               minHeight: CU.PathsSheet.minSize.height, idealHeight: CU.PathsSheet.idealSize.height, maxHeight: .infinity)
        .background(CU.content)
        .tint(CU.accent)
    }

    // MARK: Header

    private var header: some View {
        HStack(spacing: CU.Space.m) {
            startCover.frame(width: CU.PathsSheet.startCover, height: CU.PathsSheet.startCover)
            VStack(alignment: .leading, spacing: 0) {
                Text("Paths from").cuRole(CU.Font.eyebrow).textCase(.uppercase).foregroundStyle(CU.textSecondary)
                Text(model.title).cuRole(CU.Font.title2).foregroundStyle(CU.text).lineLimit(1).truncationMode(.tail).accessibilityAddTraits(.isHeader)
                if let line = subtitle { Text(line).cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).lineLimit(1) }
            }
            Spacer(minLength: CU.Space.m)
            Button { state.paths = nil } label: {
                Image(systemName: "xmark").font(CU.Icon.small(.semibold)).foregroundStyle(CU.textSecondary)
                    .frame(width: CU.PathsSheet.closeButton, height: CU.PathsSheet.closeButton).background(CU.bgFill, in: Circle())
            }
            .buttonStyle(.plain).keyboardShortcut(.cancelAction).accessibilityLabel("Close")
        }
        .padding(.horizontal, CU.Space.l).padding(.top, CU.Space.m).padding(.bottom, CU.Space.s)
    }

    @ViewBuilder private var startCover: some View {
        if model.subject == .album {
            CoverView(album: lookup.startAlbum(title: model.title, artist: model.artist), px: 224)
                .clipShape(RoundedRectangle(cornerRadius: CU.PathsSheet.startCoverRadius, style: .continuous))
        } else {
            ArtistPhoto(name: model.title, size: CU.PathsSheet.startCover)
        }
    }

    /// "artist · year" on an album sheet; "Person", "Group" or "Artist" on an artist sheet.
    private var subtitle: String? {
        if model.subject == .album { return [model.artist, model.year.map(String.init) ?? ""].filter { !$0.isEmpty }.joined(separator: " · ") }
        switch model.answer?.startType { case "person": return "Person"; case "group": return "Group"; default: return "Artist" }
    }

    // MARK: Tabs

    private var tabBar: some View {
        HStack(spacing: CU.Space.l) {
            ForEach(model.tabLabels, id: \.id) { tab in
                let on = tab.id == model.tabID
                let count = model.count(for: tab.id)
                Button {
                    model.choose(tab.id); state.loadPathsTab()
                } label: {
                    HStack(alignment: .firstTextBaseline, spacing: CU.Space.xs) {
                        Text(tab.label).font(on ? CU.Font.headline.font : CU.Font.body.font).lineLimit(1)
                        if let count { Text("\(count)").font(CU.Font.caption.weighted(.medium)).monospacedDigit().foregroundStyle(CU.textSecondary) }
                    }
                    .foregroundStyle(on ? CU.text : CU.textSecondary)
                    .padding(.vertical, CU.Space.s)
                    .overlay(alignment: .bottom) {
                        if on { RoundedRectangle(cornerRadius: 2, style: .continuous).fill(CU.accent).frame(height: CU.PathsSheet.tabUnderline).offset(y: 1) }
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(count.map { "\(tab.label), \($0) paths" } ?? tab.label)
                .accessibilityAddTraits(on ? .isSelected : [])
            }
            Spacer(minLength: 0)
        }
        .padding(.horizontal, CU.Space.l)
        .overlay(alignment: .bottom) { Rectangle().fill(CU.separator).frame(height: 1) }
    }

    // MARK: Body

    @ViewBuilder private var content: some View {
        switch model.phase {
        case .loading:
            VStack(spacing: 0) {
                summaryRow
                ProgressView("Finding the paths…").frame(maxWidth: .infinity, minHeight: 220, maxHeight: .infinity)
            }
        case .failed(let message):
            VStack(spacing: 0) {
                summaryRow
                failure(message)
            }
        case .ready(let answer):
            if answer.steps.isEmpty {
                // Nothing to summarise: the empty line alone, as in the mockup.
                Text(model.emptyText).cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).multilineTextAlignment(.center)
                    .padding(.horizontal, CU.Space.xl).frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                VStack(spacing: 0) {
                    summaryRow
                    trail(answer)
                    if let step = model.step { PathDetailBar(step: step, model: model, lookup: lookup, state: state, open: open) }
                }
            }
        }
    }

    /// The failure sentence in the danger colour, then Try Again and (when the server can be asked) Request update.
    private func failure(_ message: String) -> some View {
        VStack(spacing: CU.Space.s) {
            Label { Text(message).foregroundStyle(CU.danger).multilineTextAlignment(.center) } icon: { Image(systemName: "exclamationmark.triangle").foregroundStyle(CU.danger) }
                .font(CU.Font.body.font)
            HStack(spacing: CU.Space.s) {
                Button("Try Again") { state.loadPathsTab(retry: true) }.buttonStyle(PathButtonStyle())
                if model.canRequestUpdate {
                    let librarian = state.session?.librarian
                    Button("Request update") { Task { await model.requestUpdate(librarian: librarian) } }
                        .buttonStyle(PathButtonStyle()).disabled(model.updating)
                }
            }
            if let note = model.updateNote { Text(note).cuRole(CU.Font.caption).foregroundStyle(CU.textSecondary) }
        }
        .padding(.horizontal, CU.Space.xl).frame(maxWidth: .infinity, minHeight: 220, maxHeight: .infinity)
    }

    private var summaryRow: some View {
        HStack(alignment: .firstTextBaseline, spacing: CU.Space.l) {
            Text(model.summary).cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).lineLimit(2).fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
            if model.offersFilter { PathFilterControl(filter: model.activeFilter) { model.setFilter($0) } }
        }
        .padding(.horizontal, CU.Space.l).padding(.top, CU.Space.s).padding(.bottom, CU.Space.xs)
    }

    // MARK: Trail

    private func trail(_ answer: PathAnswer) -> some View {
        let groups = model.groups
        let totals = Dictionary(model.allGroups.map { ($0.id, $0.stepIDs.count) }, uniquingKeysWith: { a, _ in a })
        let steps = Dictionary(answer.steps.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        let flat = !groups.contains { $0.link != nil }
        let context = model.context ?? .album(.studioCrew)
        return ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    ForEach(Array(groups.enumerated()), id: \.element.id) { index, group in
                        if flat {
                            PathStopGrid(ids: group.stepIDs, steps: steps, context: context, selected: model.selected, lookup: lookup, state: state,
                                         select: { model.selected = $0 }, open: open)
                        } else {
                            PathGroupView(group: group, total: totals[group.id] ?? group.stepIDs.count, context: context, steps: steps, selected: model.selected,
                                          first: index == 0, last: index == groups.count - 1, lookup: lookup, state: state,
                                          select: { model.selected = $0 }, open: open)
                        }
                    }
                    notes(flat: flat)
                }
                .padding(.horizontal, CU.Space.l).padding(.top, CU.Space.s).padding(.bottom, CU.Space.m)
                .animation(pathMotion(reduceMotion, 0.15), value: model.activeFilter)
            }
            .onChange(of: model.selected) { _, new in
                if let new { withAnimation(pathMotion(reduceMotion, 0.12)) { proxy.scrollTo(new) } }
            }
        }
        .focusable().focusEffectDisabled()
        .onKeyPress(.leftArrow) { model.move(by: -1); return .handled }
        .onKeyPress(.upArrow) { model.move(by: -1); return .handled }
        .onKeyPress(.rightArrow) { model.move(by: 1); return .handled }
        .onKeyPress(.downArrow) { model.move(by: 1); return .handled }
    }

    @ViewBuilder private func notes(flat: Bool) -> some View {
        let loose = model.looseNotes
        if !loose.isEmpty {
            VStack(alignment: flat ? .center : .leading, spacing: 2) {
                ForEach(loose, id: \.self) { Text($0).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true) }
            }
            .frame(maxWidth: .infinity, alignment: flat ? .center : .leading)
            .padding(.leading, flat ? 0 : CU.PathsSheet.railColumn + CU.PathsSheet.railGap).padding(.top, CU.Space.s)
        }
    }

    /// A story as one styled run: people and places bold, albums, songs and works italic.
    static func attributed(_ spans: [StorySpan]) -> AttributedString {
        var out = AttributedString()
        for span in spans {
            var piece = AttributedString(span.text)
            switch span.kind {
            case .plain: break
            case .name: piece.inlinePresentationIntent = .stronglyEmphasized
            case .title: piece.inlinePresentationIntent = .emphasized
            }
            out += piece
        }
        return out
    }

    // MARK: Opening

    private func open(_ s: PathStep?) {
        guard let s, let target = s.target else { return }
        state.paths = nil
        switch target {
        case .artist(let name): state.openArtist(named: name)
        case .album(let title, let artist, _):
            // An album outside the library opens as one the page can look up (its Get button works there).
            state.open(album: lookup.libraryAlbum(s) ?? lookup.notOwned(title: title, artist: artist))
        }
    }
}
