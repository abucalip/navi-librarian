import SwiftUI

/// Listening History (contract 6.6, redesign 5.3, mockup `history--default`): a 26-week heatmap of the days songs were last
/// played, with a Fewer to More key, then a list of each day's songs. Built from Navidrome's per-song latest play; see
/// `ListeningHistory`. The heatmap is `CUHeatmap`: five stepped colours, month and weekday labels, click or arrow-key selection.
struct CupertinoHistory: View {
    let state: AppState
    private let shownDays = 30

    var body: some View {
        let songs = state.library.songs
        let days = ListeningHistory.days(songs)
        ScrollView {
            VStack(alignment: .leading, spacing: CU.Space.m) {
                Text("History").cuRole(CU.Font.largeTitle).foregroundStyle(CU.text).padding(.top, CU.Space.xs).accessibilityAddTraits(.isHeader)
                Text("When you last played each song. Navidrome keeps one latest play per song, so earlier plays of the same song are not shown.")
                    .cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).frame(maxWidth: 620, alignment: .leading)
                heat(songs)
                if days.isEmpty {
                    Text(state.library.songsLoading ? "Reading your songs…" : "No played songs yet.")
                        .cuRole(CU.Font.body).foregroundStyle(CU.textSecondary)
                }
                ForEach(days.prefix(shownDays)) { day in section(day) }
            }
            .padding(.horizontal, CU.Space.xl).padding(.bottom, CU.Space.xl)
        }
        .scrollEdgeEffectStyle(.hard, for: .top)
        .task { await state.loadHistory() }
    }

    private func heat(_ songs: [SongRow]) -> some View {
        let cells = ListeningHistory.heatmap(songs).map { CUHeatCell(date: $0.date, count: $0.count) }
        let withPlays = cells.filter { $0.count > 0 }.count
        return CUPanel {
            HStack(alignment: .top, spacing: CU.Space.m) {
                VStack(alignment: .leading, spacing: CU.Space.xs) {
                    Text("Last 26 weeks").cuRole(CU.Font.title2).foregroundStyle(CU.text).accessibilityAddTraits(.isHeader)
                    if let first = cells.first, let last = cells.last {
                        Text("Songs whose latest play fell on each day · \(CUChartMath.longDate(first.date, weekday: false)) to \(CUChartMath.longDate(last.date, weekday: false))")
                            .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
                    }
                }
                Spacer(minLength: CU.Space.m)
                CUHeatmapKey()
            }
            CUHeatmap(cells: cells, title: "Songs played each day, last 26 weeks")
                .padding(.vertical, CU.Space.xs)
            Text("Click a day or move with the arrow keys to read its count. \(withPlays) of \(cells.count) days have plays.")
                .cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Heatmap of the last 26 weeks, \(withPlays) days with plays")
    }

    private func section(_ day: HistoryDay) -> some View {
        CUPanel {
            HStack(alignment: .firstTextBaseline, spacing: CU.Space.s) {
                Text(ListeningHistory.dayTitle(day.date)).cuRole(CU.Font.title2).foregroundStyle(CU.text)
                Text("\(day.songs.count) songs").cuRole(CU.Font.callout).foregroundStyle(CU.textSecondary)
                Spacer(minLength: 0)
                Button { state.play(rows: day.songs, startAt: 0) } label: { Label("Play day", systemImage: "play.fill") }
                    .buttonStyle(CapsuleButtonStyle(small: true))
            }
            ForEach(Array(day.songs.enumerated()), id: \.offset) { i, s in
                if i > 0 { Divider() }
                Button { state.play(rows: day.songs, startAt: i) } label: {
                    HStack(spacing: CU.Space.s) {
                        Text(s.playedAt?.formatted(date: .omitted, time: .shortened) ?? "")
                            .cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).monospacedDigit().frame(width: 64, alignment: .leading)
                        Text(s.title).cuRole(CU.Font.headline).foregroundStyle(CU.text).lineLimit(1)
                        Spacer(minLength: CU.Space.s)
                        Text(s.artist).cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).lineLimit(1).frame(width: 200, alignment: .leading)
                        Text("\(s.plays) plays").cuRole(CU.Font.body).foregroundStyle(CU.textSecondary).monospacedDigit()
                            .frame(width: 90, alignment: .trailing)
                    }
                    .padding(.vertical, CU.Space.xs)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain).accessibilityLabel("Play \(s.title) by \(s.artist)")
            }
        }
        .accessibilityElement(children: .contain)
    }
}
