import AppKit
import CoreText
import SwiftUI

/// Zine Spread building blocks. Spec: `docs/design/macos-m4/mockups.html`, `.th-zine` CSS and `R.zine`.
/// Print look: paper, ink, yellow and red; 3 pt ink borders, hard offset shadows, Anton headlines, Space Mono labels.
enum Z {
    static let ink = Color(red: 0.067, green: 0.067, blue: 0.067)       // #111
    static let paper = Color(red: 1, green: 0.98, blue: 0.941)          // #fffaf0
    static let yellow = Color(red: 1, green: 0.871, blue: 0.349)        // #ffde59
    static let red = Color(red: 0.902, green: 0.196, blue: 0.133)       // #e63222
    static let white = Color.white

    /// Bundled fonts (copied from the repo's Android resources; licences next to them). Registered once per process.
    static let fontsRegistered: Bool = {
        guard let dir = Bundle.module.url(forResource: "Fonts", withExtension: nil),
              let files = try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil) else { return false }
        for f in files where f.pathExtension == "ttf" {
            CTFontManagerRegisterFontsForURL(f as CFURL, .process, nil)
        }
        return true
    }()

    static func an(_ size: CGFloat) -> Font { _ = fontsRegistered; return .custom("Anton-Regular", fixedSize: size) }
    static func mono(_ size: CGFloat = 11, bold: Bool = false) -> Font {
        _ = fontsRegistered
        return .custom(bold ? "SpaceMono-Bold" : "SpaceMono-Regular", fixedSize: size)
    }
    /// Body text: Source Serif 4 (bundled, OFL).
    static func serif(_ size: CGFloat, italic: Bool = false, bold: Bool = false) -> Font {
        _ = fontsRegistered
        let name = bold ? (italic ? "SourceSerif4-BoldItalic" : "SourceSerif4-Bold") : (italic ? "SourceSerif4-Italic" : "SourceSerif4-Regular")
        return .custom(name, fixedSize: size)
    }
}

/// Space Mono label: uppercase, tracked.
struct Mono: View {
    let text: String
    var size: CGFloat = 11
    var bold = false
    init(_ text: String, size: CGFloat = 11, bold: Bool = false) { self.text = text; self.size = size; self.bold = bold }
    var body: some View {
        Text(text).font(Z.mono(size, bold: bold)).textCase(.uppercase).tracking(size * 0.06)
    }
}

/// Anton headline: uppercase.
struct Anton: View {
    let text: String
    let size: CGFloat
    var lineLimit: Int? = 1
    init(_ text: String, _ size: CGFloat, lineLimit: Int? = 1) { self.text = text; self.size = size; self.lineLimit = lineLimit }
    var body: some View {
        Text(text).font(Z.an(size)).textCase(.uppercase).tracking(size * 0.01).lineLimit(lineLimit)
    }
}

/// A hard offset shadow behind a view (no blur).
extension View {
    func zShadow(_ d: CGFloat = 3) -> some View {
        background(alignment: .topLeading) { Rectangle().fill(Z.ink).offset(x: d, y: d) }
    }
    func zBorder(_ w: CGFloat = 3, dashed: Bool = false) -> some View {
        overlay { Rectangle().strokeBorder(Z.ink, style: StrokeStyle(lineWidth: w, dash: dashed ? [w * 2, w * 1.4] : [])) }
    }
}

enum ZineButtonKind { case plain, yellow, red }

/// The mockup `.btn`: 3 pt ink border, mono bold caps, 3 pt hard shadow.
struct ZineButtonStyle: ButtonStyle {
    var kind: ZineButtonKind = .plain
    var small = false
    func makeBody(configuration: Configuration) -> some View {
        let bg: Color = switch kind { case .plain: Z.white; case .yellow: Z.yellow; case .red: Z.red }
        configuration.label
            .font(Z.mono(small ? 11 : 12, bold: true)).textCase(.uppercase)
            .foregroundStyle(kind == .red ? Color.white : Z.ink)
            .padding(.horizontal, small ? 8 : 12).padding(.vertical, small ? 2 : 4)
            .background(bg)
            .zBorder(3)
            .zShadow(configuration.isPressed ? 1 : 3)
            .offset(x: configuration.isPressed ? 2 : 0, y: configuration.isPressed ? 2 : 0)
            .contentShape(Rectangle())
    }
}

