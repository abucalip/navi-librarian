package app.discair.player.eq

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.pow
import kotlin.math.sin
import kotlin.math.tanh

/** Biquad coefficients, already divided by a0. */
class BiquadCoefs(var b0: Double = 1.0, var b1: Double = 0.0, var b2: Double = 0.0, var a1: Double = 0.0, var a2: Double = 0.0) {
    fun set(o: BiquadCoefs) { b0 = o.b0; b1 = o.b1; b2 = o.b2; a1 = o.a1; a2 = o.a2 }
    val isIdentity: Boolean get() = b0 == 1.0 && b1 == 0.0 && b2 == 0.0 && a1 == 0.0 && a2 == 0.0

    companion object {
        const val Q = 1.41

        /** RBJ peaking filter. A band at 0 dB, or above 0.45 x the sample rate, is the identity. */
        fun peaking(sampleRate: Int, freqHz: Int, gainDb: Double): BiquadCoefs {
            if (gainDb == 0.0 || freqHz > 0.45 * sampleRate) return BiquadCoefs()
            val a = 10.0.pow(gainDb / 40.0)
            val w0 = 2.0 * PI * freqHz / sampleRate
            val alpha = sin(w0) / (2.0 * Q)
            val cosw = cos(w0)
            val a0 = 1.0 + alpha / a
            return BiquadCoefs(
                b0 = (1.0 + alpha * a) / a0,
                b1 = (-2.0 * cosw) / a0,
                b2 = (1.0 - alpha * a) / a0,
                a1 = (-2.0 * cosw) / a0,
                a2 = (1.0 - alpha / a) / a0,
            )
        }

        /** Magnitude response in dB of one filter at [freqHz]. Used by tests and the screen's curve. */
        fun responseDb(c: BiquadCoefs, sampleRate: Int, freqHz: Double): Double {
            val w = 2.0 * PI * freqHz / sampleRate
            val cr = cos(w); val ci = -sin(w)
            val c2r = cos(2 * w); val c2i = -sin(2 * w)
            val nr = c.b0 + c.b1 * cr + c.b2 * c2r; val ni = c.b1 * ci + c.b2 * c2i
            val dr = 1.0 + c.a1 * cr + c.a2 * c2r; val di = c.a1 * ci + c.a2 * c2i
            val num = nr * nr + ni * ni; val den = dr * dr + di * di
            return 10.0 * kotlin.math.log10(num / den)
        }
    }
}

/**
 * The equalizer for one stream format: ten peaking filters, a pre-gain and a soft limiter, on interleaved
 * float samples in -1..1. No Android types (ANDROID_EQ_CONTRACT.md 4, 5.1, 5.2).
 *
 * - Bit-exact bypass when the setting is off or flat and no change is still ramping.
 * - A change of setting moves the coefficients and the gain in a straight line over [RAMP_SECONDS], so there is
 *   no click. The filter state is kept, never reset, so a song change cannot click either.
 * - The engine adds no delay: it returns exactly as many samples as it is given.
 */
class EqEngine(val sampleRate: Int, val channels: Int) {
    private val current = Array(EQ_BAND_COUNT) { BiquadCoefs() }
    private val target = Array(EQ_BAND_COUNT) { BiquadCoefs() }
    private val step = Array(EQ_BAND_COUNT) { DoubleArray(5) }
    private var gain = 1.0
    private var targetGain = 1.0
    private var gainStep = 0.0
    private var rampLeft = 0
    private var started = false
    private var bypass = true
    // z1, z2 per channel per band
    private val z1 = Array(channels) { DoubleArray(EQ_BAND_COUNT) }
    private val z2 = Array(channels) { DoubleArray(EQ_BAND_COUNT) }
    private val rampSamples = maxOf(1, (RAMP_SECONDS * sampleRate).toInt())

    /** True while samples are returned untouched. */
    val isBypassing: Boolean get() = bypass && rampLeft == 0

    fun setConfig(raw: EqConfig) {
        val c = raw.sanitized()
        val flat = c.isBypass()
        for (i in 0 until EQ_BAND_COUNT) {
            val t = if (flat) BiquadCoefs() else BiquadCoefs.peaking(sampleRate, EQ_BAND_HZ[i], c.bandGainsDb[i])
            target[i].set(t)
        }
        targetGain = if (flat) 1.0 else 10.0.pow(c.effectivePreGainDb() / 20.0)
        if (!started) {
            started = true
            for (i in 0 until EQ_BAND_COUNT) current[i].set(target[i])
            gain = targetGain
            rampLeft = 0
        } else {
            for (i in 0 until EQ_BAND_COUNT) {
                val s = step[i]; val cu = current[i]; val t = target[i]
                s[0] = (t.b0 - cu.b0) / rampSamples; s[1] = (t.b1 - cu.b1) / rampSamples
                s[2] = (t.b2 - cu.b2) / rampSamples; s[3] = (t.a1 - cu.a1) / rampSamples
                s[4] = (t.a2 - cu.a2) / rampSamples
            }
            gainStep = (targetGain - gain) / rampSamples
            rampLeft = rampSamples
        }
        bypass = flat
    }

    /** Processes [frames] frames of interleaved samples in place. */
    fun process(buf: FloatArray, frames: Int) {
        if (isBypassing) return
        var idx = 0
        for (f in 0 until frames) {
            if (rampLeft > 0) advanceRamp()
            for (ch in 0 until channels) {
                var x = buf[idx].toDouble() * gain
                val a = z1[ch]; val b = z2[ch]
                for (i in 0 until EQ_BAND_COUNT) {
                    val c = current[i]
                    if (c.isIdentity && a[i] == 0.0 && b[i] == 0.0) continue
                    val y = c.b0 * x + a[i]
                    a[i] = c.b1 * x - c.a1 * y + b[i]
                    b[i] = c.b2 * x - c.a2 * y
                    x = y
                }
                buf[idx] = limit(x).toFloat()
                idx++
            }
        }
    }

    private fun advanceRamp() {
        rampLeft--
        if (rampLeft == 0) {
            for (i in 0 until EQ_BAND_COUNT) current[i].set(target[i])
            gain = targetGain
            if (bypass) clearState()
            return
        }
        for (i in 0 until EQ_BAND_COUNT) {
            val c = current[i]; val s = step[i]
            c.b0 += s[0]; c.b1 += s[1]; c.b2 += s[2]; c.a1 += s[3]; c.a2 += s[4]
        }
        gain += gainStep
    }

    private fun clearState() {
        for (ch in 0 until channels) { z1[ch].fill(0.0); z2[ch].fill(0.0) }
    }

    companion object {
        const val RAMP_SECONDS = 0.02
        private const val KNEE = 0.9

        /** Transparent up to 0.9, then a smooth curve that never exceeds 1.0. */
        fun limit(x: Double): Double {
            val ax = kotlin.math.abs(x)
            if (ax <= KNEE) return x
            val over = tanh((ax - KNEE) / (1.0 - KNEE)) * (1.0 - KNEE)
            return if (x < 0) -(KNEE + over) else KNEE + over
        }
    }
}
