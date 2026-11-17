import DiscairLibrarian
import SwiftUI

// The pieces of the Paths sheet's Trail layout (docs/MACOS_PATHS_BOOKLET.md, section 4): a group on the rail, a stop card, the
// detail bar and the filter. Measures come from `CU.PathsSheet`, colours from the CU roles.

// MARK: Library lookups

/// What the sheet knows of the library: which album a step's cover is, and which library album a step opens or plays.
@MainActor
struct PathStepLookup {
    let state: AppState

    /// Every album in the library, not only the page of them the library screen shows.
    private var libraryAlbums: [AlbumItem] { state.library.searchableAlbums }

    func library(title: String, artist: String) -> AlbumItem? {
        libraryAlbums.first { LibrarySearch.fold($0.title) == LibrarySearch.fold(title) && LibrarySearch.fold($0.artist) == LibrarySearch.fold(artist) }
    }

    /// The cover's album item. A step the server names only by title and artist borrows its Navidrome ids from the library
    /// album of that name; one outside the library is marked not owned so its cover is looked up by artist and title.
    func item(_ c: PathStep.AlbumCover) -> AlbumItem {
        let hue = Double(abs(c.title.hashValue % 360))
        if c.coverArt != nil || c.albumID != nil {
            return AlbumItem(id: -1, title: c.title, artist: c.artist, year: 0, genre: "", format: "", owned: true, hue: hue, remoteID: c.albumID, coverArt: c.coverArt)
        }
        if let a = library(title: c.title, artist: c.artist) {
            return AlbumItem(id: -1, title: c.title, artist: c.artist, year: 0, genre: "", format: "", owned: true, hue: hue,
                             remoteID: a.remoteID, coverArt: a.coverArt ?? a.remoteID.map { "al-\($0)" })
        }
        return AlbumItem(id: 0, title: c.title, artist: c.artist, year: 0, genre: "", format: "", owned: false, hue: hue)
    }

    /// The step's album in the library, by Navidrome id or by title and artist. An album the server marks as outside the library has none.
    func libraryAlbum(_ s: PathStep) -> AlbumItem? {
        guard s.owned, case .album(let title, let artist, let id)? = s.target else { return nil }
        return libraryAlbums.first {
            ($0.remoteID != nil && $0.remoteID == id) || (LibrarySearch.fold($0.title) == LibrarySearch.fold(title) && LibrarySearch.fold($0.artist) == LibrarySearch.fold(artist))
        }
    }

    /// An album outside the library, as the page and the Get action look it up.
    func notOwned(title: String, artist: String) -> AlbumItem {
        AlbumItem(id: -1, title: title, artist: artist, year: 0, genre: "", format: "", owned: false, hue: Double(abs(title.hashValue % 360)))
    }

    /// The album the Get marker and Get button act on: only a not-owned album step has one.
    func gettable(_ s: PathStep) -> AlbumItem? {
        guard !s.owned, case .album(let title, let artist, _)? = s.target else { return nil }
        return notOwned(title: title, artist: artist)
    }

    /// The album shown in the sheet's header: the start album, from the library when it is there.
    func startAlbum(title: String, artist: String) -> AlbumItem {
        library(title: title, artist: artist) ?? AlbumItem(id: 0, title: title, artist: artist, year: 0, genre: "", format: "", owned: false, hue: Double(abs(title.hashValue % 360)))
    }
}

/// An animation that is off under Reduce Motion (every duration is 0 there, section 3.6).
func pathMotion(_ reduce: Bool, _ duration: Double) -> Animation? { reduce ? nil : .easeOut(duration: duration) }

// MARK: Cover

/// A step's cover: the album's cover (with its alternate covers on hover), or a tile with the step's symbol.
struct PathStepCover: View {
    let step: PathStep
    let lookup: PathStepLookup
    let size: CGFloat
    var px = 360

    var body: some View {
        let radius = CU.PathsSheet.stopCoverRadius
        Group {
            if let c = step.cover {
                PathRowThumb(step: step, size: size, radius: radius) {
                    CoverView(album: lookup.item(c), px: px).frame(width: size, height: size).clipShape(RoundedRectangle(cornerRadius: radius, style: .continuous))
                }
            } else {
                Image(systemName: step.symbol).font(.system(size: size * 0.5)).foregroundStyle(CU.textSecondary)
                    .frame(width: size, height: size)
                    .background(CU.bgFill, in: RoundedRectangle(cornerRadius: radius, style: .continuous))
                    .accessibilityHidden(true)
            }
        }
        .frame(width: size, height: size)
    }
}

