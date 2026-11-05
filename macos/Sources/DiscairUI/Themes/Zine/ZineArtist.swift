import CoreText
import SwiftUI

/// Artist: a magazine cover. The name set huge and cropped, cover lines from top songs, back issues owned solid
/// and missing dashed. Mockup: `R.zine.artist`.
struct ZineArtist: View {
    let state: AppState
    static let bannerHeight: CGFloat = 215
    /// 240 pt for short names; longer names shrink so the whole name still fits the width (about 0.38 em per capital).
    var nameSize: CGFloat { min(240, 1000 / (0.38 * CGFloat(max(state.selectedArtist.name.count, 1)))) }
    var nameAscent: CGFloat {
        _ = Z.fontsRegistered
        return CTFontGetAscent(CTFontCreateWithName("Anton-Regular" as CFString, nameSize, nil))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            BackButton(title: AppState.title(of: state.artistBack), zine: true) { state.screen = state.artistBack }.padding(.bottom, 8)
            ZStack(alignment: .topLeading) {
                // The whole name is shown (owner review: the cropped version cut the letters off). The text box is placed
                // from the font's own ascent so the baseline sits 10 pt above the rule.
                Text(state.selectedArtist.name).font(Z.an(nameSize)).textCase(.uppercase).lineLimit(1).fixedSize()
                    .offset(x: -2, y: Self.bannerHeight - 10 - nameAscent).accessibilityAddTraits(.isHeader)
                VStack(alignment: .leading, spacing: 2) {
                    Mono("Cover lines")
                    ForEach(coverLines, id: \.self) { Text($0).font(Z.an(17)).textCase(.uppercase).lineLimit(1) }
                }
                .padding(.horizontal, 12).padding(.vertical, 10)
                .background(Z.yellow).zBorder(3)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topTrailing).padding(.trailing, 20).padding(.top, 10)
            }
            .frame(height: Self.bannerHeight, alignment: .topLeading).clipped()
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }

            HStack(spacing: 20) {
                let lib = state.library
                if state.selectedArtistIsUnowned { Mono("Not in your library") } else {
                    Mono("\(state.shownArtistOwnedCount) of \(state.shownArtistOwnedCount + state.shownArtistMissingCount) albums owned")
                    Mono("\(state.shownArtistMissingCount) missing")
                }
                Mono(lib.isLive ? genres : "Post-rock · Synth-pop")
                Spacer()
                HStack(spacing: 10) {
                    if !state.selectedArtistIsUnowned {
                    Button("Play") { state.actions.play(album: state.library.artistAlbums.first ?? Fixtures.albums[0]) }.buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
                    }
                    Button("Radio") { }.buttonStyle(ZineButtonStyle(small: true))
                    if state.shownArtistMissingCount > 0 || !state.library.isLive {
                    Button(state.library.isLive ? "Get \(state.shownArtistMissingCount) missing" : "Get both missing") {
                        for a in state.shownArtistAlbums where !a.owned { state.actions.get(album: a) }
                    }
                    .buttonStyle(ZineButtonStyle(small: true))
                    }
                }
            }
            .padding(.vertical, 6)

            HStack(alignment: .top, spacing: 22) {
                VStack(alignment: .leading, spacing: 0) {
                    if state.library.isLive { ArtistBio(state: state).padding(.bottom, 10) }
                    if state.library.isLive, state.related.loading || state.related.incomplete {
                        Mono(state.related.loading ? "Still looking for the biography and top songs…" : (state.related.lastError ?? "The Librarian had not finished.") + " Reopen the page to ask again.").padding(.bottom, 8)
                    }
                    ZineH2("Back issues", size: 20)
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 140, maximum: 140), spacing: 18, alignment: .top)], alignment: .leading, spacing: 16) {
                        ForEach(state.shownArtistAlbums) { a in issue(a) }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                if state.library.isLive { TopSongsPanel(state: state) }
                if !state.library.isLive {   // similar artists and a bio need Librarian calls the client does not have yet
                    VStack(alignment: .leading, spacing: 8) {
                        ZineH2("Also in this issue", size: 18)
                        WrapLayout(spacing: 6) { ForEach(ZineFixtures.alsoInThisIssue, id: \.self) { ZineBadge($0) } }
                        Text(ZineFixtures.artistBio).font(Z.serif(13))
                    }
                    .padding(.horizontal, 12).padding(.vertical, 10)
                    .background(Z.white).zBorder(3)
                    .frame(width: 250)
                }
            }
            if state.library.isLive { RelatedSections(state: state, mixed: true) }
        }
        .task(id: state.selectedArtist.id) { await state.loadSelectedArtist() }
    }

    private var coverLines: [String] {
        state.library.isLive ? Array(state.library.artistAlbums.prefix(3).map(\.title)) : ZineFixtures.coverLines
    }

    private var genres: String {
        var seen: [String] = []
        for g in state.library.artistAlbums.map(\.genre) where !g.isEmpty && !seen.contains(g) { seen.append(g) }
        return seen.prefix(2).joined(separator: " · ")
    }

    private func issue(_ a: AlbumItem) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            if a.owned {
                Button { state.open(album: a) } label: { ZineCover(album: a, width: 130) }
                    .buttonStyle(.plain).accessibilityLabel("Open \(a.title)")
            } else {
                VStack(spacing: 4) {
                    Mono("Missing").multilineTextAlignment(.center)
                    Button(state.acquisition.buttonLabel(for: a)) { state.actions.get(album: a) }
                        .buttonStyle(ZineButtonStyle(kind: .yellow, small: true)).disabled(!state.acquisition.canGet(a))
                        .help(state.acquisition.detail(for: a))
                        .accessibilityLabel("Get \(a.title)")
                }
                .frame(width: 130, height: 130)
                .background(StripeFill())
                .zBorder(3, dashed: true)
            }
            Button { state.open(album: a) } label: {
                Text(a.title).font(Z.an(14)).textCase(.uppercase).lineLimit(2).lineSpacing(-2).frame(width: 130, alignment: .leading)
            }
            .buttonStyle(.plain).accessibilityLabel("Open \(a.title)")
            Mono(a.line([a.yearText, a.owned ? "" : "missing"]))
        }
        .frame(width: 140, alignment: .leading)
        .accessibilityElement(children: .contain)
    }
}

/// Diagonal hatch for missing items.
private struct StripeFill: View {
    var body: some View {
        Canvas { ctx, size in
            var x: CGFloat = -size.height
            while x < size.width {
                var p = Path(); p.move(to: CGPoint(x: x, y: size.height)); p.addLine(to: CGPoint(x: x + size.height, y: 0))
                ctx.stroke(p, with: .color(.black.opacity(0.06)), lineWidth: 6)
                x += 12
            }
        }
    }
}
