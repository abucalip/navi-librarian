package app.discair.player

import java.io.File
import java.io.IOException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import okhttp3.OkHttpClient
import okhttp3.Request

/** Where a song stands in "Download to device". */
enum class OfflineStatus { Downloading, Done, Failed }

enum class OfflineProblem { Unreachable, Unauthorised, Other }

class OfflineException(val problem: OfflineProblem, message: String) : Exception(message)

/**
 * Songs saved on the device so they play without a connection. The original file is fetched from Navidrome
 * (the `download` call) into the app's private storage; nothing is converted. A small index of the songs' details
 * is kept beside the files so an album that is only partly saved can still be listed and played offline.
 * Files are written as `.part` and renamed when whole, so a stopped download never looks finished.
 */
class OfflineSongs(
    private val dir: File,
    private val http: OkHttpClient,
    /** Navidrome address, user and password, read each time (they are not fixed at start-up). */
    private val login: () -> Triple<String, String, String>,
    private val io: CoroutineDispatcher,
    private val newSalt: () -> String = { java.util.UUID.randomUUID().toString().replace("-", "").take(12) },
) {
    private val lock = Mutex()
    private val songs = LinkedHashMap<String, SongRef>()
    private val files = HashMap<String, File>()

    private val _status = MutableStateFlow<Map<String, OfflineStatus>>(emptyMap())

    /** The state of every song asked for since the app started, plus the saved ones. */
    val status: StateFlow<Map<String, OfflineStatus>> = _status

    init {
        dir.mkdirs()
        load()
    }

    private fun indexFile() = File(dir, "index.json")

    private fun load() {
        val saved = try {
            Json.parseToJsonElement(indexFile().readText()).jsonArray.mapNotNull { fromJson(it.jsonObject) }
        } catch (e: Exception) {
            emptyList()
        }
        val done = mutableMapOf<String, OfflineStatus>()
        for (song in saved) {
            val file = dir.listFiles { f -> f.name.startsWith(song.id + ".") && !f.name.endsWith(".part") }?.firstOrNull() ?: continue
            songs[song.id] = song
            files[song.id] = file
            done[song.id] = OfflineStatus.Done
        }
        dir.listFiles { f -> f.name.endsWith(".part") }?.forEach { it.delete() } // a stopped download is never kept
        _status.value = done
    }

    private fun save() {
        val array = JsonArray(songs.values.map(::toJson))
        val temp = File(dir, "index.json.tmp")
        temp.writeText(array.toString())
        if (!temp.renameTo(indexFile())) { indexFile().delete(); temp.renameTo(indexFile()) }
    }

    /** The saved file for [songId], or null. Cheap: answered from memory, so the playback service can call it on its main thread. */
    @Synchronized fun find(songId: String): File? = files[songId]?.takeIf { it.exists() }

    @Synchronized fun isSaved(songId: String): Boolean = find(songId) != null

    /** The saved songs of one album, in play order. Used when Navidrome cannot be reached. */
    @Synchronized fun savedAlbum(albumId: String): List<SongRef> =
        songs.values.filter { it.albumId == albumId && files[it.id]?.exists() == true }
            .sortedWith(compareBy({ it.disc ?: 1 }, { it.track ?: Int.MAX_VALUE }, { it.title.lowercase() }))

    @Synchronized fun savedCount(): Int = songs.size

    @Synchronized fun savedBytes(): Long = files.values.sumOf { if (it.exists()) it.length() else 0L }

    /** Saves [song] on the device. Returns when it is whole. Throws [OfflineException]. */
    suspend fun download(song: SongRef) {
        if (!isValidSongId(song.id)) throw OfflineException(OfflineProblem.Other, "That song can't be saved.")
        if (isSaved(song.id)) { mark(song.id, OfflineStatus.Done); return }
        if (_status.value[song.id] == OfflineStatus.Downloading) return
        mark(song.id, OfflineStatus.Downloading)
        try {
            lock.withLock { withContext(io) { fetch(song) } }
            mark(song.id, OfflineStatus.Done)
        } catch (e: kotlinx.coroutines.CancellationException) {
            _status.update { it - song.id }
            throw e
        } catch (e: OfflineException) {
            mark(song.id, OfflineStatus.Failed); throw e
        } catch (e: Exception) {
            mark(song.id, OfflineStatus.Failed); throw OfflineException(OfflineProblem.Other, "Couldn't save the song.")
        }
    }

    private fun mark(id: String, status: OfflineStatus) = _status.update { it + (id to status) }

    private fun fetch(song: SongRef) {
        val (base, user, password) = login()
        val url = try {
            StreamUrlBuilder(base, user, password, newSalt).buildDownload(song.id)
        } catch (e: IllegalArgumentException) {
            throw OfflineException(OfflineProblem.Other, "The Navidrome address is not set.")
        }
        val extension = song.suffix.lowercase().takeIf { Regex("^[a-z0-9]{1,5}$").matches(it) } ?: "audio"
        val part = File(dir, "${song.id}.$extension.part")
        val client = http.newBuilder().followRedirects(false).followSslRedirects(false).build()
        try {
            client.newCall(Request.Builder().url(url).get().build()).execute().use { response ->
                if (response.code == 401 || response.code == 403) throw OfflineException(OfflineProblem.Unauthorised, "Navidrome rejected the saved login.")
                if (!response.isSuccessful) throw OfflineException(OfflineProblem.Other, "Navidrome answered ${response.code}.")
                val body = response.body ?: throw OfflineException(OfflineProblem.Other, "Navidrome sent no file.")
                // Subsonic reports errors as a small JSON or XML body with a 200; a song is never that small and that type.
                val type = body.contentType()?.toString().orEmpty()
                if (type.startsWith("application/json") || type.contains("xml") || type.startsWith("text/")) {
                    throw OfflineException(OfflineProblem.Other, "Navidrome could not send that song.")
                }
                part.outputStream().use { out -> body.byteStream().use { it.copyTo(out) } }
            }
        } catch (e: IOException) {
            part.delete()
            throw OfflineException(OfflineProblem.Unreachable, "Can't reach Navidrome. Is Tailscale connected?")
        } catch (e: OfflineException) {
            part.delete(); throw e
        }
        val final = File(dir, "${song.id}.$extension")
        if (!part.renameTo(final)) { part.delete(); throw OfflineException(OfflineProblem.Other, "Couldn't save the song.") }
        synchronized(this) {
            songs[song.id] = song
            files[song.id] = final
            save()
        }
    }

    /** Removes every saved song. */
    suspend fun removeAll() = withContext(io) { removeAllNow() }

    /** The same, without suspending: sign-out calls it from its own thread. */
    fun removeAllNow() {
        synchronized(this) {
            files.values.forEach { it.delete() }
            files.clear(); songs.clear()
            runCatching { save() }
        }
        _status.value = emptyMap()
    }

    private fun toJson(s: SongRef) = buildJsonObject {
        put("id", s.id); put("title", s.title); put("artist", s.artist); put("album", s.album); put("albumId", s.albumId)
        s.track?.let { put("track", it) }; s.disc?.let { put("disc", it) }; put("duration", s.durationSec)
        s.year?.let { put("year", it) }; s.bitRateKbps?.let { put("bitRate", it) }; put("suffix", s.suffix)
        s.bitDepth?.let { put("bitDepth", it) }; s.samplingRateHz?.let { put("samplingRate", it) }
    }

    private fun fromJson(o: JsonObject): SongRef? {
        fun text(k: String) = o[k]?.jsonPrimitive?.contentOrNull.orEmpty()
        fun num(k: String) = (o[k] as? JsonPrimitive)?.intOrNull
        val id = text("id")
        if (!isValidSongId(id)) return null
        return SongRef(
            id = id, title = text("title"), artist = text("artist"), album = text("album"), albumId = text("albumId"),
            track = num("track"), disc = num("disc"), durationSec = num("duration") ?: 0, year = num("year"),
            bitRateKbps = num("bitRate"), suffix = text("suffix"), bitDepth = num("bitDepth"), samplingRateHz = num("samplingRate"),
        )
    }
}

/**
 * Asks Navidrome first; when it can't be reached, lists the album from the songs saved on the device,
 * so a saved song still plays from its album page with no connection.
 */
class OfflineAwareSongSource(private val online: SongSource, private val offline: OfflineSongs) : SongSource {
    override fun albumSongs(albumId: String): List<SongRef> = try {
        online.albumSongs(albumId)
    } catch (e: SongSourceException) {
        if (e.problem != SongSourceProblem.Unreachable) throw e
        offline.savedAlbum(albumId).ifEmpty { throw e }
    }

    override fun artistAlbumIds(artistId: String): List<String> = online.artistAlbumIds(artistId)
}
