import AppKit
import SwiftUI
import Testing
@testable import DiscairUI

/// The sample data and layout of `docs/design/redesign/macos/cupertino/charts--specimens`, built from the real chart views.
/// The render goes to `DISCAIR_SCREENSHOT_DIR` (or a temp folder) as `cupertino-chart-specimens.png`, to be put beside the mockup.
@MainActor
struct CupertinoChartSpecimenTests {
    @Test func rendersTheSpecimenSheet() throws {
        RenderMode.offscreenScreenshot = true
        let size = NSSize(width: 1520, height: 2040)
        let host = NSHostingView(rootView: CUChartSpecimenSheet().frame(width: size.width, height: size.height, alignment: .topLeading))
        host.frame = NSRect(origin: .zero, size: size)
        let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
        window.contentView = host
        window.orderBack(nil)
        host.layoutSubtreeIfNeeded()
        RunLoop.current.run(until: Date().addingTimeInterval(0.8))
        let rep = try #require(host.bitmapImageRepForCachingDisplay(in: host.bounds))
        host.cacheDisplay(in: host.bounds, to: rep)
        let png = try #require(rep.representation(using: .png, properties: [:]))
        var colours = Set<Int>()
        for ix in 0..<64 {
            for iy in 0..<64 {
                let x = (rep.pixelsWide - 1) * ix / 63, y = (rep.pixelsHigh - 1) * iy / 63
                guard let c = rep.colorAt(x: x, y: y)?.usingColorSpace(.sRGB) else { continue }
                colours.insert(Int(c.redComponent * 15) << 8 | Int(c.greenComponent * 15) << 4 | Int(c.blueComponent * 15))
            }
        }
        #expect(colours.count >= 8, "render looks blank (\(colours.count) distinct colours)")
        let dir = URL(fileURLWithPath: ProcessInfo.processInfo.environment["DISCAIR_SCREENSHOT_DIR"] ?? NSTemporaryDirectory())
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try png.write(to: dir.appendingPathComponent("cupertino-chart-specimens.png"))
    }
}

