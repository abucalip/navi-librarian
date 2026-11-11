import DiscairLibrarian
import SwiftUI

/// "Your taste" on Insights, four panels (redesign 5.3, mockup `insights--default`): lately against always (dumbbell),
/// top values (ranked bars with window and dimension controls), when you listen (columns) and morning against night.
/// Every sentence is the server's. The time-of-day panels read the server's `context` block; the client draws its numbers and
/// shows the server's state word (stated, no difference, low sample) without composing a claim of its own.
struct CupertinoTaste: View {
    let model: TasteModel
    let state: AppState

    private static let windowNames = ["recent": "Last 90 days", "mid": "Last year", "all_time": "All time"]
    private static let windowTabs = ["recent": "90 days", "mid": "Year", "all_time": "All time"]
    private static let dimensionNames = ["genre": "Genre", "era": "Decade", "area": "Area", "label": "Label"]
    /// The mockup offers four dimensions, in its order. The server also profiles collaborators; they are not offered here.
    private static let pickerDimensions = ["genre", "era", "area", "label"]
    private static let plurals = ["genre": "Genres", "era": "Decades", "area": "Areas", "label": "Labels"]
    /// Time-of-day contexts in the mockup's order, with the hours each one covers.
    private static let parts: [(key: String, label: String)] = [("night", "Night 0–5"), ("morning", "Morning 6–11"),
                                                                ("afternoon", "Afternoon 12–17"), ("evening", "Evening 18–23")]

