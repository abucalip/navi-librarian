import Charts
import SwiftUI

// Cupertino charts (redesign M4). Spec: section 4.4 of `docs/redesign.md` and `charts--specimens`.
// Geometry follows the chart functions in `docs/design/redesign/_src/mac_shell.py`.
//
// Layout of this file:
//   1. Pure maths and state choice (no SwiftUI; unit-tested in `CupertinoChartsTests`).
//   2. Shared pieces: tooltip, draw-in motion, the frame that owns the title and the five states, the accessibility descriptor.
//   3. The seven charts: line, columns, paired bars, dumbbell, ranked bars, heatmap, stage tracker.
//
// Swift Charts draws the line, column and dumbbell charts. Paired bars, ranked bars, the heatmap and the tracker are plain
// SwiftUI because their geometry (fixed 6 or 10 pt bars on a track, 12 pt cells, 4 pt segments) is not a data-scaled plot.

// MARK: - 1. Pure maths

/// How a number is written on an axis and in a tooltip: thousands separators, an optional unit, or a whole percentage.
struct CUValueFormat: Equatable, Sendable {
    var unit = ""
    /// The unit for exactly one ("1 album"). Falls back to `unit`.
    var singular: String?
    var percent = false

    static func number(_ value: Double) -> String {
        value.formatted(.number.locale(Locale(identifier: "en_US")).precision(.fractionLength(0)).grouping(.automatic))
    }

    /// Axis label: "1,300" or "20%".
    func axis(_ value: Double) -> String { Self.number(value) + (percent ? "%" : "") }

    /// Tooltip and spoken value: "1,171 albums", "1 album" or "19%".
    func text(_ value: Double) -> String {
        if percent { return axis(value) }
        let n = Self.number(value)
        guard !unit.isEmpty else { return n }
        return "\(n) \(abs(value) == 1 ? (singular ?? unit) : unit)"
    }
}

struct CUXY: Equatable, Sendable {
    var x: Double
    var y: Double
}

struct CUHeatCell: Equatable, Identifiable, Sendable {
    let date: Date
    let count: Int
    var id: Date { date }
}

struct CUHeatMonthLabel: Equatable, Sendable {
    let column: Int
    let text: String
}

struct CURankedRow: Identifiable, Equatable, Sendable {
    let label: String
    let value: Double
    var id: String { label }
}

struct CUPairedRow: Identifiable, Equatable, Sendable {
    let label: String
    /// The neutral bar, drawn above.
    let context: Double
    /// The accent bar, drawn below.
    let highlight: Double
    var id: String { label }
}

struct CUDumbbellRow: Identifiable, Equatable, Sendable {
    let label: String
    let before: Double
    let now: Double
    var id: String { label }
}

enum CUShift: Equatable, Sendable { case rose, fell, unchanged }

enum CUStageSegment: Equatable, Sendable {
    case done
    /// The segment in progress, with its fraction when the server reports one.
    case current(progress: Double?)
    case failed
    case pending
}

enum CUChartMath {
    // MARK: Value axis

    /// The smallest of 1, 2, 5, 10 times a power of ten that is at least `raw`.
    static func niceStep(_ raw: Double) -> Double {
        guard raw > 0, raw.isFinite else { return 1 }
        let base = pow(10, floor(log10(raw)))
        for m in [1.0, 2.0, 5.0, 10.0] where m * base >= raw * (1 - 1e-9) { return m * base }
        return 10 * base
    }

    /// Value-axis ticks. The first is the zero baseline (or the lowest tick of a line that starts above zero). At most `maxTicks`
    /// including the baseline, which is the "at most 4 gridlines" of section 4.4. Always covers `low...high`.
    static func ticks(low: Double, high: Double, startsAtZero: Bool, maxTicks: Int = 5) -> [Double] {
        let count = max(maxTicks, 2)
        var lo = startsAtZero ? min(0, low) : low
        var hi = max(high, lo)
        if hi == lo { hi = lo + max(abs(lo), 1) }
        var step = niceStep((hi - lo) / Double(count - 1))
        while true {
            let start = (lo / step).rounded(.down) * step
            let end = (hi / step).rounded(.up) * step
            let n = Int(((end - start) / step).rounded()) + 1
            if n <= count { return (0..<n).map { start + Double($0) * step } }
            step = niceStep(step * 1.5)
            lo = min(lo, hi)
        }
    }

    /// Linear map of `value` from a range onto the span from `start` to `end`; `end` may be smaller (a screen y axis runs
    /// downward). A zero-width source maps to `start`.
    static func scale(_ value: Double, from: ClosedRange<Double>, toStart start: Double, toEnd end: Double) -> Double {
        let span = from.upperBound - from.lowerBound
        guard span != 0 else { return start }
        return start + (value - from.lowerBound) / span * (end - start)
    }

    /// 0 to 1: how far a value reaches along a bar whose full length is `top`.
    static func fraction(_ value: Double, of top: Double) -> Double {
        guard top > 0 else { return 0 }
        return min(max(value / top, 0), 1)
    }

    // MARK: Time axis

    /// Which points carry a time label: `labels` evenly spread, the first and last always included (5 to 7 in a chart).
    static func labelIndices(count: Int, labels: Int) -> [Int] {
        guard count > 0 else { return [] }
        let n = min(max(labels, 1), count)
        guard n > 1 else { return [0] }
        return (0..<n).map { Int((Double($0) * Double(count - 1) / Double(n - 1)).rounded()) }
    }

    // MARK: Selection

    /// The point nearest to an x value, clamped to the data. `nil` stays `nil`.
    static func nearest(_ x: Double?, count: Int) -> Int? {
        guard let x, count > 0, x.isFinite else { return nil }
        return min(max(Int(x.rounded()), 0), count - 1)
    }

    /// Arrow-key movement. The first press selects the newest point; after that it steps and stops at either end.
    static func move(_ current: Int?, by delta: Int, count: Int) -> Int? {
        guard count > 0 else { return nil }
        guard let current else { return count - 1 }
        return min(max(current + delta, 0), count - 1)
    }

    // MARK: Draw-in

    /// A line drawn left to right. At `progress` 1 it is every point; below that it is the points reached plus one interpolated end.
    static func revealed(_ values: [Double], progress: Double) -> [CUXY] {
        let all = values.enumerated().map { CUXY(x: Double($0.offset), y: $0.element) }
        guard progress < 1, values.count > 1 else { return all }
        let t = max(0, progress) * Double(values.count - 1)
        let whole = Int(t.rounded(.down))
        var out = Array(all[0...whole])
        let frac = t - Double(whole)
        if frac > 0 {
            out.append(CUXY(x: t, y: values[whole] + (values[whole + 1] - values[whole]) * frac))
        }
        return out
    }