private enum Specimen {
    static let growth: [Double] = [1012, 1019, 1027, 1031, 1044, 1052, 1058, 1071, 1077, 1090, 1096, 1101, 1113, 1118, 1131, 1139, 1147, 1158, 1166, 1171, 1183, 1190, 1204, 1209, 1221, 1228, 1236, 1247, 1253, 1262, 1267, 1272, 1284]
    static let added: [Double] = [9, 14, 22, 31, 18, 12, 25, 16, 21, 28, 17, 12]
    static let last: [Double] = [6, 10, 12, 18, 20, 9, 14, 15, 11, 19, 13, 7]
    static let months = ["December", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November"]
    static let eras = [("1960s", 6.0, 4.0), ("1970s", 17, 12), ("1980s", 21, 19), ("1990s", 27, 38), ("2000s", 15, 14), ("2010s", 10, 9), ("2020s", 4, 4)]
    static let genres = [("Dream pop", 19.0), ("Ambient", 17), ("Post-rock", 14), ("Spiritual jazz", 11), ("Krautrock", 9), ("Post-punk", 8)]
    static let shelf = [212.0, 318, 204, 263, 191, 96]
    static let shelfLabels = ["This month", "1–6 mo", "6–12 mo", "1–2 years", "2+ years", "Never"]

    static let albums = CUValueFormat(unit: "albums", singular: "album")

    static var growthPoints: [CUChartPoint] {
        // 33 points spread evenly from 1 December 2025 to 11 November 2026.
        let start = DateComponents(calendar: .current, year: 2025, month: 12, day: 1).date!
        return growth.enumerated().map { i, v in
            let day = Calendar.current.date(byAdding: .day, value: Int((345.0 * Double(i) / Double(growth.count - 1)).rounded()), to: start)!
            return CUChartPoint(value: v, detail: CUChartMath.longDate(day, weekday: false))
        }
    }

    static var columns: [CUColumn] {
        added.indices.map { CUColumn(label: String(months[$0].prefix(1)), value: added[$0], detail: months[$0], comparison: last[$0]) }
    }

    static var shelfColumns: [CUColumn] { shelf.indices.map { CUColumn(label: shelfLabels[$0], value: shelf[$0], detail: shelfLabels[$0]) } }

    static var heat: [CUHeatCell] {
        // 18 weeks of made-up days, busier later in the week and later in the period.
        var rng = SystemRandomNumberGenerator()
        _ = rng
        let start = DateComponents(calendar: .current, year: 2026, month: 6, day: 15).date!
        return (0..<126).map { i in
            let date = Calendar.current.date(byAdding: .day, value: i, to: start)!
            let week = Double(i / 7) / 18, weekend = (i % 7) >= 4 ? 0.25 : 0
            let v = (sin(Double(i) * 12.9898) * 43758.5453).truncatingRemainder(dividingBy: 1)
            return CUHeatCell(date: date, count: Int(abs(v) * (0.25 + 0.5 * week + weekend) * 40))
        }
    }
}

/// The charts specimen sheet: anatomy, every type, every state.
struct CUChartSpecimenSheet: View {
    @State private var era: String? = "1990s"
    private let missing = CUChartPhase.unavailable(headline: "Needs ListenBrainz", message: "Listening charts read your history from ListenBrainz.", fixTitle: "Open Services")
    @State private var range = "1Y"

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: CU.Space.l) {
                Text("Chart anatomy · Cupertino").font(CU.title(20))
                CUPanel { anatomy }
                Text("Chart types and when to use each").font(CU.title(20))
                Grid(horizontalSpacing: CU.Space.m, verticalSpacing: CU.Space.m) {
                    GridRow { line; linePrevious; columns }
                    GridRow { paired; dumbbell; ranked }
                    GridRow { histogram; heatmap; tracker }
                }
                Text("States every chart must have").font(CU.title(20))
                Grid(horizontalSpacing: CU.Space.m, verticalSpacing: CU.Space.m) {
                    GridRow {
                        cell("Loading", "Skeleton in the plot's own footprint. No spinner, no layout shift.", phase: .loading, height: 160) { EmptyView() }
                        cell("Insufficient data", "Ghost dotted line plus one sentence that names the threshold.",
                             phase: .insufficient(headline: "Not enough history yet", threshold: "Needs albums added in 3 different months."), height: 160) { EmptyView() }
                        cell("Not available", "The source is missing or off. Say which, and offer the fix.", phase: missing, height: 160) { EmptyView() }
                        cell("Stale or failed", "Keep the last good chart, label its date, add a warning with words.",
                             phase: .stale(asOf: "9 November", message: CUChartPhase.staleMessage), height: 88) {
                            CUColumnChart(columns: Specimen.columns, highlight: 3, height: 88)
                        }
                    }
                }
            }
            .padding(CU.Space.xl)
        }
        .background(Color(red: 0.8, green: 0.8, blue: 0.84))
        .foregroundStyle(CU.text)
    }

    private var anatomy: some View {
        HStack(alignment: .top, spacing: CU.Space.xl) {
            CUPanel {
                CUChartFrame("Collection over time", subtitle: "Albums in your library · 1 December 2025 to today", plotHeight: 232,
                             accessory: { CUSegmented(["3M", "1Y", "5Y", "All"].map { (value: $0, label: $0) }, selection: $range) }) {
                    CULineChart(points: Specimen.growthPoints, axisLabels: ["Dec", "Feb", "Apr", "Jun", "Aug", "Oct", "Nov"],
                                annotations: [CUChartAnnotation(index: 12, text: "Biggest month: March, 31 added")], format: Specimen.albums,
                                height: 232, title: "Collection over time", initialSelection: 19)
                }
            }
            .frame(width: 672)
            VStack(alignment: .leading, spacing: CU.Space.s) {
                ForEach([("Title", "17/24 Semibold, sentence case. Says what is measured."), ("Subtitle", "12/18 Regular, secondary. Unit, source and the exact period."),
                         ("Value labels", "11 pt tabular, secondary, on the trailing side. No axis line, no tick marks."),
                         ("Gridlines", "Horizontal only, 1 pt #E5E5EA, at most 4. The baseline is #C7C7CC."),
                         ("Selection", "1 pt rule plus a 5 pt accent dot with a 2 pt white ring. Click, drag or ← → moves it.")], id: \.0) { k, v in
                    HStack(alignment: .top, spacing: CU.Space.m) {
                        Text(k).cuRole(CU.Font.headline).frame(width: 96, alignment: .leading)
                        Text(v).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
                    }
                }
            }
        }
    }

    private func cell<P: View>(_ title: String, _ rule: String, phase: CUChartPhase = .ready, height: CGFloat = 200, ghost: CUGhostShape = .line, @ViewBuilder plot: () -> P) -> some View {
        CUPanel {
            Text(title).cuRole(CU.Font.title3)
            Text(rule).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).frame(minHeight: 36, alignment: .topLeading)
            CUChartFrame("", phase: phase, plotHeight: height, ghost: ghost, onFix: {}, plot: plot)
        }
        .gridColumnAlignment(.leading)
    }

    private var line: some View {
        cell("Line: a total over time", "One accent line. The value axis may start above zero and the subtitle says so.") {
            CULineChart(points: Specimen.growthPoints, axisLabels: ["Dec", "Mar", "Jun", "Sep", "Nov"], format: Specimen.albums, initialSelection: 19)
        }
    }

    private var linePrevious: some View {
        let now: [Double] = [181, 164, 190, 172, 201, 188, 214], before: [Double] = [150, 171, 160, 182, 175, 169, 181]
        return cell("Line with the period before", "The comparison is 1.5 pt dashed #8E8E93, never a second colour.") {
            VStack(alignment: .leading, spacing: CU.Space.s) {
                CULineChart(points: now.map { CUChartPoint(value: $0) }, previous: before, axisLabels: ["23 Sep", "7 Oct", "21 Oct", "4 Nov"], startsAtZero: true)
                HStack(spacing: CU.Space.m) {
                    HStack(spacing: 4) { Rectangle().fill(CU.chart1).frame(width: 16, height: 2); Text("Last 7 weeks") }
                    HStack(spacing: 4) { Rectangle().fill(CU.chart2).frame(width: 16, height: 1.5); Text("The 7 weeks before") }
                }
                .font(.system(size: 11)).foregroundStyle(CU.textSecondary)
            }
        }
    }

    private var columns: some View {
        cell("Columns: counts per period", "Always from zero. The selected period is accent, the rest #C7C7CC. A 2 pt ink tick marks last year.") {
            VStack(alignment: .leading, spacing: CU.Space.s) {
                CUColumnChart(columns: Specimen.columns, highlight: 3, format: CUValueFormat(unit: "albums", singular: "album"))
                Text("Albums added per month · tick: same month a year earlier").cuRole(CU.Font.caption).foregroundStyle(CU.textSecondary)
            }
        }
    }

    private var paired: some View {
        cell("Paired bars: two shares", "Context bar neutral above, highlighted bar accent below, values right-aligned in tabular figures.") {
            CUPairedBars(rows: Specimen.eras.map { CUPairedRow(label: $0.0, context: $0.1, highlight: $0.2) }, selection: $era,
                         legend: (context: "Share of albums", highlight: "Share of listens"), rowHeight: 28, title: "Own and play by decade")
        }
    }

    private var dumbbell: some View {
        cell("Dumbbell: before and after", "Hollow dot is the baseline, filled dot is now. Accent when the share rose, ink when it fell; never red or green.") {
            CUDumbbell(rows: [CUDumbbellRow(label: "Ambient", before: 9, now: 17), CUDumbbellRow(label: "Post-punk", before: 14, now: 8), CUDumbbellRow(label: "Dream pop", before: 18, now: 19)], title: "Genre shifts")
        }
    }

    private var ranked: some View {
        cell("Ranked bars: parts of a whole", "More than 3 parts are sorted bars, never a pie. One accent bar, 10 pt tall on a ghost track.") {
            CURankedBars(rows: Specimen.genres.map { CURankedRow(label: $0.0, value: $0.1) }, title: "Top genres")
        }
    }

    private var histogram: some View {
        cell("Histogram: a distribution", "Ordered bins from zero with value labels. The actionable bin is accent.") {
            CUColumnChart(columns: Specimen.shelfColumns, highlight: 5, showsValueLabels: true, height: 184, title: "Shelf life")
        }
    }

    private var heatmap: some View {
        cell("Heatmap: days", "Five steps from #ECECF0 to accent, 12 pt cells, 4 pt gaps, a Fewer to More key. Never hover-only.") {
            VStack(alignment: .leading, spacing: CU.Space.s) {
                CUHeatmap(cells: Specimen.heat, title: "Songs by day")
                CUHeatmapKey()
            }
        }
    }

    private var tracker: some View {
        cell("Stage tracker: a pipeline", "Four 4 pt segments. Done is ink, current is accent with its percentage in words, failed is danger with words.") {
            VStack(alignment: .leading, spacing: CU.Space.m) {
                CUStageTracker(step: 1, progress: 0.64, width: 320)
                CUStageTracker(step: 3, width: 320)
                CUStageTracker(step: 1, progress: 0.41, failed: true, failureReason: "The source went offline.", width: 320)
                CUStageTracker(step: 4, showsNames: true, width: 320)
            }
        }
    }
}
