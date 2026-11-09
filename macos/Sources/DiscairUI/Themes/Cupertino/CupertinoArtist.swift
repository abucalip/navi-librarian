import SwiftUI

/// Artist: a banner (colour field from the artwork, until real blurred art arrives in M5) with the bold sans name,
/// Top Songs, Albums with the missing ones dashed and a Get button. Mockup: `R.cupertino.artist`.
/// The banner runs edge to edge under the sidebar and toolbar; only the lists below it scroll.
enum CupertinoArtistLayout { static let bannerHeight: CGFloat = 356 }

struct CupertinoArtistBanner: View {
    let state: AppState

    /// Three dots beside the name: Connections and Timeline of this artist. Small, round and centred on the name's line.
    private var artistMenu: some View {
        Menu {
            Button { open(.connections) } label: { Label("Connections", systemImage: "point.3.connected.trianglepath.dotted") }
            Button { open(.timeline) } label: { Label("Timeline", systemImage: "clock") }
        } label: {
            Image(systemName: "ellipsis").font(.system(size: 13, weight: .bold)).rotationEffect(.degrees(90))
                .frame(width: 28, height: 28)
                .background(Circle().fill(.white.opacity(0.22)))
                .contentShape(Circle())
        }
        .menuStyle(.button).buttonStyle(.plain).menuIndicator(.hidden).fixedSize()
        .help("Connections and Timeline of \(state.selectedArtist.name)")
        .accessibilityLabel("More about \(state.selectedArtist.name)")
    }

