import DiscairLibrarian
import SwiftUI

/// Insights (redesign 5.3, mockup `insights--default`): lens pills under the title, the taste panels (`CupertinoTaste`), then
/// one panel per lens. Cards are generic: title and body are the server's words, "Why?" opens a paragraph written from the
/// card's own numbers (`InsightNarrative`), Dismiss has Undo. A lens the server has not enabled shows as off; an enabled lens
/// with no cards shows an empty state. Every card action is neutral: the page has no primary action.
struct CupertinoInsights: View {
    let state: AppState
    private var model: InsightsModel { state.insights }

    private static let names = ["forgotten_gem": "Forgotten Gems", "series_completion": "Series", "blind_spot": "Blind Spots", "hidden_canon": "Hidden Canon", "anniversary": "Anniversaries"]
    static func name(_ kind: String) -> String { names[kind] ?? kind.replacingOccurrences(of: "_", with: " ").capitalized }
    /// The mockup's order: Anniversaries, then the left column; Series and Blind Spots on the right.
    private static let order = ["anniversary", "forgotten_gem", "hidden_canon", "series_completion", "blind_spot"]
    private static let leftColumn: Set<String> = ["anniversary", "forgotten_gem", "hidden_canon"]

    var body: some View {
        let kinds = model.kinds.sorted { (Self.order.firstIndex(of: $0) ?? 99) < (Self.order.firstIndex(of: $1) ?? 99) }
        let left = kinds.filter(Self.leftColumn.contains)
        let right = kinds.filter { !Self.leftColumn.contains($0) }
        ZStack(alignment: .bottom) {
            ScrollView {
                VStack(alignment: .leading, spacing: CU.Space.l) {
                    header
                    if let e = model.error { CUErrorLine(message: e).font(CU.Font.body.font) }
                    CupertinoTaste(model: state.taste, state: state)
                    VStack(alignment: .leading, spacing: CU.Space.m) {
                        Text("Lenses").cuRole(CU.Font.title1).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
                        HStack(alignment: .top, spacing: CU.Space.m) {
                            VStack(spacing: CU.Space.m) { ForEach(left, id: \.self) { panel($0) } }.frame(maxWidth: .infinity)
                            VStack(spacing: CU.Space.m) { ForEach(right, id: \.self) { panel($0) } }.frame(maxWidth: .infinity)
                        }
                    }
                }
                .padding(.horizontal, CU.Space.xl).padding(.bottom, 60)
            }
            .scrollEdgeEffectStyle(.hard, for: .top)
            if model.lastDismissed != nil { undoBar }
        }
        .task {
            await state.loadInsights()
            await state.taste.load(librarian: state.session?.librarian)
            await state.taste.refreshIfEmpty(librarian: state.session?.librarian)
        }
        // The server refreshes its cards every few hours; reading again while the page is open keeps this one current.
        .task {
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(InsightsModel.refreshSeconds))
                guard !Task.isCancelled else { return }
                await state.loadInsights()
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: CU.Space.s) {
            Text("Insights").cuRole(CU.Font.largeTitle).foregroundStyle(CU.text).padding(.top, CU.Space.xs).accessibilityAddTraits(.isHeader)
            Text("Every card says why it is here." + (model.updatedText.map { " \($0)" } ?? "")).cuRole(CU.Font.body).foregroundStyle(CU.textSecondary)
            lensPills
        }
    }

    /// One pill per lens: a green check and the count when it is on, "off" in words when it is not.
    private var lensPills: some View {
        HStack(spacing: CU.Space.s) {
            ForEach(model.kinds, id: \.self) { k in
                let on = model.isEnabled(k)
                HStack(spacing: CU.Space.xs) {
                    if on { Image(systemName: "checkmark").font(.system(size: 11, weight: .semibold)).accessibilityHidden(true) }
                    Text(Self.name(k)).fontWeight(on ? .semibold : .medium)
                    Text(on ? " · \(model.cards(k).count)" : " · off").foregroundStyle(on ? CU.success : CU.textSecondary)
                }
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(on ? CU.success : CU.textSecondary)
                .padding(.horizontal, CU.Space.m).frame(height: 24)
                .background(on ? CU.successTint : CU.bgFill, in: Capsule())
                .accessibilityElement(children: .combine)
                .accessibilityLabel("\(Self.name(k)): " + (on ? "\(model.cards(k).count) cards" : "off"))
            }
        }
    }

    private func panel(_ kind: String) -> some View {
        let cards = model.cards(kind)
        return CUPanel {
            Text(Self.name(kind)).font(CU.Font.eyebrow.font).textCase(.uppercase).tracking(CU.Font.eyebrow.tracking)
                .foregroundStyle(CU.textSecondary).accessibilityAddTraits(.isHeader)
            if !model.isEnabled(kind) {
                note("Off. The server turns a lens on only after it passes its check.")
            } else if cards.isEmpty {
                note("Nothing to show right now. The lens is on and found no cards; it never fills the gap with guesses.")
            } else {
                ForEach(Array(cards.enumerated()), id: \.element.id) { i, c in
                    if i > 0 { Divider().padding(.vertical, CU.Space.xs) }
                    card(c)
                }
            }
        }
    }

    private func note(_ s: String) -> some View {
        Text(s).cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).padding(.vertical, CU.Space.s).fixedSize(horizontal: false, vertical: true)
    }

    @ViewBuilder private func lead(_ c: InsightCard, album: AlbumItem?) -> some View {
        if let n = c.owned, let t = c.total {
            badge("\(n)/\(t)", "owned")
        } else if let years = years(c) {
            badge("\(years)", years == 1 ? "year" : "years")
        } else if let a = album {
            CoverView(album: a).frame(width: 84, height: 84).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        }
    }

    private func years(_ c: InsightCard) -> Int? {
        if c.kind == "anniversary", case .number(let n)? = c.reasons.first?.evidence["years"] { return Int(n) }
        return nil
    }

    /// A white tile with the number in title1 and its word under it, as in the mockup's Series card.
    private func badge(_ big: String, _ small: String) -> some View {
        VStack(spacing: CU.Space.xs) {
            Text(big).cuRole(CU.Font.title1).foregroundStyle(CU.text).monospacedDigit().minimumScaleFactor(0.6).lineLimit(1)
            Text(small).font(CU.Font.eyebrow.font).textCase(.uppercase).tracking(CU.Font.eyebrow.tracking).foregroundStyle(CU.textSecondary)
        }
        .frame(width: 84, height: 84)
        .background(CU.content, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }

    private func card(_ c: InsightCard) -> some View {
        let album = InsightsModel.album(for: c)
        let owned = c.kind == "anniversary" ? ownedAlbum(c) : nil
        return HStack(alignment: .top, spacing: CU.Space.m) {
            lead(c, album: album)
            VStack(alignment: .leading, spacing: CU.Space.xs) {
                Text(c.title).cuRole(CU.Font.title3).foregroundStyle(CU.text).fixedSize(horizontal: false, vertical: true)
                if let a = c.subject.artist {
                    Text([a, c.subject.year.map(String.init)].compactMap { $0 }.joined(separator: " · ")).cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
                }
                Text(c.body).cuRole(CU.Font.body).foregroundStyle(CU.text).fixedSize(horizontal: false, vertical: true)
                if let n = c.owned, let t = c.total, t > 0 { progress(n, t, c) }
                actionRow(c, album: album, owned: owned)
                if model.openWhy == c.id {
                    VStack(alignment: .leading, spacing: CU.Space.xs) {
                        Text("Why you see this").font(CU.Font.eyebrow.font).textCase(.uppercase).tracking(CU.Font.eyebrow.tracking).foregroundStyle(CU.textSecondary)
                        Text(InsightNarrative.why(c)).cuRole(CU.Font.body).foregroundStyle(CU.text).fixedSize(horizontal: false, vertical: true)
                    }
                    .padding(.horizontal, CU.Space.m).padding(.vertical, CU.Space.s).frame(maxWidth: .infinity, alignment: .leading)
                    .background(CU.content, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                }
            }
        }
        .padding(.vertical, CU.Space.s)
    }

    /// One neutral row per card. Get and Play are neutral here too (the page has no primary), Dismiss is outlined.
    private func actionRow(_ c: InsightCard, album: AlbumItem?, owned: AlbumItem?) -> some View {
        HStack(spacing: CU.Space.s) {
            if let a = album {
                Button("Get") { model.accepted(c, librarian: state.session?.librarian); state.actions.get(album: a) }.buttonStyle(CapsuleButtonStyle(small: true))
                Button("Save") { state.actions.save(album: a) }.buttonStyle(CapsuleButtonStyle(small: true))
            }
            if let o = owned {
                Button { model.accepted(c, librarian: state.session?.librarian); state.actions.play(album: o) } label: { Label("Play", systemImage: "play.fill") }
                    .buttonStyle(CapsuleButtonStyle(small: true))
            }
            Button(model.openWhy == c.id ? "Hide why" : "Why?") { model.toggleWhy(c) }
                .buttonStyle(CapsuleButtonStyle(small: true)).accessibilityValue(model.openWhy == c.id ? "expanded" : "collapsed")
            if c.dismissible {
                Button("Dismiss") { model.dismiss(c, librarian: state.session?.librarian) }.buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
            }
        }
        .padding(.top, CU.Space.xs)
    }

    /// Owned segments in ink, missing ones in the ghost track, dashed labels for each missing run.
    private func progress(_ owned: Int, _ total: Int, _ c: InsightCard) -> some View {
        let missing = Set(c.missingRuns.flatMap { Array($0.firstPosition...max($0.firstPosition, $0.lastPosition)) })
        return VStack(alignment: .leading, spacing: CU.Space.xs) {
            HStack(spacing: 2) {
                ForEach(1...total, id: \.self) { i in
                    RoundedRectangle(cornerRadius: 2).fill(missing.contains(i) ? CU.bgFill : CU.text).frame(height: 8)
                }
            }
            .accessibilityElement(children: .ignore).accessibilityLabel("\(owned) of \(total) owned")
            ForEach(Array(c.missingRuns.enumerated()), id: \.offset) { _, r in
                Text("Missing " + (r.firstPosition == r.lastPosition ? "\(r.firstPosition)" : "\(r.firstPosition) to \(r.lastPosition)") + (r.labels.isEmpty ? "" : ": " + r.labels.joined(separator: ", ")))
                    .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
                    .padding(.horizontal, CU.Space.s).padding(.vertical, CU.Space.xs)
                    .overlay(RoundedRectangle(cornerRadius: 9).strokeBorder(CU.textSecondary.opacity(0.5), style: StrokeStyle(lineWidth: 1.2, dash: [4, 3])))
            }
        }
    }

    private func ownedAlbum(_ c: InsightCard) -> AlbumItem? {
        let t = (c.subject.title ?? c.title).lowercased(), a = (c.subject.artist ?? "").lowercased()
        return state.library.albums.first { $0.title.lowercased() == t && $0.artist.lowercased() == a }
    }

    private var undoBar: some View {
        HStack(spacing: CU.Space.m) {
            Text("Dismissed. It will not come back.")
            Button("Undo") { model.undoDismiss(librarian: state.session?.librarian) }.buttonStyle(CapsuleButtonStyle(small: true))
        }
        .font(CU.Font.body.font).foregroundStyle(CU.content).padding(.leading, CU.Space.l).padding(.trailing, CU.Space.s).padding(.vertical, CU.Space.s)
        .background(CU.text.opacity(0.85), in: Capsule()).padding(.bottom, CU.Space.l)
        .task(id: model.lastDismissed?.id) { try? await Task.sleep(for: .seconds(6)); model.clearUndo() }
    }
}
