import Foundation
import Testing
@testable import DiscairUI

struct ListeningHistoryTests {
    private var cal: Calendar { var c = Calendar(identifier: .gregorian); c.timeZone = TimeZone(identifier: "UTC")!; c.firstWeekday = 2; return c }
    // Wednesday 2027-01-13 12:00 UTC
    private let now = Date(timeIntervalSince1970: 1_799_841_600)
    private func song(_ id: Int, daysAgo: Int?, hoursAgo: Double = 0) -> SongRow {
        var s = SongRow(id: id, album: 0, title: "T\(id)", artist: "A", genre: "", format: "", bitrate: "", lastPlayed: "", added: "", year: 0, plays: 1)
        s.playedAt = daysAgo.map { now.addingTimeInterval(-Double($0) * 86_400 - hoursAgo * 3600) }
        return s
    }

    @Test func daysGroupBySongsLatestPlayNewestFirstAndSkipUnplayed() {
        let songs = [song(1, daysAgo: 2), song(2, daysAgo: 0, hoursAgo: 1), song(3, daysAgo: 0), song(4, daysAgo: nil)]
        let days = ListeningHistory.days(songs, calendar: cal)
        #expect(days.count == 2)
        #expect(days[0].songs.map(\.id) == [3, 2])      // later in the day first
        #expect(days[1].songs.map(\.id) == [1])
    }

    @Test func heatmapStartsOnAMondayEndsTodayAndCountsPerDay() {
        let cells = ListeningHistory.heatmap([song(1, daysAgo: 0), song(2, daysAgo: 0, hoursAgo: 2), song(3, daysAgo: 9)], weeks: 3, now: now, calendar: cal)
        #expect(cal.component(.weekday, from: cells[0].date) == 2)        // Monday
        #expect(cells.count == 2 * 7 + 3)                                 // two full weeks plus Mon-Wed
        #expect(cells.last?.count == 2)
        #expect(cells.filter { $0.count > 0 }.count == 2)
    }

    @Test func levelsSpreadOverTheBusiestDay() {
        #expect(ListeningHistory.level(0, max: 8) == 0)
        #expect(ListeningHistory.level(1, max: 8) == 1)
        #expect(ListeningHistory.level(8, max: 8) == 4)
    }

    @Test func dayTitlesNameTodayAndYesterday() {
        #expect(ListeningHistory.dayTitle(now, now: now, calendar: cal) == "Today")
        #expect(ListeningHistory.dayTitle(now.addingTimeInterval(-86_400), now: now, calendar: cal) == "Yesterday")
    }
}
