import DiscairLibrarian
import SwiftUI

// The panels that used to fill Home with figures. Home is artwork-led now (`docs/MACOS_HOME_MARQUEE_PLAN.md`); the charts live on
// Insights under "Your collection", and Server activity under Settings > Services. Each panel reads `state` and draws what the
// Home dashboard computes, exactly as before (slice H2: a move, no change to what is drawn).

/// "Collection over time": albums owned, or added, by period.
struct CollectionOverTimePanel: View {
    let state: AppState
    @State private var growthMode: HomeScreen.GrowthMode = .total
    @State private var range: HomeDashboard.GrowthRange = .oneYear
    private var d: HomeDashboard { state.homeDashboard }

    var body: some View {
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
}

/// "Own and play, by decade": share of albums against share of listens.
struct OwnAndPlayByDecadePanel: View {
    let state: AppState
    @State private var decadeSelection: String?
    private var d: HomeDashboard { state.homeDashboard }

    var body: some View {
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
}

/// "Your taste": the server's headline and the shifts between the recent window and all time.
struct TastePanel: View {
    let state: AppState

    var body: some View {
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
}

/// "Shelf life": albums by time since the last play. The four small covers moved to Home's "Waiting longest".
struct ShelfLifePanel: View {
    let state: AppState
    private var d: HomeDashboard { state.homeDashboard }

    var body: some View {
        let shelf = d.shelfLife
        let phase: CUChartPhase = d.load == .notLoaded ? .unavailable(headline: "Not available", message: "Your library has not been read yet.", fixTitle: nil)
            : (HomeScreen.shelfAvailable(shelf) ? .ready : .insufficient(headline: "Nothing to chart yet", threshold: "Needs albums with a play history."))
        return HomePanel {
            HomeHeader(title: "Shelf life", subtitle: "Albums by time since the last play · today, from Navidrome's latest play of each album") {
                Button("Play something unplayed") { state.playSomethingUnplayed() }
                    .buttonStyle(CapsuleButtonStyle(small: true)).disabled((d.neverPlayed ?? 0) == 0)
            }
            CUChartFrame("", phase: phase, plotHeight: 168, ghost: .columns) {
                if let shelf {
                    CUColumnChart(columns: shelf.bins.map { CUColumn(label: HomeScreen.shortLabel($0.bin), value: Double($0.count), detail: $0.bin.label) },
                                  highlight: HomeDashboard.ShelfBin.allCases.firstIndex(of: .never), showsValueLabels: true,
                                  format: CUValueFormat(unit: "albums", singular: "album"), height: 200, title: "Albums by time since the last play",
                                  xTitle: "Time since last play", yTitle: "Albums")
                }
            }
            .frame(maxWidth: .infinity).padding(.top, CU.Space.s)
        }
    }
}

/// "Server activity": what the server is doing for the app, one row per job.
struct ServerActivityPanel: View {
    let state: AppState
    /// On Settings > Services the page is already the place the buttons lead to, so they are left out.
    var onServicesPage = false
    private var d: HomeDashboard { state.homeDashboard }
    private var librarianUp: Bool { d.notice != .librarianUnreachable }

    var body: some View {
        let insights = state.insights
        let rows = HomeScreen.activity(HomeScreen.ActivityInput(
            librarianReachable: librarianUp, insightsLive: insights.isLive, insightsError: insights.error != nil, insightsLoadedAt: insights.loadedAt,
            lensesOn: insights.kinds.filter(insights.isEnabled).count, lensesTotal: insights.kinds.count,
            tasteLoaded: state.taste.loaded, tasteRefreshing: state.taste.refreshing, tasteNote: state.taste.note,
            tasteListens: state.taste.recent?.listens, graphCoverage: state.serverCapabilities?.graphCoverage,
            popularity: state.popularityStatus, insightsJob: state.insightsJobStatus))
        return HomePanel {
            HomeHeader(title: "Server activity") {
                if !onServicesPage { Button("Services") { state.screen = .settings }.buttonStyle(CapsuleButtonStyle(small: true)) }
            }
            if !librarianUp {
                Text("Unknown. The app asks Librarian for this, and Librarian is not answering\(state.session?.activeProfile.map { " at \($0.librarianURL.absoluteString)" } ?? "").")
                    .cu(CU.Font.body).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true).padding(.top, CU.Space.s)
                if !onServicesPage { Button("Open Services") { state.screen = .settings }.buttonStyle(CapsuleButtonStyle()) }
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
}