// MARK: Group

/// One link of the trail: the dot on the rail, the pill, the role line, the count, the cards and the capped note.
struct PathGroupView: View {
    let group: PathTrailGroup
    let total: Int
    let context: PathContext
    let steps: [Int: PathStep]
    let selected: Int?
    let first: Bool
    let last: Bool
    let lookup: PathStepLookup
    let state: AppState
    let select: (Int) -> Void
    let open: (PathStep) -> Void

    var body: some View {
        HStack(alignment: .top, spacing: CU.PathsSheet.railGap) {
            Circle().fill(CU.accent).frame(width: CU.PathsSheet.dot, height: CU.PathsSheet.dot)
                .background(Circle().fill(CU.content).padding(-CU.PathsSheet.dotRing))
                .padding(.leading, CU.PathsSheet.railX - CU.PathsSheet.dot / 2 + 1).padding(.top, CU.PathsSheet.dotTop)
                .frame(width: CU.PathsSheet.railColumn, alignment: .topLeading)
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 0) {
                head
                PathStopGrid(ids: group.stepIDs, steps: steps, context: context, selected: selected, lookup: lookup, state: state, select: select, open: open)
                    .padding(.top, CU.Space.s)
                if let note = PathTrail.cappedText(group) {
                    Text(note).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).padding(.top, CU.Space.xs)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .padding(.top, CU.Space.m)
        .background(alignment: .topLeading) { rail }
    }

    /// The 2 pt rail: it starts at the first dot, ends at the last, and a single group draws none.
    @ViewBuilder private var rail: some View {
        if !(first && last) {
            Rectangle().fill(CU.separator)
                .frame(width: CU.PathsSheet.railWidth, height: last ? 28 : nil)
                .padding(.top, first ? 26 : 0)
                .padding(.leading, CU.PathsSheet.railX)
                .accessibilityHidden(true)
        }
    }

    private var head: some View {
        HStack(alignment: .firstTextBaseline, spacing: CU.Space.s) {
            if let link = group.link {
                pill(link)
                if !group.role.isEmpty {
                    Text(PathsSheet.attributed(group.role)).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1).truncationMode(.tail)
                }
            }
            Spacer(minLength: CU.Space.s)
            Text(PathTrail.countText(shown: group.stepIDs.count, of: total, context: context))
                .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).monospacedDigit().lineLimit(1)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(headLabel)
        .accessibilityAddTraits(.isHeader)
    }

    private func pill(_ link: PathLink) -> some View {
        var text = AttributedString(link.name.isEmpty ? link.kind : "\(link.name) · \(link.kind)")
        if !link.name.isEmpty, let range = text.range(of: link.name) { text[range].font = CU.Font.headline.font }
        let pillText = Text(text).font(CU.Font.body.font)
        return pillText.foregroundStyle(CU.text).lineLimit(1).truncationMode(.tail)
            .padding(.horizontal, 11).padding(.vertical, 3)
            .background(CU.accentTint, in: Capsule())
    }

    private var headLabel: String {
        var parts: [String] = []
        if let link = group.link { parts.append(link.name.isEmpty ? link.kind : "\(link.name), \(link.kind)") }
        if !group.role.isEmpty { parts.append(group.role.map(\.text).joined()) }
        parts.append(PathTrail.countText(shown: group.stepIDs.count, of: total, context: context))
        return parts.joined(separator: ", ")
    }
}

/// The cards of a group: a grid that wraps as the sheet is resized.
struct PathStopGrid: View {
    let ids: [Int]
    let steps: [Int: PathStep]
    let context: PathContext
    let selected: Int?
    let lookup: PathStepLookup
    let state: AppState
    let select: (Int) -> Void
    let open: (PathStep) -> Void

    var body: some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: CU.PathsSheet.stopMinWidth), spacing: CU.PathsSheet.coverGap, alignment: .top)],
                  alignment: .leading, spacing: CU.PathsSheet.coverGap) {
            ForEach(ids, id: \.self) { id in
                if let step = steps[id] {
                    PathStopCard(step: step, context: context, selected: selected == id, lookup: lookup, state: state,
                                 select: { select(id) }, open: { open(step) })
                        .id(id)
                }
            }
        }
    }
}

