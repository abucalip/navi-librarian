import SwiftUI

/// Home: the front page. Lead story is the top recommendation with real Get / Save / Not for me; New this week and
/// Classifieds columns. Mockup: `R.zine.home`.
struct ZineHome: View {
    let state: AppState

    var body: some View {
        let lib = state.library
        let picks = state.visible(lib.missing)
        let lead = picks.first ?? Fixtures.albums[7]   // the top pick; sample data is Tago Mago (never shown once live: see emptyFront)
        let story = lib.isLive ? [lead.reason ?? "Recommended for you by Librarian.",
                                  lead.suggestedTracks.isEmpty ? "" : "Suggested tracks: " + lead.suggestedTracks.prefix(4).joined(separator: ", ") + "."]
                               : [ZineFixtures.leadStory.headline + ZineFixtures.leadStory.p1, ZineFixtures.leadStory.p2]
        let fresh = lib.isLive ? Array(picks.dropFirst().prefix(3)) : Fixtures.albums([8, 9, 10])
        let classifieds = lib.isLive ? Array(picks.dropFirst(4).prefix(4)) : ZineFixtures.classifieds.compactMap { t in Fixtures.albums.first { $0.title == t } }
        if lib.isLive, picks.isEmpty, lib.phase == .loaded { emptyFront(lib) } else {
        VStack(alignment: .leading, spacing: 10) {
        if case .failed(let m) = lib.phase { Mono(m, bold: true).foregroundStyle(Z.red) }
        if lib.phase == .loading { Mono("Loading your library…") }
        if lib.isLive { LinerNoteCard(albums: picks) }
        HStack(alignment: .top, spacing: 22) {
            VStack(alignment: .leading, spacing: 0) {
                HStack(alignment: .top, spacing: 22) {
                    Button { state.open(album: lead) } label: { ZineCover(album: lead, width: 250) }
                        .buttonStyle(.plain).accessibilityLabel("Open \(lead.title)")
                    VStack(alignment: .leading, spacing: 6) {
                        Mono("Lead story · Missing from your library")
                            .foregroundStyle(Z.yellow).padding(.horizontal, 8).padding(.vertical, 1).background(Z.ink)
                        Text(lead.title).font(Z.an(92)).textCase(.uppercase).tracking(0.9).lineLimit(1).minimumScaleFactor(0.5)
                            .lineSpacing(-8).accessibilityAddTraits(.isHeader)
                        Mono(lead.line([lead.artist, lead.yearText, lead.genre])).padding(.bottom, 2)
                    }
                }
                HStack(alignment: .top, spacing: 20) {
                    (lib.isLive ? Text(story[0]) : Text(ZineFixtures.leadStory.headline).bold() + Text(ZineFixtures.leadStory.p1))
                        .frame(maxWidth: .infinity, alignment: .leading)
                    Rectangle().fill(Z.ink).frame(width: 2)
                    Text(story[1]).frame(maxWidth: .infinity, alignment: .leading)
                }
                .font(Z.serif(14.5)).fixedSize(horizontal: false, vertical: true).padding(.top, 16)
                HStack(spacing: 12) {
                    Button(state.acquisition.buttonLabel(for: lead) == "Get" ? "Get this album" : state.acquisition.buttonLabel(for: lead)) { state.actions.get(album: lead) }
                        .buttonStyle(ZineButtonStyle(kind: .yellow)).disabled(!state.acquisition.canGet(lead))
                        .help(state.acquisition.detail(for: lead))
                    Button(state.acquisition.isSaved(lead) ? "Saved" : "Save") { state.actions.save(album: lead) }
                        .buttonStyle(ZineButtonStyle()).disabled(state.acquisition.isSaved(lead))
                    Button("Not for me") { state.actions.notForMe(album: lead) }.buttonStyle(ZineButtonStyle())
                }
                .padding(.top, 14)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            VStack(alignment: .leading, spacing: 14) {
                VStack(alignment: .leading, spacing: 0) {
                    ZineH2(lib.isLive ? "More picks" : "New this week")
                    ForEach(fresh) { a in
                        ZineListRow {
                            HStack(spacing: 10) {
                                Button { state.open(album: a) } label: {
                                    HStack(spacing: 10) {
                                        ZineCover(album: a, width: 44, border: 2, shadow: 3)
                                        VStack(alignment: .leading, spacing: 1) {
                                            Text(a.title).font(Z.an(16)).textCase(.uppercase).lineLimit(1)
                                            Mono(a.artist)
                                        }
                                        Spacer(minLength: 4)
                                    }
                                    .contentShape(Rectangle())
                                }
                                .buttonStyle(.plain)
                                .accessibilityLabel("Open \(a.title) by \(a.artist)")
                                Button(state.acquisition.buttonLabel(for: a)) { state.actions.get(album: a) }
                                    .disabled(!state.acquisition.canGet(a))
                                    .buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
                                    .accessibilityLabel("Get \(a.title)")
                            }
                        }
                    }
                }
                VStack(alignment: .leading, spacing: 0) {
                    ZineH2("Classifieds · Missing", size: 18)
                    ForEach(classifieds) { a in
                        DotRow {
                            Mono(a.title).lineLimit(1)
                        } right: {
                            Button { state.actions.get(album: a) } label: { Mono(state.acquisition.buttonLabel(for: a)) }
                                .buttonStyle(ZineLinkStyle()).disabled(!state.acquisition.canGet(a)).accessibilityLabel("Get \(a.title)")
                        }
                        .padding(.vertical, 1)
                    }
                    Mono("Recently added: " + (lib.isLive ? lib.recent.prefix(2).map(\.title).joined(separator: ", ") : "Dummy, Hounds of Love")).padding(.top, 6).lineLimit(2)
                }
                .padding(.horizontal, 12).padding(.vertical, 10)
                .zBorder(3, dashed: true)
            }
            .frame(width: 400)
        }
        }
        }
    }

    /// A live library with no recommendation to lead with: say why instead of showing a sample story.
    private func emptyFront(_ lib: LibraryModel) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Mono("Lead story · No recommendation today")
                .foregroundStyle(Z.yellow).padding(.horizontal, 8).padding(.vertical, 1).background(Z.ink)
            Text("Nothing to recommend").font(Z.an(70)).textCase(.uppercase).lineLimit(1).accessibilityAddTraits(.isHeader)
            Text(lib.picksNote ?? "The Librarian has no recommendations for you right now.").font(Z.serif(16))
            if lib.picksNote?.contains("Settings") == true {
                Button("Open Settings") { state.screen = .settings }.buttonStyle(ZineButtonStyle(kind: .yellow))
            }
            ZineH2("Recently added").padding(.top, 10)
            ForEach(lib.recent.prefix(5)) { a in
                ZineListRow {
                    Button { state.open(album: a) } label: {
                        HStack(spacing: 10) {
                            ZineCover(album: a, width: 44, border: 2, shadow: 3)
                            VStack(alignment: .leading, spacing: 1) {
                                Text(a.title).font(Z.an(16)).textCase(.uppercase).lineLimit(1)
                                Mono(a.artist)
                            }
                            Spacer()
                        }
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain).accessibilityLabel("Open \(a.title) by \(a.artist)")
                }
            }
        }
    }
}
