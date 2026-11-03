import SwiftUI

/// Artist: a banner (colour field from the artwork, until real blurred art arrives in M5) with the bold sans name,
/// Top Songs, Albums with the missing ones dashed and a Get button. Mockup: `R.cupertino.artist`.
/// The banner runs edge to edge under the sidebar and toolbar; only the lists below it scroll.
enum CupertinoArtistLayout { static let bannerHeight: CGFloat = 356 }

struct CupertinoArtistBanner: View {
    let state: AppState
    var body: some View {
        let a = Fixtures.albums[1]
        let h = a.hue / 360
        ZStack(alignment: .topLeading) {
            Color(hue: h, saturation: 0.45, brightness: 0.45)
            RadialGradient(colors: [Color(hue: h, saturation: 0.6, brightness: 0.9).opacity(0.95), .clear],
                           center: UnitPoint(x: 0.2, y: 0.1), startRadius: 0, endRadius: 800)
            RadialGradient(colors: [Color(hue: (h + 0.1).truncatingRemainder(dividingBy: 1), saturation: 0.7, brightness: 0.6).opacity(0.9), .clear],
                           center: UnitPoint(x: 0.9, y: 0.9), startRadius: 0, endRadius: 700)
            LinearGradient(colors: [.black.opacity(0.05), .black.opacity(0.45)], startPoint: .top, endPoint: .bottom)
        }
        .frame(height: CupertinoArtistLayout.bannerHeight)
        .frame(maxWidth: .infinity)
        .overlay(alignment: .topLeading) {
            VStack(alignment: .leading, spacing: 0) {
                Text("Talk Talk").font(.system(size: 60, weight: .bold)).tracking(-1.5)
                Text("3 of 5 albums owned · Post-rock, Synth-pop").opacity(0.85).padding(.top, 6).padding(.bottom, 12)
                HStack(spacing: 8) {
                    Button { state.actions.play(album: Fixtures.albums[1]) } label: { Label("Play", systemImage: "play.fill") }
                        .buttonStyle(CapsuleButtonStyle(primary: true))
                    Button { } label: { Label("Shuffle", systemImage: "shuffle") }
                        .buttonStyle(CapsuleButtonStyle(translucent: true))
                    Button { } label: { Label("Radio", systemImage: "dot.radiowaves.left.and.right") }
                        .buttonStyle(CapsuleButtonStyle(translucent: true))
                }
            }
            .foregroundStyle(.white)
            .padding(.leading, 264).padding(.top, 150)       // 236 sidebar column + 28 margin
        }
        .accessibilityElement(children: .contain)
    }
}

struct CupertinoArtist: View {
    let state: AppState
    private let top: [(title: String, album: Int, sub: String, missing: Bool)] = [
        ("Life's What You Make It", 11, "The Colour of Spring", true), ("Such a Shame", 13, "Album", false),
        ("Myrrhman", 0, "Album", false), ("Talk Talk", 12, "Album", false),
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Text("Top songs").font(CU.title(20)).padding(.top, 22).padding(.bottom, 10).accessibilityAddTraits(.isHeader)
                LazyVGrid(columns: [GridItem(.flexible(), spacing: 24), GridItem(.flexible())], spacing: 0) {
                    ForEach(Array(top.enumerated()), id: \.offset) { _, t in songRow(t) }
                }
                Text("Albums").font(CU.title(20)).padding(.top, 22).padding(.bottom, 10).accessibilityAddTraits(.isHeader)
                HStack(alignment: .top, spacing: 16) {
                    ForEach(Fixtures.albums([12, 13, 11, 1, 0])) { a in albumTile(a) }
                }
            }
            .padding(.horizontal, 28).padding(.bottom, 28)
        }
    }

    private func songRow(_ t: (title: String, album: Int, sub: String, missing: Bool)) -> some View {
        HStack(spacing: 11) {
            CoverView(album: Fixtures.albums[t.album]).frame(width: 40).clipShape(RoundedRectangle(cornerRadius: 5, style: .continuous))
            VStack(alignment: .leading, spacing: 0) {
                Text(t.title).fontWeight(.semibold).lineLimit(1)
                Text(t.sub).font(.system(size: 12)).foregroundStyle(CU.muted).lineLimit(1)
            }
            Spacer(minLength: 4)
            if t.missing {
                Button("Get") { state.actions.get(album: Fixtures.albums[t.album]) }.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
            } else {
                Text("4:49").font(.system(size: 12)).monospacedDigit().foregroundStyle(CU.muted)
            }
        }
        .font(.system(size: 13)).padding(.horizontal, 8).padding(.vertical, 6)
        .accessibilityElement(children: .combine)
    }

    private func albumTile(_ a: AlbumItem) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            CoverView(album: a).frame(width: 128).clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                .opacity(a.owned ? 1 : 0.35)
                .overlay { if !a.owned { RoundedRectangle(cornerRadius: 10, style: .continuous).strokeBorder(Color(white: 0.53), style: StrokeStyle(lineWidth: 2, dash: [5, 4])).padding(-3) } }
                .shadow(color: .black.opacity(a.owned ? 0.2 : 0), radius: 7, y: 4)
                .padding(.bottom, 8)
            Text(a.title).fontWeight(.semibold).lineLimit(1)
            Text(a.owned ? String(a.year) : "\(a.year) · Missing").foregroundStyle(CU.muted)
            if !a.owned {
                Button("Get") { state.actions.get(album: a) }.buttonStyle(CapsuleButtonStyle(primary: true, small: true)).padding(.top, 7)
            }
        }
        .font(.system(size: 13)).frame(width: 128, alignment: .leading)
        .accessibilityElement(children: .contain)
    }
}
