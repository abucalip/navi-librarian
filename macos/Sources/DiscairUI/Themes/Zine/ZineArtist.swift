import CoreText
import SwiftUI

/// Artist: a magazine cover. The name set huge and cropped, cover lines from top songs, back issues owned solid
/// and missing dashed. Mockup: `R.zine.artist`.
struct ZineArtist: View {
    let state: AppState
    static let bannerHeight: CGFloat = 215
    static let nameSize: CGFloat = 240
    static var nameAscent: CGFloat {
        _ = Z.fontsRegistered
        return CTFontGetAscent(CTFontCreateWithName("Anton-Regular" as CFString, nameSize, nil))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ZStack(alignment: .topLeading) {
                // The whole name is shown (owner review: the cropped version cut the letters off). The text box is placed
                // from the font's own ascent so the baseline sits 10 pt above the rule.
                Text("Talk Talk").font(Z.an(Self.nameSize)).textCase(.uppercase).lineLimit(1).fixedSize()
                    .offset(x: -2, y: Self.bannerHeight - 10 - Self.nameAscent).accessibilityAddTraits(.isHeader)
                VStack(alignment: .leading, spacing: 2) {
                    Mono("Cover lines")
                    ForEach(ZineFixtures.coverLines, id: \.self) { Text($0).font(Z.an(17)).textCase(.uppercase) }
                }
                .padding(.horizontal, 12).padding(.vertical, 10)
                .background(Z.yellow).zBorder(3)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topTrailing).padding(.trailing, 20).padding(.top, 10)
            }
            .frame(height: Self.bannerHeight, alignment: .topLeading).clipped()
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }

            HStack(spacing: 20) {
                Mono("3 of 5 albums owned"); Mono("2 missing"); Mono("Post-rock · Synth-pop")
                Spacer()
                HStack(spacing: 10) {
                    Button("Play") { state.actions.play(album: Fixtures.albums[0]) }.buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
                    Button("Radio") { }.buttonStyle(ZineButtonStyle(small: true))
                    Button("Get both missing") {
                        for a in Fixtures.albums(ZineFixtures.backIssues) where !a.owned { state.actions.get(album: a) }
                    }
                    .buttonStyle(ZineButtonStyle(small: true))
                }
            }
            .padding(.vertical, 6)

            HStack(alignment: .top, spacing: 22) {
                VStack(alignment: .leading, spacing: 0) {
                    ZineH2("Back issues", size: 20)
                    HStack(alignment: .top, spacing: 18) {
                        ForEach(Fixtures.albums(ZineFixtures.backIssues)) { a in issue(a) }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
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
    }

    private func issue(_ a: AlbumItem) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            if a.owned {
                Button { state.selectedAlbum = a; state.screen = .album } label: { ZineCover(album: a, width: 130) }
                    .buttonStyle(.plain).accessibilityLabel("Open \(a.title)")
            } else {
                VStack(spacing: 4) {
                    Mono("Missing").multilineTextAlignment(.center)
                    Button("Get") { state.actions.get(album: a) }.buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
                        .accessibilityLabel("Get \(a.title)")
                }
                .frame(width: 130, height: 130)
                .background(StripeFill())
                .zBorder(3, dashed: true)
            }
            Button { state.selectedAlbum = a; state.screen = .album } label: {
                Text(a.title).font(Z.an(14)).textCase(.uppercase).lineLimit(2).lineSpacing(-2).frame(width: 130, alignment: .leading)
            }
            .buttonStyle(.plain).accessibilityLabel("Open \(a.title)")
            Mono("\(a.year)\(a.owned ? "" : " · missing")")
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
