package app.discair.player.eq

import org.junit.Assert.assertEquals
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.log10
import kotlin.math.sin
import kotlin.math.sqrt

private fun cfg(vararg pairs: Pair<Int, Double>, auto: Boolean = true, pre: Double = 0.0): EqConfig {
    val g = MutableList(EQ_BAND_COUNT) { 0.0 }
    for ((i, v) in pairs) g[i] = v
    return EqConfig(enabled = true, bandGainsDb = g, preGainAuto = auto, preGainDb = pre)
}

private fun sine(freq: Double, rate: Int, frames: Int, channels: Int = 1, amp: Double = 0.1, from: Int = 0): FloatArray {
    val out = FloatArray(frames * channels)
    for (f in 0 until frames) for (c in 0 until channels) out[f * channels + c] = (amp * sin(2 * PI * freq * (f + from) / rate)).toFloat()
    return out
}

private fun rms(x: FloatArray, skip: Int = 0): Double {
    var s = 0.0; var n = 0
    for (i in skip until x.size) { s += x[i].toDouble() * x[i]; n++ }
    return sqrt(s / n)
}

class EqEngineTest {
    @Test fun peakingResponseHitsTheGainAtTheCentreAtSeveralRates() {
        for (rate in listOf(44100, 48000, 96000)) for (i in 0 until EQ_BAND_COUNT) for (g in listOf(-12.0, 6.0, 12.0)) {
            val c = BiquadCoefs.peaking(rate, EQ_BAND_HZ[i], g)
            assertEquals("rate $rate band $i gain $g", g, BiquadCoefs.responseDb(c, rate, EQ_BAND_HZ[i].toDouble()), 0.1)
        }
    }

    @Test fun peakingIsFlatFarFromTheCentre() {
        val c = BiquadCoefs.peaking(48000, 1000, 12.0)
        assertEquals(0.0, BiquadCoefs.responseDb(c, 48000, 31.0), 0.5)
        assertEquals(0.0, BiquadCoefs.responseDb(c, 48000, 16000.0), 1.0)
    }

    @Test fun bandsAboveNyquistLimitAreBypassed() {
        assertTrue(BiquadCoefs.peaking(22050, 16000, 12.0).isIdentity)
        assertTrue(BiquadCoefs.peaking(32000, 16000, 12.0).isIdentity)
        assertFalse(BiquadCoefs.peaking(44100, 16000, 12.0).isIdentity)
    }

    @Test fun flatAndOffAreBitExactBypass() {
        for (config in listOf(EqConfig(), cfg(), EqConfig(enabled = false, bandGainsDb = List(10) { 6.0 }))) {
            val e = EqEngine(44100, 2); e.setConfig(config)
            assertTrue(e.isBypassing)
            val input = sine(440.0, 44100, 4000, 2, 0.95)
            val buf = input.copyOf(); e.process(buf, 4000)
            assertArrayEquals(input, buf, 0f)
        }
    }

    @Test fun aBoostRaisesTheLevelAtItsBandAndAutoPreGainCompensates() {
        val rate = 48000
        val e = EqEngine(rate, 1); e.setConfig(cfg(5 to 6.0))
        val buf = sine(1000.0, rate, rate); e.process(buf, rate)
        val gainDb = 20 * log10(rms(buf, 2000) / rms(sine(1000.0, rate, rate), 2000))
        // +6 dB band, -6 dB pre-gain: unity at the centre.
        assertEquals(0.0, gainDb, 0.15)
        val far = sine(100.0, rate, rate); val f2 = far.copyOf(); e.process(f2, rate)
        assertTrue(rms(f2, 2000) < rms(far, 2000)) // away from the band only the pre-gain cut remains
    }

    @Test fun manualPreGainIsApplied() {
        val rate = 48000
        val e = EqEngine(rate, 1); e.setConfig(cfg(0 to 0.5, auto = false, pre = -6.0))
        val buf = sine(4000.0, rate, rate); e.process(buf, rate)
        val gainDb = 20 * log10(rms(buf, 2000) / rms(sine(4000.0, rate, rate), 2000))
        assertEquals(-6.0, gainDb, 0.2)
    }

    @Test fun autoPreGainValues() {
        assertEquals(0.0, cfg().effectivePreGainDb(), 0.0)
        assertEquals(-6.0, cfg(3 to 6.0, 4 to -3.0).effectivePreGainDb(), 0.0)
        assertEquals(0.0, cfg(3 to -6.0).effectivePreGainDb(), 0.0)
        assertEquals(-12.0, cfg(9 to 12.0).effectivePreGainDb(), 0.0)
        assertEquals(0.0, EqConfig(enabled = false, bandGainsDb = List(10) { 12.0 }).effectivePreGainDb(), 0.0)
    }

    @Test fun aFullScaleSineThroughTheMaximumBoostNeverExceedsFullScale() {
        val rate = 48000
        // Manual pre-gain 0 dB with +12 dB on every band is the worst case the limiter must catch.
        val e = EqEngine(rate, 2); e.setConfig(EqConfig(true, List(10) { 12.0 }, preGainAuto = false, preGainDb = 0.0))
        for (f in listOf(31.0, 1000.0, 8000.0)) {
            val buf = sine(f, rate, rate, 2, 1.0); e.process(buf, rate)
            assertTrue("peak at $f", buf.all { abs(it) <= 1.0f })
        }
    }

