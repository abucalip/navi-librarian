package app.discair.model

import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.intOrNull

/**
 * The sound graph's data (`GET /api/songs/{id}/peaks`): one value from 0 to 1 per bar. The server answers 200 with the
 * peaks, 202 while it is still decoding the song (ask again in a few seconds) and 404 when there is nothing to draw.
 */
sealed interface PeaksResult {
    class Ready(val peaks: FloatArray) : PeaksResult
    data object Pending : PeaksResult
    /** Nothing to draw: the seek bar stays plain, as it is today. */
    data object None : PeaksResult
}

const val PEAK_MAX = 65535f

fun parsePeaks(code: Int, body: String): PeaksResult {
    if (code == 202) return PeaksResult.Pending
    if (code != 200) return PeaksResult.None
    val root = try { ApiJson.parseToJsonElement(body) as? JsonObject } catch (e: SerializationException) { null } ?: return PeaksResult.None
    val raw = (root["peaks"] as? JsonArray).orEmpty().mapNotNull { (it as? JsonPrimitive)?.intOrNull }
    if (raw.size < 2) return PeaksResult.None
    return PeaksResult.Ready(FloatArray(raw.size) { (raw[it] / PEAK_MAX).coerceIn(0f, 1f) })
}

/** The graph is drawn with fewer bars than the server sends: each bar is the loudest of its slice. */
fun FloatArray.fold(bars: Int): FloatArray {
    if (bars <= 0 || isEmpty()) return FloatArray(0)
    if (bars >= size) return copyOf()
    return FloatArray(bars) { i ->
        val lo = i * size / bars
        val hi = maxOf((i + 1) * size / bars, lo + 1)
        var top = 0f
        for (j in lo until hi) if (this[j] > top) top = this[j]
        top
    }
}
