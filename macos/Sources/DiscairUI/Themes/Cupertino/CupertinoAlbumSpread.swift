import SwiftUI

/// The album spread under the track table: liner notes, credits, MusicBrainz data, similar artists, reviews.
/// A part with nothing to show is left out. No mockup exists; it reuses the Album screen's own parts.
struct CupertinoAlbumSpread: View {
    let state: AppState

    var body: some View {
        let spread = state.spread
        VStack(alignment: .leading, spacing: 0) {
            Text("Album spread").font(CU.title(20)).padding(.top, 26).padding(.bottom, 10).accessibilityAddTraits(.isHeader)
            if spread.loading {
                Text("Loading…").foregroundStyle(CU.muted)
            } else if let c = spread.content, !c.isEmpty {
                if let notes = c.notes {
                    section("Liner notes") {
                        Text(notes).font(.system(size: 13.5)).lineSpacing(3).textSelection(.enabled)
                        if let src = c.notesSource, !src.isEmpty {
                            if let u = c.notesURL { Link(src, destination: u).font(.system(size: 11.5)) }
                            else { Text(src).font(.system(size: 11.5)).foregroundStyle(CU.muted) }
                        }
                    }
                }
                if !c.credits.isEmpty {
                    section("Credits") {
                        VStack(alignment: .leading, spacing: 6) {
                            ForEach(c.credits) { g in
                                HStack(alignment: .firstTextBaseline, spacing: 12) {
                                    Text(g.title).foregroundStyle(CU.muted).frame(width: 150, alignment: .leading)
                                    Text(g.names.joined(separator: ", "))
                                }
                                .font(.system(size: 13)).accessibilityElement(children: .combine)
                            }
                        }
                    }
                }
                if !c.facts.isEmpty || c.musicBrainzURL != nil || c.lastFmURL != nil {
                    section("MusicBrainz and links") {
                        VStack(alignment: .leading, spacing: 6) {
                            ForEach(c.facts) { f in
                                HStack(alignment: .firstTextBaseline, spacing: 12) {
                                    Text(f.label).foregroundStyle(CU.muted).frame(width: 150, alignment: .leading)
                                    Text(f.value).textSelection(.enabled)
                                }
                                .font(.system(size: 13)).accessibilityElement(children: .combine)
                            }
                            HStack(spacing: 16) {
                                if let u = c.musicBrainzURL { Link("Open on MusicBrainz", destination: u) }
                                if let u = c.lastFmURL { Link("Open on Last.fm", destination: u) }
                            }
                            .font(.system(size: 13)).padding(.top, 2)
                        }
                    }
                }
                if !c.similar.isEmpty {
                    section("Similar artists") {
                        HStack(spacing: 8) {
                            ForEach(c.similar) { s in
                                if s.inLibrary {
                                    Button(s.name) { state.openArtist(named: s.name) }.buttonStyle(CapsuleButtonStyle(small: true))
                                        .accessibilityLabel("Open artist \(s.name)")
                                } else {
                                    Text(s.name).font(.system(size: 12, weight: .medium)).padding(.horizontal, 10).padding(.vertical, 3)
                                        .foregroundStyle(CU.muted).background(CU.fill, in: Capsule())
                                }
                            }
                        }
                    }
                }
            } else {
                Text("Navidrome has no notes, credits or links for this album.").foregroundStyle(CU.muted)
            }
            section("Reviews") { reviews }
        }
    }

    @ViewBuilder private var reviews: some View {
        switch state.spread.reviews {
        case .idle: Text("Reviews need a Librarian sign-in.").foregroundStyle(CU.muted)
        case .loading: Text("Loading reviews…").foregroundStyle(CU.muted)
        case .failed:
            HStack { Text("Reviews could not be loaded.").foregroundStyle(CU.muted); retryButton }
        case .loaded(let list, let retryable):
            VStack(alignment: .leading, spacing: 10) {
                if list.isEmpty { Text(retryable ? "No reviews found. Some sources did not answer." : "No reviews found for this album.").foregroundStyle(CU.muted) }
                ForEach(list) { r in
                    VStack(alignment: .leading, spacing: 3) {
                        Text("\u{201C}\(r.quote)\u{201D}").font(.system(size: 13.5)).lineSpacing(3).textSelection(.enabled)
                        Link("Read the full review at \(r.source)", destination: r.url).font(.system(size: 12))
                    }
                    .accessibilityElement(children: .combine)
                }
                if retryable && !list.isEmpty { Text("Some sources did not answer.").font(.system(size: 12)).foregroundStyle(CU.muted) }
                if retryable { retryButton }
            }
        }
    }

    private var retryButton: some View {
        Button("Try again") { Task { await state.retrySpreadReviews() } }.buttonStyle(CapsuleButtonStyle(small: true))
    }

    private func section<C: View>(_ title: String, @ViewBuilder _ body: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.system(size: 12, weight: .semibold)).foregroundStyle(CU.muted).textCase(.uppercase)
                .accessibilityAddTraits(.isHeader)
            body()
        }
        .padding(.top, 14).frame(maxWidth: .infinity, alignment: .leading)
    }
}
