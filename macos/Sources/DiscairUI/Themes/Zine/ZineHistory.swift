import SwiftUI

/// Listening History in Zine's language: "Back Pages". A bordered ink heatmap, then one dated strip per day. No mockup
/// exists for this screen; it reuses the Gap Radar and Smart Playlists parts.
struct ZineHistory: View {
    let state: AppState
    private let shownDays = 30

    var body: some View {
        let songs = state.library.songs
        let days = ListeningHistory.days(songs)
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .bottom, spacing: 20) {
                Text("History").font(Z.an(78)).textCase(.uppercase).tracking(0.8).accessibilityAddTraits(.isHeader)
                Mono("Latest play of each song").padding(.bottom, 8)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 4) }
            heat(songs)
            if days.isEmpty { Mono(state.library.songsLoading ? "Reading your songs…" : "No played songs yet.") }
            ForEach(days.prefix(shownDays)) { day in strip(day) }
        }
        .task { await state.loadHistory() }
    }

    private func heat(_ songs: [SongRow]) -> some View {
        let cells = ListeningHistory.heatmap(songs)
        let top = cells.map(\.count).max() ?? 0
        let columns = stride(from: 0, to: cells.count, by: 7).map { Array(cells[$0..<min($0 + 7, cells.count)]) }
        return HStack(alignment: .top, spacing: 3) {
            ForEach(Array(columns.enumerated()), id: \.offset) { _, col in
                VStack(spacing: 3) {
                    ForEach(col) { c in
                        let l = ListeningHistory.level(c.count, max: top)
                        Rectangle().fill(l == 0 ? Z.paper : Z.ink.opacity(0.2 + 0.2 * Double(l))).frame(width: 12, height: 12)
                            .overlay(Rectangle().stroke(Z.ink, lineWidth: 1))
                            .help("\(c.date.formatted(date: .abbreviated, time: .omitted)): \(c.count) songs")
                    }
                }
            }
        }
        .padding(12).background(Z.paper).zBorder(3)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Heatmap of the last 26 weeks, \(cells.filter { $0.count > 0 }.count) days with plays")
    }

    private func strip(_ day: HistoryDay) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(ListeningHistory.dayTitle(day.date)).font(Z.an(26)).textCase(.uppercase)
                Mono("\(day.songs.count) songs")
                Spacer(minLength: 8)
                Button("Play day") { state.play(rows: day.songs, startAt: 0) }.buttonStyle(ZineButtonStyle(kind: .yellow, small: true))
            }
            ForEach(Array(day.songs.enumerated()), id: \.offset) { i, s in
                Button { state.play(rows: day.songs, startAt: i) } label: {
                    HStack(spacing: 10) {
                        Mono(s.playedAt?.formatted(date: .omitted, time: .shortened) ?? "", size: 10).frame(width: 64, alignment: .leading)
                        Text(s.title).font(Z.mono(12)).lineLimit(1)
                        Mono(s.artist, size: 10).lineLimit(1)
                        Spacer(minLength: 0)
                        Mono("\(s.plays) plays", size: 10)
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain).accessibilityLabel("Play \(s.title) by \(s.artist)")
            }
        }
        .padding(.bottom, 10)
        .overlay(alignment: .bottom) { Rectangle().fill(Z.ink).frame(height: 2) }
        .accessibilityElement(children: .contain)
    }
}
