package app.discair.player

import java.io.File
import java.io.IOException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.runBlocking
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class OfflineSongsTest {
    @get:Rule val tmp = TemporaryFolder()

    private val song = SongRef("s1", "Song", "Artist", "Album", "a1", 1, 1, 200, suffix = "flac")
    private val requested = mutableListOf<String>()

    private fun client(type: String = "audio/flac", code: Int = 200, fail: Boolean = false, body: String = "AUDIO-BYTES") =
        OkHttpClient.Builder().addInterceptor { chain ->
            val request = chain.request()
            requested += request.url.encodedPath
            if (fail) throw IOException("down")
            Response.Builder().request(request).protocol(Protocol.HTTP_1_1).code(code).message("x")
                .body(body.toResponseBody(type.toMediaType())).build()
        }.build()

    private fun store(http: OkHttpClient, dir: File = tmp.newFolder()) =
        OfflineSongs(dir, http, { Triple("https://nd.example", "u", "p") }, Dispatchers.Unconfined, { "salt" })

    @Test fun `downloads the original file and plays from it`() = runBlocking {
        val offline = store(client())
        offline.download(song)
        val file = offline.find("s1")
        assertNotNull(file)
        assertEquals("AUDIO-BYTES", file!!.readText())
        assertTrue(file.name.endsWith(".flac"))
        assertEquals(listOf("/rest/download"), requested)
        assertEquals(OfflineStatus.Done, offline.status.value["s1"])
        assertEquals(listOf(song), offline.savedAlbum("a1"))
    }

    @Test fun `saved songs survive a restart`() = runBlocking {
        val dir = tmp.newFolder()
        store(client(), dir).download(song)
        val again = store(client(), dir)
        assertTrue(again.isSaved("s1"))
        assertEquals(1, again.savedCount())
    }

    @Test fun `an error answer is not kept as a song`() = runBlocking {
        val offline = store(client(type = "application/json", body = "{\"subsonic-response\":{}}"))
        try { offline.download(song); fail() } catch (e: OfflineException) { assertEquals(OfflineProblem.Other, e.problem) }
        assertFalse(offline.isSaved("s1"))
        assertEquals(OfflineStatus.Failed, offline.status.value["s1"])
    }

    @Test fun `an unreachable server leaves nothing behind`() = runBlocking {
        val dir = tmp.newFolder()
        val offline = store(client(fail = true), dir)
        try { offline.download(song); fail() } catch (e: OfflineException) { assertEquals(OfflineProblem.Unreachable, e.problem) }
        assertTrue(dir.listFiles().orEmpty().none { it.name.startsWith("s1") })
    }

    @Test fun `a refused login is reported`() = runBlocking {
        val offline = store(client(code = 401))
        try { offline.download(song); fail() } catch (e: OfflineException) { assertEquals(OfflineProblem.Unauthorised, e.problem) }
    }

    @Test fun `remove all erases files and index`() = runBlocking {
        val dir = tmp.newFolder()
        val offline = store(client(), dir)
        offline.download(song)
        offline.removeAll()
        assertNull(offline.find("s1"))
        assertEquals(0, store(client(), dir).savedCount())
    }

    @Test fun `an invalid id is refused before any request`() = runBlocking {
        val offline = store(client())
        try { offline.download(song.copy(id = "../x")); fail() } catch (e: OfflineException) { }
        assertTrue(requested.isEmpty())
    }

    @Test fun `album listing falls back to saved songs only when Navidrome is unreachable`() = runBlocking {
        val offline = store(client())
        offline.download(song)
        val down = object : SongSource {
            override fun albumSongs(albumId: String): List<SongRef> = throw SongSourceException(SongSourceProblem.Unreachable, "down")
            override fun artistAlbumIds(artistId: String): List<String> = emptyList()
        }
        assertEquals(listOf(song), OfflineAwareSongSource(down, offline).albumSongs("a1"))
        try { OfflineAwareSongSource(down, offline).albumSongs("other"); fail() } catch (e: SongSourceException) { }
        val refused = object : SongSource {
            override fun albumSongs(albumId: String): List<SongRef> = throw SongSourceException(SongSourceProblem.Unauthorised, "no")
            override fun artistAlbumIds(artistId: String): List<String> = emptyList()
        }
        try { OfflineAwareSongSource(refused, offline).albumSongs("a1"); fail() } catch (e: SongSourceException) { assertEquals(SongSourceProblem.Unauthorised, e.problem) }
    }
}
