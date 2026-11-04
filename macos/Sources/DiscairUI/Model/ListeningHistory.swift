import Foundation

/// One calendar day of listening: the songs whose latest play fell on it, newest first.
struct HistoryDay: Identifiable, Equatable {
    let date: Date
    let songs: [SongRow]
    var id: Date { date }
}

/// One square of the heatmap.
struct HeatCell: Identifiable, Equatable {
    let date: Date
    let count: Int
    var id: Date { date }
}

/// Listening history from what Navidrome keeps per song: its play count and the time of its latest play (contract
/// section 6.6). Navidrome stores only the latest play of each song, so a song played on three days appears on the
/// last of them. A full play-by-play history would need the scrobble services (Last.fm, ListenBrainz), which this
/// screen does not read. Pure, so it is tested without a window.
enum ListeningHistory {
    static func days(_ songs: [SongRow], calendar: Calendar = .current) -> [HistoryDay] {
        let played = songs.compactMap { s in s.playedAt.map { (s, $0) } }
        let byDay = Dictionary(grouping: played) { calendar.startOfDay(for: $0.1) }
        return byDay.keys.sorted(by: >).map { day in
            HistoryDay(date: day, songs: byDay[day, default: []].sorted { $0.1 > $1.1 }.map(\.0))
        }
    }

    /// `weeks` full weeks ending with the week of `now`, one cell per day, oldest first, Monday to Sunday columns.
    /// Days after `now` are left out.
    static func heatmap(_ songs: [SongRow], weeks: Int = 26, now: Date = Date(), calendar: Calendar = .current) -> [HeatCell] {
        var cal = calendar
        cal.firstWeekday = 2
        let today = cal.startOfDay(for: now)
        guard let thisWeek = cal.dateInterval(of: .weekOfYear, for: today)?.start,
              let start = cal.date(byAdding: .day, value: -7 * (weeks - 1), to: thisWeek) else { return [] }
        var counts: [Date: Int] = [:]
        for s in songs { if let p = s.playedAt { counts[cal.startOfDay(for: p), default: 0] += 1 } }
        var cells: [HeatCell] = []
        var d = start
        while d <= today {
            cells.append(HeatCell(date: d, count: counts[d] ?? 0))
            guard let n = cal.date(byAdding: .day, value: 1, to: d) else { break }
            d = n
        }
        return cells
    }

    /// 0 (none) to 4 (the busiest quarter) so the colours spread whatever the range of counts.
    static func level(_ count: Int, max top: Int) -> Int {
        guard count > 0, top > 0 else { return 0 }
        return min(4, max(1, Int((Double(count) / Double(top) * 4).rounded(.up))))
    }

    static func dayTitle(_ date: Date, now: Date = Date(), calendar: Calendar = .current) -> String {
        if calendar.isDate(date, inSameDayAs: now) { return "Today" }
        if let y = calendar.date(byAdding: .day, value: -1, to: now), calendar.isDate(date, inSameDayAs: y) { return "Yesterday" }
        return date.formatted(.dateTime.weekday(.wide).day().month(.wide).year())
    }
}