    /// A column growing from the baseline.
    static func grown(_ value: Double, progress: Double) -> Double { value * min(max(progress, 0), 1) }

    // MARK: Ranked and compared

    /// Largest first. Equal values keep their given order.
    static func ranked(_ rows: [CURankedRow]) -> [CURankedRow] {
        rows.enumerated().sorted { a, b in
            a.element.value != b.element.value ? a.element.value > b.element.value : a.offset < b.offset
        }.map(\.element)
    }

    static func shift(before: Double, now: Double) -> CUShift {
        let a = before.rounded(), b = now.rounded()
        return b > a ? .rose : (b < a ? .fell : .unchanged)
    }

    /// "9% → 17% ▲". Whole percentages, an arrow for the direction.
    static func dumbbellSummary(_ row: CUDumbbellRow) -> String {
        let f = CUValueFormat(percent: true)
        let arrow = switch shift(before: row.before, now: row.now) { case .rose: " ▲"; case .fell: " ▼"; case .unchanged: "" }
        return "\(f.axis(row.before)) → \(f.axis(row.now))\(arrow)"
    }

    /// The spoken form: "Ambient rose from 9% to 17%".
    static func dumbbellWords(_ row: CUDumbbellRow) -> String {
        let f = CUValueFormat(percent: true)
        switch shift(before: row.before, now: row.now) {
        case .rose: return "\(row.label) rose from \(f.axis(row.before)) to \(f.axis(row.now))"
        case .fell: return "\(row.label) fell from \(f.axis(row.before)) to \(f.axis(row.now))"
        case .unchanged: return "\(row.label) stayed at \(f.axis(row.now))"
        }
    }

    // MARK: Heatmap

    /// 0 (none) to 4 (the busiest quarter), so the five steps spread whatever the range of counts.
    static func heatLevel(count: Int, max top: Int) -> Int {
        guard count > 0, top > 0 else { return 0 }
        return min(4, max(1, Int((Double(count) / Double(top) * 4).rounded(.up))))
    }

    /// Row of the first day: Monday is 0, Sunday is 6, whatever the calendar's own first weekday.
    static func heatLead(_ first: Date, calendar: Calendar = .current) -> Int {
        (calendar.component(.weekday, from: first) + 5) % 7
    }

    /// Columns of seven days, Monday at the top. The first column is padded before the first day and the last after the final day.
    static func heatGrid(_ cells: [CUHeatCell], calendar: Calendar = .current) -> [[CUHeatCell?]] {
        guard let first = cells.first else { return [] }
        let padded: [CUHeatCell?] = Array(repeating: nil, count: heatLead(first.date, calendar: calendar)) + cells.map { Optional($0) }
        return stride(from: 0, to: padded.count, by: 7).map { start in
            var column = Array(padded[start..<min(start + 7, padded.count)])
            while column.count < 7 { column.append(nil) }
            return column
        }
    }

    /// Column and row of the day at `index`.
    static func heatPosition(index: Int, lead: Int) -> (column: Int, row: Int) { ((index + lead) / 7, (index + lead) % 7) }

    /// The day at a column and row, or `nil` for a padded or out-of-range cell.
    static func heatIndex(column: Int, row: Int, lead: Int, count: Int) -> Int? {
        guard column >= 0, (0..<7).contains(row) else { return nil }
        let index = column * 7 + row - lead
        return (0..<count).contains(index) ? index : nil
    }

    /// Month names under the grid, at the column that holds the first of each month. The first column is labelled too unless
    /// a month begins within its first two columns, so two labels never collide.
    static func monthLabels(_ grid: [[CUHeatCell?]], calendar: Calendar = .current) -> [CUHeatMonthLabel] {
        var labels: [CUHeatMonthLabel] = []
        for (c, column) in grid.enumerated() {
            guard let day = column.compactMap({ $0 }).first(where: { calendar.component(.day, from: $0.date) == 1 }) else { continue }
            labels.append(CUHeatMonthLabel(column: c, text: calendar.shortMonthSymbols[calendar.component(.month, from: day.date) - 1]))
        }
        if let firstColumn = grid.first?.compactMap({ $0 }).first, (labels.first?.column ?? Int.max) >= 2 {
            labels.insert(CUHeatMonthLabel(column: 0, text: calendar.shortMonthSymbols[calendar.component(.month, from: firstColumn.date) - 1]), at: 0)
        }
        return labels
    }

    // MARK: Dates

    /// "Saturday 17 October 2026": day before month, as the shared rules of section 3 write dates.
    static func longDate(_ date: Date, weekday: Bool = true) -> String {
        let style = Date.FormatStyle(locale: Locale(identifier: "en_GB"))
        return weekday ? date.formatted(style.weekday(.wide).day().month(.wide).year()) : date.formatted(style.day().month(.wide).year())
    }

    // MARK: Stage tracker

    static let stageNames = ["Found", "Downloading", "Importing", "In library"]

    /// Four segments. `step` is the index of the segment in progress; 4 means every segment is done.
    static func stageSegments(step: Int, progress: Double?, failed: Bool) -> [CUStageSegment] {
        let s = min(max(step, 0), stageNames.count)
        return (0..<stageNames.count).map { i in
            if i < s { return .done }
            if i == s { return failed ? .failed : .current(progress: progress.map { min(max($0, 0), 1) }) }
            return .pending
        }
    }

    /// The tracker in words: "Downloading, 64%", "In library", "Stopped at Downloading: source went offline".
    static func stageWords(step: Int, progress: Double?, failed: Bool, reason: String? = nil) -> String {
        let s = min(max(step, 0), stageNames.count)
        if s >= stageNames.count { return stageNames[stageNames.count - 1] }
        if failed { return "Stopped at \(stageNames[s])" + (reason.map { ": \($0)" } ?? "") }
        guard let progress else { return stageNames[s] }
        return "\(stageNames[s]), \(Int((min(max(progress, 0), 1) * 100).rounded()))%"
    }
}

// MARK: Chart state

/// What a chart shows in its plot area. The five states of section 4.4, each with its own sentence.
enum CUChartPhase: Equatable, Sendable {
    case ready
    /// A skeleton in the plot's footprint. No spinner.
    case loading
    /// A dotted ghost and one sentence naming the threshold.
    case insufficient(headline: String, threshold: String)
    /// The source is missing or off: say which, and offer the fix.
    case unavailable(headline: String, message: String, fixTitle: String?)
    /// The last good chart at 50%, a warning notice with its date.
    case stale(asOf: String, message: String)

    struct Unavailable: Equatable, Sendable {
        var headline: String
        var message: String
        var fixTitle: String?
    }

    struct Threshold: Equatable, Sendable {
        var headline: String
        var sentence: String
    }

