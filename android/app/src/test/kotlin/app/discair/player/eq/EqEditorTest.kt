package app.discair.player.eq

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class EqEditorTest {
    private fun editor(s: EqSettings = EqSettings()) = EqEditor(MemoryEqSettingsStore(s))

    @Test fun everyPresetHasTenStepAlignedGainsInRangeAndUniqueIds() {
        assertEquals(9, EQ_PRESETS.size); assertEquals("flat", EQ_PRESETS[0].id)
        assertEquals(EQ_PRESETS.size, EQ_PRESETS.map { it.id }.toSet().size)
        for (p in EQ_PRESETS) {
            assertEquals(p.id, 10, p.gainsDb.size)
            assertTrue(p.id, p.gainsDb.all { it in -12.0..12.0 && (it / 0.5) % 1.0 == 0.0 })
            assertTrue(p.id, EqSettings.sanitizePresetId(p.id) == p.id)
        }
        assertTrue(EQ_PRESETS[0].gainsDb.all { it == 0.0 })
    }

    @Test fun choosingAPresetSetsTheBandsAndName() {
        val e = editor(); e.selectPreset("rock")
        assertEquals("rock", e.state.value.presetId)
        assertEquals(EQ_PRESETS.first { it.id == "rock" }.gainsDb, e.state.value.config.bandGainsDb)
    }

    @Test fun movingABandSwitchesToCustomAndNeverChangesAPreset() {
        val before = EQ_PRESETS.map { it.copy() }
        val e = editor(); e.selectPreset("rock"); e.nudgeBand(0, +1)
        assertEquals("custom", e.state.value.presetId)
        assertEquals(4.5, e.state.value.config.bandGainsDb[0], 0.0)
        assertEquals(e.state.value.config.bandGainsDb, e.state.value.customGainsDb)
        assertEquals(before, EQ_PRESETS)
    }

    @Test fun customKeepsTheHandMadeCurveWhileAPresetIsChosenInBetween() {
        val e = editor(); e.setBand(2, 5.0); e.setBand(7, -3.5)
        val mine = e.state.value.config.bandGainsDb
        e.selectPreset("vocal"); assertEquals("vocal", e.state.value.presetId)
        assertEquals(mine, e.state.value.customGainsDb)
        e.selectPreset("custom")
        assertEquals("custom", e.state.value.presetId); assertEquals(mine, e.state.value.config.bandGainsDb)
    }

    @Test fun nudgesStopAtTheLimitsAndAnIndexOutOfRangeDoesNothing() {
        val e = editor(); repeat(40) { e.nudgeBand(3, +1) }
        assertEquals(12.0, e.state.value.config.bandGainsDb[3], 0.0)
        repeat(80) { e.nudgeBand(3, -1) }
        assertEquals(-12.0, e.state.value.config.bandGainsDb[3], 0.0)
        val s = e.state.value; e.nudgeBand(10, 1); e.nudgeBand(-1, 1); e.setBand(99, 3.0)
        assertEquals(s, e.state.value)
    }

    @Test fun resetGoesFlatClearsCustomKeepsOnOffAndRestoresAutoPreGain() {
        val e = editor(); e.setEnabled(true); e.setBand(1, 6.0); e.setPreGainAuto(false); e.setPreGain(-3.0)
        e.reset()
        val s = e.state.value
        assertTrue(s.config.enabled); assertEquals("flat", s.presetId)
        assertTrue(s.config.bandGainsDb.all { it == 0.0 }); assertTrue(s.customGainsDb.all { it == 0.0 })
        assertTrue(s.config.preGainAuto); assertEquals(0.0, s.config.preGainDb, 0.0)
    }

    @Test fun preGainStaysAtOrBelowZeroAndEveryChangeIsSaved() {
        val store = MemoryEqSettingsStore(); val e = EqEditor(store)
        e.setPreGainAuto(false); e.nudgePreGain(+5); assertEquals(0.0, e.state.value.config.preGainDb, 0.0)
        e.nudgePreGain(-3); assertEquals(-1.5, store.load().config.preGainDb, 0.0)
        e.setEnabled(true); assertTrue(store.load().config.enabled)
    }

    @Test fun anEditorStartsFromWhatWasSaved() {
        val e = editor(EqSettings(EqConfig(true, List(10) { 1.0 }), "custom", List(10) { 1.0 }))
        assertTrue(e.state.value.config.enabled); assertEquals("custom", e.state.value.presetId)
    }

    @Test fun textForTheScreenAndForTalkBack() {
        assertEquals("62 Hz", bandLabel(62)); assertEquals("1 kHz", bandLabel(1000)); assertEquals("16 kHz", bandLabel(16000))
        assertEquals("62 hertz", bandSpoken(62)); assertEquals("16 kilohertz", bandSpoken(16000))
        assertEquals("+3.5 dB", formatDb(3.5)); assertEquals("−2 dB", formatDb(-2.0)); assertEquals("0 dB", formatDb(0.0))
        assertEquals("plus 3.5 decibels", formatDb(3.5, spoken = true))
        assertEquals("minus 1 decibel", formatDb(-1.0, spoken = true))
        assertEquals("minus 12 decibels", formatDb(-12.0, spoken = true))
        assertEquals("0 decibels", formatDb(0.0, spoken = true))
    }

    @Test fun summaryAndStatusLinesAreInWords() {
        assertEquals("Equalizer: off", eqSummary(EqSettings()))
        assertEquals("Equalizer: Rock", eqSummary(EqSettings(EqConfig(enabled = true), "rock")))
        assertEquals("Equalizer: Custom", eqSummary(EqSettings(EqConfig(enabled = true), "custom")))
        assertEquals("Equalizer: Flat", eqSummary(EqSettings(EqConfig(enabled = true), "nonsense")))
        assertNull(eqStatusLine(true, EqRuntimeStatus()))
        assertNull(eqStatusLine(false, EqRuntimeStatus(appliesToThisSong = false)))
        assertEquals("Not applied to this song.", eqStatusLine(true, EqRuntimeStatus(appliesToThisSong = false)))
        assertEquals("Equalizer unavailable for this song.", eqStatusLine(true, EqRuntimeStatus(faulted = true, appliesToThisSong = false)))
    }

    @Test fun theCustomCurveSurvivesTheStoreAndHostileCustomValuesAreClamped() {
        val store = MemoryEqSettingsStore()
        store.save(EqSettings(customGainsDb = listOf(99.0, Double.NaN, 1.3)))
        val c = store.load().customGainsDb
        assertEquals(10, c.size); assertEquals(12.0, c[0], 0.0); assertEquals(0.0, c[1], 0.0); assertEquals(1.5, c[2], 0.0)
        assertFalse(store.load().config.enabled)
    }
}
