import SwiftUI

/// The album spread under the article: liner notes as running text, credits as a masthead box, facts and links,
/// "Also in this issue" for similar artists. No mockup exists; it reuses the Album page's own parts.
struct ZineAlbumSpread: View {
    let state: AppState

    var body: some View {
        let spread = state.spread
        VStack(alignment: .leading, spacing: 0) {
            Rectangle().fill(Z.ink).frame(height: 4).padding(.top, 22)
            ZineH2("Album spread", size: 26).padding(.top, 8).accessibilityAddTraits(.isHeader)
            if spread.loading {
                Mono("Loading…").padding(.top, 8)
            } else if let c = spread.content, !c.isEmpty {
                HStack(alignment: .top, spacing: 22) {
                    VStack(alignment: .leading, spacing: 8) {
                        if let notes = c.notes {
                            ZineH2("Liner notes", size: 20)
                            Text(notes).font(Z.serif(14.5)).textSelection(.enabled)
                        }
                        if !c.similar.isEmpty {
                            ZineH2("Also in this issue", size: 20).padding(.top, 8)
                            ForEach(c.similar) { s in
                                if s.inLibrary {
                                    Button { state.openArtist(named: s.name) } label: { Mono("→ \(s.name)") }.buttonStyle(.plain)
                                        .accessibilityLabel("Open artist \(s.name)")
                                } else { Mono(s.name) }
                            }
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .topLeading)
                    VStack(alignment: .leading, spacing: 0) {
                        if !c.credits.isEmpty {
                            ZineH2("Credits", size: 20)
                            ForEach(c.credits) { g in
                                DotRow { Text(g.title).font(Z.serif(14)) } right: { Text(g.names.joined(separator: ", ")).font(Z.serif(14)) }
                                    .padding(.vertical, 3).accessibilityElement(children: .combine)
                            }
                        }
                        if !c.facts.isEmpty {
                            ZineH2("The facts", size: 20).padding(.top, c.credits.isEmpty ? 0 : 12)
                            ForEach(c.facts) { f in
                                DotRow { Text(f.label).font(Z.serif(14)) } right: { Text(f.value).font(Z.serif(14)).textSelection(.enabled) }
                                    .padding(.vertical, 3).accessibilityElement(children: .combine)
                            }
                        }
                        HStack(spacing: 16) {
                            if let u = c.musicBrainzURL { Link(destination: u) { Mono("MusicBrainz ↗") } }
                            if let u = c.lastFmURL { Link(destination: u) { Mono("Last.fm ↗") } }
                        }
                        .padding(.top, 8)
                    }
                    .padding(.horizontal, 12).padding(.vertical, 10).background(Z.white).zBorder(3)
                    .frame(maxWidth: .infinity)
                }
                .padding(.top, 8)
            } else {
                Mono("Navidrome has no notes, credits or links for this album").padding(.top, 8)
            }
            ZineH2("Reviews", size: 20).padding(.top, 12)
            Mono(AlbumSpread.reviewsNote)
        }
    }
}
