package app.discair.player.eq

import app.discair.player.ReleaseGuard
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

private class RecordingTarget(var fail: Boolean = false) : EqTarget {
    val seen = mutableListOf<EqConfig>()
    override fun setConfig(config: EqConfig) { if (fail) error("boom"); seen += config }
}

class EqSettingsTest {
    private fun on(vararg g: Double) = EqConfig(true, g.toList() + List(10 - g.size) { 0.0 })

    @Test fun defaultsAreOffFlatAndAuto() {
        val s = EqSettings()
        assertFalse(s.config.enabled); assertTrue(s.config.isBypass()); assertTrue(s.config.preGainAuto)
        assertEquals("flat", s.presetId)
    }

    @Test fun hostileValuesAreClampedAndPresetIdsValidated() {
        val s = EqSettings(EqConfig(true, listOf(99.0, Double.NaN), false, 50.0), "../../etc").sanitized()
        assertEquals(12.0, s.config.bandGainsDb[0], 0.0); assertEquals(0.0, s.config.bandGainsDb[1], 0.0)
        assertEquals(10, s.config.bandGainsDb.size); assertEquals(0.0, s.config.preGainDb, 0.0)
        assertEquals("flat", s.presetId)
        assertEquals("custom", EqSettings(presetId = "custom").sanitized().presetId)
        assertEquals("flat", EqSettings(presetId = "A".repeat(40)).sanitized().presetId)
    }

    @Test fun storeRoundTripsAndSanitizesOnSave() {
        val store = MemoryEqSettingsStore()
        store.save(EqSettings(on(3.5, -2.0), "rock"))
        assertEquals(3.5, store.load().config.bandGainsDb[0], 0.0); assertEquals("rock", store.load().presetId)
        store.save(EqSettings(on(500.0)))
        assertEquals(12.0, store.load().config.bandGainsDb[0], 0.0)
    }

    @Test fun bindingAppliesAtOnceThenOnEveryChangeAndStopsWhenClosed() {
        val store = MemoryEqSettingsStore(EqSettings(on(2.0)))
        val target = RecordingTarget()
        val binding = EqBinding(store, target)
        assertEquals(1, target.seen.size); assertEquals(2.0, target.seen[0].bandGainsDb[0], 0.0)
        store.save(EqSettings(on(4.0)))
        assertEquals(2, target.seen.size); assertEquals(4.0, target.seen[1].bandGainsDb[0], 0.0)
        binding.close(); binding.close()
        store.save(EqSettings(on(6.0)))
        assertEquals(2, target.seen.size); assertEquals(0, store.listenerCount)
    }

    @Test fun aFailingTargetNeverBreaksTheBindingOrTheSaver() {
        val store = MemoryEqSettingsStore(); val target = RecordingTarget(fail = true)
        EqBinding(store, target)
        store.save(EqSettings(on(2.0))) // must not throw
        target.fail = false
        store.save(EqSettings(on(3.0)))
        assertEquals(3.0, target.seen.last().bandGainsDb[0], 0.0)
    }

    @Test fun theListenerIsReleasedWithThePlayer() {
        val store = MemoryEqSettingsStore()
        val binding = EqBinding(store, RecordingTarget())
        val guard = ReleaseGuard { binding.close() }
        assertEquals(1, store.listenerCount)
        guard.release(); guard.release()
        assertEquals(0, store.listenerCount)
    }

    @Test fun theProcessorTakesTheBoundSettings() {
        val store = MemoryEqSettingsStore(EqSettings(on(0.0, 0.0, 0.0, 0.0, 0.0, 8.0)))
        val p = EqAudioProcessor(); val b = EqBinding(store, p)
        store.save(EqSettings(on(1.0))); b.close()
        assertFalse(p.hasFaulted)
    }
}
