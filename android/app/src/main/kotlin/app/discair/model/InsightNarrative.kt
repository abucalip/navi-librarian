package app.discair.model

import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

/**
 * The "Why?" text of an insight card: one short paragraph written from the numbers and names the card carries, so what
 * the owner reads matches what is on screen. It states facts (a count, a date, a listen total) and never advises.
 * Same wording as the macOS client.
 */
object InsightNarrative {
    fun why(card: InsightCard): String {
        val text = when (card.kind) {
            "series_completion" -> series(card)
            "hidden_canon" -> hiddenCanon(card)
            "anniversary" -> anniversary(card)
            "forgotten_gem" -> forgottenGem(card)
            "blind_spot" -> blindSpot(card)
            else -> ""
        }
        return text.ifEmpty { generic(card) }
    }

    private fun series(c: InsightCard): String {
        val owned = c.owned ?: c.evidenceInt("owned") ?: return ""
        val total = c.total ?: c.evidenceInt("total") ?: return ""
        val name = c.subject.title ?: c.title
        var s = "$name is a series on ${source(c, "MusicBrainz")} with $total ${plural(total, "release")}, and your library holds $owned of them."
        val missing = maxOf(total - owned, 0)
        if (missing > 0) {
            s += " The $missing you do not have " + if (c.missingRuns.size == 1) "form one run" else "fall in ${c.missingRuns.size} runs"
            val runs = c.missingRuns.map { r ->
                val span = if (r.firstPosition == r.lastPosition) "position ${r.firstPosition}" else "positions ${r.firstPosition} to ${r.lastPosition}"
                span + if (r.labels.isEmpty()) "" else ": " + list(r.labels)
            }
            s += if (runs.isEmpty()) "." else " (" + runs.joinToString("; ") + ")."
        } else {
            s += " Nothing in the series is missing."
        }
        return s
    }

    private fun hiddenCanon(c: InsightCard): String {
        val listens = c.evidenceInt("listens") ?: return ""
        val year = c.subject.year?.let { " ($it)" }.orEmpty()
        var s = "${who(c)}$year has been listened to ${grouped(listens)} times on ${source(c, "ListenBrainz")}."
        val genre = c.evidenceString("matched_genre")
        s += if (genre != null) {
            val rank = c.evidenceInt("genre_rank")
            " It belongs to $genre, which is " +
                (if (rank == 1) "your top genre" else rank?.let { "number $it among your genres" } ?: "one of your top genres") +
                ", and it is not in your library."
        } else {
            " It is not in your library."
        }
        return s
    }

    private fun anniversary(c: InsightCard): String {
        val years = c.evidenceInt("years") ?: return ""
        val event = c.evidenceString("event") ?: "album_release"
        val what = if (event == "album_release") "was released" else "marks " + humanize(event)
        var s = "${who(c)} $what"
        c.evidenceString("date")?.let { d -> longDate(d)?.let { s += " on $it" } }
        return "$s, which is $years ${plural(years, "year")} ago today."
    }

    private fun forgottenGem(c: InsightCard): String {
        val days = c.evidenceInt("days_since_last_play") ?: return ""
        var s = "You have not played ${who(c)} for ${span(days)}."
        val past = buildList {
            c.evidenceInt("play_count")?.let { add("played it ${grouped(it)} ${plural(it, "time")}") }
            if (c.hasReason("starred")) add("starred it")
            c.evidenceInt("rating")?.let { add("rated it $it out of 5") }
        }
        if (past.isNotEmpty()) s += " Before that you " + list(past) + "."
        return s
    }

    private fun blindSpot(c: InsightCard): String {
        val owned = c.evidenceInt("owned") ?: c.owned ?: return ""
        val total = c.evidenceInt("total") ?: c.total ?: return ""
        val set = humanize(c.evidenceString("set_kind") ?: "releases")
        val artist = c.subject.artist ?: c.subject.title ?: c.title
        var s = "${source(c, "MusicBrainz")} lists $total $set for $artist, and your library holds $owned of them."
        if (total > owned) s += " The other ${total - owned} are shown as a comparison, not as a recommendation."
        return s
    }

    /** For a lens this app does not know yet: every reason in words, so the card still explains itself. */
    private fun generic(c: InsightCard): String {
        val parts = c.reasons.map { r ->
            val facts = r.evidence.keys.sorted().map { "${humanize(it)} ${text(r.evidence.getValue(it))}" }
            humanize(r.kind) + if (facts.isEmpty()) "" else " (" + facts.joinToString(", ") + ")"
        }
        return if (parts.isEmpty()) "" else "${c.title} is shown because of ${list(parts)}."
    }

    // ---- Helpers

    private fun who(c: InsightCard) = listOfNotNull(c.subject.title ?: c.title, c.subject.artist?.let { "by $it" }).joinToString(" ")

    private fun source(c: InsightCard, default: String): String = when (val s = c.evidenceString("source")?.lowercase()) {
        "musicbrainz" -> "MusicBrainz"
        "listenbrainz" -> "ListenBrainz"
        null -> default
        else -> humanize(s)
    }

    /** Short text for one evidence value; nested values are flattened with commas. */
    internal fun text(v: JsonElement): String = when (v) {
        is JsonNull -> ""
        is JsonPrimitive -> when {
            v.isString -> v.content
            v.content == "true" -> "yes"
            v.content == "false" -> "no"
            else -> v.content.toDoubleOrNull()?.takeIf { it == Math.rint(it) && Math.abs(it) < 1e15 }?.toLong()?.toString() ?: v.content
        }
        is JsonArray -> v.joinToString(", ") { text(it) }
        is JsonObject -> v.keys.sorted().joinToString(", ") { "$it: ${text(v.getValue(it))}" }
    }

    internal fun humanize(s: String) = s.replace('_', ' ')
    internal fun plural(n: Int, word: String) = if (n == 1) word else word + "s"
    internal fun list(items: List<String>) = when (items.size) {
        0 -> ""
        1 -> items[0]
        2 -> items[0] + " and " + items[1]
        else -> items.dropLast(1).joinToString(", ") + " and " + items.last()
    }
    internal fun grouped(n: Int) = String.format(Locale.US, "%,d", n)
    internal fun span(days: Int) = when {
        days < 60 -> "$days ${plural(days, "day")}"
        days < 730 -> "about ${days / 30} months"
        else -> "about ${days / 365} years"
    }
    internal fun longDate(iso: String): String? = try {
        LocalDate.parse(iso).format(DateTimeFormatter.ofPattern("d MMMM yyyy", Locale.UK))
    } catch (e: Exception) {
        null
    }
}
