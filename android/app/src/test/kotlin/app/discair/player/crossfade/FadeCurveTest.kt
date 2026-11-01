package app.discair.player.crossfade

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

class FadeCurveTest {
    @Test fun gainsAtTheStartMiddleAndEnd() {
        assertEquals(1f, FadeCurve.outgoing(0.0), 1e-6f)
        assertEquals(0f, FadeCurve.incoming(0.0), 1e-6f)
        assertEquals(0.70710678f, FadeCurve.outgoing(0.5), 1e-6f)
        assertEquals(0.70710678f, FadeCurve.incoming(0.5), 1e-6f)
        assertEquals(0f, FadeCurve.outgoing(1.0), 1e-6f)
        assertEquals(1f, FadeCurve.incoming(1.0), 1e-6f)
    }

    @Test fun squaredGainsAlwaysAddUpToOne() {
        for (i in 0..1000) {
            val t = i / 1000.0
            val sum = FadeCurve.outgoing(t).let { it * it } + FadeCurve.incoming(t).let { it * it }
            assertEquals("t=$t", 1f, sum, 1e-5f)
        }
    }

    @Test fun progressOutsideTheRangeOrNotANumberIsClamped() {
        assertEquals(1f, FadeCurve.outgoing(-3.0), 1e-6f)
        assertEquals(0f, FadeCurve.incoming(-3.0), 1e-6f)
        assertEquals(0f, FadeCurve.outgoing(7.0), 1e-6f)
        assertEquals(1f, FadeCurve.incoming(7.0), 1e-6f)
        assertEquals(1f, FadeCurve.outgoing(Double.NaN), 1e-6f)
        assertEquals(0f, FadeCurve.incoming(Double.NaN), 1e-6f)
        assertEquals(1.0, FadeCurve.progress(100, 0), 0.0)
        assertEquals(1.0, FadeCurve.progress(100, -5), 0.0)
        assertEquals(0.5, FadeCurve.progress(2_500, 5_000), 1e-9)
        assertEquals(1.0, FadeCurve.progress(99_999, 5_000), 0.0)
    }

    @Test fun rampStartsAtZeroEndsExactlyAtTheLengthAndIsMonotonic() {
        for (length in listOf(1_000L, 5_000L, 12_000L, 1_234L)) {
            val steps = FadeCurve.ramp(length)
            assertEquals(0L, steps.first().atMs)
            assertEquals(length, steps.last().atMs)
            assertEquals(1f, steps.first().outgoingGain, 1e-6f)
            assertEquals(0f, steps.first().incomingGain, 1e-6f)
            assertEquals(0f, steps.last().outgoingGain, 1e-6f)
            assertEquals(1f, steps.last().incomingGain, 1e-6f)
            steps.zipWithNext().forEach { (a, b) ->
                assertTrue(b.atMs > a.atMs)
                assertTrue(b.atMs - a.atMs <= FadeCurve.DEFAULT_UPDATE_MS)
                assertTrue(b.outgoingGain <= a.outgoingGain)
                assertTrue(b.incomingGain >= a.incomingGain)
            }
        }
    }

    @Test fun noStepIsLargerThanTheBoundPerUpdate() {
        // The curve's steepest slope is π/2 per fade length, so a 20 ms step of a 1 s fade changes a gain by at most about 0.032.
        val worst = FadeCurve.ramp(1_000L).zipWithNext().maxOf { (a, b) ->
            maxOf(abs(b.outgoingGain - a.outgoingGain), abs(b.incomingGain - a.incomingGain))
        }
        assertTrue("largest step $worst", worst < 0.035f)
    }

    @Test fun rampOfNothingIsEmptyAndTheUpdateIntervalIsKeptAboveZero() {
        assertTrue(FadeCurve.ramp(0).isEmpty())
        assertTrue(FadeCurve.ramp(-10).isEmpty())
        val steps = FadeCurve.ramp(50, updateMs = 0)
        assertEquals(51, steps.size)
        assertEquals(50L, steps.last().atMs)
    }
}
