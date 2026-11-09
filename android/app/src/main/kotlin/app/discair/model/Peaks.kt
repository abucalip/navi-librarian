package app.discair.model

import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
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

/** The client hands over bodies of successful answers only (200 and 202 both are), so pending is told by its body; a 404 never gets here. */
fun parsePeaks(body: String): PeaksResult {
    val root = try { ApiJson.parseToJsonElement(body) as? JsonObject } catch (e: SerializationException) { null } ?: return PeaksResult.None
    if ((root["status"] as? JsonPrimitive)?.contentOrNull == "pending") return PeaksResult.Pending
    val raw = (root["peaks"] as? JsonArray).orEmpty().mapNotNull { (it as? JsonPrimitive)?.intOrNull }
    if (raw.size < 2) return PeaksResult.None
    return PeaksResult.Ready(FloatArray(raw.size) { (raw[it] / PEAK_MAX).coerceIn(0f, 1f) })
}

/**
 * Asks for the peaks until they are ready: the server answers pending while it decodes the song. Gives up after [tries]
 * pending answers (the seek bar stays plain). A failure of [ask] is no graph, never an error shown.
 */
suspend fun loadPeaks(tries: Int = 12, waitMs: Long = 5000, ask: suspend () -> PeaksResult): FloatArray? {
    repeat(tries) {
        when (val r = try { ask() } catch (e: kotlinx.coroutines.CancellationException) { throw e } catch (e: Exception) { PeaksResult.None }) {
            is PeaksResult.Ready -> return r.peaks
            PeaksResult.None -> return null
            PeaksResult.Pending -> kotlinx.coroutines.delay(waitMs)
        }
    }
    return null
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
