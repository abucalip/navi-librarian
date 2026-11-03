import SwiftUI

/// Home: bold title, Continue listening card, Missing shelf (Get as a red capsule, Save, a labelled Not for me),
/// Recently added grid. Mockup: `R.cupertino.home`.
struct CupertinoHome: View {
    let state: AppState

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Text("Home").font(CU.title(34)).padding(.top, 4).padding(.bottom, 14)
                continueCard
                sectionTitle("Missing from your library", sub: "Recommended for you")
                shelf(Fixtures.albums([7, 8, 9, 10, 11]), missing: true)
                sectionTitle("Recently added", sub: nil)
                shelf(Fixtures.albums([2, 3, 4, 5, 6]), missing: false)
            }
            .padding(.horizontal, 28).padding(.bottom, 28)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
    }

    private var continueCard: some View {
        let a = Fixtures.albums[0]
        return HStack(spacing: 26) {
            CoverView(album: a).frame(width: 190).clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                .shadow(color: .black.opacity(0.2), radius: 7, y: 4)
            VStack(alignment: .leading, spacing: 2) {
                Text("CONTINUE LISTENING").font(.system(size: 11, weight: .bold)).tracking(0.7).foregroundStyle(CU.accent)
                Text(a.title).font(CU.title(30))
                Text("Talk Talk · After the Flood · 3:12 of 9:41").foregroundStyle(CU.muted).padding(.bottom, 12)
                HStack {
                    Button { state.actions.resume() } label: { Label("Resume", systemImage: "play.fill") }
                        .buttonStyle(CapsuleButtonStyle(primary: true))
                    Button("Open album") { state.actions.play(album: a) }
                        .buttonStyle(CapsuleButtonStyle())
                }
            }
            Spacer(minLength: 0)
        }
        .padding(20)
        .background(CU.card, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    private func sectionTitle(_ t: String, sub: String?) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            Text(t).font(CU.title(20))
            if let sub { Text(sub).font(.system(size: 13)).foregroundStyle(CU.muted) }
        }
        .padding(.top, 22).padding(.bottom, 10)
        .accessibilityAddTraits(.isHeader)
    }

    private func shelf(_ albums: [AlbumItem], missing: Bool) -> some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(alignment: .top, spacing: 18) {
                ForEach(albums) { a in tile(a, missing: missing) }
            }
        }
    }

    private func tile(_ a: AlbumItem, missing: Bool) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            CoverView(album: a).frame(width: 156).clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                .shadow(color: .black.opacity(0.2), radius: 7, y: 4).padding(.bottom, 9)
            Text(a.title).fontWeight(.semibold).lineLimit(1)
            Text(missing ? "\(a.artist) · \(a.year)" : a.artist).foregroundStyle(CU.muted).lineLimit(1)
            if missing {
                HStack(spacing: 5) {
                    Button("Get") { state.actions.get(album: a) }.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
                    Button("Save") { state.actions.save(album: a) }.buttonStyle(CapsuleButtonStyle(small: true))
                    Button("Not for me") { state.actions.notForMe(album: a) }
                        .buttonStyle(.plain).font(.system(size: 12)).foregroundStyle(CU.muted).underline().lineLimit(1).fixedSize()
                }
                .padding(.top, 7)
            }
        }
        .frame(width: 156, alignment: .leading)
        .font(.system(size: 13))
        .accessibilityElement(children: .contain)
    }
}

struct CapsuleButtonStyle: ButtonStyle {
    var primary = false
    var small = false
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: small ? 12 : 14, weight: .semibold))
            .lineLimit(1).fixedSize()
            .padding(.horizontal, small ? 10 : 20)
            .frame(minHeight: small ? 24 : 36)
            .foregroundStyle(primary ? Color.white : CU.ink)
            .background(primary ? CU.accent : CU.fill, in: Capsule())
            .opacity(configuration.isPressed ? 0.8 : 1)
    }
}
