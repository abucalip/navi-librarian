package app.discair.ui.common

import app.discair.ui.theme.Family
import app.discair.ui.theme.Layout
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Chart kit rules (docs/redesign.md 4.4, 7.2, 7.3; step A4): scales, slots, selection, per-family style, states and summaries. */
class ChartMathTest {
    @Test fun ticksAreFewAndNiceAndCoverTheRange() {
        assertEquals(listOf(0.0, 500.0, 1000.0, 1500.0), ChartRules.niceTicks(0.0, 1300.0))
        assertEquals(listOf(1000.0, 1100.0, 1200.0, 1300.0), ChartRules.niceTicks(1000.0, 1300.0))
        assertTrue(ChartRules.niceTicks(0.0, 318.0).size <= ChartRules.MAX_GRIDLINES)
        assertTrue(ChartRules.niceTicks(0.0, 318.0).last() >= 318.0)
        assertEquals(listOf(5.0), ChartRules.niceTicks(5.0, 5.0))
    }

    @Test fun barsStartAtZeroAndNeverExceedTheTop() {
        assertEquals(0f, ChartRules.barFraction(0.0, 318.0), 0f)
        assertEquals(1f, ChartRules.barFraction(318.0, 318.0), 0f)
        assertEquals(96 / 318f, ChartRules.barFraction(96.0, 318.0), 1e-6f)
        assertEquals(1f, ChartRules.barFraction(999.0, 318.0), 0f)
        assertEquals(0f, ChartRules.barFraction(5.0, 0.0), 0f)
        assertEquals(1.0, ChartRules.columnTop(listOf(0.0, 0.0)), 0.0)
        assertEquals(318.0, ChartRules.columnTop(listOf(212.0, 318.0)), 0.0)
    }

    @Test fun yScaleRunsBottomToTopAndHandlesAFlatDomain() {
        assertEquals(100f, ChartRules.scaleY(1000.0, 1000.0, 1300.0, 0f, 100f), 0f)
        assertEquals(0f, ChartRules.scaleY(1300.0, 1000.0, 1300.0, 0f, 100f), 0f)
        assertEquals(50f, ChartRules.scaleY(1150.0, 1000.0, 1300.0, 0f, 100f), 0f)
        assertEquals(50f, ChartRules.scaleY(7.0, 7.0, 7.0, 0f, 100f), 0f)
        assertEquals(0f, ChartRules.scaleY(5000.0, 1000.0, 1300.0, 0f, 100f), 0f)
    }

    @Test fun pointsSpreadFromFirstToLast() {
        assertEquals(0f, ChartRules.pointX(0, 5, 400f), 0f)
        assertEquals(400f, ChartRules.pointX(4, 5, 400f), 0f)
        assertEquals(100f, ChartRules.pointX(1, 5, 400f), 0f)
        assertEquals(200f, ChartRules.pointX(0, 1, 400f), 0f)
    }

    @Test fun touchSelectsTheNearestPointAndClampsAtTheEdges() {
        assertEquals(0, ChartRules.nearestIndex(-30f, 400f, 5))
        assertEquals(4, ChartRules.nearestIndex(900f, 400f, 5))
        assertEquals(2, ChartRules.nearestIndex(200f, 400f, 5))
        assertEquals(1, ChartRules.nearestIndex(120f, 400f, 5))
        assertEquals(-1, ChartRules.nearestIndex(10f, 400f, 0))
        assertEquals(0, ChartRules.nearestIndex(10f, 400f, 1))
    }

    @Test fun slotsAreEqualAndCentred() {
        val s = ChartRules.slots(4, 400f, fill = 0.5f)
        assertEquals(4, s.size)
        assertEquals(25f, s[0].left, 1e-4f)
        assertEquals(50f, s[0].width, 1e-4f)
        assertEquals(325f, s[3].left, 1e-4f)
        assertTrue(ChartRules.slots(0, 400f).isEmpty())
    }

    @Test fun theHighestColumnIsTheHighlightAndTheFirstWinsATie() {
        assertEquals(5, ChartRules.highlightIndex(listOf(212.0, 318.0, 204.0, 263.0, 191.0, 400.0)))
        assertEquals(1, ChartRules.highlightIndex(listOf(1.0, 3.0, 3.0)))
        assertEquals(-1, ChartRules.highlightIndex(emptyList()))
    }

    @Test fun meterColumnsHoldWholeSegmentsOnly() {
        assertEquals(4, ChartRules.meterSegments(0.5f, 64f, 8f))
        assertEquals(3, ChartRules.meterSegments(0.49f, 64f, 8f))
        assertEquals(0, ChartRules.meterSegments(0f, 64f, 8f))
        assertEquals(0, ChartRules.meterSegments(1f, 64f, 0f))
    }

    @Test fun marksGrowFromTheBaselineWithStaggerAndEndTogetherAtTheEnd() {
        assertEquals(0f, ChartRules.staggeredProgress(0f, 0, 6), 0f)
        assertEquals(1f, ChartRules.staggeredProgress(1f, 5, 6), 1e-6f)
        // A later mark lags an earlier one at the same moment.
        assertTrue(ChartRules.staggeredProgress(0.5f, 0, 6) > ChartRules.staggeredProgress(0.5f, 5, 6))
        assertEquals(0.5f, ChartRules.staggeredProgress(0.5f, 0, 1), 0f)
    }

