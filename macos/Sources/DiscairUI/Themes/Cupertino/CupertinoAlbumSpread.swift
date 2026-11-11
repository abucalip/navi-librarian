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
                    Text("Loading…").foregroundStyle(CU.textSecondary)
                } else if let c = spread.content, !c.isEmpty {
                    if part == .notes { notes(c) } else { credits(c) }
                } else {
                    Text("Navidrome has no notes, credits or links for this album.").foregroundStyle(CU.textSecondary)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    /// Liner notes first, then the album's facts and the links at the bottom.
    @ViewBuilder private func notes(_ c: AlbumSpreadContent) -> some View {
        if let notes = c.notes {
            VStack(alignment: .leading, spacing: 8) {
                Text(notes).font(CU.Font.body.weighted(.regular)).lineSpacing(3).textSelection(.enabled)
                if let src = c.notesSource, !src.isEmpty {
                    if let u = c.notesURL { Link(src, destination: u).font(CU.Font.callout.weighted(.regular)) }
                    else { Text(src).font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary) }
                }
            }
        } else if c.facts.isEmpty && c.musicBrainzURL == nil && c.lastFmURL == nil {
            Text("No liner notes for this album.").foregroundStyle(CU.textSecondary)
        }
        if !c.facts.isEmpty || c.musicBrainzURL != nil || c.lastFmURL != nil {
            section("MusicBrainz and links") {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(c.facts) { f in
                        HStack(alignment: .firstTextBaseline, spacing: 8) {
                            Text(f.label).foregroundStyle(CU.textSecondary).frame(width: 150, alignment: .leading)
                            Text(f.value).textSelection(.enabled)
                        }
                        .font(CU.Font.body.weighted(.regular)).accessibilityElement(children: .combine)
                    }
                    HStack(spacing: 16) {
                        if let u = c.musicBrainzURL { Link("Open on MusicBrainz", destination: u) }
                        if let u = c.lastFmURL { Link("Open on Last.fm", destination: u) }
                    }
                    .font(CU.Font.body.weighted(.regular)).padding(.top, 4)
                }
            }
        }
    }

    /// The extended credits from the knowledge base, then the credits Navidrome holds for the album.
    @ViewBuilder private func credits(_ c: AlbumSpreadContent) -> some View {
        let extended = state.albumCredits
        if !extended.groups.isEmpty {
            creditList(extended.groups.map { ($0.role, $0.names) })
            if extended.truncated { Text("The list is cut short; the knowledge base holds more.").font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary).padding(.top, 8) }
        } else if !c.credits.isEmpty {
            creditList(c.credits.map { ($0.title, $0.names) })
        } else if extended.loading {
            Text("Loading credits…").foregroundStyle(CU.textSecondary)
        } else {
            Text("No credits for this album.").foregroundStyle(CU.textSecondary)
        }
    }

    private func creditList(_ rows: [(String, [String])]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(Array(rows.enumerated()), id: \.offset) { _, g in
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text(g.0).foregroundStyle(CU.textSecondary).frame(width: 150, alignment: .leading)
                    Text(g.1.joined(separator: ", ")).textSelection(.enabled)
                }
                .font(CU.Font.body.weighted(.regular)).accessibilityElement(children: .combine)
            }
        }
    }

    @ViewBuilder private var reviews: some View {
        switch state.spread.reviews {
        case .idle: Text("Reviews need a Librarian sign-in.").foregroundStyle(CU.textSecondary)
        case .loading: Text("Loading reviews…").foregroundStyle(CU.textSecondary)
        case .failed:
            HStack { Text("Reviews could not be loaded.").foregroundStyle(CU.textSecondary); retryButton }
        case .loaded(let list, let retryable):
            VStack(alignment: .leading, spacing: 8) {
                if list.isEmpty { Text(retryable ? "No reviews found. Some sources did not answer." : "No reviews found for this album.").foregroundStyle(CU.textSecondary) }
                ForEach(list) { r in
                    VStack(alignment: .leading, spacing: 4) {
                        Text("\u{201C}\(r.quote)\u{201D}").font(CU.Font.body.weighted(.regular)).lineSpacing(3).textSelection(.enabled)
                        Link("Read the full review at \(r.source)", destination: r.url).font(CU.Font.callout.weighted(.regular))
                    }
                    .accessibilityElement(children: .combine)
                }
                if retryable && !list.isEmpty { Text("Some sources did not answer.").font(CU.Font.callout.weighted(.regular)).foregroundStyle(CU.textSecondary) }
                if retryable { retryButton }
            }
        }
    }

    private var retryButton: some View {
        Button("Try again") { Task { await state.retrySpreadReviews() } }.buttonStyle(CapsuleButtonStyle(small: true))
    }

    private func section<C: View>(_ title: String, @ViewBuilder _ body: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(CU.Font.callout.weighted(.semibold)).foregroundStyle(CU.textSecondary).textCase(.uppercase)
                .accessibilityAddTraits(.isHeader)
            body()
        }
        .padding(.top, 16).frame(maxWidth: .infinity, alignment: .leading)
    }
}
