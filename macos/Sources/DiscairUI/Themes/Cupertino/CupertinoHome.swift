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
    @State private var growthMode: HomeScreen.GrowthMode = .total
    @State private var range: HomeDashboard.GrowthRange = .oneYear
    @State private var decadeSelection: String?
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
            VStack(alignment: .leading, spacing: CU.Space.m) {
                header
                if loading { skeleton } else { page }
            }
            .padding(.horizontal, CU.Space.xl).padding(.bottom, CU.Space.xl)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .onGeometryChange(for: CGFloat.self) { $0.size.width - CU.Space.xl * 2 } action: { width = $0 }
        .task(id: refreshKey) { if state.session != nil { await state.refreshHomeDashboard() } }
        .task { await state.loadInsights(); await state.loadHomeFeeds() }
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

    @ViewBuilder private var page: some View {
        notice
        briefing.padding(.vertical, CU.Space.m)
        if librarianUp {
            split([2, 1]) { pickPanel; arrivalsPanel }
            split([2, 1]) { collectionPanel; decadesPanel }
            split([1, 1]) { tastePanel; lensesPanel }
            split([2, 1]) { shelfPanel; activityPanel }
        } else {
            collectionPanel
            split([2, 1]) { shelfPanel; activityPanel }
        }
        recentlyAdded.padding(.top, CU.Space.m)
        // Draws nothing until today's picture is found; kept from the earlier Home.
        if state.library.isLive { LinerNoteCard(albums: state.visible(state.library.missing)) }
    }

    /// Two or three panels side by side, or one column in reading order when the content is under 860 pt wide.
    @ViewBuilder private func split<C: View>(_ weights: [CGFloat], @ViewBuilder _ content: () -> C) -> some View {
        if stacked { VStack(spacing: CU.Space.m) { content() } } else { HomeSplit(weights: weights) { content() } }
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
                 action: { state.openNeverPlayedPlaylist() }, actionHint: "Opens a smart playlist of songs with no plays") {
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

    // MARK: 2. Today's pick

    private var pickPanel: some View {
        HomePanel {
            if let position = HomeScreen.pickPosition(index: pickIndex, count: picks.count) {
                pickDeck(picks[position.index], position: position)
            } else {
                pickEmptyState
            }
        }
    }

    private func pickDeck(_ a: AlbumItem, position: (index: Int, label: String)) -> some View {
        let coverSide: CGFloat = stacked ? 160 : 232
        return VStack(alignment: .leading, spacing: CU.Space.m) {
            HStack(alignment: .top, spacing: CU.Space.m) {
                CoverView(album: a).frame(width: coverSide, height: coverSide)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .shadow(color: CU.shadowInk.opacity(0.16), radius: 12, y: 4)
                VStack(alignment: .leading, spacing: CU.Space.s) {
                    HStack {
                        HomeEyebrow("Today's pick · \(position.label)")
                        Spacer(minLength: 0)
                        stepButton("chevron.left", "Previous pick", position.index > 0) { pickIndex = position.index - 1 }
                        stepButton("chevron.right", "Next pick", position.index < picks.count - 1) { pickIndex = position.index + 1 }
                    }
                    Text(a.title).cu(CU.Font.title1).foregroundStyle(CU.text).lineLimit(2).fixedSize(horizontal: false, vertical: true)
                    Text(a.line([a.artist, a.yearText, a.genre, "not in your library"])).cu(CU.Font.body).foregroundStyle(CU.textSecondary).lineLimit(2)
                    if let reason = a.reason, !reason.isEmpty {
                        Text(reason).cu(CU.Font.body).foregroundStyle(CU.text).lineSpacing(CU.Font.body.lineHeight - CU.Font.body.size)
                            .lineLimit(4).fixedSize(horizontal: false, vertical: true).padding(.top, CU.Space.s)
                    }
                    if let track = a.suggestedTracks.first { suggestedTrack(track, album: a).padding(.top, CU.Space.xs) }
                    Spacer(minLength: 0)
                    pickButtons(a)
                    pickNoticeView()
                }
            }
            if !stacked { keyHints }
        }
        .focusable().focused($pickFocused).focusEffectDisabled()
        .overlay { if pickFocused { RoundedRectangle(cornerRadius: 12, style: .continuous).stroke(CU.accent.opacity(0.28), lineWidth: 3).padding(-4).allowsHitTesting(false) } }
        .onKeyPress(.rightArrow) { act(.get, a) }
        .onKeyPress(.downArrow) { act(.save, a) }
        .onKeyPress(.leftArrow) { act(.notForMe, a) }
        .onKeyPress(.space) { act(.play, a) }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Today's pick, \(position.label)")
    }

    private func stepButton(_ symbol: String, _ label: String, _ enabled: Bool, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: symbol).font(CU.Icon.small(.semibold)).frame(width: 24, height: 24).contentShape(Rectangle())
        }
        .buttonStyle(.plain).foregroundStyle(enabled ? CU.textSecondary : CU.textTertiary).disabled(!enabled).accessibilityLabel(label)
    }

    /// Picks are albums the library lacks, so there is nothing to play yet: the round button gets the song. An owned album plays it.
    private func suggestedTrack(_ title: String, album a: AlbumItem) -> some View {
        HStack(spacing: CU.Space.s) {
            Button { if a.owned { state.playAlbum(a) } else { state.actions.getSong(album: a, title: title, trackNumber: nil) } } label: {
                Image(systemName: a.owned ? "play.fill" : "arrow.down").font(CU.Icon.small(.semibold)).foregroundStyle(CU.text)
                    .frame(width: 32, height: 32).background(CU.bgFillOnPanel, in: Circle())
            }
            .buttonStyle(.plain).accessibilityLabel(a.owned ? "Play \(title)" : "Get the song \(title)")
            VStack(alignment: .leading, spacing: 0) {
                Text(title).cu(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                Text("Suggested track").cu(CU.Font.callout).foregroundStyle(CU.textSecondary)
            }
        }
    }

    @ViewBuilder private func pickNoticeView() -> some View {
        if let pickNotice {
            Label(pickNotice, systemImage: "info.circle").cu(CU.Font.callout).foregroundStyle(CU.info)
                .accessibilityAddTraits(.updatesFrequently)
        }
    }

    private func pickButtons(_ a: AlbumItem) -> some View {
        let acq = state.acquisition
        let label = acq.buttonLabel(for: a)
        return HStack(spacing: CU.Space.s) {
            Button { state.actions.get(album: a) } label: {
                Label(label == "Get" ? "Get album" : label, systemImage: "icloud.and.arrow.down")
            }
            .buttonStyle(CapsuleButtonStyle(primary: true, large: true)).disabled(!acq.canGet(a))
            .help(acq.detail(for: a)).accessibilityHint(acq.detail(for: a))
            Button(acq.isSaved(a) ? "Saved" : "Save") { state.actions.save(album: a) }
                .buttonStyle(CapsuleButtonStyle(large: true)).disabled(acq.isSaved(a))
            Button("Not for me") { state.actions.notForMe(album: a) }.buttonStyle(CapsuleButtonStyle(outlined: true, large: true))
        }
    }

    private var keyHints: some View {
        HStack(spacing: CU.Space.m) {
            HomeKeyHint(key: "arrow.right", symbol: true, label: "Get")
            HomeKeyHint(key: "arrow.down", symbol: true, label: "Save")
            HomeKeyHint(key: "arrow.left", symbol: true, label: "Not for me")
            HomeKeyHint(key: "Space", symbol: false, label: "Play the suggested track")
        }
        .accessibilityHidden(true)   // the buttons carry the same actions; the hints are for sighted keyboard users
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
            Text("Picks come from your listening history. Connect Last.fm or ListenBrainz in Services and the first list is built within a few minutes. Nothing is suggested from guesses.")
                .cu(CU.Font.body).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true)
            HStack(spacing: CU.Space.s) {
                Button("Open Services") { state.screen = .settings }.buttonStyle(CapsuleButtonStyle(large: true))
                Button("Browse New releases") { state.screen = .discover }.buttonStyle(CapsuleButtonStyle(large: true))
            }
            .padding(.top, CU.Space.s)
        case .noneRightNow:
            Text("No picks right now.").cu(CU.Font.title1).foregroundStyle(CU.text)
            Text(state.library.picksNote ?? "Nothing is missing from your recommendations right now.")
                .cu(CU.Font.body).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true)
            Button("Browse New releases") { state.screen = .discover }.buttonStyle(CapsuleButtonStyle(large: true)).padding(.top, CU.Space.s)
        case .withoutLibrarian:
            Text("Picks are unavailable.").cu(CU.Font.title1).foregroundStyle(CU.text)
            Text("Picks come from Librarian, which is not answering.").cu(CU.Font.body).foregroundStyle(CU.textSecondary)
        }
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
            HStack(spacing: CU.Space.s) {
                CoverView(album: placeholder(title: title, artist: artist)).frame(width: 48, height: 48).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                VStack(alignment: .leading, spacing: CU.Space.xs) {
                    Text(title).cu(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                    Text("Heard on \(station) at \(heardAt.formatted(date: .omitted, time: .shortened))").cu(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(1)
                }
                Spacer(minLength: 0)
                Button("Get") { Task { await state.getRadioPlay(playID) } }
                    .buttonStyle(CapsuleButtonStyle(small: true)).accessibilityLabel("Get \(title) by \(artist)")
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

    // MARK: 4. Collection over time

    private var collectionPanel: some View {
        let series = d.series(range)
        let phase = growthPhase(series)
        return HomePanel {
            HomeHeader(title: "Collection over time", subtitle: HomeScreen.growthSubtitle(series, mode: growthMode)) {
                HStack(spacing: CU.Space.s) {
                    CUSegmented(HomeScreen.GrowthMode.allCases.map { (value: $0, label: $0.rawValue) }, selection: $growthMode, accessibilityName: "Chart type")
                    CUSegmented(HomeDashboard.GrowthRange.allCases.map { (value: $0, label: $0.rawValue) }, selection: $range, accessibilityName: "Range")
                }
            }
            CUChartFrame("", phase: phase, plotHeight: 232, ghost: growthMode == .total ? .line : .columns) {
                if let series { growthChart(series) }
            }
            .padding(.top, CU.Space.s)
        }
    }

    private func growthPhase(_ series: HomeDashboard.GrowthSeries?) -> CUChartPhase {
        switch d.load {
        case .notLoaded: .unavailable(headline: "Not available", message: "Your library has not been read yet.", fixTitle: nil)
        case .empty: .insufficient(headline: "Nothing to chart yet", threshold: "Add albums and their added dates appear here.")
        case .ready:
            HomeScreen.growthAvailable(series) ? .ready
                : .insufficient(headline: "Not enough data", threshold: "Needs albums with added dates across at least two periods.")
        }
    }

    @ViewBuilder private func growthChart(_ series: HomeDashboard.GrowthSeries) -> some View {
        let unit = CUValueFormat(unit: "albums", singular: "album")
        if growthMode == .total {
            CULineChart(points: series.points.map { CUChartPoint(value: Double($0.total), detail: HomeScreen.growthDetail($0, series: series)) },
                        axisLabels: HomeScreen.growthAxisLabels(series), annotations: HomeScreen.biggestPeriod(series).map { [$0] } ?? [],
                        format: unit, height: 232, title: "Albums in your library", xTitle: "Date", yTitle: "Albums")
        } else {
            let labels = HomeScreen.growthAxisLabels(series)
            let labelAt = Dictionary(uniqueKeysWithValues: zip(CUChartMath.labelIndices(count: series.points.count, labels: labels.count), labels))
            CUColumnChart(columns: series.points.enumerated().map { i, p in
                CUColumn(label: labelAt[i] ?? "", value: Double(p.added), detail: HomeScreen.growthDetail(p, series: series))
            }, format: unit, height: 232, title: "Albums added", xTitle: "Period", yTitle: "Albums added")
        }
    }

    // MARK: 5. Own and play, by decade

    private var decadesPanel: some View {
        let shares = d.listenSharesAvailable
        return HomePanel {
            HomeHeader("Own and play, by decade",
                       subtitle: shares ? "Share of albums against share of listens, last \(state.taste.profiles?.config.recentDays ?? 90) days"
                                        : "Share of the albums you own, by decade of release")
            if d.decades.isEmpty {
                Text(d.load == .ready ? "No album has a release year, so there is nothing to group." : "Not available until your library has been read.")
                    .cu(CU.Font.body).foregroundStyle(CU.textSecondary).padding(.top, CU.Space.s)
            } else if shares {
                CUPairedBars(rows: d.decades.map { CUPairedRow(label: $0.label, context: $0.ownedShare * 100, highlight: ($0.listenShare ?? 0) * 100) },
                             selection: $decadeSelection, legend: (context: "Albums you own", highlight: "Listens"), title: "Own and play, by decade")
                    .padding(.top, CU.Space.s)
            } else {
                CURankedBars(rows: d.decades.map { CURankedRow(label: $0.label, value: $0.ownedShare * 100) }, title: "Albums you own, by decade", labelWidth: 48)
                    .padding(.top, CU.Space.s)
                Text("Listens appear here once your taste profile is saved and holds enough listens.")
                    .cu(CU.Font.callout).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    // MARK: 6. Your taste

    private var tastePanel: some View {
        let profiles = state.taste.profiles
        let model = HomeScreen.taste(profiles: profiles, loaded: state.taste.loaded)
        return HomePanel {
            HStack {
                HomeEyebrow(HomeScreen.tasteEyebrow(profiles: profiles))
                Spacer(minLength: 0)
                Button("Open Insights") { state.screen = .insights }.buttonStyle(CapsuleButtonStyle(small: true))
            }
            switch model {
            case .loading:
                HomeSkeletonBlock(height: 32); HomeSkeletonBlock(height: 96)
            case .progress(let listens, let need):
                Text("Taste needs listening history.").cu(CU.Font.title1).foregroundStyle(CU.text)
                Text(listens < need ? "Connect ListenBrainz in Services, or keep playing. A window is described once it holds \(need) listens."
                                    : "The server has not described this window yet. It will when its next refresh runs.")
                    .cu(CU.Font.body).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true)
                progressBar(listens: listens, need: need)
                Button("Open Services") { state.screen = .settings }.buttonStyle(CapsuleButtonStyle())
            case .ready(let headline, let shifts, let recentLabel, let recent, let allTime):
                Text(headline).cu(CU.Font.title1).foregroundStyle(CU.text).fixedSize(horizontal: false, vertical: true)
                if !shifts.isEmpty {
                    CUDumbbell(rows: shifts.map { CUDumbbellRow(label: $0.label, before: $0.before, now: $0.now) }, title: "Taste shifts")
                        .padding(.top, CU.Space.s)
                }
                HStack(spacing: CU.Space.m) {
                    legendDot(hollow: true, "All time, \(HomeScreen.count(allTime)) listens")
                    legendDot(hollow: false, "\(recentLabel), \(HomeScreen.count(recent)) listens")
                }
            }
        }
    }

    private func progressBar(listens: Int, need: Int) -> some View {
        let fraction = need > 0 ? min(1, Double(listens) / Double(need)) : 0
        return VStack(alignment: .leading, spacing: CU.Space.s) {
            Capsule().fill(CU.bgFillOnPanel).frame(height: 8)
                .overlay(alignment: .leading) { GeometryReader { g in Capsule().fill(CU.text).frame(width: g.size.width * fraction) } }
            Text("\(HomeScreen.count(listens)) of \(HomeScreen.count(need)) listens").cu(CU.Font.body).foregroundStyle(CU.textSecondary)
        }
        .accessibilityElement(children: .ignore).accessibilityLabel("\(listens) of \(need) listens")
    }

    private func legendDot(hollow: Bool, _ text: String) -> some View {
        HStack(spacing: CU.Space.xs) {
            Circle().fill(hollow ? CU.bgPanel : CU.chart1).overlay(Circle().stroke(hollow ? CU.chart2 : CU.chart1, lineWidth: 2)).frame(width: 10, height: 10)
            Text(text).cu(CU.Font.caption).foregroundStyle(CU.textSecondary)
        }
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

    // MARK: 8. Shelf life

    private var shelfPanel: some View {
        let shelf = d.shelfLife
        let phase: CUChartPhase = d.load == .notLoaded ? .unavailable(headline: "Not available", message: "Your library has not been read yet.", fixTitle: nil)
            : (HomeScreen.shelfAvailable(shelf) ? .ready : .insufficient(headline: "Nothing to chart yet", threshold: "Needs albums with a play history."))
        return HomePanel {
            HomeHeader(title: "Shelf life", subtitle: "Albums by time since the last play · today, from Navidrome's latest play of each album") {
                Button("Play something unplayed") { state.playSomethingUnplayed() }
                    .buttonStyle(CapsuleButtonStyle(small: true)).disabled((d.neverPlayed ?? 0) == 0)
            }
            let content = Group {
                CUChartFrame("", phase: phase, plotHeight: 168, ghost: .columns) {
                    if let shelf {
                        CUColumnChart(columns: shelf.bins.map { CUColumn(label: HomeScreen.shortLabel($0.bin), value: Double($0.count), detail: $0.bin.label) },
                                      highlight: HomeDashboard.ShelfBin.allCases.firstIndex(of: .never), showsValueLabels: true,
                                      format: CUValueFormat(unit: "albums", singular: "album"), height: 200, title: "Albums by time since the last play",
                                      xTitle: "Time since last play", yTitle: "Albums")
                    }
                }
                .frame(maxWidth: .infinity)
                if let shelf, !shelf.longestUnplayed.isEmpty { longestCovers(shelf.longestUnplayed).layoutPriority(1) }
            }
            if stacked { VStack(alignment: .leading, spacing: CU.Space.m) { content }.padding(.top, CU.Space.s) }
            else { HStack(alignment: .bottom, spacing: CU.Space.l) { content }.padding(.top, CU.Space.s) }
        }
    }

    private func longestCovers(_ ids: [String]) -> some View {
        let now = Date()
        return VStack(alignment: .leading, spacing: CU.Space.s) {
            HomeEyebrow("Longest since a play")
            HStack(alignment: .top, spacing: CU.Space.s) {
                ForEach(ids, id: \.self) { id in
                    if let album = state.library.allNavidromeAlbums.first(where: { $0.id == id }) {
                        let item = LibraryModel.item(album, index: 0)
                        let since = HomeScreen.parseDate(album.played) ?? HomeScreen.parseDate(album.created)
                        Button { state.open(album: item) } label: {
                            VStack(spacing: CU.Space.xs) {
                                CoverView(album: item).frame(width: 64, height: 64).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                                Text(since.map { HomeScreen.ageText(since: $0, now: now) } ?? "").cu(CU.Font.caption).monospacedDigit().foregroundStyle(CU.textSecondary)
                            }
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("\(item.title) by \(item.artist), \(since.map { HomeScreen.ageText(since: $0, now: now) } ?? "no date")")
                    }
                }
            }
        }
        .fixedSize()
    }

    // MARK: 9. Server activity

    private var activityPanel: some View {
        let insights = state.insights
        let rows = HomeScreen.activity(HomeScreen.ActivityInput(
            librarianReachable: librarianUp, insightsLive: insights.isLive, insightsError: insights.error != nil, insightsLoadedAt: insights.loadedAt,
            lensesOn: insights.kinds.filter(insights.isEnabled).count, lensesTotal: insights.kinds.count,
            tasteLoaded: state.taste.loaded, tasteRefreshing: state.taste.refreshing, tasteNote: state.taste.note,
            tasteListens: state.taste.recent?.listens, graphCoverage: state.serverCapabilities?.graphCoverage,
            popularity: state.popularityStatus, insightsJob: state.insightsJobStatus))
        return HomePanel {
            HomeHeader(title: "Server activity") {
                Button("Services") { state.screen = .settings }.buttonStyle(CapsuleButtonStyle(small: true))
            }
            if !librarianUp {
                Text("Unknown. The app asks Librarian for this, and Librarian is not answering\(state.session?.activeProfile.map { " at \($0.librarianURL.absoluteString)" } ?? "").")
                    .cu(CU.Font.body).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true).padding(.top, CU.Space.s)
                Button("Open Services") { state.screen = .settings }.buttonStyle(CapsuleButtonStyle())
            } else {
                VStack(spacing: 0) {
                    ForEach(Array(rows.enumerated()), id: \.element.id) { i, row in
                        if i > 0 { Rectangle().fill(CU.separator).frame(height: 1) }
                        activityRow(row).padding(.vertical, CU.Space.s)
                    }
                }
            }
        }
    }

    private func activityRow(_ row: HomeScreen.ActivityRow) -> some View {
        HStack(alignment: .top, spacing: CU.Space.s) {
            Image(systemName: row.symbol).font(CU.Icon.row()).foregroundStyle(CU.textSecondary).frame(width: 20).padding(.top, 0).accessibilityHidden(true)
            VStack(alignment: .leading, spacing: CU.Space.xs) {
                HStack(spacing: CU.Space.s) {
                    Text(row.name).cu(CU.Font.headline).foregroundStyle(CU.text)
                    CUStatusLabel(row.status)
                }
                Text(row.line).cu(CU.Font.callout).foregroundStyle(CU.textSecondary).lineLimit(2)
                if let title = row.fixTitle, let fix = row.fix {
                    Button(title) {
                    switch fix {
                    case .openSettings: state.screen = .settings
                    case .fillPopularity: Task { await state.fillPopularity() }
                    }
                }
                .buttonStyle(CapsuleButtonStyle(small: true)).accessibilityLabel("\(title) \(row.name)")
                }
            }
            Spacer(minLength: 0)
        }
        .accessibilityElement(children: .contain)
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

    private var skeleton: some View {
        VStack(alignment: .leading, spacing: CU.Space.m) {
            HStack(alignment: .top, spacing: CU.Space.xl) {
                ForEach(0..<4, id: \.self) { _ in
                    VStack(alignment: .leading, spacing: CU.Space.s) {
                        HomeSkeletonBlock(width: 72, height: 16, radius: 8)
                        HomeSkeletonBlock(width: 120, height: 48)
                        HomeSkeletonBlock(height: 16, radius: 8)
                    }
                }
            }
            .padding(.vertical, CU.Space.m)
            split([2, 1]) {
                HomePanel { HStack(alignment: .top, spacing: CU.Space.m) {
                    HomeSkeletonBlock(width: 232, height: 232)
                    VStack(alignment: .leading, spacing: CU.Space.s) { HomeSkeletonBlock(width: 100, height: 16); HomeSkeletonBlock(width: 220, height: 32); HomeSkeletonBlock(height: 16); HomeSkeletonBlock(height: 16); HomeSkeletonBlock(width: 160, height: 40, radius: 20) }
                } }
                HomePanel { HomeSkeletonBlock(width: 100, height: 24); ForEach(0..<4, id: \.self) { _ in HomeSkeletonBlock(height: 48) } }
            }
            split([2, 1]) {
                HomePanel { HomeSkeletonBlock(width: 180, height: 24); HomeSkeletonBlock(height: 200) }
                HomePanel { HomeSkeletonBlock(width: 140, height: 24); HomeSkeletonBlock(height: 200) }
            }
        }
        .accessibilityElement(children: .ignore).accessibilityLabel("Loading Home")
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
private struct FlowLayout: Layout {
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