    static let staleMessage = "The refresh failed; this is the last good data."

    /// The state for a set of inputs. Order: a missing source wins; with nothing to draw a load is a skeleton, a failure is
    /// "not available" and otherwise there is not enough data; with some data a failed refresh keeps the chart and says so.
    /// A refresh that is still running keeps showing the data it has.
    static func choose(isLoading: Bool, count: Int, minimum: Int, threshold: Threshold, unavailable: Unavailable? = nil, failedAsOf: String? = nil) -> CUChartPhase {
        if let unavailable { return .unavailable(headline: unavailable.headline, message: unavailable.message, fixTitle: unavailable.fixTitle) }
        if count == 0, failedAsOf != nil {
            return .unavailable(headline: "Couldn't load this chart", message: "The last refresh failed and nothing earlier is saved.", fixTitle: nil)
        }
        if count < max(minimum, 1) { return isLoading ? .loading : .insufficient(headline: threshold.headline, threshold: threshold.sentence) }
        if let failedAsOf { return .stale(asOf: failedAsOf, message: staleMessage) }
        return .ready
    }
}

// MARK: Accessibility description

/// What a chart says to VoiceOver: a summary sentence and every value by name.
struct CUChartDescription: Equatable {
    struct Point: Equatable {
        let label: String
        let value: Double
    }

    var kind: String
    var title: String
    var xTitle: String
    var yTitle: String
    var points: [Point]
    var format = CUValueFormat()
    /// A line or a heatmap reads as continuous; bars and rows as separate values.
    var continuous = false
    /// Time order: the summary also names the latest value.
    var ordered = false
    var summaryOverride: String?

    var summary: String {
        if let summaryOverride { return summaryOverride }
        guard let low = points.min(by: { $0.value < $1.value }), let high = points.max(by: { $0.value < $1.value }), let last = points.last else {
            return "\(kind), \(title). No values."
        }
        var s = "\(kind), \(title). \(points.count) values. Lowest \(format.text(low.value)), \(low.label). Highest \(format.text(high.value)), \(high.label)."
        if ordered { s += " Latest \(format.text(last.value)), \(last.label)." }
        return s
    }
}

struct CUChartDescriptor: AXChartDescriptorRepresentable {
    let description: CUChartDescription

    func makeChartDescriptor() -> AXChartDescriptor {
        let d = description
        let values = d.points.map(\.value)
        let x = AXCategoricalDataAxisDescriptor(title: d.xTitle, categoryOrder: d.points.map(\.label))
        let y = AXNumericDataAxisDescriptor(title: d.yTitle, range: (values.min() ?? 0)...(values.max() ?? 0), gridlinePositions: []) { d.format.text($0) }
        let series = AXDataSeriesDescriptor(name: d.title, isContinuous: d.continuous, dataPoints: d.points.map { AXDataPoint(x: $0.label, y: $0.value) })
        return AXChartDescriptor(title: d.title, summary: d.summary, xAxis: x, yAxis: y, additionalAxes: [], series: [series])
    }

    func updateChartDescriptor(_ descriptor: AXChartDescriptor) {}
}

extension View {
    /// The summary sentence as the label and the values as a chart descriptor, so a chart is never a silent picture.
    func cuChartAccessibility(_ description: CUChartDescription) -> some View {
        accessibilityLabel(description.summary).accessibilityChartDescriptor(CUChartDescriptor(description: description))
    }
}

// MARK: - 2. Shared pieces

/// White, radius 8, popover shadow, padding 8. The value in 13 Semibold tabular, then the date in 11 secondary.
struct CUTooltip: View {
    let value: String
    var detail = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(value).font(.system(size: 13, weight: .semibold)).monospacedDigit().foregroundStyle(CU.text)
            if !detail.isEmpty { Text(detail).font(.system(size: 11)).foregroundStyle(CU.textSecondary) }
        }
        .padding(CU.Space.s)
        .background(CU.content, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .shadow(color: .black.opacity(0.12), radius: 0.5)
        .shadow(color: .black.opacity(0.18), radius: 12, y: 4)
        .fixedSize()
        .accessibilityElement(children: .combine)
    }
}

private extension View {
    /// 11 pt, secondary, tabular: every axis label.
    func cuAxisLabel(bold: Bool = false) -> some View {
        font(.system(size: 11, weight: bold ? .semibold : .regular)).monospacedDigit().foregroundStyle(bold ? CU.text : CU.textSecondary)
    }
}

/// A value animated by SwiftUI frame by frame, so the chart redraws as it changes.
struct CUReveal<Content: View>: View, @preconcurrency Animatable {
    var progress: Double
    let content: (Double) -> Content

    var animatableData: Double {
        get { progress }
        set { progress = newValue }
    }

    var body: some View { content(progress) }
}

/// Marks draw in over 300 ms ease-out. None when Reduce Motion is on, or in a screenshot render.
struct CUDrawIn<Content: View>: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var target: Double
    let content: (Double) -> Content

    init(@ViewBuilder content: @escaping (Double) -> Content) {
        self.content = content
        _target = State(initialValue: RenderMode.offscreenScreenshot ? 1 : 0)
    }

    var body: some View {
        CUReveal(progress: target, content: content)
            .onAppear {
                guard target < 1 else { return }
                if reduceMotion { target = 1 } else { withAnimation(.easeOut(duration: 0.3)) { target = 1 } }
            }
    }
}

/// What the dotted ghost of an insufficient chart looks like: the shape of the real one.
enum CUGhostShape: Equatable, Sendable { case line, columns, rows, cells }

private struct CUGhost: View {
    let shape: CUGhostShape

