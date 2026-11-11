import Foundation
import Testing
@testable import DiscairUI

/// Redesign M4: the scale, bin and selection maths behind the Cupertino charts, and the state each input produces.
struct CupertinoChartsTests {
    // MARK: Value axis

    @Test func nicestepIsOneTwoFiveOrTenTimesAPowerOfTen() {
        #expect(CUChartMath.niceStep(68) == 100)
        #expect(CUChartMath.niceStep(7.75) == 10)
        #expect(CUChartMath.niceStep(4.75) == 5)
        #expect(CUChartMath.niceStep(1.2) == 2)
        #expect(CUChartMath.niceStep(0.03) == 0.05)
        #expect(CUChartMath.niceStep(0) == 1)
    }

    @Test func aLineThatStartsAboveZeroGetsTicksThatCoverItsRange() {
        // The specimen's growth line: 1,012 to 1,284 reads 1,000 to 1,300 in steps of 100.
        #expect(CUChartMath.ticks(low: 1012, high: 1284, startsAtZero: false) == [1000, 1100, 1200, 1300])
    }

    @Test func barsAndColumnsAlwaysStartTheirAxisAtZero() {
        let t = CUChartMath.ticks(low: 9, high: 31, startsAtZero: true)
        #expect(t.first == 0)
        #expect(t == [0, 10, 20, 30, 40])
        #expect(CUChartMath.ticks(low: 0, high: 19, startsAtZero: true) == [0, 5, 10, 15, 20])
        #expect(CUChartMath.ticks(low: 150, high: 214, startsAtZero: true).first == 0)
    }

    @Test func ticksNeverExceedFiveSoAtMostFourGridlinesSitAboveTheBaseline() {
        for high in stride(from: 1.0, through: 100_000, by: 977) {
            let t = CUChartMath.ticks(low: 0, high: high, startsAtZero: true)
            #expect(t.count <= 5 && t.count >= 2)
            #expect(t.last! >= high && t.first == 0)
        }
    }

    @Test func aFlatOrEmptyRangeStillGivesAnAxis() {
        #expect(CUChartMath.ticks(low: 5, high: 5, startsAtZero: false).count >= 2)
        #expect(CUChartMath.ticks(low: 0, high: 0, startsAtZero: true).count >= 2)
    }

    @Test func scaleMapsLinearlyAndSurvivesAZeroSpan() {
        #expect(CUChartMath.scale(1150, from: 1000...1300, toStart: 200, toEnd: 0) == 100)
        #expect(CUChartMath.scale(5, from: 5...5, toStart: 10, toEnd: 20) == 10)
        #expect(CUChartMath.fraction(19, of: 38) == 0.5)
        #expect(CUChartMath.fraction(50, of: 38) == 1)
        #expect(CUChartMath.fraction(3, of: 0) == 0)
    }

    // MARK: Time axis and selection

    @Test func timeLabelsAreSpreadEvenlyWithBothEndsIncluded() {
        #expect(CUChartMath.labelIndices(count: 33, labels: 5) == [0, 8, 16, 24, 32])
        #expect(CUChartMath.labelIndices(count: 7, labels: 7) == [0, 1, 2, 3, 4, 5, 6])
        #expect(CUChartMath.labelIndices(count: 3, labels: 7) == [0, 1, 2])
        #expect(CUChartMath.labelIndices(count: 10, labels: 1) == [0])
        #expect(CUChartMath.labelIndices(count: 0, labels: 5) == [])
    }

    @Test func selectionFindsTheNearestPointAndClamps() {
        #expect(CUChartMath.nearest(3.4, count: 10) == 3)
        #expect(CUChartMath.nearest(3.6, count: 10) == 4)
        #expect(CUChartMath.nearest(-2, count: 10) == 0)
        #expect(CUChartMath.nearest(99, count: 10) == 9)
        #expect(CUChartMath.nearest(nil, count: 10) == nil)
        #expect(CUChartMath.nearest(2, count: 0) == nil)
    }

    @Test func arrowKeysStartAtTheNewestPointAndStopAtBothEnds() {
        #expect(CUChartMath.move(nil, by: -1, count: 5) == 4)
        #expect(CUChartMath.move(nil, by: 1, count: 5) == 4)
        #expect(CUChartMath.move(2, by: -1, count: 5) == 1)
        #expect(CUChartMath.move(0, by: -1, count: 5) == 0)
        #expect(CUChartMath.move(4, by: 1, count: 5) == 4)
        #expect(CUChartMath.move(nil, by: 1, count: 0) == nil)
    }