/// Underlined text action (`.u`), used for Not for me so it keeps a text label.
struct ZineLinkStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(Z.mono(11, bold: true)).textCase(.uppercase).underline()
            .foregroundStyle(Z.ink).opacity(configuration.isPressed ? 0.6 : 1)
            .contentShape(Rectangle())
    }
}

/// `.badge`: small bordered tag.
struct ZineBadge: View {
    let text: String
    init(_ t: String) { text = t }
    var body: some View {
        Text(text).font(Z.mono(10, bold: true)).textCase(.uppercase)
            .padding(.horizontal, 6).background(Z.white).zBorder(2)
    }
}

/// Section heading with the 3 pt rule underneath (`h2`).
struct ZineH2: View {
    let text: String
    var size: CGFloat = 22
    init(_ t: String, size: CGFloat = 22) { text = t; self.size = size }
    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Anton(text, size)
            Rectangle().fill(Z.ink).frame(height: 3)
        }
        .padding(.bottom, 8)
        .accessibilityElement(children: .combine).accessibilityAddTraits(.isHeader)
    }
}

/// Horizontal dotted leader line (`.dot i`).
struct DottedLine: View {
    var body: some View {
        GeometryReader { g in
            Path { p in p.move(to: CGPoint(x: 0, y: 1)); p.addLine(to: CGPoint(x: g.size.width, y: 1)) }
                .stroke(Z.ink, style: StrokeStyle(lineWidth: 2, lineCap: .round, dash: [0.1, 4]))
        }
        .frame(height: 2).alignmentGuide(.firstTextBaseline) { _ in 0 }
    }
}

/// `left ........ right`.
struct DotRow<L: View, R: View>: View {
    let left: L, right: R
    init(@ViewBuilder left: () -> L, @ViewBuilder right: () -> R) { self.left = left(); self.right = right() }
    var body: some View {
        HStack(alignment: .lastTextBaseline, spacing: 6) {
            left
            DottedLine().frame(maxWidth: .infinity).alignmentGuide(.lastTextBaseline) { d in d[.bottom] + 3 }
            right
        }
    }
}

/// `.li`: a list row with a dotted underline.
struct ZineListRow<Content: View>: View {
    var highlight = false
    @ViewBuilder let content: Content
    var body: some View {
        content
            .padding(.vertical, 7).padding(.leading, highlight ? 6 : 0)
            .background(highlight ? Z.yellow : .clear)
            .overlay(alignment: .bottom) { DottedLine() }
    }
}

/// Flowing tags that wrap onto the next line.
struct WrapLayout: Layout {
    var spacing: CGFloat = 6
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        arrange(width: proposal.width ?? 300, subviews: subviews).size
    }
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let r = arrange(width: bounds.width, subviews: subviews)
        for (i, f) in r.frames.enumerated() {
            subviews[i].place(at: CGPoint(x: bounds.minX + f.minX, y: bounds.minY + f.minY), proposal: .unspecified)
        }
    }
    private func arrange(width: CGFloat, subviews: Subviews) -> (size: CGSize, frames: [CGRect]) {
        var x: CGFloat = 0, y: CGFloat = 0, rowH: CGFloat = 0, frames: [CGRect] = []
        for s in subviews {
            let sz = s.sizeThatFits(.unspecified)
            if x + sz.width > width, x > 0 { x = 0; y += rowH + spacing; rowH = 0 }
            frames.append(CGRect(origin: CGPoint(x: x, y: y), size: sz))
            x += sz.width + spacing; rowH = max(rowH, sz.height)
        }
        return (CGSize(width: width, height: y + rowH), frames)
    }
}

