package app.discair

import app.discair.data.FileResponseCache
import app.discair.data.LibrarianRepository
import app.discair.model.ArtistPage
import app.discair.net.LibrarianClient
import java.nio.file.Files
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Test

/** A revisited page keeps its saved sections while the live ones arrive: the first live section must not wipe the rest. */
class StreamSeedTest {
    private var body = ""

    private val client = OkHttpClient.Builder().addInterceptor(Interceptor { chain ->
        Response.Builder().request(chain.request()).protocol(Protocol.HTTP_1_1).code(200).message("ok")
            .body(body.toResponseBody("text/event-stream".toMediaType())).build()
    }).build()

    private val repo = LibrarianRepository(
        LibrarianClient(client, "https://l.test", "u", "p") {}, "https://l.test",
        FileResponseCache(Files.createTempDirectory("c").toFile()),
    )

    private fun sse(vararg events: Pair<String, String>) = events.joinToString("") { (name, data) -> "event: $name\ndata: $data\n\n" }

    private val artist = """{"section":"artist","available":true,"complete":true,"reason":null,"artist":{"name":"A"}}"""
    private fun owned(vararg names: String) =
        """{"section":"owned_albums","available":true,"complete":true,"reason":null,"items":[${names.joinToString(",") { "{\"name\":\"$it\"}" }}]}"""

    private fun load(): List<ArtistPage> = mutableListOf<ArtistPage>().also { pages -> repo.artistPageStream("a", null, "A", null) { pages += it } }

    @Test fun liveSectionsReplaceTheSavedOnesOneByOne() {
        body = sse("section" to artist, "section" to owned("Old"), "done" to "{}")
        load()

        body = sse("section" to artist, "section" to owned("New"), "done" to "{}")
        val pages = load()
        // The first live section (artist) arrives with the saved albums still on the page, not an empty list.
        assertEquals(listOf("Old"), pages.first().sections.ownedAlbums.items.map { it.name })
        assertEquals(listOf("New"), pages.last().sections.ownedAlbums.items.map { it.name })
    }
}