    var body: some View {
        switch shape {
        case .line:
            GeometryReader { g in
                let fractions: [Double] = [0.08, 0.08, 0.30, 0.30, 0.52, 0.52, 0.84]
                Path { p in
                    for (i, f) in fractions.enumerated() {
                        let pt = CGPoint(x: g.size.width * Double(i) / Double(fractions.count - 1), y: g.size.height * (1 - f))
                        i == 0 ? p.move(to: pt) : p.addLine(to: pt)
                    }
                }
                .stroke(CU.chart3, style: StrokeStyle(lineWidth: 2, lineCap: .round, dash: [0.1, 6]))
                Rectangle().fill(CU.chartBase).frame(height: 1).frame(maxHeight: .infinity, alignment: .bottom)
            }
        case .columns:
            GeometryReader { g in
                let heights: [Double] = [0.3, 0.45, 0.6, 0.4, 0.7, 0.5, 0.35, 0.55, 0.65, 0.45, 0.3, 0.5]
                HStack(alignment: .bottom, spacing: g.size.width * 0.38 / 12) {
                    ForEach(Array(heights.enumerated()), id: \.offset) { _, h in
                        UnevenRoundedRectangle(topLeadingRadius: 3, topTrailingRadius: 3).fill(CU.chartGhost).frame(height: g.size.height * h)
                    }
                }
                .frame(maxHeight: .infinity, alignment: .bottom)
                Rectangle().fill(CU.chartBase).frame(height: 1).frame(maxHeight: .infinity, alignment: .bottom)
            }
        case .rows:
            VStack(spacing: 18) {
                ForEach(0..<5, id: \.self) { _ in Capsule().fill(CU.chartGhost).frame(height: 10) }
            }
            .frame(maxHeight: .infinity)
        case .cells:
            Grid(horizontalSpacing: 4, verticalSpacing: 4) {
                ForEach(0..<7, id: \.self) { _ in
                    GridRow { ForEach(0..<18, id: \.self) { _ in RoundedRectangle(cornerRadius: 3, style: .continuous).fill(CU.chartGhost).frame(width: 12, height: 12) } }
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
    }
}

/// Title, subtitle, an optional control at the trailing edge, and the plot or the state that stands in for it.
/// Every chart sits in one, so each of them has the same five states.
struct CUChartFrame<Plot: View, Accessory: View>: View {
    let title: String
    var subtitle = ""
    var phase: CUChartPhase = .ready
    /// The plot's footprint: a skeleton and the states take the same height, so the page does not shift.
    var plotHeight: CGFloat = 200
    var ghost: CUGhostShape = .line
    var onFix: (() -> Void)?
    let accessory: Accessory
    let plot: Plot
    @Environment(\.cuInPanel) private var inPanel

    init(_ title: String, subtitle: String = "", phase: CUChartPhase = .ready, plotHeight: CGFloat = 200, ghost: CUGhostShape = .line,
         onFix: (() -> Void)? = nil, @ViewBuilder accessory: () -> Accessory, @ViewBuilder plot: () -> Plot) {
        self.title = title
        self.subtitle = subtitle
        self.phase = phase
        self.plotHeight = plotHeight
        self.ghost = ghost
        self.onFix = onFix
        self.accessory = accessory()
        self.plot = plot()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: CU.Space.m) {
            if !title.isEmpty {
                HStack(alignment: .top, spacing: CU.Space.m) {
                    VStack(alignment: .leading, spacing: CU.Space.xs) {
                        Text(title).cuRole(CU.Font.title3).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
                        if !subtitle.isEmpty { Text(subtitle).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary) }
                    }
                    Spacer(minLength: 0)
                    accessory
                }
            }
            state
        }
    }

    @ViewBuilder private var state: some View {
        switch phase {
        case .ready:
            plot
        case .loading:
            RoundedRectangle(cornerRadius: 8, style: .continuous).fill(inPanel ? CU.bgFillOnPanel : CU.bgFill)
                .frame(height: plotHeight)
                .accessibilityElement().accessibilityLabel("Loading \(title)")
        case .insufficient(let headline, let threshold):
            ZStack {
                CUGhost(shape: ghost).accessibilityHidden(true)
                VStack(spacing: 0) {
                    Text(headline).cuRole(CU.Font.headline).foregroundStyle(CU.text)
                    Text(threshold).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).multilineTextAlignment(.center)
                }
            }
            .frame(height: plotHeight)
            .accessibilityElement(children: .combine)
        case .unavailable(let headline, let message, let fixTitle):
            VStack(alignment: .leading, spacing: CU.Space.s) {
                Text(headline).cuRole(CU.Font.headline).foregroundStyle(CU.text)
                Text(message).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
                if let fixTitle, let onFix {
                    Button(fixTitle, action: onFix).buttonStyle(CapsuleButtonStyle(small: true))
                }
            }
            .frame(maxWidth: .infinity, minHeight: plotHeight, alignment: .leading)
            .accessibilityElement(children: .contain)
        case .stale(let asOf, let message):
            VStack(alignment: .leading, spacing: CU.Space.s) {
                CUNotice(kind: .warning, lead: "As of \(asOf).", message: message)
                plot.opacity(0.5)
            }
        }
    }
}

extension CUChartFrame where Accessory == EmptyView {
    init(_ title: String, subtitle: String = "", phase: CUChartPhase = .ready, plotHeight: CGFloat = 200, ghost: CUGhostShape = .line,
         onFix: (() -> Void)? = nil, @ViewBuilder plot: () -> Plot) {
        self.init(title, subtitle: subtitle, phase: phase, plotHeight: plotHeight, ghost: ghost, onFix: onFix, accessory: { EmptyView() }, plot: plot)
    }
}

// MARK: - 3. Charts

/// A value on a line or column: the number, and the words for its tooltip's second line (a date, a month).
struct CUChartPoint: Equatable, Sendable {
    var value: Double
    var detail = ""
}

struct CUChartAnnotation: Equatable, Sendable {
    let index: Int
    let text: String
}

private enum CUDot {
    /// The last point of a line: a 4 pt dot with a white ring.
    static var last: some View {
        ZStack { Circle().fill(.white).frame(width: 10, height: 10); Circle().fill(CU.chart1).frame(width: 6, height: 6) }
    }

    /// The selected point: a 5 pt accent dot with a 2 pt white ring.
    static var selected: some View {
        ZStack { Circle().fill(.white).frame(width: 12, height: 12); Circle().fill(CU.chart1).frame(width: 8, height: 8) }
    }
}

// MARK: Line

/// A total over time: one 2 pt accent line, an 8% area under a single series, a dot on the last point. A second dashed series
/// (`previous`) is the period before. Click, drag or ← → selects a point; a tooltip and a rule follow it.
struct CULineChart: View {
    let points: [CUChartPoint]
    /// The period before, drawn dashed in `chart.2`. It may have a different count; it is stretched over the same width.
    var previous: [Double] = []
    /// 5 to 7 labels spread evenly; the first is leading-aligned and the last trailing-aligned.
    var axisLabels: [String] = []
    /// At most 2.
    var annotations: [CUChartAnnotation] = []
    var format = CUValueFormat()
    /// A line may start above zero; the subtitle then names the range.
    var startsAtZero = false
    var height: CGFloat = 200
    var title = "Line chart"
    var xTitle = "Date"
    var yTitle = "Value"
    /// A point selected when the chart appears (a screenshot, or a page that restores a choice).
    var initialSelection: Int?
    @State private var selectedX: Double?

    private var ticks: [Double] {
        let all = points.map(\.value) + previous
        return CUChartMath.ticks(low: all.min() ?? 0, high: all.max() ?? 1, startsAtZero: startsAtZero)
    }

    private var selectedIndex: Int? { CUChartMath.nearest(selectedX, count: points.count) }

