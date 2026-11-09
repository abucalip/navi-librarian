import DiscairLibrarian
import SwiftUI

/// Insights (Server V2 Phase 3 client gate): one panel per lens. Cards are generic: title and body are the server's words,
/// "Why?" opens a paragraph written from the card's own numbers (`InsightNarrative`), Dismiss has Undo. A lens the server
/// has not enabled shows as off; an enabled lens with no cards shows an empty state. Mockup: `docs/design/macos-insights`.
struct CupertinoInsights: View {
    let state: AppState
    private var model: InsightsModel { state.insights }

    private static let names = ["forgotten_gem": "Forgotten Gems", "series_completion": "Series", "blind_spot": "Blind Spots", "hidden_canon": "Hidden Canon", "anniversary": "Anniversaries"]
    static func name(_ kind: String) -> String { names[kind] ?? kind.replacingOccurrences(of: "_", with: " ").capitalized }

    var body: some View {
        let leftKinds = ["hidden_canon", "blind_spot", "forgotten_gem"]
        let left = model.kinds.filter(leftKinds.contains).sorted { leftKinds.firstIndex(of: $0)! < leftKinds.firstIndex(of: $1)! }
        let right = model.kinds.filter { !leftKinds.contains($0) }
        ZStack(alignment: .bottom) {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    header
                    if let e = model.error { Text(e).font(.system(size: 13)).foregroundStyle(CU.accent).accessibilityLabel("Problem: \(e)") }
                    CupertinoTaste(model: state.taste)
                    HStack(alignment: .top, spacing: 16) {
                        VStack(spacing: 16) { ForEach(left, id: \.self) { panel($0) } }.frame(maxWidth: .infinity)
                        VStack(spacing: 16) { ForEach(right, id: \.self) { panel($0) } }.frame(maxWidth: .infinity)
                    }
                }
                .padding(.horizontal, 28).padding(.bottom, 60)
            }
            .scrollEdgeEffectStyle(.hard, for: .top)
            if model.lastDismissed != nil { undoBar }
        }
        .task { await state.loadInsights(); await state.taste.load(librarian: state.session?.librarian) }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Insights").font(CU.title(34)).padding(.top, 4).accessibilityAddTraits(.isHeader)
            Text("Every card says why it is here. Generation \(model.response.generation) · data version \(model.response.dataVersion)").foregroundStyle(CU.muted)
            HStack(spacing: 8) {
                ForEach(model.kinds, id: \.self) { k in
                    let on = model.isEnabled(k)
                    HStack(spacing: 6) {
                        Circle().fill(on ? Color.green : .clear).overlay(Circle().stroke(on ? .clear : CU.muted, lineWidth: 1.5)).frame(width: 8, height: 8)
                        Text(Self.name(k)).fontWeight(on ? .semibold : .regular)
                        Text(on ? "\(model.cards(k).count)" : "off").foregroundStyle(CU.muted)
                    }
                    .font(.system(size: 12)).padding(.horizontal, 12).padding(.vertical, 5)
                    .background(CU.card, in: Capsule())
                    .accessibilityElement(children: .combine)
                    .accessibilityLabel("\(Self.name(k)): " + (on ? "\(model.cards(k).count) cards" : "off"))
                }
            }
        }
    }

    private func panel(_ kind: String) -> some View {
        let cards = model.cards(kind)
        return VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(Self.name(kind)).font(.system(size: 11, weight: .bold)).textCase(.uppercase).tracking(0.9).foregroundStyle(CU.accent)
                    .accessibilityAddTraits(.isHeader)
                Spacer()
            }
            if !model.isEnabled(kind) {
                Text("Off. The server turns a lens on only after it passes its check.").font(.system(size: 13)).foregroundStyle(CU.muted).padding(.vertical, 8)
            } else if cards.isEmpty {
                Text("Nothing to show right now. The lens is on and found no cards; it never fills the gap with guesses.").font(.system(size: 13)).foregroundStyle(CU.muted).padding(.vertical, 8)
            } else {
                ForEach(Array(cards.enumerated()), id: \.element.id) { i, c in
                    if i > 0 { Divider() }
                    card(c)
                }
            }
        }
        .padding(18).frame(maxWidth: .infinity, alignment: .leading)
        .background(model.isEnabled(kind) ? Color.white : CU.fill.opacity(0.7), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    @ViewBuilder private func lead(_ c: InsightCard, album: AlbumItem?) -> some View {
        if let n = c.owned, let t = c.total {
            badge("\(n)/\(t)", "owned")
        } else if let years = years(c) {
            badge("\(years)", years == 1 ? "year" : "years")
        } else if let a = album {
            CoverView(album: a).frame(width: 84, height: 84).clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
        }
    }
    private func years(_ c: InsightCard) -> Int? {
        if c.kind == "anniversary", case .number(let n)? = c.reasons.first?.evidence["years"] { return Int(n) }
        return nil
    }
    private func badge(_ big: String, _ small: String) -> some View {
        VStack(spacing: 2) {
            Text(big).font(.system(size: 30, weight: .heavy)).foregroundStyle(CU.accent).minimumScaleFactor(0.6)
            Text(small).font(.system(size: 10, weight: .semibold)).textCase(.uppercase).tracking(0.6).foregroundStyle(CU.muted)
        }
        .frame(width: 84)
    }

    private func card(_ c: InsightCard) -> some View {
        let album = InsightsModel.album(for: c)
        let owned = c.kind == "anniversary" ? ownedAlbum(c) : nil
        return HStack(alignment: .top, spacing: 14) {
            lead(c, album: album)
            VStack(alignment: .leading, spacing: 6) {
                Text(c.title).font(.system(size: 18, weight: .bold)).fixedSize(horizontal: false, vertical: true)
                if let a = c.subject.artist {
                    Text([a, c.subject.year.map(String.init)].compactMap { $0 }.joined(separator: " · ")).font(.system(size: 13)).foregroundStyle(CU.muted)
                }
                Text(c.body).font(.system(size: 13.5)).fixedSize(horizontal: false, vertical: true)
                if let n = c.owned, let t = c.total, t > 0 { progress(n, t, c) }
                HStack(spacing: 8) {
                    if let a = album {
                        Button("Get") { model.accepted(c, librarian: state.session?.librarian); state.actions.get(album: a) }.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
                        Button("Save") { state.actions.save(album: a) }.buttonStyle(CapsuleButtonStyle(small: true))
                    }
                    if let o = owned {
                        Button("Play") { model.accepted(c, librarian: state.session?.librarian); state.actions.play(album: o) }.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
                    }
                    Button(model.openWhy == c.id ? "Hide why" : "Why?") { model.toggleWhy(c) }
                        .buttonStyle(CapsuleButtonStyle(small: true)).accessibilityValue(model.openWhy == c.id ? "expanded" : "collapsed")
                    if c.dismissible {
                        Button("Dismiss") { model.dismiss(c, librarian: state.session?.librarian) }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
                    }
                }
                if model.openWhy == c.id {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Why you see this").font(.system(size: 10, weight: .bold)).textCase(.uppercase).tracking(0.7).foregroundStyle(CU.muted)
                        Text(InsightNarrative.why(c)).font(.system(size: 13)).fixedSize(horizontal: false, vertical: true)
                    }
                    .padding(.horizontal, 12).padding(.vertical, 9).frame(maxWidth: .infinity, alignment: .leading)
                    .background(CU.card, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                }
            }
        }
        .padding(.vertical, 10)
    }

    private func progress(_ owned: Int, _ total: Int, _ c: InsightCard) -> some View {
        let missing = Set(c.missingRuns.flatMap { Array($0.firstPosition...max($0.firstPosition, $0.lastPosition)) })
        return VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 2) {
                ForEach(1...total, id: \.self) { i in
                    RoundedRectangle(cornerRadius: 2).fill(missing.contains(i) ? CU.fill : CU.accent).frame(height: 8)
                }
            }
            .accessibilityElement(children: .ignore).accessibilityLabel("\(owned) of \(total) owned")
            ForEach(Array(c.missingRuns.enumerated()), id: \.offset) { _, r in
                Text("Missing " + (r.firstPosition == r.lastPosition ? "\(r.firstPosition)" : "\(r.firstPosition) to \(r.lastPosition)") + (r.labels.isEmpty ? "" : ": " + r.labels.joined(separator: ", ")))
                    .font(.system(size: 12)).foregroundStyle(CU.muted)
                    .padding(.horizontal, 10).padding(.vertical, 4)
                    .overlay(RoundedRectangle(cornerRadius: 9).strokeBorder(CU.muted.opacity(0.5), style: StrokeStyle(lineWidth: 1.2, dash: [4, 3])))
            }
        }
    }

    private func ownedAlbum(_ c: InsightCard) -> AlbumItem? {
        let t = (c.subject.title ?? c.title).lowercased(), a = (c.subject.artist ?? "").lowercased()
        return state.library.albums.first { $0.title.lowercased() == t && $0.artist.lowercased() == a }
    }

    private var undoBar: some View {
        HStack(spacing: 12) {
            Text("Dismissed. It will not come back.")
            Button("Undo") { model.undoDismiss(librarian: state.session?.librarian) }.buttonStyle(CapsuleButtonStyle(small: true))
        }
        .font(.system(size: 13)).foregroundStyle(.white).padding(.leading, 18).padding(.trailing, 8).padding(.vertical, 8)
        .background(Color.black.opacity(0.85), in: Capsule()).padding(.bottom, 18)
        .task(id: model.lastDismissed?.id) { try? await Task.sleep(for: .seconds(6)); model.clearUndo() }
    }
}
