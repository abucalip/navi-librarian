import DiscairLibrarian
import DiscairNavidrome
import SwiftUI

/// Home, the "Marquee" layout (`docs/archive/completed/MACOS_HOME_MARQUEE_PLAN.md`): today's pick over its own blurred cover, two shelves of covers
/// ("New on the shelf", "Waiting longest") and a one-line summary. Mockups: `docs/design/macos-home-marquee/`.
/// Figures come from `HomeDashboard`, wording from `HomeScreen`. Home does not request the lens cards: Insights owns them.
struct CupertinoHome: View {
    let state: AppState
    @State private var width: CGFloat = 980
    @State private var pickIndex = 0
    @FocusState private var pickFocused: Bool
    @State private var pickNotice: String?

    private var d: HomeDashboard { state.homeDashboard }
    private var stacked: Bool { HomeScreen.isStacked(contentWidth: width) }
    private var librarianUp: Bool { d.notice != .librarianUnreachable }
    private var loading: Bool { HomeScreen.page(dashboard: d, libraryPhaseLoading: state.session != nil && state.library.phase == .loading) == .loading }
    private var picks: [AlbumItem] { state.visible(state.library.missing) }
    private var hasListeningSource: Bool { state.taste.profiles?.window("recent").map { $0.listens > 0 } ?? false }
    private var pickEmpty: HomeScreen.PickEmpty {
        HomeScreen.pickEmpty(librarianReachable: librarianUp, hasListeningSource: hasListeningSource, note: state.library.picksNote)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: CU.Space.l) {
                header
                if loading { skeleton } else { page }
            }
            .padding(.horizontal, CU.Space.xl)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .onGeometryChange(for: CGFloat.self) { $0.size.width - CU.Space.xl * 2 } action: { width = $0 }
        .task(id: refreshKey) { if state.session != nil { await state.refreshHomeDashboard() } }
        // Keyed on the connection: Home can open before the session is ready, and the feeds (the phone handoff among them) must be read once it is.
        .task(id: state.session != nil) { await state.loadHomeFeeds() }
        .task { await state.loadStationsForHome() }
        .task { await state.library.reshufflePicks(librarian: state.session?.librarian) }
    }

    /// What the figures depend on besides the album list: the Gets, the saved taste and the picks.
    private var refreshKey: String {
        state.acquisition.visibleJobs.map { $0.id + $0.status }.joined(separator: ",") + "|\(state.taste.loaded)|\(state.library.missing.count)"
    }

    // MARK: Page

    private var header: some View {
        HStack(alignment: .firstTextBaseline) {
            Text("Home").cu(CU.Font.largeTitle).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
            Spacer()
            Text(HomeScreen.headerDate(Date())).cu(CU.Font.body).foregroundStyle(CU.textSecondary)
        }
        .padding(.top, CU.Space.xs)
    }

    /// Notice, marquee, radio card, New on the shelf, Waiting longest, summary line, Liner note (plan section 1).
    @ViewBuilder private var page: some View {
        notice
        marquee
        radioCard
        HomeShelfSection(state: state, stacked: stacked)
        HomeWaitingSection(state: state, stacked: stacked)
        HomeSummaryLine(state: state, stacked: stacked)
        // Draws nothing until today's picture is found; kept from the earlier Home.
        if state.library.isLive { LinerNoteCard(albums: state.visible(state.library.missing)) }
    }

    // MARK: 0. Radio card (E7)

    /// While a station plays, or when a last station is known and still listed. No card otherwise.
    @ViewBuilder private var radioCard: some View {
        if let card = HomeRadioCard.of(live: state.player.live, line: state.player.liveLine, lastStationID: state.player.lastStationID,
                                       stations: state.stations.stations, at: Date()) {
            HomeRadioCardView(state: state, card: card)
        }
    }

    // MARK: 0. Notice

    @ViewBuilder private var notice: some View {
        switch d.notice {
        case .librarianUnreachable:
            CUNotice(kind: .danger, lead: "Can't reach Librarian.",
                     message: "Your library still plays from Navidrome. Picks, arrivals, taste and insights return when the server answers.",
                     actionTitle: "Try again") { Task { await state.retryConnection() } }
        case .failedJob(let title, let reason, let others):
            CUNotice(kind: .danger, lead: "\(title) did not arrive.",
                     message: reason + (others > 0 ? " \(others) more \(others == 1 ? "Get" : "Gets") failed too." : ""),
                     actionTitle: "Open Downloads") { state.screen = .downloads }
        case .handoff(let h):
            CUNotice(kind: .info, lead: "Playing on your phone:", message: HomeScreen.handoffText(h),
                     actionTitle: "Continue on this Mac") { state.continueFromPhone() }
        case nil:
            EmptyView()
        }
    }

    // MARK: 1. Marquee

    private static let marqueeRadius: CGFloat = 18
    private static let marqueeMinHeight: CGFloat = 292
    fileprivate static let dayAccentStrong = CUPalette.day.accentStrong.color

    @ViewBuilder private var marquee: some View {
        if let position = HomeScreen.pickPosition(index: pickIndex, count: picks.count) {
            pickDeck(picks[position.index], position: position)
        } else {
            emptyMarquee
        }
    }

    /// No pick: a plain `bg.panel` panel with no artwork, at the marquee's height.
    private var emptyMarquee: some View {
        VStack(alignment: .leading, spacing: CU.Space.s) { pickEmptyState }
            .padding(CU.Space.xl)
            .frame(maxWidth: .infinity, minHeight: Self.marqueeMinHeight, alignment: .leading)
            .background(CU.bgPanel, in: RoundedRectangle(cornerRadius: Self.marqueeRadius, style: .continuous))
            .environment(\.cuInPanel, true)
            .accessibilityElement(children: .contain)
    }

    /// The marquee is the one place on Home where text sits on artwork, so it looks the same in Day and Night: a blurred cover
    /// under a flat 55% black wash, white text at full opacity (plan section 2).
    private func pickDeck(_ a: AlbumItem, position: (index: Int, label: String)) -> some View {
        let coverSide: CGFloat = stacked ? 160 : 240
        let next = HomeScreen.nextPicks(index: position.index, count: picks.count)
        return VStack(alignment: .leading, spacing: CU.Space.l) {
            HStack(alignment: .top, spacing: CU.Space.l) {
                CoverView(album: a).frame(width: coverSide, height: coverSide)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                    .shadow(color: CU.shadowInk.opacity(0.45), radius: 40, y: 14)
                    .accessibilityHidden(true)   // the title that follows names the album
                pickText(a, position: position)
                if !stacked && !next.isEmpty {
                    VStack(alignment: .trailing, spacing: CU.Space.s) { Spacer(minLength: 0); nextPicksView(next) }
                }
            }
            if stacked && !next.isEmpty { nextPicksView(next) }
        }
        .padding(CU.Space.l)
        .frame(maxWidth: .infinity, minHeight: Self.marqueeMinHeight, alignment: .topLeading)
        .background {
            ZStack {
                Color.clear.overlay { CoverView(album: a).scaledToFill() }.clipped()
                BlurredArtwork(album: a, radius: 44)
                Color.black.opacity(0.55)
            }
            .accessibilityHidden(true)   // decoration: the cover is read once, from the pick's own text
        }
        .clipShape(RoundedRectangle(cornerRadius: Self.marqueeRadius, style: .continuous))
        .foregroundStyle(.white)
        .focusable().focused($pickFocused).focusEffectDisabled()
        .overlay {
            if pickFocused {
                RoundedRectangle(cornerRadius: Self.marqueeRadius + 4, style: .continuous).stroke(Color.white.opacity(0.6), lineWidth: 3)
                    .padding(-4).allowsHitTesting(false)
            }
        }
        .overlay(alignment: .topTrailing) { if picks.count > 1 { chevrons(from: position.index) }}
        .onKeyPress(.rightArrow) { step(from: position.index, by: 1) }
        .onKeyPress(.leftArrow) { step(from: position.index, by: -1) }
        .onKeyPress(.space) { play(a) }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Today's pick, \(position.label)")
        .accessibilityHint("Left and right arrows show the previous and next pick. Space plays the album.")
    }

    private func pickText(_ a: AlbumItem, position: (index: Int, label: String)) -> some View {
        VStack(alignment: .leading, spacing: CU.Space.s) {
            Text("Today's pick · \(position.label)".uppercased()).cuRole(CU.Font.eyebrow).accessibilityAddTraits(.isHeader)
            Text(a.title).font(CU.Font.largeTitle.font).tracking(-0.5).lineLimit(2).fixedSize(horizontal: false, vertical: true)
            Text(a.line([a.artist, a.yearText, a.genre, "not in your library"])).font(.system(size: 15)).lineLimit(2)
            if let line = a.reasonLine {
                Text(line).font(.system(size: 14, weight: .semibold)).lineLimit(2).fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: 400, alignment: .leading).padding(.top, CU.Space.xs)
            }
            if let reason = a.reason, !reason.isEmpty {
                Text(reason).font(.system(size: 14)).lineSpacing(4).lineLimit(4).fixedSize(horizontal: false, vertical: true)
                    .frame(maxWidth: 400, alignment: .leading).padding(.top, CU.Space.xs)
            }
            if let track = a.suggestedTracks.first { suggestedTrack(track, album: a).padding(.top, CU.Space.xs) }
            Spacer(minLength: CU.Space.s)
            pickButtons(a)
            pickNoticeView()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    /// The other picks in order, after the current one and wrapping round: covers 46 across, three to a row, two rows at most.
    private func nextPicksView(_ indices: [Int]) -> some View {
        let rows = stride(from: 0, to: indices.count, by: 3).map { Array(indices[$0..<min($0 + 3, indices.count)]) }
        let covers = ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
            HStack(spacing: 6) { ForEach(row, id: \.self) { nextPickButton($0) } }
        }
        // Narrow (mockup `home-marquee--narrow`): the same block, wrapped under the text instead of at the trailing edge.
        return VStack(alignment: .trailing, spacing: 6) {
            Text("NEXT PICKS").cuRole(CU.Font.eyebrow).accessibilityAddTraits(.isHeader).padding(.bottom, 2)
            covers
        }
    }

    private func nextPickButton(_ i: Int) -> some View {
        let p = picks[i]
        return Button { pickIndex = i; pickNotice = nil } label: {
            CoverView(album: p).frame(width: 46, height: 46)
                .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
                .shadow(color: .black.opacity(0.4), radius: 8, y: 2)
        }
        .buttonStyle(.plain).accessibilityLabel("Show pick \(i + 1) of \(picks.count): \(p.title) by \(p.artist)")
    }

    // MARK: 2. Today's pick

    /// Picks are albums the library lacks, so there is nothing to play yet: the round button gets the song. An owned album plays it.
    private func suggestedTrack(_ title: String, album a: AlbumItem) -> some View {
        HStack(spacing: CU.Space.s) {
            Button { if a.owned { state.playAlbum(a) } else { state.actions.getSong(album: a, title: title, trackNumber: nil) } } label: {
                Image(systemName: a.owned ? "play.fill" : "arrow.down").font(CU.Icon.small(.semibold)).foregroundStyle(.white)
                    .frame(width: 32, height: 32).background(Color.white.opacity(0.2), in: Circle())
            }
            .buttonStyle(.plain).accessibilityLabel(a.owned ? "Play \(title)" : "Get the song \(title)")
            VStack(alignment: .leading, spacing: 0) {
                Text(title).cu(CU.Font.headline).lineLimit(1)
                Text("Suggested track").cu(CU.Font.callout)
            }
        }
    }

    @ViewBuilder private func pickNoticeView() -> some View {
        if let pickNotice {
            Label(pickNotice, systemImage: "info.circle").cu(CU.Font.callout)
                .accessibilityAddTraits(.updatesFrequently)
        }
    }

    /// Back and forward through the picks, wrapping round: at the panel's top right corner. The left and right arrow keys do the same.
    private func chevrons(from index: Int) -> some View {
        HStack(spacing: CU.Space.s) {
            chevron("chevron.left", help: "Previous pick") { _ = step(from: index, by: -1) }
            chevron("chevron.right", help: "Next pick") { _ = step(from: index, by: 1) }
        }
        .padding(CU.Space.m)
    }

    private func chevron(_ symbol: String, help: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: symbol).font(CU.Icon.small(.semibold)).foregroundStyle(.white)
                .frame(width: 30, height: 30).background(Color.white.opacity(0.2), in: Circle())
        }
        .buttonStyle(.plain).help(help).accessibilityLabel(help)
    }

    private func step(from index: Int, by step: Int) -> KeyPress.Result {
        pickIndex = HomeScreen.steppedPick(index: index, count: picks.count, by: step); pickNotice = nil
        return .handled
    }

    /// Get is the one primary button: white, its label in the Day `accentStrong` in both modes. Each key is shown inside its button.
    private func pickButtons(_ a: AlbumItem) -> some View {
        let acq = state.acquisition
        let label = acq.buttonLabel(for: a)
        return HStack(spacing: CU.Space.s) {
            Button { state.actions.get(album: a) } label: { Text(label == "Get" ? "Get album" : label) }
                .buttonStyle(MarqueeButtonStyle(primary: true)).disabled(!acq.canGet(a))
                .help(acq.detail(for: a)).accessibilityHint(acq.detail(for: a))
            Button { state.actions.save(album: a) } label: { Text(acq.isSaved(a) ? "Saved" : "Save") }
                .buttonStyle(MarqueeButtonStyle()).disabled(acq.isSaved(a))
            Button { state.actions.notForMe(album: a) } label: { Text("Not for me") }
                .buttonStyle(MarqueeButtonStyle())
            CupertinoPickFeedbackMenu(state: state, album: a, marquee: true)
        }
    }

    /// Space plays the album when owned, and otherwise shows a short notice.
    private func play(_ a: AlbumItem) -> KeyPress.Result {
        switch HomeScreen.spaceOutcome(owned: a.owned) {
        case .play: pickNotice = nil; state.playAlbum(a)
        case .notOwned(let notice): pickNotice = notice
        }
        return .handled
    }

    @ViewBuilder private var pickEmptyState: some View {
        HomeEyebrow("Today's pick")
        switch pickEmpty {
        case .needsHistory:
            Text("No picks yet.").cu(CU.Font.title1).foregroundStyle(CU.text)
            emptyBody("Picks come from your listening history. Connect Last.fm or ListenBrainz in Services and the first list is built within a few minutes. Nothing is suggested from guesses.")
            HStack(spacing: CU.Space.s) {
                Button("Open Services") { state.screen = .settings }.buttonStyle(CapsuleButtonStyle(large: true))
                Button("Browse New releases") { state.screen = .discover }.buttonStyle(CapsuleButtonStyle(large: true))
            }
            .padding(.top, CU.Space.s)
        case .noneRightNow:
            Text("No picks right now.").cu(CU.Font.title1).foregroundStyle(CU.text)
            emptyBody(state.library.picksNote ?? "Nothing is missing from your recommendations right now.")
            Button("Browse New releases") { state.screen = .discover }.buttonStyle(CapsuleButtonStyle(large: true)).padding(.top, CU.Space.s)
        case .withoutLibrarian:
            Text("Picks are unavailable.").cu(CU.Font.title1).foregroundStyle(CU.text)
            emptyBody("Picks come from Librarian, which is not answering.")
        }
    }

    private func emptyBody(_ text: String) -> some View {
        Text(text).font(.system(size: 14)).lineSpacing(3).foregroundStyle(CU.textSecondary)
            .fixedSize(horizontal: false, vertical: true).frame(maxWidth: 520, alignment: .leading)
    }

    // MARK: Loading

    /// One block for the marquee, then two rows of a title block and six square blocks (three when narrow).
    private var skeleton: some View {
        VStack(alignment: .leading, spacing: CU.Space.l) {
            HomeSkeletonBlock(height: Self.marqueeMinHeight, radius: Self.marqueeRadius)
            ForEach(0..<2, id: \.self) { _ in
                VStack(alignment: .leading, spacing: 12) {   // the mockup's 12 under the title block
                    HomeSkeletonBlock(width: 170, height: 20)
                    LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: CU.Space.m), count: stacked ? 3 : 6), spacing: CU.Space.m) {
                        ForEach(0..<6, id: \.self) { _ in
                            RoundedRectangle(cornerRadius: 8, style: .continuous).fill(CU.bgFill).aspectRatio(1, contentMode: .fit)
                        }
                    }
                }
            }
        }
        .accessibilityElement(children: .ignore).accessibilityLabel("Loading Home")
    }
}

