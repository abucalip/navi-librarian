package app.discair.data

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import app.discair.net.ConnectionException
import java.io.IOException
import javax.net.ssl.SSLException
import app.discair.model.AcquisitionJob
import app.discair.model.AlbumLinks
import app.discair.model.GetState
import app.discair.model.albumLaunchBody
import app.discair.model.identityBody
import app.discair.model.launchOutcome
import app.discair.model.parseAcquisitions
import app.discair.model.replyMessage
import app.discair.model.trackLaunchBody
import app.discair.model.DiscoveryResult
import app.discair.model.FeedbackAction
import app.discair.model.FeedbackReply
import app.discair.model.SearchEvent
import app.discair.model.feedbackBody
import app.discair.model.parseDiscovery
import app.discair.model.parseSearchEvent
import kotlinx.serialization.json.JsonObject
import app.discair.model.AlbumPage
import app.discair.model.ApiJson
import app.discair.model.ArtistPage
import app.discair.model.GenrePage
import app.discair.model.GenreTiles
import app.discair.model.ImageLookup
import app.discair.model.LibraryAlbum
import app.discair.model.LibraryArtist
import app.discair.model.Page
import app.discair.model.Picks
import app.discair.model.Shelf
import app.discair.net.LibrarianClient
import java.util.concurrent.ConcurrentHashMap
import kotlinx.serialization.serializer

/** Thrown from a stream callback to end the read and close the connection. */
class StopStream : RuntimeException()

enum class Shelves(val path: String) { Newest("newest"), Recent("recent"), Frequent("frequent") }

/** Server-side sort fields, exactly as Librarian names them, with the direction each starts in. */
enum class ArtistSort(val param: String, val label: String, val startsDescending: Boolean) {
    Name("name", "Name", false), Albums("album_count", "Album count", true), Added("added", "Date added", true)
}

enum class AlbumSort(val param: String, val label: String, val startsDescending: Boolean) {
    Name("name", "Name", false), Artist("artist", "Artist", false), Year("year", "Year", true),
    Added("added", "Date added", true), Tracks("song_count", "Track count", true)
}

/** The acquisition calls (contract 5.3). The server decides everything; nothing here assumes success. */
interface AcquisitionApi {
    /** Launches an album with automatic source choice. The outcome reads the reply's `ok` and `status`, not the HTTP code. */
    fun acquireAlbum(artist: String, album: String, metadata: JsonObject): GetState

    /** Launches one song, filed with its album. */
    fun acquireTrack(artist: String, album: String, title: String, trackNumber: Int?, year: Int?, metadata: JsonObject?): GetState

    fun acquisitions(): List<AcquisitionJob>

    /**
     * Reads the live status stream, calling [onSnapshot] for each snapshot and [onProblem] for an
     * `error` event. Blocks until the stream ends or [onSnapshot] throws [StopStream].
     */
    fun acquisitionStream(onSnapshot: (List<AcquisitionJob>) -> Unit, onProblem: (String) -> Unit)

    /** Asks for the next source; returns the server's message. Throws on a refusal. */
    fun skipSource(artist: String, album: String): String?

    /** Dismisses a record and deletes its download files (ACQ-04); returns the server's message. Throws on refusal. */
    fun dismissAcquisition(artist: String, album: String): String?
}

/**
 * Everything the screens read. Librarian supplies the order and the content; nothing here sorts,
 * ranks or filters. All calls block, so callers run them on the IO dispatcher.
 */
interface LibraryRepository : AcquisitionApi {
    /** When the saved copy now being shown was fetched (epoch ms), or null while reads come from the server. */
    val staleSince: Long? get() = null

    /** Resolves a server-relative path such as an owned-artwork URL to an absolute address. */
    fun absolute(path: String): String

    fun picks(count: Int): Picks
    fun genres(): GenreTiles
    fun shelf(shelf: Shelves, count: Int): Shelf
    fun artists(query: String, sort: ArtistSort, descending: Boolean?, cursor: String?): Page<LibraryArtist>
    fun albums(query: String, sort: AlbumSort, descending: Boolean?, cursor: String?): Page<LibraryAlbum>
    fun artistPage(key: String, id: String?, name: String?, mbid: String?): ArtistPage
    fun albumPage(key: String, id: String?, artist: String?, name: String?, year: Int?): AlbumPage
    fun genrePage(tag: String): GenrePage

