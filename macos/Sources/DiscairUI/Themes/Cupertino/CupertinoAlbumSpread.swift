import SwiftUI

/// The album spread under the track table: liner notes, credits, MusicBrainz data, similar artists, reviews.
/// A part with nothing to show is left out. No mockup exists; it reuses the Album screen's own parts.
struct CupertinoAlbumSpread: View {
    enum Part { case notes, credits, reviews }
    let state: AppState
    let part: Part

    var body: some View {
        let spread = state.spread
        VStack(alignment: .leading, spacing: 0) {
            switch part {
            case .reviews: reviews
            case .notes, .credits:
                if spread.loading {
                    Text("Loading…").foregroundStyle(CU.muted)
                } else if let c = spread.content, !c.isEmpty {
                    if part == .notes { notes(c) } else { credits(c) }
                } else {
                    Text("Navidrome has no notes, credits or links for this album.").foregroundStyle(CU.muted)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    /// Liner notes first, then the album's facts and the links at the bottom.
    @ViewBuilder private func notes(_ c: AlbumSpreadContent) -> some View {
        if let notes = c.notes {
            VStack(alignment: .leading, spacing: 8) {
                Text(notes).font(.system(size: 13.5)).lineSpacing(3).textSelection(.enabled)
                if let src = c.notesSource, !src.isEmpty {
                    if let u = c.notesURL { Link(src, destination: u).font(.system(size: 11.5)) }
                    else { Text(src).font(.system(size: 11.5)).foregroundStyle(CU.muted) }
                }
            }
        } else if c.facts.isEmpty && c.musicBrainzURL == nil && c.lastFmURL == nil {
            Text("No liner notes for this album.").foregroundStyle(CU.muted)
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
    }

    /// The extended credits from the knowledge base, then the credits Navidrome holds for the album.
    @ViewBuilder private func credits(_ c: AlbumSpreadContent) -> some View {
        let extended = state.albumCredits
        if !extended.groups.isEmpty {
            creditList(extended.groups.map { ($0.role, $0.names) })
            if extended.truncated { Text("The list is cut short; the knowledge base holds more.").font(.system(size: 12)).foregroundStyle(CU.muted).padding(.top, 8) }
        } else if !c.credits.isEmpty {
            creditList(c.credits.map { ($0.title, $0.names) })
        } else if extended.loading {
            Text("Loading credits…").foregroundStyle(CU.muted)
        } else {
            Text("No credits for this album.").foregroundStyle(CU.muted)
        }
    }

    private func creditList(_ rows: [(String, [String])]) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            ForEach(Array(rows.enumerated()), id: \.offset) { _, g in
                HStack(alignment: .firstTextBaseline, spacing: 12) {
                    Text(g.0).foregroundStyle(CU.muted).frame(width: 150, alignment: .leading)
                    Text(g.1.joined(separator: ", ")).textSelection(.enabled)
                }
                .font(.system(size: 13)).accessibilityElement(children: .combine)
            }
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
