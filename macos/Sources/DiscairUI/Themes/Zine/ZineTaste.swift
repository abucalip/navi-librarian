import DiscairLibrarian
import SwiftUI

/// "Your taste" in Zine's language (Server V2 Phase 6 presentation slice 6), drawn from the owner's approved mockup
/// (`docs/design/macos-taste/mockups-zine.html`): the server's headline is the lead story, the windows are a chart sheet, decades
/// sit on a yellow serial card. Every sentence is the server's; a window or dimension it flagged low-sample is hatched or shown as
/// a dashed notice. The morning-vs-night item is a later slice, as in Cupertino. Stamps cover genre and decade only.
struct ZineTaste: View {
    let model: TasteModel
    let state: AppState

    private static let ghost = Color(red: 0.812, green: 0.776, blue: 0.690)   // #cfc6b0
    private static let windowNames = ["recent": "Last 90 days", "mid": "Last year", "all_time": "All time"]
    private static let windowTabs = ["recent": "90 days", "mid": "Year", "all_time": "All time"]
    private var recentDays: Int { model.profiles?.config.recentDays ?? 90 }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .bottom) {
                Text("Your Taste").font(Z.an(78)).textCase(.uppercase).tracking(0.8).accessibilityAddTraits(.isHeader)
                if model.refreshing { ProgressView().controlSize(.small).accessibilityLabel("Refreshing your taste") }
                Spacer()
                if let a = model.allTime { Mono("\(a.listens.formatted()) listens analysed", size: 12).padding(.bottom, 8) }
            }
            .overlay(alignment: .top) { Rectangle().fill(Z.ink).frame(height: 6).offset(y: -6) }
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 2) }
            .padding(.top, 6)
            ticker
            if let note = model.note { Mono(note, size: 11).foregroundStyle(Z.red) }
            if model.profiles == nil {
                emptyNotice
            } else {
                HStack(alignment: .top, spacing: 0) {
                    shiftStory.padding(.trailing, 20).frame(maxWidth: .infinity, alignment: .topLeading)
                        .overlay(alignment: .trailing) { Rectangle().fill(Z.ink).frame(width: 2) }
                    VStack(alignment: .leading, spacing: 18) {
                        windowSheet
                        if model.decades != nil { decadesSerial }
                    }
                    .padding(.leading, 20).frame(maxWidth: .infinity, alignment: .topLeading)
                }
            }
        }
    }

    // MARK: Pieces

    private func eyebrow(_ s: String) -> some View {
        Text(s).font(Z.mono(11, bold: true)).textCase(.uppercase).tracking(0.5).foregroundStyle(Z.yellow)
            .padding(.horizontal, 8).padding(.vertical, 1).background(Z.ink)
    }
    private func pct(_ x: Double) -> String { "\(Int((x * 100).rounded()))%" }

    private var ticker: some View {
        let text: String
        if let r = model.recent, let m = model.profiles?.window("mid"), let a = model.allTime {
            text = "Recent: \(r.listens) listens\(r.lowSample ? " (sketch)" : "")   ///   Year: \(m.listens.formatted())   ///   All time: \(a.listens.formatted())"
        } else { text = "Nothing printed yet" }
        return Text(text).font(Z.mono(12)).textCase(.uppercase).foregroundStyle(Z.yellow).lineLimit(1)
            .padding(.horizontal, 10).padding(.vertical, 4).frame(maxWidth: .infinity, alignment: .leading).background(Z.ink)
            .accessibilityLabel(text)
    }

    private func head(_ title: String, _ side: String) -> some View {
        HStack(alignment: .firstTextBaseline) { Text(title).font(Z.an(26)).textCase(.uppercase); Spacer(); Mono(side, size: 11) }
            .padding(.bottom, 2).overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 3) }
            .accessibilityElement(children: .combine).accessibilityAddTraits(.isHeader)
    }

    private func progress(_ have: Int, _ need: Int, chip: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            GeometryReader { g in
                ZStack(alignment: .leading) {
                    Rectangle().fill(Z.white)
                    Rectangle().fill(Z.red).frame(width: g.size.width * model.progress(listens: have, need: need))
                }.zBorder(2)
            }.frame(height: 16).padding(.top, 8)
            Text(chip).font(Z.mono(12)).textCase(.uppercase).padding(.horizontal, 10).padding(.vertical, 2).zBorder(2, dashed: true)
        }
        .accessibilityElement(children: .ignore).accessibilityLabel(chip)
    }

    private func notice(_ title: String, _ body: String, chip: (Int, Int, String)? = nil, solid: Bool = false) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title).font(Z.an(22)).textCase(.uppercase)
            Text(body).font(Z.serif(14)).fixedSize(horizontal: false, vertical: true)
            if let c = chip { progress(c.0, c.1, chip: c.2) }
        }
        .padding(10).frame(maxWidth: .infinity, alignment: .leading).zBorder(3, dashed: !solid)
    }

    private func segmented(_ order: [String], names: [String: String], selection: Binding<String>, label: String) -> some View {
        HStack(spacing: 0) {
            ForEach(Array(order.enumerated()), id: \.offset) { i, k in
                let on = selection.wrappedValue == k
                Button { selection.wrappedValue = k } label: {
                    Text(names[k] ?? k).font(Z.mono(11, bold: true)).textCase(.uppercase).foregroundStyle(on ? Z.yellow : Z.ink)
                        .padding(.horizontal, 10).padding(.vertical, 3).background(on ? Z.ink : .clear)
                }
                .buttonStyle(.plain).accessibilityAddTraits(on ? .isSelected : [])
                if i < order.count - 1 { Rectangle().fill(Z.ink).frame(width: 2) }
            }
        }
        .background(Z.white).zBorder(2).accessibilityElement(children: .contain).accessibilityLabel(label)
    }

    /// Stamps start a smart playlist or open the Library filtered; neither changes ranking.
    @ViewBuilder private func stamps(_ a: TasteAction?, playlist: Bool) -> some View {
        if let a {
            WrapLayout(spacing: 10) {
                if playlist { Button("Make a playlist: \(a.label)") { state.makeSmartPlaylist(from: a) }.buttonStyle(ZineButtonStyle(kind: .red)) }
                Button(playlist ? "Show in Library" : "Show \(a.label) in Library") { state.openLibrary(filteredBy: a) }.buttonStyle(ZineButtonStyle())
            }.padding(.top, 12)
        }
    }

    // MARK: Empty

    private var emptyNotice: some View {
        notice(model.refreshing ? "Reading your listens." : model.loaded ? "Taste needs listening history." : "Reading your saved profile.",
               model.refreshing ? "This can take about a minute the first time." : model.note ?? (model.loaded ? "Connect ListenBrainz in Settings or play more; once a window has \(model.minListens) listens I will start describing it." : ""),
               chip: model.loaded ? (0, model.minListens, "0 of \(model.minListens) listens needed before I will describe a window") : nil)
    }

    // MARK: Lately vs. always (lead story)

    private var shiftStory: some View {
        VStack(alignment: .leading, spacing: 6) {
            eyebrow("Lately vs. always")
            if let h = model.profiles?.cardHeadline {
                let mid = h.window == "mid"
                let base = model.profiles?.window(h.window)?.listens ?? 0
                Text(h.text).font(Z.an(54)).textCase(.uppercase).lineSpacing(-6).fixedSize(horizontal: false, vertical: true).padding(.top, 4)
                Text(mid ? "Based on \(base.formatted()) listens in the past year against \((model.allTime?.listens ?? 0).formatted()) overall."
                         : "Based on \(base.formatted()) listens in the last \(recentDays) days against \((model.allTime?.listens ?? 0).formatted()) overall.")
                    .font(Z.serif(16, italic: true)).fixedSize(horizontal: false, vertical: true).padding(.bottom, 4)
                ForEach(Array(model.shifts.enumerated()), id: \.offset) { _, s in shiftRow(s) }
                HStack(spacing: 14) {
                    legend("All time", hatched: true); legend(mid ? "Past year" : "Last \(recentDays) days", hatched: false)
                }.padding(.top, 4)
                stamps(model.shiftAction, playlist: true)
            } else {
                Text("No clear shift yet.").font(Z.an(54)).textCase(.uppercase).padding(.top, 4)
                Text("I only call a change when both the recent window and your history are solid, and it moved at least \(Int(((model.profiles?.config.minShift ?? 0.05) * 100).rounded())) points.")
                    .font(Z.serif(15)).fixedSize(horizontal: false, vertical: true)
                if let r = model.recent, r.lowSample {
                    progress(r.listens, model.minListens, chip: "\(r.listens) of \(model.minListens) listens needed before I'll call a shift")
                }
            }
        }
    }

    private func hatch(_ color: Color = Z.ink) -> some View {
        Canvas { ctx, size in
            var p = Path(); var x = -size.height
            while x < size.width { p.move(to: CGPoint(x: x, y: size.height)); p.addLine(to: CGPoint(x: x + size.height, y: 0)); x += 8 }
            ctx.stroke(p, with: .color(Self.ghost), lineWidth: 3)
        }
    }

    private func legend(_ label: String, hatched: Bool) -> some View {
        HStack(spacing: 5) {
            Group { if hatched { hatch().background(Z.white) } else { Z.red } }.frame(width: 12, height: 12).clipped().zBorder(2)
            Mono(label, size: 11)
        }
    }

    private func shiftRow(_ s: TasteShift) -> some View {
        let up = s.direction == "up"
        return HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 0) {
                Text(s.value).font(Z.serif(14)).lineLimit(1)
                Mono(s.dimension, size: 10).opacity(0.7)
            }.frame(width: 120, alignment: .leading)
            GeometryReader { g in
                ZStack(alignment: .leading) {
                    Z.white
                    hatch().frame(width: g.size.width * min(1, s.fromShare * 2.4)).clipped()
                        .overlay(alignment: .trailing) { Rectangle().fill(Z.ink).frame(width: 2) }
                    (up ? Z.red : Z.ink).frame(width: g.size.width * min(1, s.toShare * 2.4), height: g.size.height - 8)
                }.zBorder(2)
            }.frame(height: 18)
            Text("\(pct(s.fromShare)) → \(pct(s.toShare))").font(Z.mono(12, bold: true)).frame(width: 92, alignment: .trailing)
        }
        .padding(.vertical, 4)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(s.value), \(s.dimension), \(up ? "up" : "down") from \(pct(s.fromShare)) to \(pct(s.toShare))")
    }

    // MARK: The shape of it

    private var windowSheet: some View {
        VStack(alignment: .leading, spacing: 8) {
            head("The shape of it", Self.windowNames[model.window] ?? model.window)
            WrapLayout(spacing: 10) {
                segmented(TasteProfiles.windowNames, names: Self.windowTabs, selection: Binding(get: { model.window }, set: { model.window = $0 }), label: "Window")
                segmented(TasteProfiles.dimensions, names: Dictionary(uniqueKeysWithValues: TasteProfiles.dimensions.map { ($0, $0.capitalized) }),
                          selection: Binding(get: { model.dimension }, set: { model.dimension = $0 }), label: "Dimension")
            }
            if let w = model.selectedWindow {
                let name = Self.windowNames[model.window] ?? model.window
                if w.lowSample {
                    Text("\(name): only \(w.listens) listens, so this is a sketch, not a verdict.").font(Z.serif(14))
                } else {
                    Mono("\(w.listens.formatted()) listens" + (model.window != "all_time" ? " · red tick = your all-time share" : ""), size: 12)
                }
                rows(for: w)
                stamps(model.windowAction, playlist: false)
            } else {
                Text("No \(Self.windowNames[model.window] ?? model.window) window yet.").font(Z.serif(14))
            }
        }
    }

    @ViewBuilder private func rows(for w: TasteWindow) -> some View {
        if w.isLowSample(model.dimension) && !w.lowSample {
            let n = w.attributed[model.dimension] ?? 0
            notice("Not enough \(model.dimension) data.", "Only \(n) listens carry a \(model.dimension). I won't read missing tags as taste.",
                   chip: (n, model.minAttributed, "\(n) of \(model.minAttributed) listens needed before I'll read \(model.dimension)"))
        } else {
            let entries = w.entries(model.dimension)
            if entries.isEmpty {
                Text("Nothing recorded for \(model.dimension) in this window.").font(Z.serif(14))
            } else {
                let top = (entries.map(\.share).max() ?? 0.01) * 1.15
                let allTime = Dictionary(model.allTime?.entries(model.dimension).map { ($0.value, $0.share) } ?? [], uniquingKeysWith: { a, _ in a })
                ForEach(Array(entries.prefix(8).enumerated()), id: \.offset) { _, e in
                    HStack(spacing: 10) {
                        Text(e.value).font(Z.serif(14)).lineLimit(1).frame(width: 120, alignment: .leading)
                        GeometryReader { g in
                            ZStack(alignment: .leading) {
                                Z.white
                                if w.lowSample { hatch().frame(width: g.size.width * e.share / top).clipped() }
                                else { Z.ink.frame(width: g.size.width * e.share / top) }
                                if model.window != "all_time", let t = allTime[e.value] {
                                    Z.red.frame(width: 3, height: g.size.height + 10).offset(x: g.size.width * t / top - 1.5)
                                }
                            }.zBorder(2)
                        }.frame(height: 14)
                        Text(pct(e.share)).font(Z.mono(12, bold: true)).frame(width: 44, alignment: .trailing)
                    }
                    .padding(.vertical, 3)
                    .accessibilityElement(children: .ignore)
                    .accessibilityLabel("\(e.value), \(pct(e.share))" + (w.lowSample ? ", low sample" : ""))
                }
            }
        }
    }

    // MARK: Decades (yellow serial)

    private var decadesSerial: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline) { Text("Decades").font(Z.an(26)).textCase(.uppercase); Spacer(); Mono("Last \(recentDays) days against all time", size: 11) }
                .padding(.bottom, 2).overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 3) }
                .accessibilityElement(children: .combine).accessibilityAddTraits(.isHeader)
            if let d = model.decades {
                let top = d.flatMap { [$0.recent, $0.allTime] }.max() ?? 1
                HStack(alignment: .bottom, spacing: 8) {
                    ForEach(Array(d.enumerated()), id: \.offset) { _, e in
                        VStack(spacing: 4) {
                            ZStack(alignment: .bottom) {
                                Rectangle().strokeBorder(Z.ink, style: StrokeStyle(lineWidth: 2, dash: [4, 3]))
                                    .frame(height: 100 * (top > 0 ? e.allTime / top : 0))
                                Z.red.frame(height: 100 * (top > 0 ? e.recent / top : 0)).zBorder(2)
                            }.frame(height: 100, alignment: .bottom)
                            Mono(e.label, size: 11)
                        }
                        .frame(maxWidth: .infinity)
                        .accessibilityElement(children: .ignore)
                        .accessibilityLabel("\(e.label): \(pct(e.recent)) recently, \(pct(e.allTime)) all time")
                    }
                }
                Mono("Dashed = all time · red = last \(recentDays) days", size: 11).padding(.top, 4)
            }
        }
        .padding(.horizontal, 14).padding(.vertical, 12).background(Z.yellow).zBorder(3).zShadow(5)
    }
}