// MARK: Card

/// A stop card: cover, Get marker, title, second line, extra line and ownership badge (section 4.3).
struct PathStopCard: View {
    let step: PathStep
    let context: PathContext
    let selected: Bool
    let lookup: PathStepLookup
    let state: AppState
    let select: () -> Void
    let open: () -> Void
    @State private var hovering = false
    @FocusState private var focused: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        Button(action: select) {
            VStack(alignment: .leading, spacing: 0) {
                Color.clear.aspectRatio(1, contentMode: .fit)
                    .overlay { GeometryReader { g in PathStepCover(step: step, lookup: lookup, size: g.size.width) } }
                    .overlay(alignment: .topTrailing) { getMarker }
                    .padding(.bottom, CU.Space.s)
                Text(step.name).cuRole(CU.Font.headline).foregroundStyle(CU.text).lineLimit(2).multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)
                if let line = secondLine {
                    Text(line).cuRole(CU.Font.callout).foregroundStyle(selected ? CU.PathsSheet.selectedInk2 : CU.textSecondary).lineLimit(1).truncationMode(.tail)
                        .padding(.top, 2)
                }
                if let extra = extraLine { Text(extra).cuRole(CU.Font.caption).foregroundStyle(CU.text).lineLimit(1).truncationMode(.tail).monospacedDigit() }
                badge.padding(.top, CU.Space.xs)
            }
            .padding(CU.Space.s)
            .frame(maxWidth: .infinity, alignment: .topLeading)
            .background(selected ? CU.accentTint : (hovering ? CU.bgPanel : Color.clear), in: RoundedRectangle(cornerRadius: CU.PathsSheet.stopRadius, style: .continuous))
            .overlay { RoundedRectangle(cornerRadius: CU.PathsSheet.stopRadius, style: .continuous).stroke(selected ? CU.PathsSheet.selectedEdge : Color.clear, lineWidth: 1) }
            .contentShape(RoundedRectangle(cornerRadius: CU.PathsSheet.stopRadius, style: .continuous))
        }
        .buttonStyle(.plain)
        .focused($focused).focusEffectDisabled()
        .overlay { if focused { RoundedRectangle(cornerRadius: CU.PathsSheet.stopRadius, style: .continuous).stroke(CU.accent, lineWidth: 2).padding(-2) } }
        .simultaneousGesture(TapGesture(count: 2).onEnded { open() })
        .onHover { hovering = $0 }
        .animation(pathMotion(reduceMotion, 0.12), value: hovering)
        .animation(pathMotion(reduceMotion, 0.12), value: selected)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(label)
        .accessibilityAddTraits(selected ? [.isButton, .isSelected] : .isButton)
    }

    /// Artist; "album · album artist" on Follow the Musician; the recording on Composition. Not on Sideman or Scene.
    private var secondLine: String? {
        if case .artist(let kind) = context, kind == .sidemanToLeader || kind == .scenePath { return nil }
        return step.detail.isEmpty ? nil : step.detail
    }

    /// Gaps: the play label. Sonic: the track count line, with the year when it is sent.
    private var extraLine: String? {
        guard case .album(let tab) = context else { return nil }
        switch tab {
        case .listenThroughGaps: return step.play
        case .neighboursByEar: return [step.why, step.year.map(String.init) ?? ""].filter { !$0.isEmpty }.joined(separator: " · ")
        default: return nil
        }
    }

    @ViewBuilder private var getMarker: some View {
        if let item = lookup.gettable(step) {
            Text(state.acquisition.buttonLabel(for: item)).cuRole(CU.Font.caption).font(CU.Font.caption.weighted(.semibold))
                .foregroundStyle(CU.accentStrong)
                .padding(.horizontal, 5).padding(.vertical, 3)
                .background(CU.PathsSheet.badgeGround, in: RoundedRectangle(cornerRadius: CU.PathsSheet.cornerBadgeRadius, style: .continuous))
                .padding(CU.PathsSheet.cornerBadgeInset)
                .accessibilityHidden(true)
        }
    }

    /// A word and a mark, never colour alone.
    @ViewBuilder private var badge: some View {
        if step.owned {
            HStack(spacing: CU.Space.xs) { Image(systemName: "checkmark"); Text("In library") }
                .font(CU.Font.caption.weighted(.semibold)).foregroundStyle(CU.success)
                .padding(.horizontal, 6).padding(.vertical, 1)
                .background(CU.successTint, in: RoundedRectangle(cornerRadius: CU.PathsSheet.badgeRadius, style: .continuous))
        } else {
            HStack(spacing: CU.Space.xs) { Image(systemName: "circle"); Text("Not in library") }
                .font(CU.Font.caption.weighted(.semibold)).foregroundStyle(CU.accentStrong)
                .padding(.horizontal, 6).padding(.vertical, 1)
                .overlay { RoundedRectangle(cornerRadius: CU.PathsSheet.badgeRadius, style: .continuous).stroke(CU.PathsSheet.outEdge, lineWidth: 1) }
        }
    }

    private var label: String {
        var parts = [step.name]
        if let by = step.artistName, by != step.name { parts.append(by) }
        parts.append(step.owned ? "in your library" : "not in your library")
        if let item = lookup.gettable(step), state.acquisition.canGet(item) { parts.append("can be got") }
        return parts.joined(separator: ", ")
    }
}