/// Printed cover: the mockup's five generated patterns (index mod 5), ink border and hard shadow.
struct ZineCover: View {
    let album: AlbumItem
    var width: CGFloat
    var border: CGFloat = 3
    var shadow: CGFloat = 6

    var body: some View {
        let h = album.hue
        let c1 = Color(hue: h / 360, saturation: 0.62, brightness: 0.98 - 0.0)
        let c2 = Color(hue: ((h + 40).truncatingRemainder(dividingBy: 360)) / 360, saturation: 0.75, brightness: 0.46)
        let c3 = Color(hue: ((h + 180).truncatingRemainder(dividingBy: 360)) / 360, saturation: 0.6, brightness: 0.95)
        ZStack {
            pattern(album.id % 5, c1, c2, c3)
            ArtworkImage(album: album, px: width > 200 ? 600 : 200).frame(width: width, height: width).clipped()
        }
            .frame(width: width, height: width)
            .clipped()
            .zBorder(border)
            .zShadow(shadow)
            .accessibilityElement().accessibilityLabel("\(album.title) cover")
    }

    @ViewBuilder private func pattern(_ p: Int, _ c1: Color, _ c2: Color, _ c3: Color) -> some View {
        switch p {
        case 0:
            ZStack {
                LinearGradient(colors: [c1, c2], startPoint: .topLeading, endPoint: .bottomTrailing)
                GeometryReader { g in Circle().fill(c3).frame(width: g.size.width * 0.36).position(x: g.size.width * 0.62, y: g.size.height * 0.38) }
            }
        case 1:
            GeometryReader { g in
                HStack(spacing: 0) {
                    ForEach(0..<7, id: \.self) { i in (i % 2 == 0 ? c1 : c2).frame(width: g.size.width * 0.14) }
                }
                .frame(width: g.size.width, alignment: .leading)
            }
        case 2:
            ZStack {
                GeometryReader { g in
                    Path { q in q.move(to: .zero); q.addLine(to: CGPoint(x: g.size.width, y: 0)); q.addLine(to: CGPoint(x: 0, y: g.size.height)); q.closeSubpath() }.fill(c1)
                    Path { q in q.move(to: CGPoint(x: g.size.width, y: 0)); q.addLine(to: CGPoint(x: g.size.width, y: g.size.height)); q.addLine(to: CGPoint(x: 0, y: g.size.height)); q.closeSubpath() }.fill(c2)
                    Circle().fill(c3).frame(width: g.size.width * 0.44).position(x: g.size.width / 2, y: g.size.height / 2)
                }
            }
        case 3:
            GeometryReader { g in
                ZStack {
                    c2
                    ForEach(0..<9, id: \.self) { i in
                        let d = g.size.width * 2.2 * (1 - CGFloat(i) / 9)
                        Circle().fill(i % 2 == 0 ? c1 : c2).frame(width: d).position(x: g.size.width / 2, y: g.size.height * 0.6)
                    }
                }
            }
        default:
            VStack(spacing: 0) { c3.frame(maxHeight: .infinity).layoutPriority(0.3); c1.frame(maxHeight: .infinity); c2.frame(maxHeight: .infinity) }
        }
    }
}

/// Halftone dots over the cover (Now Playing). Multiply blend at 28%.
struct Halftone: View {
    var body: some View {
        Canvas { ctx, size in
            let step: CGFloat = 9
            var y: CGFloat = step / 2
            while y < size.height {
                var x: CGFloat = step / 2
                while x < size.width {
                    ctx.fill(Path(ellipseIn: CGRect(x: x - 2.4, y: y - 2.4, width: 4.8, height: 4.8)), with: .color(Z.ink))
                    x += step
                }
                y += step
            }
        }
        .opacity(0.28).blendMode(.multiply).allowsHitTesting(false).accessibilityHidden(true)
    }
}