    /**
     * The album page as it fills in: [onPage] gets the page after each section the server finishes, as
     * the web does, so the header and tracks show before the slow network sections arrive.
     */
    fun albumPageStream(key: String, id: String?, artist: String?, name: String?, year: Int?, onPage: (AlbumPage) -> Unit) =
        onPage(albumPage(key, id, artist, name, year))

    /** The artist page as it fills in; owned albums arrive first. */
    fun artistPageStream(key: String, id: String?, name: String?, mbid: String?, onPage: (ArtistPage) -> Unit) =
        onPage(artistPage(key, id, name, mbid))
    fun albumLinks(artist: String, album: String, mbid: String?): AlbumLinks

    /** One discovery list in the server's order. [list] is a path name such as `new_releases` or a lens name. */
    fun discovery(list: String, count: Int): DiscoveryResult

    /** Sends feedback; throws unless the server answers `ok`. Nothing is assumed saved before this returns. */
    fun feedback(action: FeedbackAction, artist: String, album: String, metadata: JsonObject)

    /** Asks the server to rebuild a list in the background (count 1-20). */
    fun refreshList(list: String)

    /** Artist biography text, or null when none is available. */
    fun artistBio(artist: String): String?

    /** Streams a search to [onEvent]; blocks until it ends. */
    fun search(query: String, onEvent: (SearchEvent) -> Unit)

    /** Cover for an album the library does not own; null when no source has one. */
    fun albumImage(artist: String, album: String): String?

    /** The year of an album the list did not date, or null when the catalogue has no exact match. */
    fun albumYear(artist: String, album: String): Int? = null
    fun artistImage(name: String): String?
}