// MARK: Filter

/// All / Not in library / In library, a segmented control drawn to the mockup.
struct PathFilterControl: View {
    let filter: PathFilter
    let choose: (PathFilter) -> Void
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        HStack(spacing: 2) {
            ForEach(PathFilter.allCases, id: \.self) { f in
                let on = f == filter
                Button { choose(f) } label: {
                    Text(f.rawValue).cuRole(CU.Font.callout).foregroundStyle(on ? CU.text : CU.textSecondary)
                        .padding(.horizontal, 10).padding(.vertical, 3)
                        .background { if on { RoundedRectangle(cornerRadius: 5, style: .continuous).fill(CU.content).shadow(color: CU.shadowInk.opacity(0.2), radius: 1, y: 0.5) } }
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(on ? .isSelected : [])
            }
        }
        .padding(2)
        .background(CU.bgFill, in: RoundedRectangle(cornerRadius: 7, style: .continuous))
        .animation(pathMotion(reduceMotion, 0.12), value: filter)
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Show")
    }
}

// MARK: Detail bar

/// The bar under the trail: the selected step's cover, title line, story and evidence, and the actions (section 4.7).
struct PathDetailBar: View {
    let step: PathStep
    let model: PathsSheetModel
    let lookup: PathStepLookup
    let state: AppState
    let open: (PathStep?) -> Void

    var body: some View {
        HStack(alignment: .center, spacing: CU.Space.m) {
            PathStepCover(step: step, lookup: lookup, size: CU.PathsSheet.detailCover, px: 144)
            VStack(alignment: .leading, spacing: 0) {
                VStack(alignment: .leading, spacing: 0) {
                    Text(titleLine).cuRole(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1).truncationMode(.tail)
                    Text(story).cuRole(CU.Font.body).foregroundStyle(CU.text).lineLimit(3).fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: CU.PathsSheet.storyMaxWidth, alignment: .leading).padding(.top, CU.Space.xs)
                        .help(storyPlain)
                    evidenceLine.padding(.top, CU.Space.xs)
                }
                .accessibilityElement(children: .combine)
                extraSlot
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            actions
        }
        .padding(.horizontal, CU.Space.l).padding(.vertical, CU.Space.m)
        .frame(maxWidth: .infinity, minHeight: 104, alignment: .leading)
        .background(CU.bgPanel)
        .overlay(alignment: .top) { Rectangle().fill(CU.separator).frame(height: 1) }
    }

    private var titleLine: String {
        var parts = [step.name]
        if let by = step.artistName, by != step.name { parts.append(by) }
        if let year = step.year { parts.append(String(year)) }
        parts.append(step.owned ? "In your library" : "Not in your library")
        return parts.joined(separator: " · ")
    }

    /// The step's story paragraphs joined by a space; with none, the first reason's eyebrow and text.
    private var story: AttributedString {
        if !step.story.isEmpty {
            var out = AttributedString()
            for (i, paragraph) in step.story.enumerated() {
                if i > 0 { out += AttributedString(" ") }
                out += PathsSheet.attributed(paragraph)
            }
            return out
        }
        guard let r = step.reasons.first else { return AttributedString() }
        var head = AttributedString(r.eyebrow)
        head.inlinePresentationIntent = .stronglyEmphasized
        return head + AttributedString(" · " + r.text)
    }

    private var storyPlain: String { String(story.characters) }

