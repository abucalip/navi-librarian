import DiscairLibrarian
import SwiftUI

/// "Your taste" section of Insights (Server V2 Phase 6 presentation slice 5), drawn from the owner's mockup
/// (`docs/design/macos-taste/mockups.html`): an editorial serif headline first, bars as evidence. Every sentence is the
/// server's. A window or dimension it flagged low-sample shows as a sketch or as progress, and nothing is stated that the
/// server did not list. The mockup's morning-vs-night card and its smart-playlist/library actions are later slices.
struct CupertinoTaste: View {
    let model: TasteModel

    private static let up = Color(red: 0.122, green: 0.541, blue: 0.325)     // #1f8a53
    private static let down = Color(red: 0.761, green: 0.255, blue: 0.047)   // #c2410c
    private static let ghost = Color(red: 0.812, green: 0.792, blue: 0.765)  // #cfcac3
    private static let windowNames = ["recent": "Last 90 days", "mid": "Last year", "all_time": "All time"]
    private static let windowTabs = ["recent": "90 days", "mid": "Year", "all_time": "All time"]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text("Your taste").font(.system(size: 12, weight: .semibold)).textCase(.uppercase).tracking(1.1).foregroundStyle(CU.muted)
                    .accessibilityAddTraits(.isHeader)
                if model.refreshing { ProgressView().controlSize(.small).accessibilityLabel("Refreshing your taste") }
                Spacer()
                if let a = model.allTime { Text("\(a.listens.formatted()) listens analysed").font(.system(size: 12)).foregroundStyle(CU.muted) }
            }
            if let note = model.note { Text(note).font(.system(size: 13)).foregroundStyle(CU.muted) }
            if model.profiles == nil {
                emptyCard
            } else {
                Grid(horizontalSpacing: 16, verticalSpacing: 16) {
                    GridRow(alignment: .top) { shiftCard.gridColumnAlignment(.leading); windowCard }
                    if model.decades != nil { GridRow(alignment: .top) { decadesCard; Color.clear.frame(height: 0) } }
                }
            }
        }
    }

    // MARK: Pieces

    private func card<C: View>(@ViewBuilder _ content: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 4, content: content)
            .padding(.horizontal, 20).padding(.vertical, 18).frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.white, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    private func eyebrow(_ s: String) -> some View {
        Text(s).font(.system(size: 11, weight: .bold)).textCase(.uppercase).tracking(0.9).foregroundStyle(CU.accent)
    }
    private func headline(_ s: String) -> some View {
        Text(s).font(.system(size: 24, weight: .bold, design: .serif)).fixedSize(horizontal: false, vertical: true).padding(.top, 2)
    }
    private func caption(_ s: String) -> some View {
        Text(s).font(.system(size: 13.5)).foregroundStyle(CU.muted).fixedSize(horizontal: false, vertical: true).padding(.bottom, 6)
    }
    private func pct(_ x: Double) -> String { "\(Int((x * 100).rounded()))%" }

    /// Thin track with a fill, as in the mockup's bars.
    private func track(_ fraction: Double, fill: some ShapeStyle = CU.accent, tick: Double? = nil, hatched: Bool = false) -> some View {
        GeometryReader { g in
            ZStack(alignment: .leading) {
                Capsule().fill(Self.ghost.opacity(0.35))
                Capsule().fill(hatched ? AnyShapeStyle(Self.ghost) : AnyShapeStyle(fill))
                    .frame(width: g.size.width * max(0, min(1, fraction)))
                    .opacity(hatched ? 0.7 : 1)
                if let t = tick {
                    Rectangle().fill(CU.ink.opacity(0.55)).frame(width: 2, height: 16)
                        .offset(x: g.size.width * max(0, min(1, t)) - 1, y: 0)
                }
            }
            .frame(height: 10).frame(maxHeight: .infinity, alignment: .center)
        }
        .frame(height: 16)
    }

    /// Progress ring-bar plus the dashed chip the mockup uses for "N of M listens needed".
    private func progress(_ have: Int, _ need: Int, chip: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            GeometryReader { g in
                ZStack(alignment: .leading) {
                    Capsule().fill(Self.ghost.opacity(0.4))
                    Capsule().fill(CU.accent).frame(width: g.size.width * model.progress(listens: have, need: need))
                }
            }
            .frame(height: 8).padding(.top, 6)
            Text(chip).font(.system(size: 12.5)).foregroundStyle(CU.muted)
                .padding(.horizontal, 10).padding(.vertical, 3)
                .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(Self.ghost, style: StrokeStyle(lineWidth: 1.5, dash: [4, 3])))
        }
        .accessibilityElement(children: .ignore).accessibilityLabel(chip)
    }

    /// The mockup's segmented control: a pale track with a white selected pill.
    private func segmented(_ order: [String], names: [String: String], selection: Binding<String>, label: String) -> some View {
        HStack(spacing: 2) {
            ForEach(order, id: \.self) { k in
                let on = selection.wrappedValue == k
                Button { selection.wrappedValue = k } label: {
                    Text(names[k] ?? k).font(.system(size: 12.5, weight: .semibold)).foregroundStyle(on ? CU.ink : CU.muted)
                        .padding(.horizontal, 12).padding(.vertical, 4)
                        .background(on ? Color.white : .clear, in: Capsule())
                        .shadow(color: on ? .black.opacity(0.18) : .clear, radius: 1, y: 1)
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(on ? .isSelected : [])
            }
        }
        .padding(3).background(CU.fill.opacity(0.8), in: Capsule())
        .accessibilityElement(children: .contain).accessibilityLabel(label)
    }

    // MARK: Empty

    private var emptyCard: some View {
        card {
            VStack(spacing: 4) {
                Text(model.loaded ? "Taste needs listening history." : "Reading your saved profile.")
                    .font(.system(size: 18, weight: .bold, design: .serif)).foregroundStyle(CU.ink)
                if model.loaded {
                    Text("Connect ListenBrainz or play more; once a window has \(model.minListens) listens I will start describing it.")
                        .font(.system(size: 14)).foregroundStyle(CU.muted).multilineTextAlignment(.center)
                    progress(0, model.minListens, chip: "0 of \(model.minListens) listens needed before I will describe a window")
                }
            }
            .frame(maxWidth: .infinity).padding(.vertical, 14)
        }
    }

    // MARK: Lately vs. always

    private var shiftCard: some View {
        card {
            eyebrow("Lately vs. always")
            if let h = model.profiles?.headline {
                headline(h.text)
                let mid = h.window == "mid"
                let base = model.profiles?.window(h.window)?.listens ?? 0
                caption(mid ? "Based on \(base.formatted()) listens in the past year against \((model.allTime?.listens ?? 0).formatted()) overall."
                            : "Based on \(base.formatted()) listens in the last \(model.profiles?.config.recentDays ?? 90) days against \((model.allTime?.listens ?? 0).formatted()) overall.")
                ForEach(Array(model.shifts.enumerated()), id: \.offset) { _, s in shiftRow(s) }
                HStack(spacing: 14) {
                    legend("All time", Self.ghost); legend(mid ? "Past year" : "Last \(model.profiles?.config.recentDays ?? 90) days", CU.accent)
                }.padding(.top, 6)
            } else {
                headline("No clear shift yet.")
                caption("I only call a change when both the recent window and your history are solid, and it moved at least \(Int(((model.profiles?.config.minShift ?? 0.05) * 100).rounded())) points.")
                if let r = model.recent, r.lowSample {
                    progress(r.listens, model.minListens, chip: "\(r.listens) of \(model.minListens) listens needed before I'll call a shift")
                }
            }
        }
    }

    private func legend(_ label: String, _ color: Color) -> some View {
        HStack(spacing: 5) { RoundedRectangle(cornerRadius: 3).fill(color).frame(width: 10, height: 10); Text(label).font(.system(size: 11.5)).foregroundStyle(CU.muted) }
    }

    private func shiftRow(_ s: TasteShift) -> some View {
        let up = s.direction == "up"
        return HStack(spacing: 10) {
            (Text(s.value) + Text("  \(s.dimension)").font(.system(size: 11.5)).foregroundColor(CU.muted))
                .font(.system(size: 13.5)).lineLimit(1).frame(width: 110, alignment: .leading)
            ZStack(alignment: .leading) {
                track(s.fromShare, fill: Self.ghost)
                GeometryReader { g in
                    RoundedRectangle(cornerRadius: 3).fill(CU.accent).frame(width: g.size.width * min(1, s.toShare), height: 6).frame(maxHeight: .infinity, alignment: .center)
                }
            }
            Text("\(pct(s.fromShare)) → \(pct(s.toShare))").font(.system(size: 13.5, weight: .semibold).monospacedDigit())
                .foregroundStyle(up ? Self.up : Self.down).frame(width: 84, alignment: .trailing)
        }
        .padding(.vertical, 4)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(s.value), \(s.dimension), \(up ? "up" : "down") from \(pct(s.fromShare)) to \(pct(s.toShare))")
    }

    // MARK: The shape of it

    private var windowCard: some View {
        card {
            HStack {
                eyebrow("The shape of it")
                Spacer()
                segmented(TasteProfiles.windowNames, names: Self.windowTabs, selection: Binding(get: { model.window }, set: { model.window = $0 }), label: "Window")
            }
            .padding(.bottom, 6)
            segmented(TasteProfiles.dimensions, names: Dictionary(uniqueKeysWithValues: TasteProfiles.dimensions.map { ($0, $0.capitalized) }),
                      selection: Binding(get: { model.dimension }, set: { model.dimension = $0 }), label: "Dimension")
                .padding(.bottom, 8)
            if let w = model.selectedWindow {
                let name = Self.windowNames[model.window] ?? model.window
                if w.lowSample {
                    caption("\(name): only \(w.listens) listens, so this is a sketch, not a verdict.")
                } else {
                    caption("\(name) · \(w.listens.formatted()) listens" + (model.window != "all_time" ? " · tick = your all-time share" : ""))
                }
                body(for: w)
            } else {
                caption("No \(Self.windowNames[model.window] ?? model.window) window yet.")
            }
        }
    }

    @ViewBuilder private func body(for w: TasteWindow) -> some View {
        if w.isLowSample(model.dimension) && !w.lowSample {
            VStack(spacing: 4) {
                Text("Not enough \(model.dimension) data.").font(.system(size: 18, weight: .bold, design: .serif)).foregroundStyle(CU.ink)
                Text("Only \(w.attributed[model.dimension] ?? 0) listens carry a \(model.dimension). I won't read missing tags as taste.")
                    .font(.system(size: 14)).foregroundStyle(CU.muted).multilineTextAlignment(.center)
                progress(w.attributed[model.dimension] ?? 0, model.minAttributed,
                         chip: "\(w.attributed[model.dimension] ?? 0) of \(model.minAttributed) listens needed before I'll read \(model.dimension)")
            }
            .frame(maxWidth: .infinity).padding(.vertical, 14)
        } else {
            let entries = w.entries(model.dimension)
            if entries.isEmpty {
                Text("Nothing recorded for \(model.dimension) in this window.").font(.system(size: 13)).foregroundStyle(CU.muted)
            } else {
                let top = (entries.map(\.share).max() ?? 0.01) * 1.15
                let allTime = Dictionary(model.allTime?.entries(model.dimension).map { ($0.value, $0.share) } ?? [], uniquingKeysWith: { a, _ in a })
                ForEach(Array(entries.prefix(8).enumerated()), id: \.offset) { _, e in
                    HStack(spacing: 10) {
                        Text(e.value).font(.system(size: 13.5)).lineLimit(1).frame(width: 120, alignment: .leading)
                        track(e.share / top, tick: model.window != "all_time" ? allTime[e.value].map { $0 / top } : nil, hatched: w.lowSample)
                        Text(pct(e.share)).font(.system(size: 13.5).monospacedDigit()).foregroundStyle(CU.muted).frame(width: 44, alignment: .trailing)
                    }
                    .padding(.vertical, 2)
                    .accessibilityElement(children: .ignore)
                    .accessibilityLabel("\(e.value), \(pct(e.share))" + (w.lowSample ? ", low sample" : ""))
                }
            }
        }
    }

    // MARK: Decades

    private var decadesCard: some View {
        card {
            eyebrow("Decades")
            caption("Outline is all time, fill is the last \(model.profiles?.config.recentDays ?? 90) days.")
            if let d = model.decades {
                let top = d.flatMap { [$0.recent, $0.allTime] }.max() ?? 1
                HStack(alignment: .bottom, spacing: 10) {
                    ForEach(Array(d.enumerated()), id: \.offset) { _, e in
                        VStack(spacing: 4) {
                            ZStack(alignment: .bottom) {
                                UnevenRoundedRectangle(topLeadingRadius: 4, topTrailingRadius: 4).strokeBorder(Self.ghost, lineWidth: 1.5)
                                    .frame(height: 90 * (top > 0 ? e.allTime / top : 0))
                                UnevenRoundedRectangle(topLeadingRadius: 4, topTrailingRadius: 4).fill(CU.accent.opacity(0.9))
                                    .frame(height: 90 * (top > 0 ? e.recent / top : 0))
                            }
                            .frame(height: 90, alignment: .bottom)
                            Text(e.label).font(.system(size: 11.5)).foregroundStyle(CU.muted)
                        }
                        .frame(maxWidth: .infinity)
                        .accessibilityElement(children: .ignore)
                        .accessibilityLabel("\(e.label): \(pct(e.recent)) recently, \(pct(e.allTime)) all time")
                    }
                }
                .padding(.top, 8)
            }
        }
    }
}