    // MARK: Draw-in

    @Test func aLineDrawsInFromTheLeft() {
        let v: [Double] = [10, 20, 40]
        #expect(CUChartMath.revealed(v, progress: 1).map(\.y) == [10, 20, 40])
        #expect(CUChartMath.revealed(v, progress: 0).map(\.y) == [10])
        let half = CUChartMath.revealed(v, progress: 0.75)   // 1.5 steps: two points and one halfway between 20 and 40
        #expect(half.map(\.x) == [0, 1, 1.5] && half.map(\.y) == [10, 20, 30])
        #expect(CUChartMath.revealed([], progress: 0.5).isEmpty)
    }

    @Test func aColumnGrowsFromTheBaseline() {
        #expect(CUChartMath.grown(30, progress: 0) == 0)
        #expect(CUChartMath.grown(30, progress: 0.5) == 15)
        #expect(CUChartMath.grown(30, progress: 3) == 30)
    }

    // MARK: Ranked, paired and compared

    @Test func rankedRowsAreSortedLargestFirstAndTiesKeepTheirOrder() {
        let rows = [CURankedRow(label: "B", value: 14), CURankedRow(label: "A", value: 19), CURankedRow(label: "C", value: 14)]
        #expect(CUChartMath.ranked(rows).map(\.label) == ["A", "B", "C"])
    }

    @Test func aShareThatRoseIsDistinctFromOneThatFell() {
        #expect(CUChartMath.shift(before: 9, now: 17) == .rose)
        #expect(CUChartMath.shift(before: 14, now: 8) == .fell)
        #expect(CUChartMath.shift(before: 18.4, now: 18.2) == .unchanged)   // equal as whole percentages
    }

    @Test func dumbbellRowsCarryTheirNumbersAndDirectionInWords() {
        #expect(CUChartMath.dumbbellSummary(CUDumbbellRow(label: "Ambient", before: 9, now: 17)) == "9% → 17% ▲")
        #expect(CUChartMath.dumbbellSummary(CUDumbbellRow(label: "Post-punk", before: 14, now: 8)) == "14% → 8% ▼")
        #expect(CUChartMath.dumbbellSummary(CUDumbbellRow(label: "Flat", before: 5, now: 5)) == "5% → 5%")
        #expect(CUChartMath.dumbbellWords(CUDumbbellRow(label: "Ambient", before: 9, now: 17)) == "Ambient rose from 9% to 17%")
        #expect(CUChartMath.dumbbellWords(CUDumbbellRow(label: "Post-punk", before: 14, now: 8)) == "Post-punk fell from 14% to 8%")
        #expect(CUChartMath.dumbbellWords(CUDumbbellRow(label: "Flat", before: 5, now: 5)) == "Flat stayed at 5%")
    }

    // MARK: Heatmap

    @Test func heatLevelsSpreadAcrossTheBusiestQuarter() {
        #expect(CUChartMath.heatLevel(count: 0, max: 40) == 0)
        #expect(CUChartMath.heatLevel(count: 1, max: 40) == 1)
        #expect(CUChartMath.heatLevel(count: 10, max: 40) == 1)
        #expect(CUChartMath.heatLevel(count: 11, max: 40) == 2)
        #expect(CUChartMath.heatLevel(count: 30, max: 40) == 3)
        #expect(CUChartMath.heatLevel(count: 40, max: 40) == 4)
        #expect(CUChartMath.heatLevel(count: 5, max: 0) == 0)
    }

    private var calendar: Calendar {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = TimeZone(identifier: "UTC")!
        c.locale = Locale(identifier: "en_US")
        c.firstWeekday = 1   // Sunday: the grid must still put Monday on top
        return c
    }

    private func days(from start: String, count: Int) -> [CUHeatCell] {
        let f = ISO8601DateFormatter(); f.formatOptions = [.withFullDate]; f.timeZone = TimeZone(identifier: "UTC")
        let first = f.date(from: start)!
        return (0..<count).map { CUHeatCell(date: calendar.date(byAdding: .day, value: $0, to: first)!, count: $0) }
    }

