package app.discair

import app.discair.data.FileResponseCache
import app.discair.data.LibrarianRepository
import app.discair.model.ArtistLean
import app.discair.model.Lean
import app.discair.model.artistBody
import app.discair.model.blockableGenres
import app.discair.model.genreBody
import app.discair.model.leanBody
import app.discair.model.parseArtistLeans
import app.discair.model.parseBlockedArtists
import app.discair.model.parseBlockedGenres
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

/** Star Operation S2c: the blocklist's parsers, bodies and routes (DELETE carries a JSON body). */
class BlocklistTest {
    private val seen = mutableListOf<String>()
    private val replies = ArrayDeque<String>()

    private fun repo(): LibrarianRepository {
        val http = OkHttpClient.Builder().addInterceptor(Interceptor { chain ->
            val request = chain.request()
            val body = request.body?.let { b -> okio.Buffer().also { b.writeTo(it) }.readUtf8() }.orEmpty()
            seen += request.method + " " + request.url.encodedPath + " " + body
            Response.Builder().request(request).protocol(Protocol.HTTP_1_1).code(200).message("m")
                .body((replies.removeFirstOrNull() ?: "{}").toResponseBody("application/json".toMediaType())).build()
        }).build()
        val cache = FileResponseCache(Files.createTempDirectory("c").toFile())
        return LibrarianRepository(LibrarianClient(http, "https://l.test", "u", "p"), "https://l.test", cache)
    }

    @Test fun parsesTheThreeListsAndDropsWhatItCannotUse() {
        assertEquals(listOf("Shoegaze"), parseBlockedGenres("""{"genres":[{"genre":"Shoegaze","blocked_at":1.0},{"genre":" "}]}"""))
        assertEquals(listOf("Ride"), parseBlockedArtists("""{"artists":[{"artist":"Ride","blocked_at":1.0},{}]}"""))
        assertEquals(
            listOf(ArtistLean("Lush", Lean.More)),
            parseArtistLeans("""{"artists":[{"artist":"Lush","lean":"more"},{"artist":"X","lean":"sideways"},{"lean":"less"}]}"""),
        )
        assertEquals(emptyList<String>(), parseBlockedGenres("{}"))
    }

    @Test fun readsAllThreeRoutesLive() {
        replies += """{"genres":[{"genre":"Shoegaze"}]}"""
        replies += """{"artists":[{"artist":"Ride"}]}"""
        replies += """{"artists":[{"artist":"Lush","lean":"less"}]}"""
        val list = repo().blocklist()
        assertEquals(listOf("Shoegaze"), list.genres)
        assertEquals(listOf("Ride"), list.hiddenArtists)
        assertEquals(listOf(ArtistLean("Lush", Lean.Less)), list.leans)
        assertEquals(
            listOf("GET /api/discovery/blocked-genres ", "GET /api/discovery/blocked-artists ", "GET /api/discovery/artist-lean "),
            seen,
        )
    }

    @Test fun writesUseThePostAndDeleteBodiesTheServerExpects() {
        val r = repo()
        r.blockGenre("Post Punk")
        r.unblockGenre("Post Punk")
        r.unblockArtist("Ride")
        r.setArtistLean("Lush", Lean.More, listOf("Shoegaze"), null)
        r.clearArtistLean("Lush")
        assertEquals(
            listOf(
                """POST /api/discovery/blocked-genres {"genre":"Post Punk"}""",
                """DELETE /api/discovery/blocked-genres {"genre":"Post Punk"}""",
                """DELETE /api/discovery/blocked-artists {"artist":"Ride"}""",
                """POST /api/discovery/artist-lean {"artist":"Lush","lean":"more","metadata":{"genres":["Shoegaze"]}}""",
                """DELETE /api/discovery/artist-lean {"artist":"Lush"}""",
            ),
            seen,
        )
    }

    @Test fun leanBodyKeepsOnlyGenresAndLens() {
        assertEquals("""{"artist":"A","lean":"less","metadata":{}}""", leanBody("A", Lean.Less, emptyList()))
        assertEquals(
            """{"artist":"A","lean":"less","metadata":{"genres":["x"],"lens":"deep_cuts"}}""",
            leanBody("A", Lean.Less, listOf("x"), "deep_cuts"),
        )
        assertEquals("""{"genre":"G"}""", genreBody("G"))
        assertEquals("""{"artist":"A"}""", artistBody("A"))
    }

    @Test fun onlyTheAlbumsOwnGenresAreOffered() {
        assertEquals(listOf("Post Punk", "Jazz", "Soul"), blockableGenres(listOf(" Post  Punk ", "post punk", "", "Jazz", "Soul", "Funk")))
        assertEquals(emptyList<String>(), blockableGenres(emptyList()))
    }
}