    @Test fun aSharethatRoseIsAccentAndOneThatFellIsInk() {
        assertTrue(ChartRules.rose(ShiftRow("1990s", 20.0, 38.0)))
        assertFalse(ChartRules.rose(ShiftRow("2010s", 12.0, 9.0)))
    }

    @Test fun trackerHasFourSegmentsAndOneCurrent() {
        assertEquals(
            listOf(ChartRules.Stage.Done, ChartRules.Stage.Current, ChartRules.Stage.Pending, ChartRules.Stage.Pending),
            ChartRules.stages(1, failed = false),
        )
        assertEquals(List(4) { ChartRules.Stage.Done }, ChartRules.stages(4, failed = false))
        assertEquals(
            listOf(ChartRules.Stage.Done, ChartRules.Stage.Done, ChartRules.Stage.Failed, ChartRules.Stage.Pending),
            ChartRules.stages(2, failed = true),
        )
        assertEquals("Downloading, in progress", ChartRules.stageLabel("Downloading", ChartRules.Stage.Current))
        assertEquals("Importing, failed", ChartRules.stageLabel("Importing", ChartRules.Stage.Failed))
    }

    @Test fun numbersUseSeparatorsAndWholePercentages() {
        assertEquals("1,171", ChartRules.formatCount(1171.0))
        assertEquals("96", ChartRules.formatCount(96.0))
        assertEquals("1.5", ChartRules.formatCount(1.5))
        assertEquals("38%", ChartRules.formatPercent(37.6))
        assertEquals("1,171", ChartPoint("Nov", 1171.0).display)
    }

    @Test fun lineSummaryNamesRangeAndEnds() {
        val pts = listOf(ChartPoint("Dec", 1000.0), ChartPoint("Jun", 1100.0), ChartPoint("Nov", 1171.0))
        val s = ChartRules.lineSummary("Collection over time", pts)
        assertTrue(s.startsWith("Collection over time. 3 points."))
        assertTrue(s.contains("From 1,000 at Dec to 1,171 at Nov"))
        assertTrue(s.contains("Lowest 1,000 at Dec, highest 1,171 at Nov"))
        assertEquals("Empty. No data.", ChartRules.lineSummary("Empty", emptyList()))
    }

    @Test fun barAndShiftSummariesStateTheirValues() {
        val items = listOf(ChartPoint("Month", 212.0), ChartPoint("1-6m", 318.0), ChartPoint("Never", 96.0))
        val s = ChartRules.barsSummary("Shelf life", items)
        assertTrue(s.contains("3 bars"))
        assertTrue(s.contains("Largest 1-6m, 318"))
        assertTrue(s.contains("Smallest Never, 96"))
        val shifts = ChartRules.shiftSummary("Lately against always", listOf(ShiftRow("Jazz", 10.0, 25.0), ShiftRow("Folk", 30.0, 12.0)))
        assertTrue(shifts.contains("Jazz rose from 10% to 25%"))
        assertTrue(shifts.contains("Folk fell from 30% to 12%"))
        val paired = ChartRules.pairedSummary("Own and play", listOf(PairedRow("1980s", 21.0, 19.0), PairedRow("1990s", 27.0, 38.0)), "albums", "listens")
        assertTrue(paired.contains("Largest gap: 1990s, 27% against 38%"))
    }

    @Test fun selectedValueIsWrittenAsValueThenLabel() {
        assertEquals("1,171 · Nov", ChartRules.selectedText(ChartPoint("Nov", 1171.0)))
    }

    @Test fun eachFamilyDrawsItsOwnMarks() {
        val day = ChartRules.style(Family.Classic, Layout.Standard, light = true)
        assertEquals(MarkShape.Rounded, day.marks)
        assertTrue(day.area)
        assertEquals(3f, day.barRadiusDp, 0f)
        val night = ChartRules.style(Family.Classic, Layout.Standard, light = false)
        assertFalse(night.area)
        val tape = ChartRules.style(Family.Brutal, Layout.TapeDeck, light = true)
        assertEquals(MarkShape.Outlined, tape.marks)
        assertTrue(tape.steppedLine)
        assertTrue(tape.meterColumns)
        assertTrue(tape.area)
        assertEquals(0f, tape.barRadiusDp, 0f)
        val sheet = ChartRules.style(Family.Brutal, Layout.SheetStack, light = false)
        assertEquals(MarkShape.Outlined, sheet.marks)
        assertEquals(3f, sheet.lineWidthDp, 0f)
        assertFalse(sheet.area)
        assertFalse(sheet.steppedLine)
        assertFalse(sheet.meterColumns)
    }

    @Test fun plotHeightFloorIsTheSpec() {
        assertEquals(152, ChartRules.MIN_PLOT_HEIGHT_DP)
        assertEquals(4, ChartRules.MAX_GRIDLINES)
    }
}