    var body: some View {
        CUDrawIn { progress in plot(progress) }
            .frame(height: height)
            .focusable()
            .onKeyPress(.leftArrow) { select(-1) }
            .onKeyPress(.rightArrow) { select(1) }
            .onKeyPress(.escape) { selectedX = nil; return .handled }
            .onAppear { if selectedX == nil, let initialSelection { selectedX = Double(initialSelection) } }
            .cuChartAccessibility(description)
    }

    private var description: CUChartDescription {
        CUChartDescription(kind: "Line chart", title: title, xTitle: xTitle, yTitle: yTitle,
                           points: points.map { .init(label: $0.detail.isEmpty ? "Point" : $0.detail, value: $0.value) }, format: format, continuous: true, ordered: true)
    }

    private func select(_ delta: Int) -> KeyPress.Result {
        guard let i = CUChartMath.move(selectedIndex, by: delta, count: points.count) else { return .ignored }
        selectedX = Double(i)
        return .handled
    }

    private func plot(_ progress: Double) -> some View {
        let ticks = ticks
        let shown = CUChartMath.revealed(points.map(\.value), progress: progress)
        let lastX = Double(max(points.count - 1, 1))
        let labelIdx = CUChartMath.labelIndices(count: points.count, labels: axisLabels.count)
        let selected = selectedIndex
        return Chart {
            if previous.count > 1 {
                ForEach(Array(previous.enumerated()), id: \.offset) { i, v in
                    LineMark(x: .value("Step", Double(i) * lastX / Double(previous.count - 1)), y: .value("Before", v), series: .value("Series", "Before"))
                        .foregroundStyle(CU.chart2)
                        .lineStyle(StrokeStyle(lineWidth: 1.5, dash: [4, 4]))
                }
            }
            if previous.isEmpty {
                ForEach(shown, id: \.x) { p in
                    AreaMark(x: .value("Step", p.x), yStart: .value("Base", ticks[0]), yEnd: .value("Value", p.y), series: .value("Series", "Area"))
                        .foregroundStyle(CU.chart1.opacity(0.08))
                }
            }
            ForEach(shown, id: \.x) { p in
                LineMark(x: .value("Step", p.x), y: .value("Value", p.y), series: .value("Series", "Now"))
                    .foregroundStyle(CU.chart1)
                    .lineStyle(StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round))
            }
            ForEach(Array(annotations.prefix(2).enumerated()), id: \.offset) { _, a in
                if points.indices.contains(a.index) {
                    PointMark(x: .value("Step", Double(a.index)), y: .value("Value", points[a.index].value))
                        .symbol { Circle().fill(.white).overlay(Circle().stroke(CU.textSecondary, lineWidth: 1.5)).frame(width: 6, height: 6) }
                        .annotation(position: .top, spacing: 2, overflowResolution: .init(x: .fit(to: .chart), y: .disabled)) {
                            VStack(spacing: 0) {
                                Text(a.text).font(.system(size: 11)).foregroundStyle(CU.textSecondary).fixedSize()
                                Rectangle().fill(CU.textSecondary).frame(width: 1, height: 12)
                            }
                        }
                }
            }
            if progress >= 1, selected == nil, let last = points.last {
                PointMark(x: .value("Step", Double(points.count - 1)), y: .value("Value", last.value)).symbol { CUDot.last }
            }
            if let selected {
                RuleMark(x: .value("Selected", Double(selected)))
                    .foregroundStyle(CU.textSecondary)
                    .lineStyle(StrokeStyle(lineWidth: 1))
                PointMark(x: .value("Step", Double(selected)), y: .value("Value", points[selected].value))
                    .symbol { CUDot.selected }
                    .annotation(position: .trailing, spacing: 8, overflowResolution: .init(x: .automatic, y: .fit(to: .chart))) {
                        CUTooltip(value: format.text(points[selected].value), detail: points[selected].detail)
                    }
            }
        }
        .chartYScale(domain: (ticks.first ?? 0)...(ticks.last ?? 1))
        .chartXScale(domain: 0...lastX)
        .chartXSelection(value: $selectedX)
        .chartYAxis {
            AxisMarks(position: .trailing, values: ticks) { value in
                let v = value.as(Double.self) ?? 0
                AxisGridLine(stroke: StrokeStyle(lineWidth: 1)).foregroundStyle(value.index == 0 ? CU.chartBase : CU.chartGrid)
                AxisValueLabel { Text(format.axis(v)).cuAxisLabel() }
            }
        }
        .chartXAxis {
            AxisMarks(values: labelIdx.map(Double.init)) { value in
                AxisValueLabel(anchor: value.index == 0 ? .topLeading : (value.index == labelIdx.count - 1 ? .topTrailing : .top)) {
                    if axisLabels.indices.contains(value.index) { Text(axisLabels[value.index]).cuAxisLabel() }
                }
            }
        }
    }
}

// MARK: Columns

struct CUColumn: Equatable, Identifiable, Sendable {
    /// The short label under the column ("M").
    let label: String
    let value: Double
    /// The tooltip's second line and the spoken name ("March 2026").
    var detail = ""
    /// The same period a year earlier, drawn as a 2 pt ink tick across the column.
    var comparison: Double?
    var id: String { detail.isEmpty ? label : detail }
}

/// Counts per period, always from zero. One accent column (the selected one, else `highlight`), the rest `chart.3`.
/// With `showsValueLabels` it is a histogram: the value above each bar, a baseline and no value axis.
struct CUColumnChart: View {
    let columns: [CUColumn]
    var highlight: Int?
    var showsValueLabels = false
    var format = CUValueFormat()
    var height: CGFloat = 200
    var title = "Column chart"
    var xTitle = "Period"
    var yTitle = "Value"
    var initialSelection: Int?
    @State private var selectedID: String?

    private var ids: [String] { columns.indices.map(String.init) }
    private var selectedIndex: Int? { selectedID.flatMap(Int.init).flatMap { columns.indices.contains($0) ? $0 : nil } }
    private var top: Double {
        let all: [Double] = columns.flatMap { (c: CUColumn) -> [Double] in [c.value, c.comparison ?? 0] }
        let peak = all.max() ?? 1
        if showsValueLabels { return peak * 1.15 }
        return CUChartMath.ticks(low: 0, high: peak, startsAtZero: true).last ?? 1
    }

    var body: some View {
        CUDrawIn { progress in plot(progress) }
            .frame(height: height)
            .focusable()
            .onKeyPress(.leftArrow) { select(-1) }
            .onKeyPress(.rightArrow) { select(1) }
            .onKeyPress(.escape) { selectedID = nil; return .handled }
            .onAppear { if selectedID == nil, let initialSelection { selectedID = String(initialSelection) } }
            .cuChartAccessibility(description)
    }

