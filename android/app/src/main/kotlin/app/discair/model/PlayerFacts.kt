package app.discair.model

import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull

/** One line shown in the player while a song plays. Every line names its source ("MusicBrainz", "Your library"). */
data class PlayerFact(val kind: String, val text: String, val source: String, val fromServer: Boolean) {
    val key get() = "$kind|$text"
}

/** Lines from `GET /api/knowledge/song-facts`. A line without text is dropped; one bad line never drops the rest. */
fun parseSongFacts(body: String): List<PlayerFact> {
    val root = try { ApiJson.parseToJsonElement(body) as? JsonObject } catch (e: SerializationException) { null } ?: return emptyList()
    return (root["facts"] as? JsonArray).orEmpty().mapNotNull { element ->
        val o = element as? JsonObject ?: return@mapNotNull null
        fun str(name: String) = (o[name] as? JsonPrimitive)?.takeIf { it.isString }?.contentOrNull?.trim().orEmpty()
        val text = str("text").takeIf { it.isNotEmpty() } ?: return@mapNotNull null
        PlayerFact(str("kind"), text, str("source").ifEmpty { "MusicBrainz" }, fromServer = true)
    }
}

const val MAX_FACTS = 14

/** Alternates the server's lines and the library's own, server first, never repeating a line, at most [MAX_FACTS]. */
fun mixFacts(server: List<PlayerFact>, library: List<PlayerFact>): List<PlayerFact> {
    val out = mutableListOf<PlayerFact>()
    val seen = mutableSetOf<String>()
    val s = server.iterator()
    val l = library.iterator()
    var fromServer = true
    while (out.size < MAX_FACTS) {
        val next = if (fromServer) (if (s.hasNext()) s.next() else if (l.hasNext()) l.next() else null)
        else (if (l.hasNext()) l.next() else if (s.hasNext()) s.next() else null)
        if (next == null) break
        if (seen.add(next.key)) out += next
        fromServer = !fromServer
    }
    return out
}
