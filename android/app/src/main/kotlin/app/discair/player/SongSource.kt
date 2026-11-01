package app.discair.player

import app.discair.net.Subsonic
import java.io.IOException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import okhttp3.Request

/** One song as Navidrome lists it. Only songs in the owner's library can come from here. */
data class SongRef(
    val id: String,
    val title: String,
    val artist: String,
    val album: String,
    val albumId: String,
    val track: Int?,
    val disc: Int?,
    val durationSec: Int,
    val year: Int? = null,
    val bitRateKbps: Int? = null,
    val suffix: String = "",
    val bitDepth: Int? = null,
    val samplingRateHz: Int? = null,
)

enum class SongSourceProblem { Unreachable, Unauthorised, NotFound, Other }

class SongSourceException(val problem: SongSourceProblem, message: String) : Exception(message)

/** Where the song ids come from. The web album page carries none, so the app asks Navidrome directly (contract 5.1). */
interface SongSource {
    /** The album's songs in play order. Throws [SongSourceException]. */
    fun albumSongs(albumId: String): List<SongRef>

    /** The ids of the artist's albums in Navidrome's order. Throws [SongSourceException]. */
    fun artistAlbumIds(artistId: String): List<String>

    /** One song with its year and file details, or null when Navidrome can't give it. Throws [SongSourceException]. */
    fun song(songId: String): SongRef? = null
}

object SubsonicParse {
    private val json = Json { ignoreUnknownKeys = true }
    private val AUTH = setOf(40, 41, 44, 50)

    private fun root(body: String): JsonObject {
        val root = try {
            json.parseToJsonElement(body).jsonObject["subsonic-response"] as? JsonObject
        } catch (e: Exception) {
            null
        } ?: throw SongSourceException(SongSourceProblem.Other, "That address did not answer like Navidrome.")
        if (root["status"]?.jsonPrimitive?.contentOrNull != "ok") {
            val code = (root["error"] as? JsonObject)?.get("code")?.jsonPrimitive?.intOrNull
            throw when {
                code in AUTH -> SongSourceException(SongSourceProblem.Unauthorised, "Navidrome rejected the saved login.")
                code == 70 -> SongSourceException(SongSourceProblem.NotFound, "Navidrome has no such item.")
                else -> SongSourceException(SongSourceProblem.Other, "Navidrome could not answer.")
            }
        }
        return root
    }

    private fun JsonObject.text(key: String) = this[key]?.jsonPrimitive?.contentOrNull.orEmpty()
    private fun JsonObject.number(key: String) = this[key]?.jsonPrimitive?.intOrNull

    fun song(body: String): SongRef? = (root(body)["song"] as? JsonObject)?.let { songRef(it, null) }

    private fun songRef(s: JsonObject, album: JsonObject?): SongRef? {
        val id = s.text("id")
        if (!isValidSongId(id)) return null
        val fallback = album ?: JsonObject(emptyMap())
        return run {
            SongRef(
                id = id, title = s.text("title"), artist = s.text("artist").ifBlank { fallback.text("artist") },
                album = s.text("album").ifBlank { fallback.text("name") }, albumId = s.text("albumId").ifBlank { fallback.text("id") },
                track = s.number("track"), disc = s.number("discNumber"), durationSec = s.number("duration") ?: 0,
                year = (s.number("year") ?: fallback.number("year"))?.takeIf { it > 0 },
                bitRateKbps = s.number("bitRate")?.takeIf { it > 0 }, suffix = s.text("suffix"),
                bitDepth = s.number("bitDepth")?.takeIf { it > 0 }, samplingRateHz = s.number("samplingRate")?.takeIf { it > 0 },
            )
        }
    }

    fun albumSongs(body: String): List<SongRef> {
        val album = root(body)["album"] as? JsonObject ?: return emptyList()
        val songs = (album["song"] as? JsonArray)?.map { it.jsonObject } ?: return emptyList()
        return songs.mapNotNull { songRef(it, album) }.sortedWith(compareBy({ it.disc ?: 1 }, { it.track ?: Int.MAX_VALUE }, { it.title.lowercase() }))
    }

    fun artistAlbumIds(body: String): List<String> {
        val artist = root(body)["artist"] as? JsonObject ?: return emptyList()
        return (artist["album"] as? JsonArray)?.mapNotNull { it.jsonObject.text("id").takeIf(::isValidSongId) }.orEmpty()
    }
}

/** Reads album and artist listings from Navidrome with the login saved on the device. */
class SubsonicSongSource(
    private val http: OkHttpClient,
    private val login: () -> Triple<String, String, String>,
    private val newSalt: () -> String = { java.util.UUID.randomUUID().toString().replace("-", "").take(12) },
) : SongSource {
    private fun url(call: String, id: String): HttpUrl {
        if (!isValidSongId(id)) throw SongSourceException(SongSourceProblem.NotFound, "Navidrome has no such item.")
        val (base, user, password) = login()
        val parsed = base.toHttpUrlOrNull()?.takeIf { it.isHttps }
            ?: throw SongSourceException(SongSourceProblem.Other, "The Navidrome address is not set.")
        val salt = newSalt()
        return parsed.newBuilder().addPathSegments("rest/$call")
            .addQueryParameter("u", user).addQueryParameter("t", Subsonic.token(password, salt)).addQueryParameter("s", salt)
            .addQueryParameter("v", Subsonic.API_VERSION).addQueryParameter("c", Subsonic.CLIENT).addQueryParameter("f", "json")
            .addQueryParameter("id", id).build()
    }

    private fun get(call: String, id: String): String {
        val client = http.newBuilder().followRedirects(false).followSslRedirects(false).build()
        try {
            client.newCall(Request.Builder().url(url(call, id)).get().build()).execute().use { response ->
                if (response.code == 401 || response.code == 403) throw SongSourceException(SongSourceProblem.Unauthorised, "Navidrome rejected the saved login.")
                if (!response.isSuccessful) throw SongSourceException(SongSourceProblem.Other, "Navidrome answered ${response.code}.")
                return response.body?.string().orEmpty()
            }
        } catch (e: IOException) {
            throw SongSourceException(SongSourceProblem.Unreachable, "Can't reach Navidrome. Is Tailscale connected?")
        }
    }

    override fun albumSongs(albumId: String) = SubsonicParse.albumSongs(get("getAlbum", albumId))
    override fun artistAlbumIds(artistId: String) = SubsonicParse.artistAlbumIds(get("getArtist", artistId))
    override fun song(songId: String) = SubsonicParse.song(get("getSong", songId))
}
