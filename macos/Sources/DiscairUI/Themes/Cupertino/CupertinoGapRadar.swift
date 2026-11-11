import SwiftUI

/// Gap Radar (contract 6.4): artists you own albums of that have albums missing, each on a year axis with the owned
/// ones solid and the missing ones dashed with a Get. The order is the biggest gap first. Mockup: the artist screen's
/// radar (`R.cupertino.artist`), given a screen of its own. Missing picks carry no year, so they follow a divider.
struct CupertinoGapRadar: View {
    let state: AppState
    private var lib: LibraryModel { state.library }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("Gap Radar").font(CU.title(34)).padding(.top, 4).accessibilityAddTraits(.isHeader)
                Text("Artists you own, with the albums the Librarian says are missing.").foregroundStyle(CU.muted)
                if lib.gapRadar.isEmpty {
                    Text(lib.gapLoading ? "Reading your artists…" : (lib.picksNote ?? "No gaps found: every recommended album by your artists is already here."))
                        .foregroundStyle(CU.muted).padding(.top, 8)
                }
                // Cards are only as wide as their albums need, so small ones sit side by side and only artists with many
                // albums take (up to) the whole row.
                GapFlowLayout(spacing: 14) {
                    ForEach(lib.gapRadar) { artist in card(artist).frame(minWidth: 0, idealWidth: GapCardWidth.width(albums: artist.total, undatedDivider: !artist.undatedOwned.isEmpty || !artist.undatedMissing.isEmpty), maxWidth: GapCardWidth.width(albums: artist.total, undatedDivider: !artist.undatedOwned.isEmpty || !artist.undatedMissing.isEmpty)) }
                }
            }
            .padding(.horizontal, CU.Space.xl).padding(.bottom, CU.Space.xl)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .task { await state.loadGapRadar() }
    }

    private func card(_ g: GapArtist) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 6) {
                Button { state.openArtist(named: g.name) } label: { Text(g.name).font(CU.title(20)).lineLimit(1) }
                    .buttonStyle(.plain).accessibilityLabel("Open \(g.name)")
                HStack(spacing: 10) {
                    Text(g.summary).font(.system(size: 12)).foregroundStyle(CU.muted).lineLimit(1)
                    Spacer(minLength: 4)
                    ProgressView(value: g.completeness).frame(width: 60).tint(CU.accent).accessibilityHidden(true)
                }
                if g.missing.count > 1 {
                    Button("Get \(g.missing.count) missing") { state.getAllMissing(g) }.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
                }
            }
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(alignment: .top, spacing: 14) {
                    ForEach(g.dated) { a in tile(a) }
                    if !g.undatedOwned.isEmpty || !g.undatedMissing.isEmpty {
                        Rectangle().fill(CU.muted.opacity(0.3)).frame(width: 1, height: 96).padding(.horizontal, 4)
                            .accessibilityHidden(true)
                        ForEach(g.undatedOwned + g.undatedMissing) { a in tile(a) }
                    }
                }
                .padding(.vertical, 4)
            }
        }
        .padding(16)
        .background(CU.card, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .accessibilityElement(children: .contain)
    }

    private func tile(_ a: AlbumItem) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Button { if a.owned { state.open(album: a) } } label: {
                CoverView(album: a).frame(width: 96).clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    .opacity(a.owned ? 1 : 0.35)
                    .overlay { if !a.owned { RoundedRectangle(cornerRadius: 8, style: .continuous).strokeBorder(Color(white: 0.53), style: StrokeStyle(lineWidth: 2, dash: [5, 4])).padding(-3) } }
            }
            .buttonStyle(.plain).accessibilityLabel(a.owned ? "Open \(a.title)" : "\(a.title), missing")
            Text(a.title).font(.system(size: 12, weight: .semibold)).lineLimit(1)
            Text(a.owned ? (a.yearText.isEmpty ? "Owned" : a.yearText) : (a.year > 0 ? "\(a.yearText) · Missing" : "Missing"))
                .font(.system(size: 11)).foregroundStyle(CU.muted).lineLimit(1)
            if !a.owned {
                Button(state.acquisition.buttonLabel(for: a)) { state.actions.get(album: a) }
                    .buttonStyle(CapsuleButtonStyle(primary: true, small: true)).disabled(!state.acquisition.canGet(a))
                    .help(state.acquisition.detail(for: a))
            }
        }
        .frame(width: 96, alignment: .leading)
    }
}

/// How wide a Gap Radar card is: room for each album tile, never narrower than the heading needs.
enum GapCardWidth {
    static let tile: CGFloat = 96, gap: CGFloat = 14, padding: CGFloat = 16, minimum: CGFloat = 250

    static func width(albums: Int, undatedDivider: Bool = false) -> CGFloat {
        let n = CGFloat(max(albums, 1))
        let tiles = n * tile + (n - 1) * gap + (undatedDivider ? 9 + gap : 0)
        return max(minimum, tiles + padding * 2)
    }
}

/// Lays cards out left to right and starts a new row when the next card does not fit. A card wider than the row is
/// squeezed to the row (its albums scroll inside it). Rows are as tall as their tallest card.
struct GapFlowLayout: Layout {
    var spacing: CGFloat = 14

    private func rows(_ subviews: Subviews, width: CGFloat) -> [[(index: Int, size: CGSize)]] {
        var rows: [[(Int, CGSize)]] = [[]]
        var x: CGFloat = 0
        for (i, v) in subviews.enumerated() {
            let ideal = v.sizeThatFits(.unspecified)
            let w = min(ideal.width, width)
            let size = v.sizeThatFits(ProposedViewSize(width: w, height: nil))
            if x > 0, x + w > width + 0.5 { rows.append([]); x = 0 }
            rows[rows.count - 1].append((i, CGSize(width: w, height: size.height)))
            x += w + spacing
        }
        return rows.filter { !$0.isEmpty }
    }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? 800
        let r = rows(subviews, width: width)
        let h = r.map { $0.map(\.size.height).max() ?? 0 }.reduce(0, +) + CGFloat(max(r.count - 1, 0)) * spacing
        return CGSize(width: width, height: h)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var y = bounds.minY
        for row in rows(subviews, width: bounds.width) {
            var x = bounds.minX
            for (i, size) in row {
                subviews[i].place(at: CGPoint(x: x, y: y), anchor: .topLeading, proposal: ProposedViewSize(size))
                x += size.width + spacing
            }
            y += (row.map(\.size.height).max() ?? 0) + spacing
        }
    }
}
