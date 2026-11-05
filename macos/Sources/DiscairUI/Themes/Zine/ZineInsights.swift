import DiscairLibrarian
import SwiftUI

/// Insights in Zine's language: "The Insights". Hidden canon is the lead story, anniversaries are "On this day", series
/// are "Serials"; a lens that is off or empty is printed as a dashed notice, never as invented copy. Mockup:
/// `docs/design/macos-insights/mockups.html` (Zine Daily).
struct ZineInsights: View {
    let state: AppState
    private var model: InsightsModel { state.insights }

    private static let heads: [String: (String, String)] = [
        "hidden_canon": ("Lead story", "Hidden canon"), "blind_spot": ("Missing chapters", "Blind spots"),
        "anniversary": ("On this day", "Anniversaries"), "series_completion": ("Serials", "Series completion"),
        "forgotten_gem": ("Dust jacket", "Forgotten gems"),
    ]
    private static func head(_ k: String) -> (String, String) { heads[k] ?? (k.replacingOccurrences(of: "_", with: " ").capitalized, "More") }

    var body: some View {
        let extra = model.kinds.filter { Self.heads[$0] == nil }
        ZStack(alignment: .bottom) {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .bottom, spacing: 20) {
                    Text("The Insights").font(Z.an(78)).textCase(.uppercase).tracking(0.8).accessibilityAddTraits(.isHeader)
                    Mono("Gen \(model.response.generation) · data v\(model.response.dataVersion) · every item cites its source").padding(.bottom, 8)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }
                ticker
                if let e = model.error { Mono(e).foregroundStyle(Z.red) }
                ShareColumns(shares: [0.42, 0.28, 0.30]) {
                    column(["hidden_canon", "blind_spot"])
                    column(["anniversary"], rule: true)
                    column(["series_completion", "forgotten_gem"] + extra, rule: true)
                }
            }
            if model.lastDismissed != nil { undoBar }
        }
        .task { await state.loadInsights() }
    }

    private var ticker: some View {
        let text = model.kinds.map { k in Self.head(k).0 + ": " + (model.isEnabled(k) ? "\(model.cards(k).count) printed" : "not printed") }.joined(separator: "   ///   ")
        return Text(text).font(Z.mono(11, bold: true)).textCase(.uppercase).foregroundStyle(Z.yellow).lineLimit(1)
            .padding(.horizontal, 10).padding(.vertical, 4).frame(maxWidth: .infinity, alignment: .leading).background(Z.ink)
            .accessibilityLabel("Lenses: " + model.kinds.map { Self.head($0).1 + (model.isEnabled($0) ? " on" : " off") }.joined(separator: ", "))
    }

    private func column(_ kinds: [String], rule: Bool = false) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            ForEach(kinds, id: \.self) { k in section(k) }
        }
        .padding(.horizontal, 18).frame(maxWidth: .infinity, alignment: .topLeading)
        .overlay(alignment: .leading) { if rule { Rectangle().fill(Z.ink).frame(width: 2) } }
    }

    @ViewBuilder private func section(_ kind: String) -> some View {
        let h = Self.head(kind), cards = model.cards(kind)
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline) { Anton(h.0, 24); Spacer(); Mono(h.1, size: 10) }
                .padding(.bottom, 2).overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 3) }
                .accessibilityElement(children: .combine).accessibilityAddTraits(.isHeader)
            if !model.isEnabled(kind) {
                notice("Not printed", "This lens is off. The server enables it only after it passes its check.")
            } else if cards.isEmpty {
                notice("Nothing to print today", "The lens is on and found no cards. It never fills the gap with guesses.")
            } else {
                ForEach(cards) { c in item(c, lead: kind == "hidden_canon") }
            }
        }
    }

    private func notice(_ head: String, _ body: String) -> some View {
        VStack(alignment: .leading, spacing: 3) { Anton(head, 18); Text(body).font(Z.serif(13)) }
            .padding(10).frame(maxWidth: .infinity, alignment: .leading).zBorder(3, dashed: true).opacity(0.75)
    }

    @ViewBuilder private func item(_ c: InsightCard, lead: Bool) -> some View {
        let album = InsightsModel.album(for: c)
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 16) {
                if lead, let a = album { ZineCover(album: a, width: 150, shadow: 5) }
                VStack(alignment: .leading, spacing: 4) {
                    if let n = c.owned, let t = c.total { ZineBadge("\(n) of \(t) owned") }
                    if c.kind == "anniversary", case .number(let n)? = c.reasons.first?.evidence["years"] {
                        Text("\(Int(n))").font(Z.an(54)).foregroundStyle(Z.red) + Text(" years").font(Z.mono(12, bold: true))
                    }
                    Text(c.title).font(Z.an(lead ? 40 : 24)).textCase(.uppercase).fixedSize(horizontal: false, vertical: true)
                    if let a = c.subject.artist {
                        Text([a, c.subject.year.map(String.init)].compactMap { $0 }.joined(separator: " · ")).font(Z.serif(15, italic: true))
                    }
                    Text(c.body).font(Z.serif(14)).fixedSize(horizontal: false, vertical: true)
                }
            }
            if let n = c.owned, let t = c.total, t > 0 { tape(n, t, c) }
            WrapLayout(spacing: 8) {
                if let a = album {
                    Button("Get") { model.accepted(c, librarian: state.session?.librarian); state.actions.get(album: a) }.buttonStyle(ZineButtonStyle(kind: .red, small: true))
                    Button("Save") { state.actions.save(album: a) }.buttonStyle(ZineButtonStyle(small: true))
                }
                if c.kind == "anniversary", let o = ownedAlbum(c) {
                    Button("Play") { model.accepted(c, librarian: state.session?.librarian); state.actions.play(album: o) }.buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
                }
                Button(model.openWhy == c.id ? "Hide why" : "Why?") { model.toggleWhy(c) }.buttonStyle(ZineButtonStyle(small: true))
                    .accessibilityValue(model.openWhy == c.id ? "expanded" : "collapsed")
                if c.dismissible { Button("Dismiss") { model.dismiss(c, librarian: state.session?.librarian) }.buttonStyle(ZineLinkStyle()) }
            }
            if model.openWhy == c.id {
                VStack(alignment: .leading, spacing: 3) {
                    Mono("Why this ran", size: 10, bold: true)
                    Text(InsightNarrative.why(c)).font(Z.serif(13)).fixedSize(horizontal: false, vertical: true)
                }
                .padding(8).frame(maxWidth: .infinity, alignment: .leading).background(Z.white.opacity(0.6)).zBorder(2)
            }
        }
        .padding(.vertical, 6)
        .overlay(alignment: .bottom) { Rectangle().fill(Z.ink.opacity(0.4)).frame(height: 1) }
    }

    private func tape(_ owned: Int, _ total: Int, _ c: InsightCard) -> some View {
        let missing = Set(c.missingRuns.flatMap { Array($0.firstPosition...max($0.firstPosition, $0.lastPosition)) })
        return VStack(alignment: .leading, spacing: 5) {
            HStack(spacing: 3) {
                ForEach(1...total, id: \.self) { i in
                    Rectangle().fill(missing.contains(i) ? Color.clear : Z.ink).frame(height: 14).zBorder(2, dashed: missing.contains(i))
                }
            }
            .accessibilityElement(children: .ignore).accessibilityLabel("\(owned) of \(total) owned")
            ForEach(Array(c.missingRuns.enumerated()), id: \.offset) { _, r in
                Mono("Missing " + (r.firstPosition == r.lastPosition ? "\(r.firstPosition)" : "\(r.firstPosition) to \(r.lastPosition)") + (r.labels.isEmpty ? "" : ": " + r.labels.joined(separator: ", ")), size: 10)
            }
        }
    }

    private func ownedAlbum(_ c: InsightCard) -> AlbumItem? {
        let t = (c.subject.title ?? c.title).lowercased(), a = (c.subject.artist ?? "").lowercased()
        return state.library.albums.first { $0.title.lowercased() == t && $0.artist.lowercased() == a }
    }

    private var undoBar: some View {
        HStack(spacing: 12) {
            Mono("Dismissed. It will not come back.", size: 11, bold: true).foregroundStyle(Z.yellow)
            Button("Undo") { model.undoDismiss(librarian: state.session?.librarian) }.buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
        }
        .padding(10).background(Z.ink).padding(.bottom, 14)
        .task(id: model.lastDismissed?.id) { try? await Task.sleep(for: .seconds(6)); model.clearUndo() }
    }
}

/// Places its children side by side, each taking its share of the width, so a wide lead story cannot squeeze the others.
private struct ShareColumns: Layout {
    let shares: [CGFloat]
    private func widths(_ total: CGFloat, _ n: Int) -> [CGFloat] {
        let used = Array(shares.prefix(n)); let sum = used.reduce(0, +)
        return used.map { total * $0 / max(sum, 0.01) }
    }
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let total = proposal.width ?? 1000
        let w = widths(total, subviews.count)
        let h = zip(subviews, w).map { $0.sizeThatFits(.init(width: $1, height: nil)).height }.max() ?? 0
        return CGSize(width: total, height: h)
    }
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX
        for (view, w) in zip(subviews, widths(bounds.width, subviews.count)) {
            view.place(at: CGPoint(x: x, y: bounds.minY), anchor: .topLeading, proposal: .init(width: w, height: bounds.height))
            x += w
        }
    }
}
