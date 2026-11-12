import AppKit
import DiscairLibrarian
import SwiftUI

/// The artist's biography from the Librarian, four lines until "Read more" (the web and Android pages do the same).
struct ArtistBio: View {
    let state: AppState
    @State private var expanded = false
    private var zine: Bool { state.themeID == .zine }

    var body: some View {
        if let text = state.related.bio {
            if zine { zineBody(text) } else { cupertinoBody(text) }
        }
    }

    /// Cupertino: a centred column of justified text with equal room either side, split into paragraphs; the biography
    /// starts well below the banner.
    private func cupertinoBody(_ text: String) -> some View {
        let paragraphs = BioParagraphs.split(text)
        return VStack(alignment: .leading, spacing: 10) {
            ForEach(Array((expanded ? paragraphs : Array(paragraphs.prefix(1))).enumerated()), id: \.offset) { _, p in
                JustifiedText(text: p, size: 14, lineLimit: expanded ? 0 : 4)
            }
            HStack(spacing: 12) {
                if text.count > 280 {
                    Button(expanded ? "Show less" : "Read more") { expanded.toggle() }
                        .buttonStyle(.plain).font(.system(size: 12, weight: .semibold)).foregroundStyle(CU.accent)
                }
                if let s = state.related.bioSource, !s.isEmpty { Text(s).font(.system(size: 11)).foregroundStyle(CU.textSecondary) }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, 44).padding(.bottom, 10)
        .accessibilityElement(children: .contain)
    }

    private func zineBody(_ text: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(text).font(Z.serif(14.5)).lineSpacing(3)
                .lineLimit(expanded ? nil : 4).textSelection(.enabled)
            HStack(spacing: 12) {
                if text.count > 280 {
                    Button(expanded ? "Show less" : "Read more") { expanded.toggle() }
                        .buttonStyle(.plain).font(Z.mono(11, bold: true)).foregroundStyle(Z.red)
                }
                if let s = state.related.bioSource, !s.isEmpty { Text(s).font(Z.mono(10)).foregroundStyle(Z.ink.opacity(0.6)) }
            }
        }
        .padding(.top, 18)
        .accessibilityElement(children: .contain)
    }
}

/// Fully justified, selectable text (SwiftUI's Text cannot justify). Wraps at the width it is offered; `lineLimit` 0 is no limit.
struct JustifiedText: NSViewRepresentable {
    let text: String
    var size: CGFloat = 14
    var lineLimit = 0

    func makeNSView(context: Context) -> NSTextField {
        let f = NSTextField(wrappingLabelWithString: "")
        f.isSelectable = true
        f.drawsBackground = false
        f.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        return f
    }

    func updateNSView(_ f: NSTextField, context: Context) {
        let style = NSMutableParagraphStyle()
        style.alignment = .justified
        style.lineSpacing = 3
        style.lineBreakMode = .byWordWrapping
        f.attributedStringValue = NSAttributedString(string: text, attributes: [
            .font: NSFont.systemFont(ofSize: size), .paragraphStyle: style, .foregroundColor: NSColor(CU.text)])
        f.maximumNumberOfLines = lineLimit
        f.lineBreakMode = lineLimit > 0 ? .byTruncatingTail : .byWordWrapping
    }

    func sizeThatFits(_ proposal: ProposedViewSize, nsView f: NSTextField, context: Context) -> CGSize? {
        let w = proposal.width ?? 600
        guard w.isFinite, w > 0 else { return nil }
        f.preferredMaxLayoutWidth = w
        let h = f.cell?.cellSize(forBounds: NSRect(x: 0, y: 0, width: w, height: .greatestFiniteMagnitude)).height ?? 20
        return CGSize(width: w, height: ceil(h))
    }
}

/// A numbered list of the artist's most listened songs with listen counts; an owned song shows a check, one the library
/// lacks gets a Get when the source names its album.
struct TopSongsPanel: View {
    let state: AppState
    static let width: CGFloat = 310
    private static let shown = 5
    @State private var all = false
    private var zine: Bool { state.themeID == .zine }

    var body: some View {
        let songs = state.related.topSongs
        if !songs.isEmpty {
            VStack(alignment: .leading, spacing: 0) {
                Group {
                    if zine { ZineH2("Top songs", size: 20) } else { Text("Top songs").font(CU.title(20)) }
                }
                .padding(.bottom, 8).accessibilityAddTraits(.isHeader)
                ForEach(all ? songs : Array(songs.prefix(Self.shown))) { s in row(s) }
                if songs.count > Self.shown {
                    action(all ? "Fewer" : "All top songs", primary: false) { all.toggle() }.padding(.top, 8)
                }
            }
            .padding(zine ? 12 : 0)
            .background { if zine { Z.white } }
            .overlay { if zine { Rectangle().stroke(Z.ink, lineWidth: 3) } }
            .frame(width: Self.width, alignment: .leading)
            .accessibilityElement(children: .contain)
        }
    }

    @ViewBuilder private func action(_ title: String, primary: Bool, _ run: @escaping () -> Void) -> some View {
        if zine { Button(title, action: run).buttonStyle(ZineButtonStyle(kind: primary ? .yellow : .plain, small: true)) }
        else { Button(title, action: run).buttonStyle(CapsuleButtonStyle(primary: primary, small: true)) }
    }

    private func row(_ s: TopSongEntry) -> some View {
        HStack(spacing: 10) {
            Text("\(s.rank)").font(zine ? Z.an(18) : .system(size: 15, weight: .bold)).monospacedDigit()
                .foregroundStyle(zine ? Z.ink : CU.textSecondary).frame(width: 24, alignment: .trailing)
            VStack(alignment: .leading, spacing: 1) {
                Text(s.name).font(zine ? Z.serif(14, bold: true) : .system(size: 13, weight: .semibold)).lineLimit(1)
                Text([s.album, s.listensText.map { "\($0) listens" }].compactMap { $0 }.joined(separator: " · "))
                    .font(zine ? Z.mono(10) : .system(size: 11)).opacity(0.65).lineLimit(1)
            }
            Spacer(minLength: 4)
            if s.owned {
                Image(systemName: "checkmark.circle.fill").foregroundStyle(.green).accessibilityLabel("In your library")
            } else if let album = s.album {
                let item = AlbumItem(id: 9000 + s.rank, title: album, artist: state.selectedArtist.name, year: 0, genre: "", format: "", owned: false,
                                     hue: LibraryModel.hue(for: album))
                let label = state.acquisition.buttonLabel(for: item, song: s.name)
                action(label, primary: true) { state.actions.getSong(album: item, title: s.name, trackNumber: nil) }
                    .disabled(!state.acquisition.canGet(item, song: s.name)).help(state.acquisition.detail(for: item, song: s.name))
                    .accessibilityLabel("Get \(s.name)")
            }
        }
        .padding(.vertical, 5)
        .accessibilityElement(children: .combine)
    }
}
