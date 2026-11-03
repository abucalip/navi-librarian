import SwiftUI

/// Home: the front page. Lead story is the top recommendation with real Get / Save / Not for me; New this week and
/// Classifieds columns. Mockup: `R.zine.home`.
struct ZineHome: View {
    let state: AppState

    var body: some View {
        let lead = Fixtures.albums[7]   // Tago Mago, missing
        HStack(alignment: .top, spacing: 22) {
            VStack(alignment: .leading, spacing: 0) {
                HStack(alignment: .top, spacing: 22) {
                    ZineCover(album: lead, width: 250)
                    VStack(alignment: .leading, spacing: 6) {
                        Mono("Lead story · Missing from your library")
                            .foregroundStyle(Z.yellow).padding(.horizontal, 8).padding(.vertical, 1).background(Z.ink)
                        Text(lead.title).font(Z.an(92)).textCase(.uppercase).tracking(0.9).lineLimit(1).minimumScaleFactor(0.5)
                            .lineSpacing(-8).accessibilityAddTraits(.isHeader)
                        Mono("\(lead.artist) · \(lead.year) · \(lead.genre)").padding(.bottom, 2)
                    }
                }
                HStack(alignment: .top, spacing: 20) {
                    (Text(ZineFixtures.leadStory.headline).bold() + Text(ZineFixtures.leadStory.p1))
                        .frame(maxWidth: .infinity, alignment: .leading)
                    Rectangle().fill(Z.ink).frame(width: 2)
                    Text(ZineFixtures.leadStory.p2).frame(maxWidth: .infinity, alignment: .leading)
                }
                .font(Z.serif(14.5)).fixedSize(horizontal: false, vertical: true).padding(.top, 16)
                HStack(spacing: 12) {
                    Button("Get this album") { state.actions.get(album: lead) }.buttonStyle(ZineButtonStyle(kind: .yellow))
                    Button("Save") { state.actions.save(album: lead) }.buttonStyle(ZineButtonStyle())
                    Button("Not for me") { state.actions.notForMe(album: lead) }.buttonStyle(ZineLinkStyle()).padding(.leading, 4)
                }
                .padding(.top, 14)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            VStack(alignment: .leading, spacing: 14) {
                VStack(alignment: .leading, spacing: 0) {
                    ZineH2("New this week")
                    ForEach(Fixtures.albums([8, 9, 10])) { a in
                        ZineListRow {
                            HStack(spacing: 10) {
                                ZineCover(album: a, width: 44, border: 2, shadow: 3)
                                VStack(alignment: .leading, spacing: 1) {
                                    Text(a.title).font(Z.an(16)).textCase(.uppercase).lineLimit(1)
                                    Mono(a.artist)
                                }
                                Spacer(minLength: 4)
                                Button("Get") { state.actions.get(album: a) }
                                    .buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
                                    .accessibilityLabel("Get \(a.title)")
                            }
                        }
                    }
                }
                VStack(alignment: .leading, spacing: 0) {
                    ZineH2("Classifieds · Missing", size: 18)
                    ForEach(ZineFixtures.classifieds, id: \.self) { t in
                        DotRow {
                            Mono(t)
                        } right: {
                            Button { if let a = Fixtures.albums.first(where: { $0.title == t }) { state.actions.get(album: a) } } label: { Mono("Get") }
                                .buttonStyle(ZineLinkStyle()).accessibilityLabel("Get \(t)")
                        }
                        .padding(.vertical, 1)
                    }
                    Mono("Recently added: Dummy, Hounds of Love").padding(.top, 6)
                }
                .padding(.horizontal, 12).padding(.vertical, 10)
                .zBorder(3, dashed: true)
            }
            .frame(width: 400)
        }
    }
}