    @Test fun limiterIsTransparentBelowTheKneeAndMonotonic() {
        assertEquals(0.5, EqEngine.limit(0.5), 0.0); assertEquals(-0.9, EqEngine.limit(-0.9), 0.0)
        var prev = 0.0
        for (i in 0..400) { val y = EqEngine.limit(i / 100.0); assertTrue(y >= prev); assertTrue(y <= 1.0); prev = y }
    }

    @Test fun monoStereoAndSixChannelsAllWorkAndChannelsAreIndependent() {
        for (ch in listOf(1, 2, 6)) {
            val e = EqEngine(44100, ch); e.setConfig(cfg(5 to 9.0))
            val buf = sine(1000.0, 44100, 8000, ch)
            val before = buf.copyOf(); e.process(buf, 8000)
            assertFalse(buf.contentEquals(before))
            // every channel carries the same input, so every channel gets the same output
            for (f in 0 until 8000) for (c in 1 until ch) assertEquals(buf[f * ch], buf[f * ch + c], 0f)
        }
        val e = EqEngine(44100, 2); e.setConfig(cfg(5 to 9.0))
        val buf = FloatArray(16000) { if (it % 2 == 0) 0.2f * sin(it * 0.1).toFloat() else 0f }
        e.process(buf, 8000)
        assertTrue((0 until 8000).all { buf[it * 2 + 1] == 0f })
    }

    @Test fun anUpdateAfterTheFormatRateChangeUsesNewCoefficients() {
        val a = EqEngine(44100, 1); a.setConfig(cfg(8 to 12.0))
        val b = EqEngine(96000, 1); b.setConfig(cfg(8 to 12.0))
        val x44 = sine(8000.0, 44100, 20000); val x96 = sine(8000.0, 96000, 20000)
        a.process(x44, 20000); b.process(x96, 20000)
        val ga = 20 * log10(rms(x44, 5000) / rms(sine(8000.0, 44100, 20000), 5000))
        val gb = 20 * log10(rms(x96, 5000) / rms(sine(8000.0, 96000, 20000), 5000))
        assertEquals(ga, gb, 0.3)
    }

    @Test fun thereIsNoStepWhenASettingChangesWhilePlaying() {
        val rate = 48000
        val e = EqEngine(rate, 1); e.setConfig(cfg(5 to 12.0))
        val warm = sine(1000.0, rate, rate); e.process(warm, rate)
        val next = sine(1000.0, rate, 4000, from = rate)
        e.setConfig(cfg(5 to -12.0, auto = false))
        val ref = EqEngine(rate, 1); ref.setConfig(cfg(5 to 12.0)); ref.process(sine(1000.0, rate, rate), rate)
        e.process(next, 4000)
        var maxJump = 0.0
        for (i in 1 until next.size) maxJump = maxOf(maxJump, abs((next[i] - next[i - 1]).toDouble()))
        // A 1 kHz sine at 0.1 amplitude with at most about 4x gain moves < 0.06 per sample at 48 kHz.
        assertTrue("jump $maxJump", maxJump < 0.08)
    }

    @Test fun switchingToFlatRampsOutThenBypassesExactly() {
        val rate = 48000
        val e = EqEngine(rate, 1); e.setConfig(cfg(5 to 12.0))
        e.process(sine(1000.0, rate, 4000), 4000)
        e.setConfig(cfg())
        assertFalse(e.isBypassing) // still ramping
        e.process(sine(1000.0, rate, 4000), 4000)
        assertTrue(e.isBypassing)
        val input = sine(300.0, rate, 3000, amp = 0.8); val buf = input.copyOf(); e.process(buf, 3000)
        assertArrayEquals(input, buf, 0f)
    }

    @Test fun noSamplesAreAddedOrRemovedAndStateSurvivesBufferBoundaries() {
        val rate = 44100
        val whole = EqEngine(rate, 2); whole.setConfig(cfg(2 to 6.0, 7 to -4.0))
        val split = EqEngine(rate, 2); split.setConfig(cfg(2 to 6.0, 7 to -4.0))
        val x = sine(500.0, rate, 30001, 2)
        val a = x.copyOf(); whole.process(a, 30001)
        // The same audio in odd-sized pieces (a "song change" inside one stream) must give identical output.
        val b = x.copyOf(); var off = 0
        for (n in listOf(1, 77, 4096, 1234, 24593)) {
            val piece = b.copyOfRange(off * 2, (off + n) * 2); split.process(piece, n)
            piece.copyInto(b, off * 2); off += n
        }
        assertEquals(30001, off)
        assertArrayEquals(a, b, 0f)
    }

    @Test fun configIsClampedRoundedAndCorruptValuesAreSafe() {
        val c = EqConfig(true, listOf(99.0, -99.0, 0.26, 0.24, Double.NaN), true, 5.0).sanitized()
        assertEquals(12.0, c.bandGainsDb[0], 0.0); assertEquals(-12.0, c.bandGainsDb[1], 0.0)
        assertEquals(0.5, c.bandGainsDb[2], 0.0); assertEquals(0.0, c.bandGainsDb[3], 0.0)
        assertEquals(0.0, c.bandGainsDb[4], 0.0); assertEquals(0.0, c.bandGainsDb[9], 0.0)
        assertEquals(10, c.bandGainsDb.size); assertEquals(0.0, c.preGainDb, 0.0)
    }

    @Test fun anEngineWithMisshapenSettingsStillRuns() {
        val e = EqEngine(44100, 2); e.setConfig(EqConfig(true, listOf(Double.NaN, 1e9), false, Double.NaN))
        val buf = sine(440.0, 44100, 1000, 2); e.process(buf, 1000)
        assertTrue(buf.none { it.isNaN() })
    }
}