    private var description: CUChartDescription {
        CUChartDescription(kind: "Column chart", title: title, xTitle: xTitle, yTitle: yTitle,
                           points: columns.map { .init(label: $0.detail.isEmpty ? $0.label : $0.detail, value: $0.value) }, format: format, ordered: true)
    }

    private func select(_ delta: Int) -> KeyPress.Result {
        guard let i = CUChartMath.move(selectedIndex, by: delta, count: columns.count) else { return .ignored }
        selectedID = String(i)
        return .handled
    }

    private func plot(_ progress: Double) -> some View {
        let ticks = showsValueLabels ? [0] : CUChartMath.ticks(low: 0, high: top, startsAtZero: true)
        let selected = selectedIndex
        let accent = selected ?? highlight
        let top = top
        return Chart {
            ForEach(Array(columns.enumerated()), id: \.offset) { i, c in
                BarMark(x: .value("Period", String(i)), y: .value("Value", CUChartMath.grown(c.value, progress: progress)), width: .ratio(0.62))
                    .foregroundStyle(i == accent ? CU.chart1 : CU.chart3)
                    .clipShape(UnevenRoundedRectangle(topLeadingRadius: 3, topTrailingRadius: 3))
                    .annotation(position: .top, spacing: 4, overflowResolution: .init(x: .fit(to: .chart), y: .fit(to: .chart))) {
                        if i == selected {
                            CUTooltip(value: format.text(c.value), detail: c.detail.isEmpty ? c.label : c.detail)
                        } else if showsValueLabels, progress >= 1 {
                            Text(CUValueFormat.number(c.value)).cuAxisLabel(bold: i == accent)
                        }
                    }
                if let tick = c.comparison {
                    RectangleMark(x: .value("Period", String(i)), y: .value("Last year", CUChartMath.grown(tick, progress: progress)), width: .ratio(0.78), height: .fixed(2))
                        .foregroundStyle(CU.text)
                }
            }
        }
        .chartYScale(domain: 0...top)
        .chartXScale(domain: ids)
        .chartXSelection(value: $selectedID)
        .chartYAxis {
            AxisMarks(position: .trailing, values: ticks) { value in
                AxisGridLine(stroke: StrokeStyle(lineWidth: 1)).foregroundStyle(value.index == 0 ? CU.chartBase : CU.chartGrid)
                if !showsValueLabels { AxisValueLabel { Text(format.axis(value.as(Double.self) ?? 0)).cuAxisLabel() } }
            }
        }
        .chartXAxis {
            AxisMarks(values: ids) { value in
                AxisValueLabel(anchor: .top) {
                    if columns.indices.contains(value.index) { Text(columns[value.index].label).cuAxisLabel() }
                }
            }
        }
    }
}

// MARK: Paired bars

/// Two shares per row: the neutral context bar above, the accent bar below, 6 pt tall, values right-aligned in tabular figures.
/// The selected row is bold and the other accent bars step back. Click a row or use ↑ ↓.
struct CUPairedBars: View {
    let rows: [CUPairedRow]
    @Binding var selection: String?
    /// A legend appears because two series exist: what the neutral and the accent bars each mean.
    var legend: (context: String, highlight: String)
    var rowHeight: CGFloat = 32
    var title = "Paired bars"

    private let labelWidth: CGFloat = 48
    private let valueWidth: CGFloat = 84

    var body: some View {
        let top = rows.map { max($0.context, $0.highlight) }.max() ?? 1
        VStack(alignment: .leading, spacing: CU.Space.s) {
            VStack(spacing: 0) {
                ForEach(rows) { row in line(row, top: top) }
            }
            HStack(spacing: CU.Space.m) {
                key(CU.chart3, legend.context)
                key(CU.chart1, legend.highlight)
            }
        }
        .focusable()
        .onKeyPress(.upArrow) { move(-1) }
        .onKeyPress(.downArrow) { move(1) }
        .cuChartAccessibility(CUChartDescription(kind: "Paired bar chart", title: title, xTitle: "Row", yTitle: legend.highlight,
                                                 points: rows.map { .init(label: $0.label, value: $0.highlight) }, format: CUValueFormat(percent: true),
                                                 summaryOverride: "Paired bar chart, \(title). " + rows.map { "\($0.label): \(CUValueFormat.number($0.context))% \(legend.context.lowercased()), \(CUValueFormat.number($0.highlight))% \(legend.highlight.lowercased())." }.joined(separator: " ")))
    }

    private func move(_ delta: Int) -> KeyPress.Result {
        let current = rows.firstIndex { $0.id == selection }
        guard let i = CUChartMath.move(current, by: delta, count: rows.count) else { return .ignored }
        selection = rows[i].id
        return .handled
    }

    private func key(_ colour: Color, _ text: String) -> some View {
        HStack(spacing: CU.Space.xs) {
            RoundedRectangle(cornerRadius: 2, style: .continuous).fill(colour).frame(width: 8, height: 8)
            Text(text).font(.system(size: 11)).foregroundStyle(CU.textSecondary)
        }
    }

    private func line(_ row: CUPairedRow, top: Double) -> some View {
        let on = row.id == selection
        return Button { selection = on ? nil : row.id } label: {
            HStack(spacing: 0) {
                Text(row.label).font(.system(size: 12, weight: on ? .semibold : .regular)).monospacedDigit()
                    .foregroundStyle(on ? CU.text : CU.textSecondary).frame(width: labelWidth, alignment: .leading)
                GeometryReader { g in
                    VStack(alignment: .leading, spacing: 3) {
                        Capsule().fill(CU.chart3).frame(width: g.size.width * CUChartMath.fraction(row.context, of: top), height: 6)
                        Capsule().fill(CU.chart1).opacity(selection == nil || on ? 1 : 0.45)
                            .frame(width: g.size.width * CUChartMath.fraction(row.highlight, of: top), height: 6)
                    }
                    .frame(maxHeight: .infinity, alignment: .center)
                }
                VStack(alignment: .trailing, spacing: 0) {
                    Text("\(CUValueFormat.number(row.context))%").cuAxisLabel()
                    Text("\(CUValueFormat.number(row.highlight))%").cuAxisLabel(bold: on)
                }
                .frame(width: valueWidth, alignment: .trailing)
            }
            .frame(height: rowHeight)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(row.label): \(CUValueFormat.number(row.context))% \(legend.context.lowercased()), \(CUValueFormat.number(row.highlight))% \(legend.highlight.lowercased())")
        .accessibilityAddTraits(on ? .isSelected : [])
    }
}

// MARK: Dumbbell

/// Before and after on one track: a hollow dot for the baseline, a filled dot for now. Accent when the share rose, ink when it
/// fell, never red or green; each row also carries its arrow and its numbers.
struct CUDumbbell: View {
    let rows: [CUDumbbellRow]
    var title = "Shifts"
    var rowHeight: CGFloat = 40
    private let summaryWidth: CGFloat = 104
    private let labelWidth: CGFloat = 96

