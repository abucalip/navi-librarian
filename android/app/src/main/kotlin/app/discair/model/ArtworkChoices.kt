package app.discair.model

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

/**
 * The owner's cover picks, library album id to artwork image id (`GET /api/artwork/choices`). The server serves a pick on the
 * same address as the automatic cover, so every screen adds the pick to the address ([versioned]): a new pick is a new address
 * and no screen keeps showing the old image from the loader's cache. Reading [versioned] inside a composable also redraws it
 * when a pick changes.
 */
object ArtworkChoices {
    private const val OWNED = "/api/owned/artwork/"
    private var picks by mutableStateOf<Map<String, Long>>(emptyMap())

    /** Replaces every pick with the server's answer. */
    fun replace(all: Map<String, Long>) { picks = all }

    fun set(albumId: String, imageId: Long) { picks = picks + (albumId to imageId) }

    fun clear(albumId: String) { picks = picks - albumId }

    /** [url] with `c=<pick>` added when it is an owned-cover address that does not carry one yet; any other address is returned as it is. */
    fun versioned(url: String): String {
        val at = url.indexOf(OWNED)
        if (at < 0) return url
        val query = url.indexOf('?', at)
        if (query >= 0 && url.substring(query + 1).split('&').any { it.startsWith("c=") }) return url
        val id = url.substring(at + OWNED.length, if (query >= 0) query else url.length)
        return coverUrlFor(url, picks[id]) ?: url
    }

    /** The picks in a `/api/artwork/choices` body; an unreadable body is no picks. */
    fun parse(body: String): Map<String, Long> = try {
        (ApiJson.parseToJsonElement(body).jsonObject["choices"] as? JsonObject).orEmpty()
            .mapNotNull { (id, v) -> v.jsonPrimitive.content.toLongOrNull()?.let { id to it } }.toMap()
    } catch (e: Exception) { emptyMap() }
}
