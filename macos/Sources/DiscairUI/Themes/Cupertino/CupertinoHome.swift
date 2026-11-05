import SwiftUI

/// Home: bold title, Continue listening card, Missing shelf (Get as a red capsule, Save, a labelled Not for me),
/// Recently added grid. Mockup: `R.cupertino.home`.
struct CupertinoHome: View {
    let state: AppState

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Text("Home").font(CU.title(34)).padding(.top, 4).padding(.bottom, 14)
                if !state.library.isLive { continueCard }   // needs playback history, which arrives with the audio engine
                if case .failed(let m) = state.library.phase { Text(m).foregroundStyle(CU.accent).padding(.bottom, 8) }
                if state.library.phase == .loading { Text("Loading your library…").foregroundStyle(CU.muted).padding(.bottom, 8) }
                sectionTitle("Missing from your library", sub: "Recommended for you")
                if state.library.isLive, state.visible(state.library.missing).isEmpty, state.library.phase == .loaded {
                    HStack(spacing: 12) {
                        Text(state.library.picksNote ?? "Nothing is missing from your recommendations right now.").foregroundStyle(CU.muted)
                        if state.library.picksNote?.contains("Settings") == true {
                            Button("Open Settings") { state.screen = .settings }.buttonStyle(CapsuleButtonStyle(small: true))
                        }
                    }
                } else {
                    shelf(state.visible(state.library.missing), missing: true)
                }
                sectionTitle("Recently added", sub: nil)
                shelf(state.library.recent, missing: false)
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
                    Button("Open album") { state.open(album: a) }
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
            Button { state.open(album: a) } label: {
                CoverView(album: a).frame(width: 156).clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    .shadow(color: .black.opacity(0.2), radius: 7, y: 4)
            }
            .buttonStyle(.plain).padding(.bottom, 9).accessibilityLabel(a.owned ? "Open \(a.title)" : "Open \(a.title), not in your library")
            Text(a.title).fontWeight(.semibold).lineLimit(1)
            Text(missing ? a.line([a.artist, a.yearText]) : a.artist).foregroundStyle(CU.muted).lineLimit(1)
            if missing {
                // Get, Save and Not for me are all real buttons with text labels; the third sits on its own row to fit the tile.
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 5) {
                        Button(state.acquisition.buttonLabel(for: a)) { state.actions.get(album: a) }
                            .buttonStyle(CapsuleButtonStyle(primary: true, small: true)).disabled(!state.acquisition.canGet(a))
                            .help(state.acquisition.detail(for: a)).accessibilityHint(state.acquisition.detail(for: a))
                        Button(state.acquisition.isSaved(a) ? "Saved" : "Save") { state.actions.save(album: a) }
                            .buttonStyle(CapsuleButtonStyle(small: true)).disabled(state.acquisition.isSaved(a))
                    }
                    Button("Not for me") { state.actions.notForMe(album: a) }
                        .buttonStyle(CapsuleButtonStyle(small: true, outlined: true))
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
    var outlined = false
    var large = false
    /// White text on a 28% white fill, for buttons over a banner image.
    var translucent = false
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: small ? 12 : 14, weight: .semibold))
            .lineLimit(1).fixedSize()
            .padding(.horizontal, small ? 10 : (large ? 24 : 20))
            .frame(minHeight: small ? 24 : (large ? 40 : 36))
            .foregroundStyle(primary || translucent ? Color.white : (outlined ? CU.muted : CU.ink))
            .background(primary ? CU.accent : (translucent ? Color.white.opacity(0.28) : (outlined ? Color.clear : CU.fill)), in: Capsule())
            .overlay { if outlined { Capsule(style: .circular).inset(by: 0.75).stroke(CU.muted, lineWidth: 1.5) } }
            .opacity(configuration.isPressed ? 0.8 : 1)
    }
}
