package app.discair.model

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlin.math.abs
import kotlin.math.roundToInt

/**
 * Taste profiles (docs/SERVER_V2_CONTRACT.md, `GET /api/insights/taste`). The server writes the headline and lists every
 * shift; the app draws them as given. It never composes prose, never states a shift that is not listed, and shows a
 * window or dimension the server flagged low-sample as progress, not as a finding. Parsing is forgiving: an unknown or
 * missing flag means "not sound".
 */

data class TasteEntry(val value: String, val count: Int, val share: Double)

data class TasteWindow(
    val listens: Int,
    val lowSample: Boolean,
    val dimensionLowSample: Map<String, Boolean>,
    val dimensions: Map<String, List<TasteEntry>>,
) {
    fun isLowSample(dimension: String) = dimensionLowSample[dimension] ?: true
    fun entries(dimension: String) = dimensions[dimension].orEmpty()
}

data class TasteShift(
    val window: String,
    val dimension: String,
    val value: String,
    val direction: String,
    val fromShare: Double,
    val toShare: Double,
) {
    val isUp get() = direction == "up"
}

data class TasteHeadline(val text: String, val kind: String, val window: String)

data class TasteProfiles(
    val headline: TasteHeadline?,
    val windows: Map<String, TasteWindow>,
    val shifts: List<TasteShift>,
    val recentDays: Int,
    val minListens: Int,
) {
    fun window(name: String) = windows[name]

    /** Shifts of one window, biggest move first. Only what the server listed. */
    fun shifts(window: String) = shifts.filter { it.window == window }.sortedByDescending { abs(it.toShare - it.fromShare) }

    companion object {
        val WindowNames = listOf("recent", "mid", "all_time")
        val Dimensions = listOf("genre", "era", "area", "label", "collaborator")
    }
}

/** `profiles` is null until a refresh has saved some ("not computed yet"). */
data class TasteResponse(
    val profiles: TasteProfiles?,
    val dataVersion: Int,
    val generation: Int,
    /** D2: listens per UTC day, oldest first, ending the day before today. Null until a refresh has saved it. */
    val listensByDay: List<ListensDay>? = null,
)

/** One day of listens. [date] is a UTC calendar day, "2026-11-10". */
data class ListensDay(val date: String, val count: Int)

/** `POST /api/insights/taste/refresh`: `state` is refreshed, unchanged, too_soon, failed or no_listens_source. */
data class TasteRefreshResult(val state: String, val changed: Boolean, val retryAfter: Double, val error: String?)

/** What the card shows. The server's flags decide it; the app adds no thresholds of its own. */
sealed interface TasteCardState {
    /** Nothing saved yet, or no window at all. */
    data object Empty : TasteCardState

    /** Windows exist but none is sound enough for a headline: show progress toward [need] listens. */
    data class Thin(val have: Int, val need: Int) : TasteCardState

    /** The server's headline, with the movers it listed for the headline's window. */
    data class Ready(val headline: TasteHeadline, val movers: List<TasteShift>, val windowListens: Int, val allTimeListens: Int) : TasteCardState
}

object TasteCard {
    /** The card shows the three biggest movers; the sheet shows all of them. */
    const val ChipCount = 3

    fun state(profiles: TasteProfiles?): TasteCardState {
        if (profiles == null || profiles.windows.isEmpty()) return TasteCardState.Empty
        val headline = profiles.headline
        if (headline == null) {
            val recent = profiles.window("recent")
            return TasteCardState.Thin(recent?.listens ?: 0, profiles.minListens)
        }
        return TasteCardState.Ready(
            headline,
            profiles.shifts(headline.window),
            profiles.window(headline.window)?.listens ?: 0,
            profiles.window("all_time")?.listens ?: 0,
        )
    }

    /** 0..1 for the progress bar; never above one and never negative. */
    fun progress(have: Int, need: Int): Double = if (need <= 0) 1.0 else (have.toDouble() / need).coerceIn(0.0, 1.0)

    fun percent(share: Double): Int = (share * 100).roundToInt()