class LibrarianRepository(
    private val client: LibrarianClient,
    private val baseUrl: String,
    private val cache: ResponseCache = NoCache,
) : LibraryRepository {
    private var stale by mutableStateOf<Long?>(null)
    override val staleSince: Long? get() = stale

    private val images = ConcurrentHashMap<String, String>()
    private val years = ConcurrentHashMap<String, Int>()
    private val noImage = ConcurrentHashMap.newKeySet<String>()

    override fun absolute(path: String) = if (path.startsWith("http")) path else baseUrl + path

    override fun picks(count: Int) = read<Picks>(listOf("api", "dashboard-picks"), mapOf("count" to "$count"))
    override fun genres() = read<GenreTiles>(listOf("api", "dashboard", "genres"))
    override fun shelf(shelf: Shelves, count: Int) =
        read<Shelf>(listOf("api", "dashboard", "albums", shelf.path), mapOf("count" to "$count"))

    override fun artists(query: String, sort: ArtistSort, descending: Boolean?, cursor: String?) =
        read<Page<LibraryArtist>>(listOf("api", "library", "artists"), listQuery(query, sort.param, descending, cursor))

    override fun albums(query: String, sort: AlbumSort, descending: Boolean?, cursor: String?) =
        read<Page<LibraryAlbum>>(listOf("api", "library", "albums"), listQuery(query, sort.param, descending, cursor))

    override fun artistPage(key: String, id: String?, name: String?, mbid: String?) =
        read<ArtistPage>(listOf("api", "artists", key), mapOf("id" to id, "name" to name, "mbid" to mbid))

    override fun albumPage(key: String, id: String?, artist: String?, name: String?, year: Int?): AlbumPage {
        // An album key is "artist key/album key"; the route takes them as two path segments.
        val (artistKey, albumKey) = key.split("/", limit = 2).let { it[0] to it.getOrElse(1) { "" } }
        return read(
            listOf("api", "albums", artistKey, albumKey),
            mapOf("id" to id, "artist" to artist, "name" to name, "year" to year?.toString()),
        )
    }

    override fun albumPageStream(key: String, id: String?, artist: String?, name: String?, year: Int?, onPage: (AlbumPage) -> Unit) {
        val (artistKey, albumKey) = key.split("/", limit = 2).let { it[0] to it.getOrElse(1) { "" } }
        streamSections(
            listOf("api", "albums", artistKey, albumKey),
            mapOf("id" to id, "artist" to artist, "name" to name, "year" to year?.toString()),
        ) { onPage(ApiJson.decodeFromString(AlbumPage.serializer(), it)) }
    }

    override fun artistPageStream(key: String, id: String?, name: String?, mbid: String?, onPage: (ArtistPage) -> Unit) =
        streamSections(listOf("api", "artists", key), mapOf("id" to id, "name" to name, "mbid" to mbid)) {
            onPage(ApiJson.decodeFromString(ArtistPage.serializer(), it))
        }

    /**
     * Reads a page's `section` events and hands [onBody] the page JSON built so far after each one.
     * The finished page is saved under the same key a plain read uses, so offline reads still work, and
     * a phone that cannot stream gets the saved copy, as any other read does.
     */
    private fun streamSections(segments: List<String>, query: Map<String, String?>, onBody: (String) -> Unit) {
        if (ReadMode.isCacheOnly) return onBody(fetch(segments, query))
        val sections = linkedMapOf<String, kotlinx.serialization.json.JsonElement>()
        var done: kotlinx.serialization.json.JsonElement? = null
        fun page(): String = JsonObject(buildMap {
            put("sections", JsonObject(sections))
            done?.let { put("done", it) }
        }).toString()
        try {
            client.stream(segments, query) { name, data ->
                when (name) {
                    "section" -> (ApiJson.parseToJsonElement(data) as? JsonObject)?.let { o ->
                        val section = (o["section"] as? kotlinx.serialization.json.JsonPrimitive)?.content ?: return@let
                        sections[section] = JsonObject(o.filterKeys { it != "section" })
                        onBody(page())
                    }
                    "done" -> done = ApiJson.parseToJsonElement(data)
                }
            }
        } catch (e: Exception) {
            if (!isOffline(e)) throw e
            onBody(fetch(segments, query))
            return
        }
        if (sections.isEmpty()) {
            onBody(fetch(segments, query))
            return
        }
        cache.put(cacheKey(segments, query), page())
        stale = null
    }

    override fun genrePage(tag: String) = read<GenrePage>(listOf("api", "genres", tag))

    override fun albumLinks(artist: String, album: String, mbid: String?) =
        read<AlbumLinks>(listOf("api", "album-links"), mapOf("artist" to artist, "album" to album, "mbid" to mbid))

    override fun discovery(list: String, count: Int) =
        parseDiscovery(fetch(listOf("api", "discovery", list), mapOf("count" to "$count")))

    override fun feedback(action: FeedbackAction, artist: String, album: String, metadata: JsonObject) {
        val reply = ApiJson.decodeFromString(
            FeedbackReply.serializer(),
            client.post(listOf("api", "discovery", "feedback"), feedbackBody(action, artist, album, metadata)),
        )
        if (!reply.ok) throw IllegalStateException(reply.error ?: "The server did not accept this.")
    }

    override fun refreshList(list: String) {
        client.post(listOf("api", "discovery", list, "refresh"), """{"count":20}""")
    }

    override fun artistBio(artist: String): String? = try {
        (ApiJson.parseToJsonElement(client.get(listOf("api", "artist-bio"), mapOf("artist" to artist)))
            as? JsonObject)?.get("bio")?.let { it as? kotlinx.serialization.json.JsonPrimitive }
            ?.takeIf { it.isString }?.content?.takeIf { it.isNotBlank() }
    } catch (e: Exception) {
        null
    }

    override fun search(query: String, onEvent: (SearchEvent) -> Unit) =
        client.stream(listOf("api", "search"), mapOf("q" to query, "scope" to "all", "limit" to "10")) { name, data ->
            parseSearchEvent(name, data)?.let(onEvent)
        }

    override fun acquireAlbum(artist: String, album: String, metadata: JsonObject) =
        launchOutcome(client.post(listOf("api", "acquire"), albumLaunchBody(artist, album, metadata)))

    override fun acquireTrack(artist: String, album: String, title: String, trackNumber: Int?, year: Int?, metadata: JsonObject?) =
        launchOutcome(
            client.post(listOf("api", "acquire", "track"), trackLaunchBody(artist, album, title, trackNumber, year, metadata)),
        )

    override fun acquisitions() = parseAcquisitions(client.get(listOf("api", "acquisitions")))

    override fun acquisitionStream(onSnapshot: (List<AcquisitionJob>) -> Unit, onProblem: (String) -> Unit) {
        try {
            client.stream(listOf("api", "acquisitions", "stream"), emptyMap()) { name, data ->
                when (name) {
                    "message" -> onSnapshot(parseAcquisitions(data))
                    "error" -> onProblem(replyMessage(data) ?: "The status stream could not read the list.")
                }
            }
        } catch (stop: StopStream) {
            // The screen left; the connection is closed.
        }
    }

    override fun skipSource(artist: String, album: String) =
        replyMessage(client.post(listOf("api", "acquisitions", "skip"), identityBody(artist, album)))

    override fun dismissAcquisition(artist: String, album: String) =
        replyMessage(client.post(listOf("api", "acquisitions", "dismiss"), identityBody(artist, album)))

    override fun albumImage(artist: String, album: String) =
        lookup("album|$artist|$album", listOf("api", "artwork"), mapOf("artist" to artist, "album" to album))

    override fun albumYear(artist: String, album: String): Int? {
        val key = "${artist.trim().lowercase()}::${album.trim().lowercase()}"
        years[key]?.let { return it.takeIf { y -> y > 0 } }
        // A year found before survives restarts; the answer "no year" is not saved, so it is asked again.
        cache.get("year|$key")?.body?.toIntOrNull()?.let { years[key] = it; return it }
        val body = JsonObject(mapOf("items" to kotlinx.serialization.json.JsonArray(listOf(JsonObject(mapOf(
            "artist" to kotlinx.serialization.json.JsonPrimitive(artist),
            "album" to kotlinx.serialization.json.JsonPrimitive(album),
        ))))))
        return try {
            val answer = (ApiJson.parseToJsonElement(client.post(listOf("api", "album-years"), body.toString())) as? JsonObject)
                ?.get("years") as? kotlinx.serialization.json.JsonArray
            // An album the catalogue call failed for is left out of the answer, so it is not remembered.
            val entry = answer?.firstOrNull() as? JsonObject ?: return null
            val year = (entry["year"] as? kotlinx.serialization.json.JsonPrimitive)?.content?.toIntOrNull()
            years[key] = year ?: 0
            if (year != null) cache.put("year|$key", year.toString())
            year
        } catch (e: Exception) {
            null
        }
    }

    override fun artistImage(name: String) =
        lookup("artist|$name", listOf("api", "artist-image"), mapOf("name" to name))

    private fun lookup(cacheKey: String, segments: List<String>, query: Map<String, String?>): String? {
        images[cacheKey]?.let { return it }
        if (cacheKey in noImage) return null
        val url = try {
            read<ImageLookup>(segments, query).artworkUrl?.takeIf { it.isNotBlank() }
        } catch (e: Exception) {
            return null // not cached, so a later visit can try again
        }
        if (url == null) noImage += cacheKey else images[cacheKey] = url
        return url
    }

    private fun listQuery(q: String, sort: String, descending: Boolean?, cursor: String?) = mapOf(
        "q" to q.takeIf { it.isNotBlank() },
        "sort" to sort,
        "order" to descending?.let { if (it) "desc" else "asc" },
        "cursor" to cursor,
        "limit" to "60",
    )

    private inline fun <reified T> read(segments: List<String>, query: Map<String, String?> = emptyMap()): T =
        ApiJson.decodeFromString(serializer<T>(), fetch(segments, query))

    private fun cacheKey(segments: List<String>, query: Map<String, String?>) =
        baseUrl + "/" + segments.joinToString("/") + "?" +
            query.filterValues { it != null }.toSortedMap().entries.joinToString("&") { "${it.key}=${it.value}" }

    /**
     * A read-only GET with the last good answer as a fallback when the phone cannot reach the server
     * (no connection, timeout, unreachable). A server error, a refusal or a bad certificate is never
     * answered from the cache: those say something is wrong, not that the phone is offline.
     */
    private fun fetch(segments: List<String>, query: Map<String, String?> = emptyMap()): String {
        val key = cacheKey(segments, query)
        // First paint from the saved copy: no request, and the offline banner is left alone.
        if (ReadMode.isCacheOnly) return cache.get(key)?.body ?: throw CacheMiss()
        return try {
            client.get(segments, query).also { cache.put(key, it); stale = null }
        } catch (e: Exception) {
            if (!isOffline(e)) throw e
            val hit = cache.get(key) ?: throw e
            stale = hit.savedAtMillis
            hit.body
        }
    }
}

/** The phone could not reach the server, as opposed to the server answering with a problem. */
fun isOffline(e: Throwable) = e is IOException && e !is ConnectionException && e !is SSLException