    private var top: Double {
        CUChartMath.ticks(low: 0, high: rows.flatMap { [$0.before, $0.now] }.max() ?? 1, startsAtZero: true).last ?? 1
    }

    var body: some View {
        let ticks = CUChartMath.ticks(low: 0, high: top, startsAtZero: true)
        HStack(alignment: .top, spacing: 0) {
            // One cell per row, the same height as a plot row, so each name and summary lines up with its dumbbell.
            VStack(spacing: 0) {
                ForEach(rows) { row in
                    Text(row.label).font(.system(size: 13, weight: .semibold)).foregroundStyle(CU.text).lineLimit(1)
                        .frame(width: labelWidth, height: rowHeight, alignment: .leading)
                }
            }
            chart(ticks: ticks)
            VStack(spacing: 0) {
                ForEach(rows) { row in
                    Text(CUChartMath.dumbbellSummary(row)).cuAxisLabel(bold: true).frame(width: summaryWidth, height: rowHeight, alignment: .trailing)
                }
            }
        }
        .cuChartAccessibility(CUChartDescription(kind: "Dumbbell chart", title: title, xTitle: "Item", yTitle: "Share now",
                                                 points: rows.map { .init(label: $0.label, value: $0.now) }, format: CUValueFormat(percent: true),
                                                 summaryOverride: "Dumbbell chart, \(title). " + rows.map { CUChartMath.dumbbellWords($0) + "." }.joined(separator: " ")))
    }

    private func chart(ticks: [Double]) -> some View {
        Chart {
            ForEach(rows) { row in
                let up = CUChartMath.shift(before: row.before, now: row.now) == .rose
                RuleMark(xStart: .value("Before", row.before), xEnd: .value("Now", row.now), y: .value("Item", row.label))
                    .lineStyle(StrokeStyle(lineWidth: 3, lineCap: .round))
                    .foregroundStyle(up ? CU.chart1 : CU.chart2)
                PointMark(x: .value("Before", row.before), y: .value("Item", row.label))
                    .symbol { Circle().fill(CU.bgPanel).overlay(Circle().stroke(CU.chart2, lineWidth: 2)).frame(width: 10, height: 10) }
                PointMark(x: .value("Now", row.now), y: .value("Item", row.label))
                    .symbol { Circle().fill(up ? CU.chart1 : CU.text).frame(width: 12, height: 12) }
            }
        }
        .chartXScale(domain: 0...top)
        .chartYScale(domain: rows.map(\.label))
        .chartXAxis {
            AxisMarks(values: ticks) { value in
                AxisGridLine(stroke: StrokeStyle(lineWidth: 1)).foregroundStyle(CU.chartGrid)
                AxisValueLabel(anchor: value.index == 0 ? .topLeading : (value.index == ticks.count - 1 ? .topTrailing : .top)) { Text(CUValueFormat(percent: true).axis(value.as(Double.self) ?? 0)).cuAxisLabel() }
            }
        }
        .chartYAxis(.hidden)
        .chartPlotStyle { $0.frame(height: rowHeight * Double(rows.count)) }
        .frame(height: rowHeight * Double(rows.count) + 24)
    }
}

// MARK: Ranked bars

/// Parts of a whole, sorted: one accent bar, 10 pt tall on a ghost track. Never a pie.
struct CURankedBars: View {
    let rows: [CURankedRow]
    /// The accent row; defaults to the largest.
    var highlight: String?
    var title = "Ranked bars"
    var labelWidth: CGFloat = 120
    var format = CUValueFormat(percent: true)

    var body: some View {
        let sorted = CUChartMath.ranked(rows)
        let top = sorted.first?.value ?? 1
        let accent = highlight ?? sorted.first?.label
        VStack(spacing: 0) {
            ForEach(sorted) { row in
                let on = row.label == accent
                HStack(spacing: 0) {
                    Text(row.label).font(.system(size: 12, weight: on ? .semibold : .regular)).foregroundStyle(on ? CU.text : CU.textSecondary)
                        .lineLimit(1).frame(width: labelWidth, alignment: .leading)
                    GeometryReader { g in
                        ZStack(alignment: .leading) {
                            Capsule().fill(CU.chartGhost)
                            Capsule().fill(on ? CU.chart1 : CU.chart3).frame(width: g.size.width * CUChartMath.fraction(row.value, of: top))
                        }
                        .frame(height: 10).frame(maxHeight: .infinity)
                    }
                    Text(format.axis(row.value)).cuAxisLabel(bold: on).frame(width: 48, alignment: .trailing)
                }
                .frame(height: 28)
                .accessibilityElement(children: .ignore)
                .accessibilityLabel("\(row.label): \(format.text(row.value))")
            }
        }
        .cuChartAccessibility(CUChartDescription(kind: "Ranked bar chart", title: title, xTitle: "Item", yTitle: "Share",
                                                 points: sorted.map { .init(label: $0.label, value: $0.value) }, format: format))
    }
}

// MARK: Heatmap

/// Days as cells: 12 pt, 4 pt gaps, Monday at the top, five steps from `chart.ghost` to accent. A day is chosen by click, drag
/// or the arrow keys (← → move a week, ↑ ↓ a day); its count and date appear in a tooltip. Never hover-only.
struct CUHeatmap: View {
    let cells: [CUHeatCell]
    var format = CUValueFormat(unit: "songs", singular: "song")
    var calendar: Calendar = .current
    var title = "Heatmap"
    var initialSelection: Int?
    @State private var selected: Int?

    private let cell: CGFloat = 12, gap: CGFloat = 4, labelWidth: CGFloat = 28
    private var pitch: CGFloat { cell + gap }

