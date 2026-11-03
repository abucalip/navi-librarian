import SwiftUI

/// Queue: a printed running order with dotted leaders; Radio from this is a classified ad. Mockup: `R.zine.queue`.
struct ZineQueue: View {
    let state: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .bottom, spacing: 20) {
                Text("Running Order").font(Z.an(78)).textCase(.uppercase).tracking(0.8).lineLimit(1).accessibilityAddTraits(.isHeader)
                Mono("8 songs · 52 min").padding(.bottom, 8)
                Spacer()
                HStack(spacing: 10) {
                    Button("Save queue") { }.buttonStyle(ZineButtonStyle())
                    Button("Clear") { }.buttonStyle(ZineButtonStyle())
                }
                .padding(.bottom, 8)
            }
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }
            HStack(alignment: .top, spacing: 26) {
                VStack(spacing: 0) {
                    ForEach(Array(ZineFixtures.runningOrder.enumerated()), id: \.offset) { i, row in
                        let on = i == ZineFixtures.playingIndex
                        let a = Fixtures.albums[row.album]
                        ZineListRow(highlight: on) {
                            HStack(spacing: 10) {
                                Text("\(i + 1)").font(Z.an(22)).lineLimit(1).fixedSize().frame(width: 36, alignment: .leading)
                                ZineCover(album: a, width: 44, border: 2, shadow: 3)
                                VStack(alignment: .leading, spacing: 1) {
                                    Text(row.title).font(Z.an(16)).textCase(.uppercase).lineLimit(1)
                                    Mono(a.artist)
                                }
                                Spacer(minLength: 4)
                                Mono((on ? "▶ playing · " : "") + row.time)
                                Mono("≡").accessibilityHidden(true)
                            }
                        }
                        .accessibilityElement(children: .combine)
                        .accessibilityLabel("\(i + 1). \(row.title), \(a.artist), \(row.time)\(on ? ", playing" : "")")
                    }
                }
                .frame(maxWidth: .infinity)
                .layoutPriority(1.5)
                VStack(alignment: .leading, spacing: 14) {
                    VStack(alignment: .leading, spacing: 8) {
                        ZineH2("Classified · Radio", size: 20)
                        Text("Wanted: more like this. Keeps playing similar artists picked by Librarian.").font(Z.serif(14))
                        Button("Start radio from this") { }.buttonStyle(ZineButtonStyle())
                    }
                    .padding(.horizontal, 12).padding(.vertical, 10).frame(maxWidth: .infinity, alignment: .leading)
                    .background(Z.yellow).zBorder(3)
                    VStack(alignment: .leading, spacing: 0) {
                        ZineH2("Saved queues", size: 20)
                        DotRow { Mono("Late night") } right: { Mono("24") }
                        DotRow { Mono("Sunday morning") } right: { Mono("17") }.padding(.top, 2)
                    }
                    .padding(.horizontal, 12).padding(.vertical, 10).frame(maxWidth: .infinity, alignment: .leading)
                    .background(Z.white).zBorder(3)
                    VStack(alignment: .leading, spacing: 0) {
                        ZineH2("Earlier today", size: 20)
                        Mono("Glory Box · Roygbiv · Cloudbusting")
                    }
                    .padding(.horizontal, 12).padding(.vertical, 10).frame(maxWidth: .infinity, alignment: .leading)
                    .zBorder(3, dashed: true)
                }
                .frame(maxWidth: .infinity)
            }
        }
    }
}