    private var evidenceLine: some View {
        HStack(spacing: CU.Space.xs) {
            if let e = step.evidence { Text(e + "  ·").cuRole(CU.Font.caption).foregroundStyle(CU.textSecondary) }
            PathKeyCap("←"); PathKeyCap("→")
            Text("move").cuRole(CU.Font.caption).foregroundStyle(CU.textSecondary)
            PathKeyCap("↩")
            Text("open").cuRole(CU.Font.caption).foregroundStyle(CU.textSecondary)
        }
        .lineLimit(1)
    }

    /// Room: the two albums' session photos. Gaps: the listening card.
    @ViewBuilder private var extraSlot: some View {
        if model.subject == .album, model.tabID == AlbumPathTab.sameRoom.id, let cover = step.cover {
            SameRoomPhotos(startTitle: model.title, startArtist: model.artist, otherTitle: cover.title, otherArtist: cover.artist)
                .frame(maxWidth: 2 * 96 + CU.Space.s).padding(.top, CU.Space.s)
        } else if let play = step.play {
            VStack(alignment: .leading, spacing: 0) {
                Text("Your listening").cuRole(CU.Font.eyebrow).textCase(.uppercase).foregroundStyle(CU.textSecondary)
                Text(play).cuRole(CU.Font.headline).foregroundStyle(CU.text)
            }
            .padding(.horizontal, CU.Space.s).padding(.vertical, CU.Space.xs)
            .background(CU.content, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay { RoundedRectangle(cornerRadius: 8, style: .continuous).stroke(CU.separator, lineWidth: 0.5) }
            .padding(.top, CU.Space.s)
        }
    }

    private var actions: some View {
        HStack(spacing: CU.Space.s) {
            if let by = step.artistName, step.target != .artist(name: by) {
                Button("Open Artist") { state.paths = nil; state.openArtist(named: by) }.buttonStyle(PathButtonStyle())
            }
            if let item = lookup.gettable(step) {
                Button { state.actions.get(album: item) } label: {
                    Label { Text(state.acquisition.buttonLabel(for: item)) } icon: { Image(systemName: "arrow.down").font(CU.Icon.small(.semibold)) }
                }
                .buttonStyle(PathButtonStyle()).disabled(!state.acquisition.canGet(item)).help(state.acquisition.detail(for: item))
            }
            if model.subject == .album, let album = lookup.libraryAlbum(step) {
                Button { state.paths = nil; state.actions.play(album: album) } label: {
                    Label { Text("Play Album") } icon: { Image(systemName: "play.fill").font(CU.Icon.small()) }
                }
                .buttonStyle(PathButtonStyle())
            }
            Button(step.target?.label ?? "Open") { open(step) }
                .keyboardShortcut(.defaultAction).buttonStyle(PathButtonStyle(prominent: true)).disabled(step.target == nil)
        }
    }
}

/// A key cap in the hint line.
private struct PathKeyCap: View {
    let key: String
    init(_ key: String) { self.key = key }
    var body: some View {
        Text(key).font(.system(size: CU.Font.caption.size, weight: .medium, design: .monospaced)).foregroundStyle(CU.textSecondary)
            .padding(.horizontal, CU.Space.xs)
            .background(CU.content, in: RoundedRectangle(cornerRadius: 4, style: .continuous))
            .overlay { RoundedRectangle(cornerRadius: 4, style: .continuous).stroke(CU.separator, lineWidth: 1) }
            .accessibilityHidden(true)
    }
}

/// The sheet's buttons: 28 high, radius 8, headline type; secondary has a hairline border, the one primary is the accent.
struct PathButtonStyle: ButtonStyle {
    var prominent = false
    @Environment(\.isEnabled) private var enabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(CU.Font.headline.font)
            .foregroundStyle(prominent ? CU.onAccent : CU.text)
            .padding(.horizontal, 12).frame(height: CU.PathsSheet.buttonHeight)
            .background(RoundedRectangle(cornerRadius: CU.PathsSheet.buttonRadius, style: .continuous).fill(prominent ? CU.accent : CU.content))
            .overlay { if !prominent { RoundedRectangle(cornerRadius: CU.PathsSheet.buttonRadius, style: .continuous).stroke(CU.separatorStrong, lineWidth: 1) } }
            .opacity(!enabled ? 0.45 : configuration.isPressed ? 0.8 : 1)
            .fixedSize()
    }
}
