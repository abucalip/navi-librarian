import DiscairLibrarian
import SwiftUI

/// The menu beside Not for me on a pick (Star Operation S2c): More like this and Less like this lean on the artist (neither hides
/// anything), and Block genre names the album's own genre, the one the Librarian matches on. A block hides picks only, never the
/// library. The answer shows in the window's notice; Settings › Blocklist lifts any of these. No motion: a plain menu.
struct CupertinoPickFeedbackMenu: View {
    let state: AppState
    let album: AlbumItem
    /// Over the Home marquee's banner: a translucent capsule, as its other buttons.
    var marquee = false

    var body: some View {
        Menu {
            Button("More like \(album.artist)") { Task { await state.blocklist.lean(.more, on: album) } }
            Button("Less like \(album.artist)") { Task { await state.blocklist.lean(.less, on: album) } }
            if let genre = BlocklistModel.blockableGenre(of: album) {
                Divider()
                Button("Block genre: \(genre)") { Task { await state.blocklist.blockGenre(of: album) } }
            }
        } label: { Text("More") }
            .menuStyle(.button).menuIndicator(.hidden)
            .buttonStyle(CapsuleButtonStyle(small: true, outlined: !marquee, translucent: marquee))
            .fixedSize()
            .accessibilityLabel("More options for \(album.title)")
    }
}

/// Settings › Blocklist: blocked genres, artists hidden with Not this artist, and artists marked More or Less like this, each with
/// a button that lifts it. A block hides picks only. Lifting a Not this artist also lifts its score penalty; the album that was
/// dismissed with it stays dismissed.
struct CupertinoBlocklist: View {
    let state: AppState
    private var model: BlocklistModel { state.blocklist }

    var body: some View {
        VStack(alignment: .leading, spacing: CU.Space.m) {
            if case .failed(let message) = model.phase {
                HStack(spacing: CU.Space.s) {
                    CUNotice(kind: .danger, lead: "The blocklist could not be read.", message: message)
                    Button("Try again") { Task { await model.load() } }.buttonStyle(CapsuleButtonStyle(small: true))
                }
            }
            Text("A block hides picks only. Your library and Saved are not affected. Unblocking brings them back on the next refresh.")
                .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).fixedSize(horizontal: false, vertical: true)
            group("Blocked genres", empty: "No blocked genres.", rows: model.list.genres.map { g in (g, "Unblock", { await model.unblockGenre(g) }) })
            group("Hidden with Not this artist", empty: "No hidden artists.", rows: model.list.hiddenArtists.map { a in (a, "Unblock", { await model.unblockArtist(a) }) })
            group("More and Less like this", empty: "No artists marked.", rows: model.list.leans.map { l in
                ("\(l.artist) · \(l.lean == .more ? "More" : "Less") like this", "Clear", { await model.clearLean(l.artist) }) })
            if let note = model.note { CUNotice(kind: .danger, lead: "Could not do that.", message: note) }
        }
        .task { await model.load() }
    }

    private func group(_ title: String, empty: String, rows: [(String, String, () async -> Void)]) -> some View {
        CUPanel(title) {
            if rows.isEmpty {
                Text(model.phase == .loading ? "Reading the blocklist…" : empty)
                    .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary).padding(.vertical, CU.Space.s)
            } else {
                VStack(spacing: 0) {
                    ForEach(Array(rows.enumerated()), id: \.offset) { i, row in
                        if i > 0 { Divider() }
                        HStack(spacing: CU.Space.m) {
                            Text(row.0).cuRole(CU.Font.headline).foregroundStyle(CU.text).lineLimit(2)
                                .frame(maxWidth: .infinity, alignment: .leading)
                            Button(row.1) { Task { await row.2() } }
                                .buttonStyle(CapsuleButtonStyle(small: true, outlined: true)).disabled(model.busy)
                                .accessibilityLabel("\(row.1) \(row.0)")
                        }
                        .padding(.vertical, CU.Space.s)
                        .accessibilityElement(children: .contain)
                    }
                }
            }
        }
    }
}
