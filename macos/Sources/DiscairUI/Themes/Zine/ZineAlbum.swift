import SwiftUI

/// Album: an article. Giant headline, byline, a contents box where the missing song is a dashed coupon with its
/// own Get. Mockup: `R.zine.album`.
struct ZineAlbum: View {
    let state: AppState

    var body: some View {
        let a = state.selectedAlbum
        VStack(alignment: .leading, spacing: 0) {
            Text(a.title).font(Z.an(118)).textCase(.uppercase).tracking(1.2).lineLimit(1).minimumScaleFactor(0.4)
                .padding(.bottom, 4).accessibilityAddTraits(.isHeader)
            Rectangle().fill(Z.ink).frame(height: 4)
            byline(a)
            HStack(alignment: .top, spacing: 22) {
                VStack(alignment: .leading, spacing: 0) {
                    ZineCover(album: a, width: 260)
                    Rectangle().fill(Z.ink).frame(height: 4).padding(.top, 20)
                    Text(ZineFixtures.albumPull).font(Z.serif(19, italic: true)).padding(.top, 6)
                }
                .frame(width: 260)
                VStack(alignment: .leading, spacing: 8) {
                    (Text(ZineFixtures.albumLede).bold() + Text(ZineFixtures.albumBody1))
                    Text(ZineFixtures.albumBody2)
                }
                .font(Z.serif(14.5)).frame(maxWidth: .infinity, alignment: .topLeading)
                contents(a).frame(maxWidth: .infinity)
            }
        }
    }

    private func byline(_ a: AlbumItem) -> some View {
        HStack(spacing: 26) {
            Mono("By \(a.artist)"); Mono("\(a.year)"); Mono(a.genre); Mono("6 songs · 41 min")
            ZineBadge(a.format.isEmpty ? "Not owned" : a.format)
            Spacer()
            HStack(spacing: 10) {
                Button { state.actions.play(album: a) } label: { Label("Play", systemImage: "play.fill") }
                    .buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
                Button("Save") { state.actions.save(album: a) }.buttonStyle(ZineButtonStyle(small: true))
                Button("Get album") { state.actions.get(album: a) }.buttonStyle(ZineButtonStyle(small: true))
            }
        }
        .padding(.vertical, 6)
        .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 2) }
        .padding(.bottom, 14)
    }

    private func contents(_ a: AlbumItem) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            ZineH2("Contents", size: 20)
            ForEach(Array(Fixtures.tracks.enumerated()), id: \.element.id) { i, t in
                if t.owned {
                    DotRow {
                        HStack(spacing: 6) { Text("\(i + 1)").font(Z.an(15)); Text(t.title).font(Z.serif(14)) }
                    } right: { Text(t.duration).font(Z.serif(14)) }
                    .padding(.vertical, 3)
                    .accessibilityElement(children: .combine)
                } else {
                    HStack {
                        Mono("\(i + 1) \(t.title) · not owned")
                        Spacer(minLength: 6)
                        Button("Get song") { state.actions.get(album: a) }.buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
                    }
                    .padding(.horizontal, 10).padding(.vertical, 6)
                    .background(Z.yellow).zBorder(3, dashed: true)
                    .padding(.vertical, 4)
                }
            }
            if let p = Fixtures.tracks.firstIndex(where: { $0.playing }) {
                Mono("▶ Now playing: \(p + 1) \(Fixtures.tracks[p].title)").padding(.top, 6)
            }
        }
        .padding(.horizontal, 12).padding(.vertical, 10)
        .background(Z.white).zBorder(3)
    }
}
