import DiscairLibrarian
import DiscairNavidrome
import SwiftUI

/// Home, redesigned (`docs/redesign.md` section 5.1, step M8). A dashboard that leads with the two collector's questions:
/// "what do I have?" (the briefing band, collection, decades, shelf life) and "what should I add next?" (today's pick,
/// arrivals, taste and lenses). Operations sit last, and move to the top as a notice when something is wrong.
/// Mockups: `docs/design/redesign/macos/cupertino/home--*`. Figures come from `HomeDashboard`, wording from `HomeScreen`.
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
            .padding(.horizontal, CU.Space.xl).padding(.bottom, CU.Space.xl)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .onGeometryChange(for: CGFloat.self) { $0.size.width - CU.Space.xl * 2 } action: { width = $0 }
        .task(id: refreshKey) { if state.session != nil { await state.refreshHomeDashboard() } }
        .task { await state.loadInsights(); await state.loadHomeFeeds() }
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

    /// Two or three panels side by side, or one column in reading order when the content is under 860 pt wide.
    @ViewBuilder private func split<C: View>(_ weights: [CGFloat], @ViewBuilder _ content: () -> C) -> some View {
        if stacked { VStack(spacing: CU.Space.m) { content() } } else { HomeSplit(weights: weights) { content() } }
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

    // MARK: 1. Briefing band

    private var briefing: some View {
        // One cell per figure, the hero wider; each cell after the first has a hairline on its leading edge.
        HomeSplit(weights: librarianUp ? [1.75, 1, 1, 1] : [1.75, 1, 1], spacing: 0) {
            heroStat
            if librarianUp {
                cell(listensStat); cell(neverPlayedStat); cell(waitingStat)
            } else {
                cell(neverPlayedStat); cell(unavailableStat)
            }
        }
        .accessibilityElement(children: .contain)
    }

    private func cell<C: View>(_ content: C) -> some View {
        content.padding(.leading, CU.Space.m).padding(.trailing, CU.Space.xs)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .overlay(alignment: .leading) { Rectangle().fill(CU.separator).frame(width: 1) }
    }

    private var heroStat: some View {
        let line = HomeScreen.addedLine(d.added)
        return HomeStat(eyebrow: "Your library", value: d.albumCount.map { HomeScreen.count($0) } ?? "—", unit: "albums", hero: true,
                        action: { state.screen = .library }, actionHint: "Opens your Library") {
            switch d.load {
            case .notLoaded: Text("Your library has not been read yet.").cu(CU.Font.callout).foregroundStyle(CU.textSecondary)
            case .empty: Text("Nothing in your library yet.").cu(CU.Font.callout).foregroundStyle(CU.textSecondary)
            case .ready: HomeChange(line: line)
            }
        }
    }

    private var listensStat: some View {
        let tile = HomeScreen.listensTile(librarianReachable: librarianUp, listenBrainzConnected: hasListeningSource || state.listenBrainz.isConnected,
                                          figure: d.listens)
        if case .figure(let f) = tile {
            return AnyView(HomeStat(eyebrow: "Listens · last 7 days", value: HomeScreen.count(f.last), unit: "plays",
                                    action: { state.screen = .history }, actionHint: "Opens History") {
                HomeChange(line: HomeScreen.listensLine(f, now: Date()))
            })
        }
        return AnyView(HomeStat(eyebrow: "Listens · last 7 days", value: "—", action: { state.screen = .history }, actionHint: "Opens History") {
            HStack(alignment: .firstTextBaseline) {
                Text(tile.sentence).cu(CU.Font.callout).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true)
                if tile.offersConnect {
                    Button("Connect") { state.screen = .settings }
                        .buttonStyle(.plain).cu(CU.Font.callout).foregroundStyle(CU.accentStrong).underline()
                }
            }
        })
    }

    private var neverPlayedStat: some View {
        HomeStat(eyebrow: "Never played", value: d.neverPlayed.map { HomeScreen.count($0) } ?? "—", unit: d.neverPlayed == nil ? "" : "albums",
                 action: { state.openNeverPlayedAlbums() }, actionHint: "Opens the albums with no plays") {
            if d.neverPlayed == nil { Text("Not counted yet").cu(CU.Font.callout).foregroundStyle(CU.textSecondary) }
            else { HomeChange(line: HomeScreen.neverPlayedLine(d.neverPlayedChange)) }
        }
    }

    private var waitingStat: some View {
        let tile = HomeScreen.waitingTile(d.waiting)
        return HomeStat(eyebrow: "Waiting for you", value: tile.picks.map { HomeScreen.count($0) } ?? "—", unit: tile.picks == nil ? "" : "picks",
                        action: { state.screen = .discover }, actionHint: "Opens Discover") {
            Text(tile.detail).cu(CU.Font.callout).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true)
        }
    }

    /// With Librarian unreachable the listens and waiting figures merge into one honest tile.
    private var unavailableStat: some View {
        HomeStat(eyebrow: "Listens · waiting", value: "—") {
            Text("Unavailable without Librarian").cu(CU.Font.callout).foregroundStyle(CU.textSecondary)
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
        .onKeyPress(.rightArrow) { act(.get, a) }
        .onKeyPress(.downArrow) { act(.save, a) }
        .onKeyPress(.leftArrow) { act(.notForMe, a) }
        .onKeyPress(.space) { act(.play, a) }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Today's pick, \(position.label)")
    }

    private func pickText(_ a: AlbumItem, position: (index: Int, label: String)) -> some View {
        VStack(alignment: .leading, spacing: CU.Space.s) {
            Text("Today's pick · \(position.label)".uppercased()).cuRole(CU.Font.eyebrow).accessibilityAddTraits(.isHeader)
            Text(a.title).font(CU.Font.largeTitle.font).tracking(-0.5).lineLimit(2).fixedSize(horizontal: false, vertical: true)
            Text(a.line([a.artist, a.yearText, a.genre, "not in your library"])).font(.system(size: 15)).lineLimit(2)
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
        return Group {
            if stacked {
                HStack(spacing: CU.Space.s) {
                    Text("NEXT PICKS").cuRole(CU.Font.eyebrow).accessibilityAddTraits(.isHeader)
                    HStack(spacing: 6) { ForEach(indices, id: \.self) { nextPickButton($0) } }
                }
            } else {
                VStack(alignment: .trailing, spacing: 6) {
                    Text("NEXT PICKS").cuRole(CU.Font.eyebrow).accessibilityAddTraits(.isHeader).padding(.bottom, 2)
                    covers
                }
            }
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

    /// A button's words with its key beside them, smaller (the key hints row is gone; each key is shown inside its button).
    private func keyed(_ words: Text, _ key: String) -> some View {
        HStack(spacing: 6) { words; Text(key).font(.system(size: 10.5, weight: .semibold)).accessibilityHidden(true) }
    }

    /// Get is the one primary button: white, its label in the Day `accentStrong` in both modes. Each key is shown inside its button.
    private func pickButtons(_ a: AlbumItem) -> some View {
        let acq = state.acquisition
        let label = acq.buttonLabel(for: a)
        return HStack(spacing: CU.Space.s) {
            Button { state.actions.get(album: a) } label: { keyed(Text(label == "Get" ? "Get album" : label), "→") }
                .buttonStyle(MarqueeButtonStyle(primary: true)).disabled(!acq.canGet(a))
                .help(acq.detail(for: a)).accessibilityHint(acq.detail(for: a))
            Button { state.actions.save(album: a) } label: { keyed(Text(acq.isSaved(a) ? "Saved" : "Save"), "↓") }
                .buttonStyle(MarqueeButtonStyle()).disabled(acq.isSaved(a))
            Button { state.actions.notForMe(album: a) } label: { keyed(Text("Not for me"), "←") }
                .buttonStyle(MarqueeButtonStyle())
        }
    }

    /// Arrow keys act on the pick in view. Space plays the album when owned, and otherwise shows a short notice.
    private func act(_ key: HomeScreen.PickKey, _ a: AlbumItem) -> KeyPress.Result {
        if key != .play { pickNotice = nil }
        switch key {
        case .get: guard state.acquisition.canGet(a) else { return .ignored }; state.actions.get(album: a)
        case .save: guard !state.acquisition.isSaved(a) else { return .ignored }; state.actions.save(album: a)
        case .notForMe: state.actions.notForMe(album: a)
        case .play:
            switch HomeScreen.spaceOutcome(owned: a.owned) {
            case .play: pickNotice = nil; state.playAlbum(a)
            case .notOwned(let notice): pickNotice = notice
            }
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

    // MARK: 3. Arrivals

    @ViewBuilder private var arrivalsPanel: some View {
        // Arrivals collapses when empty once the app has history; before that its empty sentence explains what will appear.
        if !(d.arrivals.isEmpty && pickEmpty != .needsHistory) {
            HomePanel {
                HomeHeader(title: "Arrivals") {
                    Button("All downloads") { state.screen = .downloads }.buttonStyle(CapsuleButtonStyle(small: true))
                }
                if d.arrivals.isEmpty {
                    Text("Nothing on its way. Albums you Get appear here while they download, and stay until you have played them.")
                        .cu(CU.Font.body).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true).padding(.top, CU.Space.s)
                } else {
                    VStack(spacing: 0) {
                        ForEach(Array(d.arrivals.enumerated()), id: \.element.id) { i, row in
                            if i > 0 { Rectangle().fill(CU.separator).frame(height: 1) }
                            arrivalRow(row).padding(.vertical, CU.Space.s)
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder private func arrivalRow(_ row: HomeDashboard.ArrivalRow) -> some View {
        switch row {
        case .job(_, let title, let artist, let stage, let failure):
            HStack(spacing: CU.Space.s) {
                CoverView(album: placeholder(title: title, artist: artist)).frame(width: 48, height: 48).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                VStack(alignment: .leading, spacing: CU.Space.xs) {
                    Text(title).cu(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                    Text("\(artist) · \(failure == nil ? Self.stageWords[stage.rawValue] : "Failed")").cu(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
                    CUStageTracker(step: stage.rawValue, failed: failure != nil, failureReason: failure)
                }
            }
            .accessibilityElement(children: .combine)
        case .radio(let playID, let title, let artist, let station, let heardAt):
            VStack(alignment: .leading, spacing: CU.Space.xs) {
            HStack(spacing: CU.Space.s) {
                CoverView(album: placeholder(title: title, artist: artist)).frame(width: 48, height: 48).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                VStack(alignment: .leading, spacing: CU.Space.xs) {
                    Text(title).cu(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                    Text("Heard on \(station) at \(heardAt.formatted(date: .omitted, time: .shortened))").cu(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
                }
                Spacer(minLength: 0)
                DownloadButton(state: state.downloadState(playID: playID), compact: true, surface: .page) {
                    Task { await state.radioDownloads.get(playID: playID) }
                }
            }
            if let sentence = state.radioDownloads.sentence(for: playID) {
                Text(sentence).cu(CU.Font.caption).foregroundStyle(state.downloadState(playID: playID) == .failed ? CU.danger : CU.textSecondary)
                    .lineLimit(2).padding(.leading, 48 + CU.Space.s)
            }
            }
        case .arrived(let id, let title, let artist):
            HStack(spacing: CU.Space.s) {
                let item = ownedItem(id) ?? placeholder(title: title, artist: artist)
                CoverView(album: item).frame(width: 48, height: 48).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                VStack(alignment: .leading, spacing: CU.Space.xs) {
                    Text(title).cu(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                    Text("\(artist) · Not played yet").cu(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
                }
                Spacer(minLength: 0)
                Button { state.playAlbum(item) } label: { Label("Play", systemImage: "play.fill") }
                    .buttonStyle(CapsuleButtonStyle(small: true)).accessibilityLabel("Play \(title)")
            }
        }
    }

    private static let stageWords = ["Looking for a source", "Downloading", "Importing", "In library"]

    private func placeholder(title: String, artist: String) -> AlbumItem {
        AlbumItem(id: -1, title: title, artist: artist, year: 0, genre: "", format: "", owned: false, hue: LibraryModel.hue(for: title))
    }

    private func ownedItem(_ navidromeID: String) -> AlbumItem? {
        state.library.allNavidromeAlbums.first { $0.id == navidromeID }.map { LibraryModel.item($0, index: 0) }
    }

    // MARK: 7. From the lenses

    private var lensesPanel: some View {
        let insights = state.insights
        let summary = HomeScreen.lenses(insights.kinds.map {
            HomeScreen.LensInput(kind: $0, name: CupertinoInsights.name($0), enabled: insights.isEnabled($0), cards: insights.cards($0))
        })
        return HomePanel {
            HomeHeader(title: "From the lenses") {
                HStack(spacing: CU.Space.s) {
                    Text(summary.countText).cu(CU.Font.body).foregroundStyle(CU.textSecondary)
                    Button("All insights") { state.screen = .insights }.buttonStyle(CapsuleButtonStyle(small: true))
                }
            }
            if summary.enabledCount == 0 {
                Text("No lens is on yet. The server turns a lens on only after it passes its own check, so nothing here is a guess.")
                    .cu(CU.Font.body).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true).padding(.top, CU.Space.s)
                FlowChips(items: summary.off.map { "\($0) · off" })
            } else if summary.rows.isEmpty {
                Text("Every lens that is on found nothing to show today. A lens never fills the gap with guesses.")
                    .cu(CU.Font.body).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true).padding(.top, CU.Space.s)
            } else {
                VStack(spacing: 0) {
                    ForEach(Array(summary.rows.enumerated()), id: \.element.card.id) { i, row in
                        if i > 0 { Rectangle().fill(CU.separator).frame(height: 1) }
                        lensRow(row.card, lens: row.lens).padding(.vertical, CU.Space.s)
                    }
                }
            }
        }
    }

    private func lensRow(_ c: InsightCard, lens: String) -> some View {
        let get = InsightsModel.album(for: c)
        let owned = c.kind == "anniversary" ? ownedAlbum(c) : nil
        return HStack(spacing: CU.Space.s) {
            if let n = c.owned, let t = c.total {
                VStack(spacing: 0) {
                    Text("\(n)/\(t)").cu(CU.Font.metric).monospacedDigit().foregroundStyle(CU.text)
                    Text("owned").cu(CU.Font.caption).foregroundStyle(CU.textSecondary)
                }
                .frame(width: 56, height: 56).background(CU.content, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            } else {
                CoverView(album: owned ?? get ?? placeholder(title: c.subject.title ?? c.title, artist: c.subject.artist ?? ""))
                    .frame(width: 56, height: 56).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            }
            VStack(alignment: .leading, spacing: CU.Space.xs) {
                Text(c.title).cu(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                Text("\(lens) · \(c.body)").cu(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
            }
            Spacer(minLength: 0)
            if let owned {
                Button { state.insights.accepted(c, librarian: state.session?.librarian); state.actions.play(album: owned) } label: { Label("Play", systemImage: "play.fill") }
                    .buttonStyle(CapsuleButtonStyle(small: true)).accessibilityLabel("Play \(owned.title)")
            } else if let get {
                Button("Get") { state.insights.accepted(c, librarian: state.session?.librarian); state.actions.get(album: get) }
                    .buttonStyle(CapsuleButtonStyle(small: true)).disabled(!state.acquisition.canGet(get)).accessibilityLabel("Get \(get.title)")
            }
        }
        .accessibilityElement(children: .contain)
    }

    private func ownedAlbum(_ c: InsightCard) -> AlbumItem? {
        let t = (c.subject.title ?? c.title).lowercased(), a = (c.subject.artist ?? "").lowercased()
        return state.library.albums.first { $0.title.lowercased() == t && $0.artist.lowercased() == a }
    }

    // MARK: 10. Recently added

    private var recentlyAdded: some View {
        let albums = Array(state.library.recent.prefix(6))
        let columns = Array(repeating: GridItem(.flexible(), spacing: CU.Space.m, alignment: .top), count: stacked ? 3 : 6)
        return VStack(alignment: .leading, spacing: CU.Space.m) {
            HomeHeader(title: "Recently added") {
                Button("Library") { state.screen = .library }.buttonStyle(CapsuleButtonStyle(small: true))
            }
            if albums.isEmpty {
                Text(d.load == .notLoaded ? "Your library has not been read yet." : "Albums you add appear here.").cu(CU.Font.body).foregroundStyle(CU.textSecondary)
            } else {
                LazyVGrid(columns: columns, alignment: .leading, spacing: CU.Space.m) {
                    ForEach(albums) { a in
                        Button { state.open(album: a) } label: {
                            VStack(alignment: .leading, spacing: CU.Space.xs) {
                                CoverView(album: a).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                                    .shadow(color: CU.shadowInk.opacity(0.16), radius: 12, y: 4).padding(.bottom, CU.Space.xs)
                                Text(a.title).cu(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                                Text(a.artist).cu(CU.Font.body).foregroundStyle(CU.textSecondary).lineLimit(1)
                            }
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain).accessibilityLabel("\(a.title) by \(a.artist)")
                    }
                }
            }
        }
    }

    // MARK: Loading

    /// One block for the marquee, then two rows of a title block and six square blocks (three when narrow).
    private var skeleton: some View {
        VStack(alignment: .leading, spacing: CU.Space.l) {
            HomeSkeletonBlock(height: Self.marqueeMinHeight, radius: Self.marqueeRadius)
            ForEach(0..<2, id: \.self) { _ in
                VStack(alignment: .leading, spacing: CU.Space.m) {
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

/// Small neutral chips that wrap: the "Forgotten Gems · off" list of a first run.
private struct FlowChips: View {
    let items: [String]
    @Environment(\.cuInPanel) private var inPanel

    var body: some View {
        FlowLayout(spacing: CU.Space.s) {
            ForEach(items, id: \.self) { item in
                Text(item).cu(CU.Font.headline).foregroundStyle(CU.textSecondary)
                    .padding(.horizontal, CU.Space.m).frame(height: 32)
                    .background(inPanel ? CU.bgFillOnPanel : CU.bgFill, in: Capsule())
            }
        }
    }
}

/// Lays children out left to right and wraps to the next line when the row is full.
struct FlowLayout: Layout {
    var spacing: CGFloat

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? .infinity
        var x: CGFloat = 0, y: CGFloat = 0, rowHeight: CGFloat = 0, maxX: CGFloat = 0
        for s in subviews {
            let size = s.sizeThatFits(.unspecified)
            if x > 0, x + size.width > width { x = 0; y += rowHeight + spacing; rowHeight = 0 }
            x += size.width + spacing; rowHeight = max(rowHeight, size.height); maxX = max(maxX, x - spacing)
        }
        return CGSize(width: maxX, height: y + rowHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, rowHeight: CGFloat = 0
        for s in subviews {
            let size = s.sizeThatFits(.unspecified)
            if x > bounds.minX, x + size.width > bounds.maxX { x = bounds.minX; y += rowHeight + spacing; rowHeight = 0 }
            s.place(at: CGPoint(x: x, y: y), anchor: .topLeading, proposal: ProposedViewSize(size))
            x += size.width + spacing; rowHeight = max(rowHeight, size.height)
        }
    }
}