    @Test func theHeatGridPutsMondayOnTopWhateverTheCalendarsFirstWeekday() {
        // 2026-11-09 is a Monday, 2026-11-11 a Wednesday.
        #expect(CUChartMath.heatLead(days(from: "2026-11-09", count: 1)[0].date, calendar: calendar) == 0)
        #expect(CUChartMath.heatLead(days(from: "2026-11-11", count: 1)[0].date, calendar: calendar) == 2)
        #expect(CUChartMath.heatLead(days(from: "2026-11-15", count: 1)[0].date, calendar: calendar) == 6)   // Sunday
        let grid = CUChartMath.heatGrid(days(from: "2026-11-11", count: 10), calendar: calendar)
        #expect(grid.count == 2 && grid.allSatisfy { $0.count == 7 })
        #expect(grid[0][0] == nil && grid[0][1] == nil && grid[0][2]?.count == 0)
        #expect(grid[1][0]?.count == 5)             // the following Monday, 16 November
        #expect(grid[1][4]?.count == 9 && grid[1][5] == nil)   // the last day, then padding
    }

    @Test func heatPositionAndIndexAreInverses() {
        let cells = days(from: "2026-11-11", count: 30)
        let lead = CUChartMath.heatLead(cells[0].date, calendar: calendar)
        for i in cells.indices {
            let p = CUChartMath.heatPosition(index: i, lead: lead)
            #expect(CUChartMath.heatIndex(column: p.column, row: p.row, lead: lead, count: cells.count) == i)
        }
        #expect(CUChartMath.heatIndex(column: 0, row: 0, lead: lead, count: cells.count) == nil)   // padding before the first day
        #expect(CUChartMath.heatIndex(column: 9, row: 0, lead: lead, count: cells.count) == nil)
        #expect(CUChartMath.heatIndex(column: 0, row: 7, lead: lead, count: cells.count) == nil)
    }

