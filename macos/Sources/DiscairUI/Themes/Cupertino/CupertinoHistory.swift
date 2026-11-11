import SwiftUI

/// Listening History (contract 6.6): a 26-week heatmap of the days songs were last played, and a timeline by day
/// below it. Built from Navidrome's per-song latest play; see `ListeningHistory`. No mockup exists for this screen.
struct CupertinoHistory: View {
    let state: AppState
    private let shownDays = 30

    var body: some View {
        let songs = state.library.songs
        let days = ListeningHistory.days(songs)
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("History").font(CU.title(34)).padding(.top, 4).accessibilityAddTraits(.isHeader)
                Text("When you last played each song. Navidrome keeps one latest play per song.").foregroundStyle(CU.muted)
                heat(songs)
                if days.isEmpty {
                    Text(state.library.songsLoading ? "Reading your songs…" : "No played songs yet.").foregroundStyle(CU.muted)
                }
                ForEach(days.prefix(shownDays)) { day in section(day) }
            }
            .padding(.horizontal, CU.Space.xl).padding(.bottom, CU.Space.xl)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
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
                        RoundedRectangle(cornerRadius: 2, style: .continuous)
                            .fill(c.count == 0 ? CU.muted.opacity(0.15) : CU.accent.opacity(0.25 + 0.2 * Double(ListeningHistory.level(c.count, max: top))))
                            .frame(width: 11, height: 11)
                            .help("\(c.date.formatted(date: .abbreviated, time: .omitted)): \(c.count) songs")
                    }
                }
            }
        }
        .padding(16).frame(maxWidth: .infinity, alignment: .leading)
        .background(CU.card, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Heatmap of the last 26 weeks, \(cells.filter { $0.count > 0 }.count) days with plays")
    }

    private func section(_ day: HistoryDay) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(ListeningHistory.dayTitle(day.date)).font(CU.title(18))
                Text("\(day.songs.count) songs").foregroundStyle(CU.muted)
                Spacer()
                Button("Play day") { state.play(rows: day.songs, startAt: 0) }.buttonStyle(CapsuleButtonStyle(primary: true, small: true))
            }
            ForEach(Array(day.songs.enumerated()), id: \.offset) { i, s in
                Button { state.play(rows: day.songs, startAt: i) } label: {
                    HStack(spacing: 10) {
                        Text(s.playedAt?.formatted(date: .omitted, time: .shortened) ?? "").foregroundStyle(CU.muted).frame(width: 64, alignment: .leading)
                        Text(s.title).lineLimit(1)
                        Text(s.artist).foregroundStyle(CU.muted).lineLimit(1)
                        Spacer(minLength: 0)
                        Text("\(s.plays) plays").font(.system(size: 11)).foregroundStyle(CU.muted)
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain).accessibilityLabel("Play \(s.title) by \(s.artist)")
            }
        }
        .padding(16).frame(maxWidth: .infinity, alignment: .leading)
        .background(CU.card, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .accessibilityElement(children: .contain)
    }
}
