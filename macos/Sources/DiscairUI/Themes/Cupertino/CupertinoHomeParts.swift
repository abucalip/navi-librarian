import SwiftUI

// Small pieces of the redesigned Cupertino Home (redesign M8). Mockups: `docs/design/redesign/macos/cupertino/home--*`.

extension View {
    /// A type role's size, weight and tracking, for any view (`Text.cuRole` is the Text-only form).
    func cu(_ role: CU.Font.Role) -> some View { font(role.font).tracking(role.tracking) }
}

/// Rows of the page: a fixed ratio split (2:1, or 1:1) with a 16 gap. Every child is as tall as the tallest, so panels line up.
struct HomeSplit: Layout {
    var weights: [CGFloat]
    var spacing: CGFloat = CU.Space.m

    private func widths(_ total: CGFloat, _ count: Int) -> [CGFloat] {
        let w = Array(weights.prefix(count))
        let net = total - spacing * CGFloat(max(w.count - 1, 0))
        let sum = w.reduce(0, +)
        return w.map { sum > 0 ? net * $0 / sum : 0 }
    }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let total = proposal.width ?? 980
        let ws = widths(total, subviews.count)
        let h = zip(subviews, ws).map { $0.sizeThatFits(ProposedViewSize(width: $1, height: nil)).height }.max() ?? 0
        return CGSize(width: total, height: h)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX
        for (s, w) in zip(subviews, widths(bounds.width, subviews.count)) {
            s.place(at: CGPoint(x: x, y: bounds.minY), anchor: .topLeading, proposal: ProposedViewSize(width: w, height: bounds.height))
            x += w + spacing
        }
    }
}

/// A grouped panel for the page: `bg.panel`, radius 24, padding 16, and as tall as its row.
struct HomePanel<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: CU.Space.s) { content }
            .padding(CU.Space.m)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(CU.bgPanel, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
            .environment(\.cuInPanel, true)
            .accessibilityElement(children: .contain)
    }
}

/// Panel title (`title2`), a supporting line, and a control at the trailing edge.
struct HomeHeader<Accessory: View>: View {
    let title: String
    var subtitle = ""
    @ViewBuilder var accessory: Accessory

    var body: some View {
        HStack(alignment: .top, spacing: CU.Space.m) {
            VStack(alignment: .leading, spacing: CU.Space.xs) {
                Text(title).cu(CU.Font.title2).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
                if !subtitle.isEmpty { Text(subtitle).cu(CU.Font.callout).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true) }
            }
            Spacer(minLength: 0)
            accessory.fixedSize()
        }
    }
}

extension HomeHeader where Accessory == EmptyView {
    init(_ title: String, subtitle: String = "") { self.init(title: title, subtitle: subtitle, accessory: { EmptyView() }) }
}

/// Short caps label: 11 bold, +0.06em, secondary.
struct HomeEyebrow: View {
    let text: String
    init(_ text: String) { self.text = text }
    var body: some View {
        Text(text.uppercased()).cuRole(CU.Font.eyebrow).foregroundStyle(CU.textSecondary).accessibilityAddTraits(.isHeader)
    }
}

/// A key cap (24 high, radius 8, white, 1 pt border) and what the key does.
struct HomeKeyHint: View {
    let key: String
    let symbol: Bool
    let label: String

    var body: some View {
        HStack(spacing: CU.Space.s) {
            Group { if symbol { Image(systemName: key) } else { Text(key) } }
                .font(CU.Font.caption.weighted(.semibold)).foregroundStyle(CU.text)
                .padding(.horizontal, symbol ? 0 : CU.Space.s).frame(minWidth: 24, minHeight: 24)
                .background(CU.content, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .overlay(RoundedRectangle(cornerRadius: 8, style: .continuous).strokeBorder(CU.separatorStrong, lineWidth: 1))
                .accessibilityHidden(true)
            Text(label).cu(CU.Font.callout).foregroundStyle(CU.textSecondary)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(symbol ? Self.name(key) : key): \(label)")
    }

    private static func name(_ symbol: String) -> String {
        switch symbol {
        case "arrow.right": "Right arrow"
        case "arrow.left": "Left arrow"
        case "arrow.down": "Down arrow"
        default: symbol
        }
    }
}

/// A trend arrow with its words. The arrow is never the only carrier: the sentence says the same.
struct HomeChange: View {
    let line: HomeScreen.ChangeLine

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: CU.Space.xs) {
            if let trend = line.trend {
                Image(systemName: trend == .up ? "arrow.up" : trend == .down ? "arrow.down" : "equal")
                    .font(CU.Font.callout.weighted(.semibold)).foregroundStyle(trend == .up ? CU.success : CU.text).accessibilityHidden(true)
            }
            Text(line.text).cu(CU.Font.callout).foregroundStyle(CU.text).fixedSize(horizontal: false, vertical: true)
        }
    }
}

/// One figure of the briefing band: eyebrow, the number with its unit, and a line beneath. A button when it has somewhere to go.
struct HomeStat<Detail: View>: View {
    let eyebrow: String
    let value: String
    var unit = ""
    var hero = false
    var action: (() -> Void)?
    var actionHint = ""
    @ViewBuilder var detail: Detail

    var body: some View {
        let content = VStack(alignment: .leading, spacing: CU.Space.xs) {
            HomeEyebrow(eyebrow)
            HStack(alignment: .firstTextBaseline, spacing: CU.Space.xs) {
                Text(value).font((hero ? CU.Font.heroMetric : CU.Font.metric).font).tracking(hero ? CU.Font.heroMetric.tracking : CU.Font.metric.tracking)
                    .monospacedDigit().foregroundStyle(CU.text)
                if !unit.isEmpty { Text(unit).cu(hero ? CU.Font.title3 : CU.Font.headline).foregroundStyle(CU.textSecondary) }
            }
            detail
        }
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .contentShape(Rectangle())
        if let action {
            Button(action: action) { content }.buttonStyle(.plain).accessibilityHint(actionHint)
        } else {
            content
        }
    }
}

/// A flat placeholder in the footprint of what is loading: no spinner, nothing moves.
struct HomeSkeletonBlock: View {
    var width: CGFloat?
    var height: CGFloat
    var radius: CGFloat = 8
    @Environment(\.cuInPanel) private var inPanel

    var body: some View {
        RoundedRectangle(cornerRadius: radius, style: .continuous).fill(inPanel ? CU.bgFillOnPanel : CU.bgFill)
            .frame(width: width, height: height).frame(maxWidth: width == nil ? .infinity : nil, alignment: .leading)
            .accessibilityHidden(true)
    }
}
