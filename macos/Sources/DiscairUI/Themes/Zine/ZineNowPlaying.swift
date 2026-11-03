import SwiftUI

/// Now Playing: a centre spread. Halftone cover on the left page, synced lyrics set as article columns on the
/// right. Mockup: `R.zine.now`.
struct ZineNowPlaying: View {
    let state: AppState

    var body: some View {
        let a = Fixtures.albums[0]
        let lyr = ZineFixtures.lyrics
        HStack(alignment: .top, spacing: 26) {
            VStack(alignment: .leading, spacing: 0) {
                Mono("Centre spread · Now playing").padding(.bottom, 6)
                ZineCover(album: a, width: 350)
                    .overlay { Halftone().padding(3) }
                Text("After the Flood").font(Z.an(54)).textCase(.uppercase).tracking(0.5).lineLimit(1).minimumScaleFactor(0.5)
                    .padding(.top, 16).accessibilityAddTraits(.isHeader)
                Mono("Talk Talk · Laughing Stock · 3 of 6 · FLAC 16/44")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            Rectangle().fill(Z.ink).frame(width: 6)
            VStack(alignment: .leading, spacing: 0) {
                Mono("Lyrics · synced").padding(.bottom, 6)
                HStack(alignment: .top, spacing: 20) {
                    column([0, 1, 2], lyr)
                    Rectangle().fill(Z.ink).frame(width: 2)
                    column([3, 4], lyr)
                }
                .fixedSize(horizontal: false, vertical: true)
                HStack(spacing: 10) {
                    Button("EQ · Custom") { }.buttonStyle(ZineButtonStyle())
                    Button("Crossfade 6 s") { }.buttonStyle(ZineButtonStyle())
                    Button("Quality · Original") { }.buttonStyle(ZineButtonStyle())
                    Button("Queue") { state.screen = .queue }.buttonStyle(ZineButtonStyle(kind: .yellow))
                }
                .padding(.top, 14)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    /// One text column; line 2 is the current line (yellow highlight), the rest are dimmed.
    private func column(_ idx: [Int], _ lyr: [String]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            ForEach(idx, id: \.self) { i in
                let now = i == 2
                Text(lyr[i]).font(Z.serif(24, italic: true)).lineSpacing(2)
                    .padding(.horizontal, now ? 4 : 0).background(now ? Z.yellow : .clear)
                    .opacity(now ? 1 : 0.45)
                    .accessibilityAddTraits(now ? .isSelected : [])
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
