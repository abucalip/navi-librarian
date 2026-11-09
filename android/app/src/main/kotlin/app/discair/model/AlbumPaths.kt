package app.discair.model

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull

/**
 * The album paths the server builds for `GET /api/knowledge/paths?type=release` (the Paths button on an album page).
 * Same route and body as the artist paths, parsed by [parsePaths]. `album_room` and `album_gaps` are not built yet
 * (the server answers 501), so they are not offered.
 */
enum class AlbumPathKind(val wire: String, val label: String) {
    StudioCrew("album_crew", "Studio crew"),
    GuestList("album_guests", "Guest list"),
    CoversAndSources("album_works", "Covers and sources"),
    SameYearSameScene("album_moment", "Same year, same scene"),
}

/** A person or work whose albums were cut at the server's cap; [more] albums were left out and must be said so. */
data class PathCapped(val via: String, val more: Int)

/** The `capped[]` list of an album path body: entries without a name or a count are left out. */
internal fun parseCapped(root: JsonObject): List<PathCapped> =
    (root["capped"] as? JsonArray).orEmpty().mapNotNull { element ->
        val o = element as? JsonObject ?: return@mapNotNull null
        val more = o.num("more") ?: return@mapNotNull null
        val via = o.str("via")?.trim()?.takeIf { it.isNotEmpty() }
            ?: o.sub("via")?.str("canonical_name")?.trim()?.takeIf { it.isNotEmpty() }
            ?: return@mapNotNull null
        if (more <= 0) return@mapNotNull null
        PathCapped(via, more)
    }

private fun JsonObject.str(name: String) = (this[name] as? JsonPrimitive)?.takeIf { it.isString }?.contentOrNull
private fun JsonObject.num(name: String) = (this[name] as? JsonPrimitive)?.let { it.intOrNull ?: it.doubleOrNull?.toInt() }
private fun JsonObject.sub(name: String) = this[name] as? JsonObject