    var body: some View {
        let grid = CUChartMath.heatGrid(cells, calendar: calendar)
        let lead = cells.first.map { CUChartMath.heatLead($0.date, calendar: calendar) } ?? 0
        let top = cells.map(\.count).max() ?? 0
        let months = CUChartMath.monthLabels(grid, calendar: calendar)
        let width = labelWidth + CGFloat(grid.count) * pitch - gap
        ZStack(alignment: .topLeading) {
            ForEach([(0, "Mon"), (2, "Wed"), (4, "Fri"), (6, "Sun")], id: \.0) { row, name in
                Text(name).cuAxisLabel().position(x: 12, y: CGFloat(row) * pitch + cell / 2)
            }
            ForEach(Array(grid.enumerated()), id: \.offset) { c, column in
                ForEach(Array(column.enumerated()), id: \.offset) { r, day in
                    if let day {
                        RoundedRectangle(cornerRadius: 3, style: .continuous)
                            .fill(CU.heat[CUChartMath.heatLevel(count: day.count, max: top)])
                            .frame(width: cell, height: cell)
                            .position(x: labelWidth + CGFloat(c) * pitch + cell / 2, y: CGFloat(r) * pitch + cell / 2)
                    }
                }
            }
            ForEach(months, id: \.column) { m in
                Text(m.text).cuAxisLabel().fixedSize().offset(x: labelWidth + CGFloat(m.column) * pitch, y: 7 * pitch)
            }
            if let i = selected, cells.indices.contains(i) {
                let p = CUChartMath.heatPosition(index: i, lead: lead)
                let x = labelWidth + CGFloat(p.column) * pitch
                let y = CGFloat(p.row) * pitch
                RoundedRectangle(cornerRadius: 4, style: .continuous).stroke(CU.text, lineWidth: 2)
                    .frame(width: cell + 2, height: cell + 2).position(x: x + cell / 2, y: y + cell / 2)
                CUTooltip(value: format.text(Double(cells[i].count)), detail: CUChartMath.longDate(cells[i].date))
                    .alignmentGuide(.leading) { p.column > grid.count / 2 ? $0.width - cell : 0 }
                    .offset(x: x + (p.column > grid.count / 2 ? 0 : cell + 4), y: max(y - 52, 0))
            }
        }
        .frame(width: width, height: 7 * pitch + 20, alignment: .topLeading)
        .contentShape(Rectangle())
        .gesture(DragGesture(minimumDistance: 0).onChanged { value in
            let c = Int(((value.location.x - labelWidth) / pitch).rounded(.down))
            let r = Int((value.location.y / pitch).rounded(.down))
            if let i = CUChartMath.heatIndex(column: c, row: r, lead: lead, count: cells.count) { selected = i }
        })
        .focusable()
        .onKeyPress(.leftArrow) { move(-7) }
        .onKeyPress(.rightArrow) { move(7) }
        .onKeyPress(.upArrow) { move(-1) }
        .onKeyPress(.downArrow) { move(1) }
        .onKeyPress(.escape) { selected = nil; return .handled }
        .onAppear { if selected == nil, let initialSelection { selected = initialSelection } }
        .cuChartAccessibility(description)
    }

    private func move(_ delta: Int) -> KeyPress.Result {
        guard let i = CUChartMath.move(selected, by: delta, count: cells.count) else { return .ignored }
        selected = i
        return .handled
    }

    private var description: CUChartDescription {
        let withPlays = cells.filter { $0.count > 0 }.count
        let busiest = cells.max(by: { $0.count < $1.count })
        var summary = "Heatmap, \(title). \(cells.count) days, \(withPlays) with \(format.unit)."
        if let busiest, busiest.count > 0 { summary += " Busiest: \(format.text(Double(busiest.count))), \(CUChartMath.longDate(busiest.date, weekday: false))." }
        return CUChartDescription(kind: "Heatmap", title: title, xTitle: "Day", yTitle: format.unit.capitalized,
                                  points: cells.map { .init(label: CUChartMath.longDate($0.date), value: Double($0.count)) },
                                  format: format, continuous: true, ordered: true, summaryOverride: summary)
    }
}

/// "Fewer ▢▢▢▢▢ More": the key to the heat steps.
struct CUHeatmapKey: View {
    var body: some View {
        HStack(spacing: CU.Space.xs) {
            Text("Fewer").font(.system(size: 11)).foregroundStyle(CU.textSecondary)
            ForEach(Array(CU.heat.enumerated()), id: \.offset) { _, c in
                RoundedRectangle(cornerRadius: 3, style: .continuous).fill(c).frame(width: 12, height: 12)
            }
            Text("More").font(.system(size: 11)).foregroundStyle(CU.textSecondary)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Key: lighter squares are fewer, darker squares are more")
    }
}

// MARK: Stage tracker

/// A circle filled from twelve o'clock to `fraction` of the way round.
private struct CUPieSlice: Shape {
    var fraction: Double
    var animatableData: Double { get { fraction } set { fraction = newValue } }
    func path(in rect: CGRect) -> Path {
        var p = Path()
        let c = CGPoint(x: rect.midX, y: rect.midY)
        p.move(to: c)
        p.addArc(center: c, radius: min(rect.width, rect.height) / 2, startAngle: .degrees(-90),
                 endAngle: .degrees(-90 + 360 * min(max(fraction, 0), 1)), clockwise: false)
        p.closeSubpath()
        return p
    }
}

/// Four circles, one per stage: Found, Downloading, Importing, In library. A done stage is a full ink circle, the current one is
/// accent and fills round to its percentage when the server gives one (a solid accent circle when it does not), a failed one is danger
/// and its reason is written under it, and one still to come is an empty ring.
struct CUStageTracker: View {
    let step: Int
    var progress: Double?
    var failed = false
    var failureReason: String?
    var showsNames = false
    var width: CGFloat?

    var body: some View {
        let segments = CUChartMath.stageSegments(step: step, progress: progress, failed: failed)
        VStack(alignment: .leading, spacing: CU.Space.xs) {
            HStack(alignment: .top, spacing: showsNames ? 0 : CU.Space.s) {
                ForEach(Array(segments.enumerated()), id: \.offset) { i, s in
                    VStack(spacing: 5) {
                        segment(s)
                        if showsNames {
                            Text(CUChartMath.stageNames[i]).font(.system(size: 11, weight: i == step ? .semibold : .regular))
                                .foregroundStyle(i == step ? (failed ? CU.danger : CU.text) : CU.textSecondary)
                                .lineLimit(1).fixedSize()
                        }
                    }
                    .frame(maxWidth: showsNames ? .infinity : nil)
                }
            }
            if failed, let failureReason {
                CUErrorLine(message: failureReason).font(.system(size: 12))
            }
        }
        .frame(width: width)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(CUChartMath.stageWords(step: step, progress: progress, failed: failed, reason: failureReason))
    }

    private static let diameter: CGFloat = 20

    @ViewBuilder private func segment(_ s: CUStageSegment) -> some View {
        let d = Self.diameter
        switch s {
        case .done: Circle().fill(CU.text).frame(width: d, height: d)
        case .failed: Circle().fill(CU.danger).frame(width: d, height: d)
        case .pending: Circle().strokeBorder(CU.trackerTrack, lineWidth: 2).frame(width: d, height: d)
        case .current(let progress):
            if let progress {
                Circle().strokeBorder(CU.trackerTrack, lineWidth: 2).frame(width: d, height: d)
                    .overlay { CUPieSlice(fraction: progress).fill(CU.accent).padding(3) }
            } else {
                Circle().fill(CU.accent).frame(width: d, height: d)
            }
        }
    }
}
