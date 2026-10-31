package app.discair.data

import app.discair.model.AlbumLinks
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

enum class Shelves(val path: String) { Newest("newest"), Recent("recent"), Frequent("frequent") }

/** Server-side sort fields, exactly as Librarian names them, with the direction each starts in. */
enum class ArtistSort(val param: String, val label: String, val startsDescending: Boolean) {
    Name("name", "Name", false), Albums("album_count", "Album count", true), Added("added", "Date added", true)
}

enum class AlbumSort(val param: String, val label: String, val startsDescending: Boolean) {
    Name("name", "Name", false), Artist("artist", "Artist", false), Year("year", "Year", true),
    Added("added", "Date added", true), Tracks("song_count", "Track count", true)
}

/**
 * Everything the screens read. Librarian supplies the order and the content; nothing here sorts,
 * ranks or filters. All calls block, so callers run them on the IO dispatcher.
 */
interface LibraryRepository {
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
    fun artistImage(name: String): String?
}

class LibrarianRepository(
    private val client: LibrarianClient,
    private val baseUrl: String,
) : LibraryRepository {
    private val images = ConcurrentHashMap<String, String>()
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

    override fun genrePage(tag: String) = read<GenrePage>(listOf("api", "genres", tag))

    override fun albumLinks(artist: String, album: String, mbid: String?) =
        read<AlbumLinks>(listOf("api", "album-links"), mapOf("artist" to artist, "album" to album, "mbid" to mbid))

    override fun discovery(list: String, count: Int) =
        parseDiscovery(client.get(listOf("api", "discovery", list), mapOf("count" to "$count")))

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

    override fun albumImage(artist: String, album: String) =
        lookup("album|$artist|$album", listOf("api", "artwork"), mapOf("artist" to artist, "album" to album))

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
        ApiJson.decodeFromString(serializer<T>(), client.get(segments, query))
}
