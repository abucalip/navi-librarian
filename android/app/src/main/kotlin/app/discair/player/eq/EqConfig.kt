package app.discair.player.eq

import kotlin.math.max

/** Centre frequencies of the ten bands, in hertz (ANDROID_EQ_CONTRACT.md 5.1). */
val EQ_BAND_HZ: IntArray = intArrayOf(31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000)

const val EQ_BAND_COUNT = 10
const val EQ_MAX_GAIN_DB = 12.0
const val EQ_STEP_DB = 0.5

/**
 * The equalizer setting as the audio path sees it. Plain data, no Android types.
 * Gains are clamped and rounded to the 0.5 dB step by [sanitized]; the engine only ever sees sanitized values.
 */
data class EqConfig(
    val enabled: Boolean = false,
    val bandGainsDb: List<Double> = List(EQ_BAND_COUNT) { 0.0 },
    val preGainAuto: Boolean = true,
    val preGainDb: Double = 0.0,
) {
    fun sanitized(): EqConfig = EqConfig(
        enabled = enabled,
        bandGainsDb = List(EQ_BAND_COUNT) { i -> clampStep(bandGainsDb.getOrNull(i) ?: 0.0, EQ_MAX_GAIN_DB) },
        preGainAuto = preGainAuto,
        preGainDb = clampStep(preGainDb, EQ_MAX_GAIN_DB).coerceAtMost(0.0),
    )

    /** Pre-gain actually applied, in dB (<= 0). Automatic: the negative of the largest boost (5.2). */
    fun effectivePreGainDb(): Double {
        val c = sanitized()
        if (!c.enabled) return 0.0
        return if (c.preGainAuto) -max(0.0, c.bandGainsDb.max()) else c.preGainDb
    }

    /** True when the audio must pass through bit-exact: off, or every band and the pre-gain at 0 dB. */
    fun isBypass(): Boolean {
        val c = sanitized()
        return !c.enabled || (c.bandGainsDb.all { it == 0.0 } && c.effectivePreGainDb() == 0.0)
    }

    private fun clampStep(v: Double, limit: Double): Double {
        if (v.isNaN()) return 0.0
        val c = v.coerceIn(-limit, limit)
        return Math.round(c / EQ_STEP_DB) * EQ_STEP_DB + 0.0 // + 0.0 turns -0.0 into 0.0
    }
}
