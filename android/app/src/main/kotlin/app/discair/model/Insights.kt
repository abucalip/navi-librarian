package app.discair.model

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull

/**
 * Insight cards (docs/SERVER_V2_CONTRACT.md, `GET /api/insights`). The server writes the title and body; the app shows
 * them as they are and never computes a card. Parsing is forgiving: a card the app cannot explain (no key or no
 * reasons) is dropped rather than shown unexplained, and unknown fields and lens kinds are kept out of the way.
 */

/** Why a card was shown (`reasons[]`). Evidence keys differ per lens, so they stay as plain JSON values. */
data class InsightReason(val kind: String, val evidence: Map<String, JsonElement>)

/** What a card is about. [key] is the dismiss and accept key and is kept exactly as the server wrote it. */
data class InsightSubject(
    val key: String,
    val type: String = "",
    val title: String? = null,
    val artist: String? = null,
    val mbid: String? = null,
    val year: Int? = null,
)

/** A run of missing chapters in a series card ("missing 3 to 5"). [labels] carry the year where the server gave one. */
data class InsightMissingRun(val firstPosition: Int, val lastPosition: Int, val labels: List<String>)

data class InsightCard(
    val kind: String,
    val title: String,
    val body: String,
    val subject: InsightSubject,
    val reasons: List<InsightReason>,
    val dismissible: Boolean,
    val score: Double,
    val owned: Int?,
    val total: Int?,
    val missingRuns: List<InsightMissingRun>,
) {
    val id get() = "$kind|${subject.key}"

    /** First non-null evidence value named [name] across the reasons. */
    fun evidence(name: String): JsonElement? =
        reasons.firstNotNullOfOrNull { r -> r.evidence[name]?.takeIf { it !is JsonNull } }

    fun evidenceInt(name: String): Int? = (evidence(name) as? JsonPrimitive)?.let { it.intOrNull ?: it.doubleOrNull?.toInt() }
    fun evidenceString(name: String): String? =
        (evidence(name) as? JsonPrimitive)?.takeIf { it.isString }?.contentOrNull?.takeIf { it.isNotEmpty() }
    fun hasReason(kind: String) = reasons.any { it.kind == kind }
}

/** One lens. `enabled == false` means off (show "off"); enabled with no cards is an empty state, never invented cards. */
data class InsightLens(val enabled: Boolean, val cards: List<InsightCard>)

data class InsightsResponse(val lenses: Map<String, InsightLens>, val dataVersion: Int, val generation: Int) {
    /** Lens kinds in dashboard order; kinds the app does not know yet follow, alphabetically. */
    val orderedKinds: List<String>
        get() = KnownOrder.filter { it in lenses } + lenses.keys.filter { it !in KnownOrder }.sorted()

    companion object {
        val KnownOrder = listOf("forgotten_gem", "series_completion", "blind_spot", "hidden_canon", "anniversary")
    }
}

private fun JsonObject.string(name: String) = (this[name] as? JsonPrimitive)?.takeIf { it.isString }?.content
private fun JsonObject.int(name: String) = (this[name] as? JsonPrimitive)?.let { it.intOrNull ?: it.doubleOrNull?.toInt() }
private fun JsonObject.obj(name: String) = this[name] as? JsonObject
private fun JsonObject.list(name: String) = (this[name] as? JsonArray).orEmpty()

private fun parseRun(element: JsonElement): InsightMissingRun? {
    val o = element as? JsonObject ?: return null
    val first = o.int("first_position") ?: 0
    val labels = o.list("items").mapNotNull { item ->
        val i = item as? JsonObject ?: return@mapNotNull null
        val title = i.string("title") ?: return@mapNotNull null
        i.int("year")?.let { "$title ($it)" } ?: title
    }
    return InsightMissingRun(first, o.int("last_position") ?: first, labels)
}

private fun parseCard(element: JsonElement): InsightCard? {
    val o = element as? JsonObject ?: return null
    val s = o.obj("subject") ?: return null
    val key = s.string("key").orEmpty()
    val reasons = o.list("reasons").mapNotNull { r ->
        val ro = r as? JsonObject ?: return@mapNotNull null
        InsightReason(ro.string("kind").orEmpty(), ro.obj("evidence").orEmpty())
    }
    // A card the app cannot explain is not shown.
    if (key.isEmpty() || reasons.isEmpty()) return null
    return InsightCard(
        kind = o.string("kind").orEmpty(),
        title = o.string("title").orEmpty().trim(),
        body = o.string("body").orEmpty().trim(),
        subject = InsightSubject(key, s.string("type").orEmpty(), s.string("title"), s.string("artist"), s.string("mbid"), s.int("year")),
        reasons = reasons,
        dismissible = (o["dismissible"] as? JsonPrimitive)?.booleanOrNull ?: false,
        score = (o["score"] as? JsonPrimitive)?.doubleOrNull ?: 0.0,
        owned = o.int("owned"),
        total = o.int("total"),
        missingRuns = o.list("missing_runs").mapNotNull(::parseRun),
    )
}

/** Parses a `GET /api/insights` body. A body that is not an object gives an empty response. */
fun parseInsights(body: String): InsightsResponse {
    val root = ApiJson.parseToJsonElement(body) as? JsonObject
    val lenses = root?.obj("lenses").orEmpty().mapNotNull { (kind, value) ->
        val lens = value as? JsonObject ?: return@mapNotNull null
        kind to InsightLens(
            enabled = (lens["enabled"] as? JsonPrimitive)?.booleanOrNull ?: false,
            cards = lens.list("cards").mapNotNull(::parseCard),
        )
    }.toMap()
    return InsightsResponse(lenses, root?.int("data_version") ?: 0, root?.int("generation") ?: 0)
}

/** The body of the dismiss, restore and accept routes: the card's own kind and key. */
fun insightWriteBody(kind: String, key: String): String =
    JsonObject(mapOf("kind" to JsonPrimitive(kind), "key" to JsonPrimitive(key))).toString()

/** The three write routes under `/api/insights/`. */
enum class InsightVerb(val wire: String) { Dismiss("dismiss"), Restore("restore"), Accept("accept") }