    @Test func monthLabelsSitAtTheFirstOfEachMonthWithoutCollisions() {
        let grid = CUChartMath.heatGrid(days(from: "2026-05-18", count: 182), calendar: calendar)
        let labels = CUChartMath.monthLabels(grid, calendar: calendar)
        #expect(labels.map(\.text) == ["May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"])
        for (a, b) in zip(labels, labels.dropFirst()) { #expect(b.column - a.column >= 2) }
        #expect(labels.first?.column == 0)
    }

    // MARK: Stage tracker

    @Test func theTrackerMarksDoneCurrentAndPendingSegments() {
        #expect(CUChartMath.stageSegments(step: 1, progress: 0.64, failed: false) == [.done, .current(progress: 0.64), .pending, .pending])
        #expect(CUChartMath.stageSegments(step: 0, progress: nil, failed: false) == [.current(progress: nil), .pending, .pending, .pending])
        #expect(CUChartMath.stageSegments(step: 4, progress: nil, failed: false) == [.done, .done, .done, .done])
        #expect(CUChartMath.stageSegments(step: 1, progress: 0.4, failed: true) == [.done, .failed, .pending, .pending])
        #expect(CUChartMath.stageSegments(step: 9, progress: nil, failed: false) == [.done, .done, .done, .done])
        #expect(CUChartMath.stageSegments(step: 2, progress: 4, failed: false)[2] == .current(progress: 1))
    }

    @Test func theTrackerSaysItInWords() {
        #expect(CUChartMath.stageNames == ["Found", "Downloading", "Importing", "In library"])
        #expect(CUChartMath.stageWords(step: 1, progress: 0.64, failed: false) == "Downloading, 64%")
        #expect(CUChartMath.stageWords(step: 0, progress: nil, failed: false) == "Found")
        #expect(CUChartMath.stageWords(step: 4, progress: nil, failed: false) == "In library")
        #expect(CUChartMath.stageWords(step: 1, progress: 0.41, failed: true, reason: "the source went offline") == "Stopped at Downloading: the source went offline")
        #expect(CUChartMath.stageWords(step: 2, progress: nil, failed: true) == "Stopped at Importing")
    }

    // MARK: Values

    @Test func valuesUseThousandsSeparatorsUnitsAndWholePercentages() {
        let albums = CUValueFormat(unit: "albums", singular: "album")
        #expect(albums.axis(1300) == "1,300")
        #expect(albums.text(1171) == "1,171 albums")
        #expect(albums.text(1) == "1 album")
        #expect(CUValueFormat(unit: "songs").text(1) == "1 songs")   // no singular given
        #expect(CUValueFormat(percent: true).axis(19.4) == "19%")
        #expect(CUValueFormat(percent: true).text(8) == "8%")
        #expect(CUValueFormat().text(212) == "212")
    }

    // MARK: States

    private let threshold = CUChartPhase.Threshold(headline: "Not enough history yet", sentence: "Needs albums added in 3 different months.")

    @Test func dataThatIsThereIsReady() {
        #expect(CUChartPhase.choose(isLoading: false, count: 12, minimum: 3, threshold: threshold) == .ready)
        // A refresh still running keeps showing what it has.
        #expect(CUChartPhase.choose(isLoading: true, count: 12, minimum: 3, threshold: threshold) == .ready)
    }

    @Test func nothingYetWhileLoadingIsASkeleton() {
        #expect(CUChartPhase.choose(isLoading: true, count: 0, minimum: 3, threshold: threshold) == .loading)
        #expect(CUChartPhase.choose(isLoading: true, count: 2, minimum: 3, threshold: threshold) == .loading)
    }

    @Test func tooLittleDataNamesTheThresholdInsteadOfShowingZero() {
        let phase = CUChartPhase.choose(isLoading: false, count: 2, minimum: 3, threshold: threshold)
        #expect(phase == .insufficient(headline: "Not enough history yet", threshold: "Needs albums added in 3 different months."))
        #expect(CUChartPhase.choose(isLoading: false, count: 0, minimum: 3, threshold: threshold) == phase)
    }

    @Test func aMissingSourceBeatsEverythingElseAndOffersTheFix() {
        let missing = CUChartPhase.Unavailable(headline: "Needs ListenBrainz", message: "Listening charts read your history from ListenBrainz.", fixTitle: "Open Services")
        let phase = CUChartPhase.choose(isLoading: true, count: 40, minimum: 3, threshold: threshold, unavailable: missing, failedAsOf: "9 November")
        #expect(phase == .unavailable(headline: "Needs ListenBrainz", message: "Listening charts read your history from ListenBrainz.", fixTitle: "Open Services"))
    }

    @Test func aFailedRefreshKeepsTheLastGoodChartAndDatesIt() {
        let phase = CUChartPhase.choose(isLoading: false, count: 40, minimum: 3, threshold: threshold, failedAsOf: "9 November")
        #expect(phase == .stale(asOf: "9 November", message: "The refresh failed; this is the last good data."))
    }

    @Test func aFailureWithNothingSavedIsNotAvailableNotZero() {
        let phase = CUChartPhase.choose(isLoading: false, count: 0, minimum: 3, threshold: threshold, failedAsOf: "9 November")
        guard case .unavailable(let headline, _, let fix) = phase else { Issue.record("expected unavailable, got \(phase)"); return }
        #expect(headline == "Couldn't load this chart" && fix == nil)
    }

    // MARK: Spoken summary

    @Test func theSummarySentenceNamesTheRangeAndTheLatestValue() {
        let d = CUChartDescription(kind: "Line chart", title: "Collection over time", xTitle: "Date", yTitle: "Albums",
                                   points: [.init(label: "1 December 2025", value: 1012), .init(label: "12 July 2026", value: 1171), .init(label: "11 November 2026", value: 1284)],
                                   format: CUValueFormat(unit: "albums", singular: "album"), continuous: true, ordered: true)
        #expect(d.summary == "Line chart, Collection over time. 3 values. Lowest 1,012 albums, 1 December 2025. Highest 1,284 albums, 11 November 2026. Latest 1,284 albums, 11 November 2026.")
        let unordered = CUChartDescription(kind: "Column chart", title: "Shelf life", xTitle: "Time", yTitle: "Albums", points: [.init(label: "Never", value: 96)])
        #expect(!unordered.summary.contains("Latest"))
        #expect(CUChartDescription(kind: "Line chart", title: "Empty", xTitle: "", yTitle: "", points: []).summary == "Line chart, Empty. No values.")
        #expect(CUChartDescription(kind: "x", title: "y", xTitle: "", yTitle: "", points: [], summaryOverride: "Custom.").summary == "Custom.")
    }

    @Test func columnsKeyOnTheirDetailSoRepeatedLettersStayDistinct() {
        let months = ["M", "J", "J"].enumerated().map { CUColumn(label: $0.element, value: Double($0.offset), detail: "Month \($0.offset)") }
        #expect(Set(months.map(\.id)).count == 3)
    }
}
