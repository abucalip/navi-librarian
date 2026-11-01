package app.discair.lyrics

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.longOrNull

/**
 * One line. [startMs] is null in plain lyrics. Lyrics text is copyrighted (contract 3.4): it is never
 * logged, so `toString` is hidden on every type that holds it.
 */
@Serializable
class LyricLine(val startMs: Long?, val text: String) {
    override fun toString() = "LyricLine(startMs=$startMs)"
}

/** The cleaned lyrics chosen for one song. [timed] lines are sorted by start; plain lines keep their order. */
@Serializable
class Lyrics(val timed: Boolean, val lines: List<LyricLine>) {
    override fun toString() = "Lyrics(timed=$timed, lines=${lines.size})"
}

/** What Navidrome said about one song. */
sealed interface LyricsAnswer {
    class Found(val lyrics: Lyrics) : LyricsAnswer
    /** A normal answer: the song has none (also error code 70). */
    data object None : LyricsAnswer
    /** The server does not list the `songLyrics` extension; no lyrics request was made. */
    data object Unsupported : LyricsAnswer
}

enum class LyricsProblem { Unreachable, Unauthorised, Other }

/** Messages are fixed text: never a URL, token, response body or lyric (contract L1 tests). */
class LyricsException(val problem: LyricsProblem, message: String) : Exception(message)

/** Choosing and cleaning rules of contract section 5, and the shape of Navidrome's answers. */
object LyricsParse {
    const val MAX_LINES = 2_000
    const val MAX_LINE_CHARS = 500

    private val json = Json { ignoreUnknownKeys = true }
    private val AUTH = setOf(40, 41, 44, 50)

    private fun root(body: String): JsonObject {
        val root = try {
            json.parseToJsonElement(body).jsonObject["subsonic-response"] as? JsonObject
        } catch (e: Exception) {
            null
        } ?: throw LyricsException(LyricsProblem.Other, "That address did not answer like Navidrome.")
        if (root["status"]?.jsonPrimitive?.contentOrNull != "ok") {
            val code = (root["error"] as? JsonObject)?.get("code")?.jsonPrimitive?.longOrNull?.toInt()
            throw when {
                code in AUTH -> LyricsException(LyricsProblem.Unauthorised, "Navidrome rejected the saved login.")
                else -> NoSuchSong.takeIf { code == 70 } ?: LyricsException(LyricsProblem.Other, "Navidrome could not answer.")
            }
        }
        return root
    }

    /** Error code 70: caught by the source and turned into [LyricsAnswer.None]. */
    internal val NoSuchSong = LyricsException(LyricsProblem.Other, "Navidrome has no such song.")

    /** True when the extensions answer lists `songLyrics`. */
    fun supportsLyrics(body: String): Boolean {
        val list = root(body)["openSubsonicExtensions"] as? JsonArray ?: return false
        return list.any { (it as? JsonObject)?.get("name")?.jsonPrimitive?.contentOrNull == "songLyrics" }
    }

    /** The answer for one song. [phoneLanguage] is a code such as "en"; "xxx" (undetermined) never matches. */
    fun answer(body: String, phoneLanguage: String): LyricsAnswer {
        val entries = try {
            ((root(body)["lyricsList"] as? JsonObject)?.get("structuredLyrics") as? JsonArray).orEmpty()
        } catch (e: LyricsException) {
            if (e === NoSuchSong) return LyricsAnswer.None else throw e
        }
        val cleaned = entries.mapNotNull { (it as? JsonObject)?.let(::clean) }
        val chosen = pick(cleaned.filter { it.first.timed }, phoneLanguage)
            ?: pick(cleaned.filter { !it.first.timed }, phoneLanguage)
        return if (chosen == null) LyricsAnswer.None else LyricsAnswer.Found(chosen)
    }

    private fun pick(entries: List<Pair<Lyrics, String>>, phoneLanguage: String): Lyrics? {
        val want = phoneLanguage.lowercase().take(2)
        val match = if (want.length == 2) entries.firstOrNull { it.second.lowercase().take(2) == want } else null
        return (match ?: entries.firstOrNull())?.first
    }

    /** Lyrics and its language, or null when nothing readable is left. */
    private fun clean(entry: JsonObject): Pair<Lyrics, String>? {
        val lang = entry["lang"]?.jsonPrimitive?.contentOrNull.orEmpty()
        val synced = entry["synced"]?.jsonPrimitive?.booleanOrNull == true
        val offset = entry["offset"]?.jsonPrimitive?.longOrNull ?: 0L
        val raw = (entry["line"] as? JsonArray).orEmpty().mapNotNull { it as? JsonObject }
        val texts = raw.map { line -> tidy(line["value"]?.jsonPrimitive?.contentOrNull.orEmpty()) }
        if (texts.none { it.isNotBlank() }) return null

        if (synced) {
            // A timed line without a usable start is dropped (contract 5).
            val timed = raw.indices.mapNotNull { i ->
                val start = raw[i]["start"]?.jsonPrimitive?.longOrNull
                if (start == null || start < 0) null else LyricLine((start + offset).coerceAtLeast(0), texts[i])
            }
            val distinct = timed.map { it.startMs }.distinct().size
            val backwards = timed.size > 1 && timed.zipWithNext().all { (a, b) -> b.startMs!! <= a.startMs!! }
            if (timed.isNotEmpty() && distinct > 1 && !backwards && timed.any { it.text.isNotBlank() }) {
                val sorted = timed.sortedBy { it.startMs }.take(MAX_LINES)
                return Lyrics(true, sorted) to lang
            }
            // Equal or backward starts: the timings cannot be trusted, so show it as plain text.
        }
        return Lyrics(false, texts.take(MAX_LINES).map { LyricLine(null, it) }) to lang
    }

    /** Plain text only: control characters (including line breaks) removed, long lines cut. */
    private fun tidy(value: String): String =
        value.filterNot { Character.isISOControl(it) }.take(MAX_LINE_CHARS)
}