    private func open(_ screen: Screen) {
        let artist = state.selectedArtist
        state.screen = screen
        Task { if screen == .connections { await state.loadConnections(for: artist) } else { await state.loadTimeline(for: artist) } }
    }
    var body: some View {
        let lib = state.library
        let h = (lib.isLive ? LibraryModel.hue(for: state.selectedArtist.name) : Fixtures.albums[1].hue) / 360
        ZStack(alignment: .topLeading) {
            Color(hue: h, saturation: 0.45, brightness: 0.45)
            RadialGradient(colors: [Color(hue: h, saturation: 0.6, brightness: 0.9).opacity(0.95), .clear],
                           center: UnitPoint(x: 0.2, y: 0.1), startRadius: 0, endRadius: 800)
            RadialGradient(colors: [Color(hue: (h + 0.1).truncatingRemainder(dividingBy: 1), saturation: 0.7, brightness: 0.6).opacity(0.9), .clear],
                           center: UnitPoint(x: 0.9, y: 0.9), startRadius: 0, endRadius: 700)
            if lib.isLive, let cover = lib.artistAlbums.first(where: { !($0.coverArt ?? "").isEmpty }) { BlurredArtwork(album: cover, radius: 24); Color.black.opacity(0.12) }
            LinearGradient(colors: [.black.opacity(0.0), .black.opacity(0.4)], startPoint: .top, endPoint: .bottom)
        }
        .frame(height: CupertinoArtistLayout.bannerHeight)
        .frame(maxWidth: .infinity)
        .overlay(alignment: .topLeading) {
            VStack(alignment: .leading, spacing: 0) {
                BackButton(title: AppState.title(of: state.artistBack), onDark: true) { state.screen = state.artistBack }.padding(.bottom, 14)
                HStack(alignment: .center, spacing: 12) {
                    Text(state.selectedArtist.name).font(.system(size: 60, weight: .bold)).tracking(-1.5).lineLimit(1).minimumScaleFactor(0.5)
                    artistMenu
                }
                Text(state.selectedArtistIsUnowned ? "Not in your library" : lib.isLive ? "\(state.shownArtistOwnedCount) of \(state.shownArtistOwnedCount + state.shownArtistMissingCount) albums owned" : "3 of 5 albums owned · Post-rock, Synth-pop").opacity(0.85).padding(.top, 6).padding(.bottom, 12)
                HStack(spacing: 8) {
                    if !state.selectedArtistIsUnowned {
                    Button { state.actions.play(album: lib.artistAlbums.first ?? Fixtures.albums[1]) } label: { Label("Play", systemImage: "play.fill") }
                        .buttonStyle(CapsuleButtonStyle(primary: true))
                    }
                    Button { } label: { Label("Shuffle", systemImage: "shuffle") }
                        .buttonStyle(CapsuleButtonStyle(translucent: true))
                    Button { } label: { Label("Radio", systemImage: "dot.radiowaves.left.and.right") }
                        .buttonStyle(CapsuleButtonStyle(translucent: true))
                    if state.canShowArtistPaths {
                        Button { state.showArtistPaths() } label: { Label("Paths", systemImage: "point.topleft.down.to.point.bottomright.curvepath") }
                            .buttonStyle(CapsuleButtonStyle(translucent: true))
                            .help("Songs, albums and artists linked to this artist by credits, labels, compositions and scene")
                    }
                }
            }
            .foregroundStyle(.white)
            .padding(.leading, 264).padding(.top, 104)       // 236 sidebar column + 28 margin
        }
        .overlay(alignment: .trailing) {
            ArtistPhoto(name: state.selectedArtist.name, size: 210)
                .overlay(Circle().stroke(.white.opacity(0.85), lineWidth: 4))
                .shadow(color: .black.opacity(0.35), radius: 14, y: 6)
                .padding(.trailing, state.queueOpen ? CupertinoQueueInspector.width + 40 : 40).padding(.top, 60)
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
                if !state.library.isLive {   // top songs need a Navidrome call the client does not have yet
                    Text("Top songs").font(CU.title(20)).padding(.top, 22).padding(.bottom, 10).accessibilityAddTraits(.isHeader)
                    LazyVGrid(columns: [GridItem(.flexible(), spacing: 24), GridItem(.flexible())], spacing: 0) {
                        ForEach(Array(top.enumerated()), id: \.offset) { _, t in songRow(t) }
                    }
                }
                // The bio and the albums on the left; the numbered top songs on the right (the page is the web's, in this theme).
                HStack(alignment: .top, spacing: 32) {
                    VStack(alignment: .leading, spacing: 0) {
                        if state.library.isLive { ArtistBio(state: state) }
                        if state.library.isLive, state.related.loading || state.related.incomplete { relatedStatus }
                        Text("Albums").font(CU.title(20)).padding(.top, 22).padding(.bottom, 10).accessibilityAddTraits(.isHeader)
                        LazyVGrid(columns: [GridItem(.adaptive(minimum: 128, maximum: 128), spacing: 16, alignment: .top)], alignment: .leading, spacing: 18) {
                            ForEach(state.shownArtistAlbums) { a in albumTile(a) }
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    if state.library.isLive { TopSongsPanel(state: state).padding(.top, 18) }
                }
                if state.library.isLive { RelatedSections(state: state, mixed: true) }
            }
            .padding(.horizontal, 28).padding(.bottom, 28)
        }
        .task(id: state.selectedArtist.id) { await state.loadSelectedArtist() }
    }

    @ViewBuilder private var relatedStatus: some View {
        Text(state.related.loading ? "Still looking for the biography and top songs…" : (state.related.lastError ?? "The Librarian had not finished.") + " Reopen the page to ask again.")
            .font(.system(size: 12)).foregroundStyle(CU.muted).padding(.top, 10)
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
            Button { state.open(album: a) } label: {
            CoverView(album: a).frame(width: 128).clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                .opacity(a.owned ? 1 : 0.35)
                .overlay { if !a.owned { RoundedRectangle(cornerRadius: 10, style: .continuous).strokeBorder(Color(white: 0.53), style: StrokeStyle(lineWidth: 2, dash: [5, 4])).padding(-3) } }
                .shadow(color: .black.opacity(a.owned ? 0.2 : 0), radius: 7, y: 4)
            }
            .buttonStyle(.plain).padding(.bottom, 8).accessibilityLabel(a.owned ? "Open \(a.title)" : "\(a.title), missing")
            Text(a.title).fontWeight(.semibold).lineLimit(1)
            Text(a.line([a.yearText, a.owned ? "" : "Missing"])).foregroundStyle(CU.muted)
            if !a.owned {
                Button(state.acquisition.buttonLabel(for: a)) { state.actions.get(album: a) }
                    .buttonStyle(CapsuleButtonStyle(primary: true, small: true)).padding(.top, 7).disabled(!state.acquisition.canGet(a))
                    .help(state.acquisition.detail(for: a))
            }
        }
        .font(.system(size: 13)).frame(width: 128, alignment: .leading)
        .accessibilityElement(children: .contain)
    }
}