    var body: some View {
        VStack(alignment: .leading, spacing: CU.Space.m) {
            HStack(alignment: .firstTextBaseline, spacing: CU.Space.s) {
                Text("Your taste").cuRole(CU.Font.title1).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
                if model.refreshing { ProgressView().controlSize(.small).accessibilityLabel("Refreshing your taste") }
                Spacer(minLength: 0)
                if let a = model.allTime { Text("\(a.listens.formatted()) listens analysed").cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary) }
            }
            if let note = model.note { Text(note).cuRole(CU.Font.body).foregroundStyle(CU.textSecondary) }
            if model.profiles == nil {
                emptyPanel
            } else {
                Grid(horizontalSpacing: CU.Space.m, verticalSpacing: CU.Space.m) {
                    GridRow(alignment: .top) { shiftPanel.gridColumnAlignment(.leading); valuesPanel }
                    GridRow(alignment: .top) { listenPanel; nightPanel }
                }
            }
        }
    }

    // MARK: Pieces

    private func eyebrow(_ s: String) -> some View {
        Text(s).font(CU.Font.eyebrow.font).textCase(.uppercase).tracking(CU.Font.eyebrow.tracking).foregroundStyle(CU.textSecondary)
            .accessibilityAddTraits(.isHeader)
    }

    private func pct(_ x: Double) -> String { "\(Int((x * 100).rounded()))%" }

    private func note(_ s: String) -> some View {
        Text(s).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true)
    }

    /// Progress toward a sample size, with the sentence that names it. The bar is ink, the track ghost.
    private func progress(_ have: Int, _ need: Int, sentence: String) -> some View {
        VStack(alignment: .leading, spacing: CU.Space.xs) {
            GeometryReader { g in
                ZStack(alignment: .leading) {
                    Capsule().fill(CU.chartGhost)
                    Capsule().fill(CU.text).frame(width: g.size.width * model.progress(listens: have, need: need))
                }
            }
            .frame(height: 8)
            note(sentence)
        }
        .accessibilityElement(children: .combine)
    }

    private var emptyPanel: some View {
        CUPanel {
            VStack(alignment: .leading, spacing: CU.Space.s) {
                Text(model.refreshing ? "Reading your listens." : model.loaded ? "Taste needs listening history." : "Reading your saved profile.")
                    .cuRole(CU.Font.title3).foregroundStyle(CU.text)
                if model.refreshing {
                    note("This can take about a minute the first time.")
                } else if model.loaded {
                    if let n = model.note { note(n) }
                    note("Connect ListenBrainz in Settings or play more; once a window has \(model.minListens) listens I will start describing it.")
                    progress(0, model.minListens, sentence: "0 of \(model.minListens) listens needed before I will describe a window")
                }
            }
        }
    }

    // MARK: Lately against always

    private var shiftPanel: some View {
        CUPanel {
            eyebrow("Lately against always")
            if let h = model.profiles?.headline {
                Text(h.text).cuRole(CU.Font.title1).foregroundStyle(CU.text).fixedSize(horizontal: false, vertical: true)
                let base = model.profiles?.window(h.window)?.listens ?? 0
                note(h.window == "mid"
                     ? "\(base.formatted()) listens in the past year against \((model.allTime?.listens ?? 0).formatted()) overall."
                     : "\(base.formatted()) listens in the last \(model.profiles?.config.recentDays ?? 90) days against \((model.allTime?.listens ?? 0).formatted()) overall.")
                if !model.shifts.isEmpty {
                    CUDumbbell(rows: model.shifts.map { CUDumbbellRow(label: $0.value, before: $0.fromShare, now: $0.toShare) }, title: "Lately against always")
                }
                actions(model.shiftAction)
            } else {
                Text("No clear shift yet.").cuRole(CU.Font.title1).foregroundStyle(CU.text)
                note("I only call a change when both the recent window and your history are solid, and it moved at least \(Int(((model.profiles?.config.minShift ?? 0.05) * 100).rounded())) points.")
                if let r = model.recent, r.lowSample {
                    progress(r.listens, model.minListens, sentence: "\(r.listens) of \(model.minListens) listens needed before I'll call a shift")
                }
            }
        }
    }

    /// The mockup's two neutral buttons. They start a smart playlist or open the Library filtered; neither changes ranking.
    /// Neutral on purpose: Insights has no primary action.
    @ViewBuilder private func actions(_ a: TasteAction?) -> some View {
        if let a {
            HStack(spacing: CU.Space.s) {
                Button("Make \(Self.article(a.label)) \(a.label) playlist") { state.makeSmartPlaylist(from: a) }
                    .buttonStyle(CapsuleButtonStyle(small: true))
                Button("Show \(a.label) in Library") { state.openLibrary(filteredBy: a) }
                    .buttonStyle(CapsuleButtonStyle(small: true))
            }
            .padding(.top, CU.Space.xs)
        }
    }

    /// "an Ambient", "a Jazz": the indefinite article for a button label.
    static func article(_ word: String) -> String {
        guard let first = word.lowercased().first else { return "a" }
        return "aeiou".contains(first) ? "an" : "a"
    }

    // MARK: Top values

    private var valuesPanel: some View {
        CUPanel {
            eyebrow("Top \(Self.plurals[model.dimension]?.lowercased() ?? "values")")
            VStack(alignment: .leading, spacing: CU.Space.s) {
                CUSegmented(TasteProfiles.windowNames.map { (value: $0, label: Self.windowTabs[$0] ?? $0) },
                            selection: Binding(get: { model.window }, set: { model.window = $0 }), accessibilityName: "Window")
                CUSegmented(Self.pickerDimensions.map { (value: $0, label: Self.dimensionNames[$0] ?? $0) },
                            selection: Binding(get: { model.dimension }, set: { model.dimension = $0 }), accessibilityName: "Dimension")
            }
            valuesBody
        }
    }

    @ViewBuilder private var valuesBody: some View {
        if let w = model.selectedWindow {
            let name = Self.windowNames[model.window] ?? model.window
            if w.lowSample {
                note("\(name): only \(w.listens) listens, so this is a sketch, not a verdict.")
            } else {
                note("\(name) · \(w.listens.formatted()) listens" + (model.window != "all_time" ? " · the all-time share is listed beside each value." : ""))
            }
            if w.isLowSample(model.dimension) && !w.lowSample {
                progress(w.attributed[model.dimension] ?? 0, model.minAttributed,
                         sentence: "Only \(w.attributed[model.dimension] ?? 0) listens carry a \(Self.dimensionNames[model.dimension]?.lowercased() ?? model.dimension). Need \(model.minAttributed) before I read it; missing tags are not taste.")
            } else {
                let entries = w.entries(model.dimension)
                if entries.isEmpty {
                    note("Nothing recorded for \(Self.dimensionNames[model.dimension]?.lowercased() ?? model.dimension) in this window.")
                } else {
                    CURankedBars(rows: entries.prefix(8).map { CURankedRow(label: $0.value, value: $0.share * 100) },
                                 title: "Top \(Self.plurals[model.dimension]?.lowercased() ?? model.dimension)", labelWidth: 120,
                                 format: CUValueFormat(percent: true))
                }
            }
            actions(model.windowAction)
        } else {
            note("No \(Self.windowNames[model.window] ?? model.window) window yet.")
        }
    }

    // MARK: Time of day

    private var listenPanel: some View {
        CUPanel {
            let timezone = model.context?.timezone ?? "UTC"
            CUChartFrame("When you listen", subtitle: "Listens by time of day, \(timezone) · all time", phase: model.context == nil ? .unavailable(
                headline: "Not computed yet", message: "The server has not saved the listening contexts yet. Refresh your taste to build them.", fixTitle: nil) : .ready,
                plotHeight: 180) {
                if let ctx = model.context {
                    let columns = Self.parts.map { CUColumn(label: $0.label, value: Double(ctx.listensIn($0.key)), detail: "\($0.label): \(ctx.listensIn($0.key).formatted()) listens") }
                    CUColumnChart(columns: columns, highlight: columns.indices.max { columns[$0].value < columns[$1].value },
                                  showsValueLabels: true, format: CUValueFormat(unit: "listens", singular: "listen"), height: 180,
                                  title: "Listens by time of day", xTitle: "Time of day")
                } else {
                    EmptyView()
                }
            }
        }
    }

    // MARK: Morning against night

    /// The server's contrast in its three states. Below the sample size nothing is compared: the bar shows the short side.
    private var nightPanel: some View {
        CUPanel {
            eyebrow("Morning against night")
            if let c = model.context?.contrast {
                let points = Int(((model.profiles?.config.minShift ?? 0.05) * 100).rounded())
                switch c.state {
                case "stated":
                    Text("Morning against night").cuRole(CU.Font.title3).foregroundStyle(CU.text)
                    note("Share of listens, night to morning. Only values that differ by at least \(points) points are shown.")
                    CUDumbbell(rows: c.entries.prefix(6).map { CUDumbbellRow(label: $0.value, before: $0.night, now: $0.morning) },
                               title: "Morning against night")
                case "no_difference":
                    Text("No clear difference.").cuRole(CU.Font.title3).foregroundStyle(CU.text)
                    note("No value differs by at least \(points) points between morning and night.")
                default:
                    let night = c.listens["night"] ?? 0, morning = c.listens["morning"] ?? 0
                    let short = min(night, morning)
                    let side = night < morning ? "night" : "morning"
                    Text("Not enough \(side) listening to compare.").cuRole(CU.Font.title3).foregroundStyle(CU.text)
                    note("A contrast is stated only when both sides hold \(c.minListens) listens. Night has \(night), morning has \(morning).")
                    progress(short, c.minListens, sentence: "\(short) of \(c.minListens) listens")
                }
            } else {
                Text("Not computed yet.").cuRole(CU.Font.title3).foregroundStyle(CU.text)
                note("The server has not saved the morning and night comparison.")
            }
        }
    }
}