    /** "90 days" for the recent window, "past year" for mid, which the server uses when recent is low-sample. */
    fun windowLabel(window: String, recentDays: Int) = when (window) {
        "mid" -> "Past year"
        "all_time" -> "All time"
        else -> "$recentDays days"
    }
}

private fun JsonObject.string(name: String) = (this[name] as? JsonPrimitive)?.takeIf { it.isString }?.content
private fun JsonObject.int(name: String) = (this[name] as? JsonPrimitive)?.let { it.intOrNull ?: it.doubleOrNull?.toInt() }
private fun JsonObject.double(name: String) = (this[name] as? JsonPrimitive)?.doubleOrNull
private fun JsonObject.obj(name: String) = this[name] as? JsonObject
private fun JsonObject.list(name: String) = (this[name] as? JsonArray).orEmpty()

private fun parseEntry(element: JsonElement): TasteEntry? {
    val o = element as? JsonObject ?: return null
    val value = o.string("value")?.takeIf { it.isNotEmpty() } ?: return null
    return TasteEntry(value, o.int("count") ?: 0, o.double("share") ?: 0.0)
}

private fun parseWindow(o: JsonObject) = TasteWindow(
    listens = o.int("listens") ?: 0,
    lowSample = (o["low_sample"] as? JsonPrimitive)?.booleanOrNull ?: true,
    dimensionLowSample = o.obj("dimension_low_sample").orEmpty().mapNotNull { (k, v) -> (v as? JsonPrimitive)?.booleanOrNull?.let { k to it } }.toMap(),
    dimensions = o.obj("dimensions").orEmpty().mapValues { (_, v) -> (v as? JsonArray).orEmpty().mapNotNull(::parseEntry) },
)

private fun parseShift(element: JsonElement): TasteShift? {
    val o = element as? JsonObject ?: return null
    val value = o.string("value")?.takeIf { it.isNotEmpty() } ?: return null
    return TasteShift(o.string("window").orEmpty(), o.string("dimension").orEmpty(), value, o.string("direction").orEmpty(), o.double("from_share") ?: 0.0, o.double("to_share") ?: 0.0)
}

private fun parseProfiles(o: JsonObject): TasteProfiles {
    val headline = o.obj("headline")?.let { h ->
        h.string("text")?.trim()?.takeIf { it.isNotEmpty() }?.let { TasteHeadline(it, h.string("kind").orEmpty(), h.string("window").orEmpty()) }
    }
    val config = o.obj("config")
    return TasteProfiles(
        headline = headline,
        windows = o.obj("windows").orEmpty().mapNotNull { (k, v) -> (v as? JsonObject)?.let { k to parseWindow(it) } }.toMap(),
        shifts = o.list("shifts").mapNotNull(::parseShift),
        recentDays = config?.double("recent_days")?.toInt() ?: 90,
        minListens = config?.int("min_listens") ?: 50,
    )
}

/** Parses a `GET /api/insights/taste` body. A body that is not an object, or a null `profiles`, gives "not computed yet". */
fun parseTaste(body: String): TasteResponse {
    val root = runCatching { ApiJson.parseToJsonElement(body) }.getOrNull() as? JsonObject
    // A missing or malformed series is "not served", never zero days; a bad entry drops only itself.
    val days = (root?.get("listens_by_day") as? kotlinx.serialization.json.JsonArray)?.mapNotNull { e ->
        val o = e as? JsonObject ?: return@mapNotNull null
        val date = o.string("date") ?: return@mapNotNull null
        val count = o.int("count")?.takeIf { it >= 0 } ?: return@mapNotNull null
        ListensDay(date, count)
    }
    return TasteResponse(
        root?.obj("profiles")?.let(::parseProfiles), root?.int("data_version") ?: 0, root?.int("generation") ?: 0, days,
    )
}

fun parseTasteRefresh(body: String): TasteRefreshResult {
    val o = runCatching { ApiJson.parseToJsonElement(body) }.getOrNull() as? JsonObject
    return TasteRefreshResult(
        o?.string("state") ?: "failed",
        (o?.get("changed") as? JsonPrimitive)?.booleanOrNull ?: false,
        o?.double("retry_after") ?: 0.0,
        o?.string("error"),
    )
}