/// The marquee's buttons (plan section 2): Get is a white capsule with its label in the Day `accentStrong`; the others are white at
/// 20% with a white label. A disabled button is dimmed.
private struct MarqueeButtonStyle: ButtonStyle {
    var primary = false
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 13, weight: .semibold)).lineLimit(1).fixedSize()
            .padding(.horizontal, 18).frame(minHeight: 32)
            .foregroundStyle(primary ? CupertinoHome.dayAccentStrong : Color.white)
            .background(primary ? Color.white : Color.white.opacity(0.2), in: Capsule())
            .opacity(!isEnabled ? 0.5 : configuration.isPressed ? 0.85 : 1)
    }
}

/// Lays children out left to right and wraps to the next line when the row is full.
struct FlowLayout: Layout {
    var spacing: CGFloat
    var rowSpacing: CGFloat? = nil

    private var verticalSpacing: CGFloat { rowSpacing ?? spacing }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? .infinity
        var x: CGFloat = 0, y: CGFloat = 0, rowHeight: CGFloat = 0, maxX: CGFloat = 0
        for s in subviews {
            let natural = s.sizeThatFits(.unspecified)
            let size = natural.width > width && width.isFinite ? s.sizeThatFits(ProposedViewSize(width: width, height: nil)) : natural
            if x > 0, x + size.width > width { x = 0; y += rowHeight + verticalSpacing; rowHeight = 0 }
            x += size.width + spacing; rowHeight = max(rowHeight, size.height); maxX = max(maxX, x - spacing)
        }
        return CGSize(width: maxX, height: y + rowHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, rowHeight: CGFloat = 0
        for s in subviews {
            let natural = s.sizeThatFits(.unspecified)
            let size = natural.width > bounds.width ? s.sizeThatFits(ProposedViewSize(width: bounds.width, height: nil)) : natural
            if x > bounds.minX, x + size.width > bounds.maxX { x = bounds.minX; y += rowHeight + verticalSpacing; rowHeight = 0 }
            s.place(at: CGPoint(x: x, y: y), anchor: .topLeading, proposal: ProposedViewSize(size))
            x += size.width + spacing; rowHeight = max(rowHeight, size.height)
        }
    }
}
