package app.discair.ui

import app.discair.ui.common.ChartRules
import app.discair.ui.common.MarkShape
import app.discair.ui.radio.FlowRadioRules
import app.discair.ui.theme.Family
import app.discair.ui.theme.Layout
import app.discair.ui.theme.Palettes
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class FlowRadioDownloadsStatsRulesTest {
    @Test fun radioSizesAreTheMockups() {
        // flow.css: .lg 48 with radius 10, .li .cv 48, .npc 312 with radius 18, .cb.main 72.
        assertEquals(48, FlowRadioRules.LOGO)
        assertEquals(10, FlowRadioRules.LOGO_RADIUS)
        assertEquals(312, FlowRadioRules.LIVE_COVER)
        assertEquals(18, FlowRadioRules.LIVE_COVER_RADIUS)
        assertEquals(72, FlowRadioRules.PLAY_BUTTON)
    }

    @Test fun flowChartsAreRoundedWithAnArea() {
        val flow = ChartRules.style(Palettes.Flow.family, Layout.Flow, true)
        assertEquals(MarkShape.Rounded, flow.marks)
        assertTrue(flow.area)
        assertEquals(3f, flow.barRadiusDp)
        assertEquals(2f, flow.lineWidthDp)
    }

    @Test fun noOtherLayoutsChartMoved() {
        assertEquals(false, ChartRules.style(Family.Brutal, Layout.Standard, true).area)
        assertEquals(MarkShape.Outlined, ChartRules.style(Palettes.SoftBrut.family, Layout.CoverStack, true).marks)
        assertEquals(MarkShape.Rounded, ChartRules.style(Family.Classic, Layout.Standard, light = true).marks)
        assertEquals(false, ChartRules.style(Family.Classic, Layout.Standard, light = false).area)
    }
}
