package app.discair.player.crossfade

import kotlin.math.PI
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.sin

/** One update of a fade: the time since the fade began and the two gains to apply then. */
data class FadeStep(val atMs: Long, val outgoingGain: Float, val incomingGain: Float)

/**
 * Equal-power crossfade curve (ANDROID_CROSSFADE_CONTRACT.md 5.2): with progress t from 0 to 1 the outgoing gain
 * is cos(t·π/2) and the incoming gain is sin(t·π/2), so the squares of the gains always add up to 1 and unrelated
 * songs do not dip in loudness in the middle. No Android types, so it is tested in plain Kotlin.
 */
object FadeCurve {
    /** Progress is clamped to 0..1; NaN counts as 0. */
    private fun clamp(t: Double): Double = if (t.isNaN()) 0.0 else t.coerceIn(0.0, 1.0)

    fun outgoing(t: Double): Float = cos(clamp(t) * PI / 2).toFloat()
    fun incoming(t: Double): Float = sin(clamp(t) * PI / 2).toFloat()

    /** Progress for a time into a fade of [lengthMs]; a non-positive length is already finished. */
    fun progress(elapsedMs: Long, lengthMs: Long): Double =
        if (lengthMs <= 0) 1.0 else clamp(elapsedMs.toDouble() / lengthMs)

    /**
     * The whole ramp as steps at most [updateMs] apart (default 20 ms, contract 5.2), the first at 0 and the last
     * exactly at [lengthMs] with the outgoing gain 0 and the incoming gain 1. An empty list for a non-positive length.
     */
    fun ramp(lengthMs: Long, updateMs: Long = DEFAULT_UPDATE_MS): List<FadeStep> {
        if (lengthMs <= 0) return emptyList()
        val every = updateMs.coerceAtLeast(1)
        val count = ceil(lengthMs.toDouble() / every).toInt()
        return (0..count).map { i ->
            val at = if (i == count) lengthMs else i * every
            val t = progress(at, lengthMs)
            FadeStep(at, outgoing(t), incoming(t))
        }
    }

    const val DEFAULT_UPDATE_MS = 20L
}
