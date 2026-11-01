package app.discair.player

import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class SongSourceTest {
    private fun fixture(name: String): String {
        val text = javaClass.classLoader!!.getResource("navidrome/$name.json")!!.readText()
        // The fixture wraps the recorded answer as {"request":..., "response":{"body":{...}}}.
        val body = kotlinx.serialization.json.Json.parseToJsonElement(text).let {
            (it as kotlinx.serialization.json.JsonObject)["response"] as kotlinx.serialization.json.JsonObject
        }["body"]!!
        return body.toString()
    }

    @Test fun recordedAlbumGivesSongsWithIds() {
        val songs = SubsonicParse.albumSongs(fixture("get_album"))
        assertEquals(1, songs.size)
        val s = songs.single()
        assertEquals("1aF3pKQJpLQmSVb50IlxsP", s.id); assertEquals("''Woo Hoo''", s.title)
        assertEquals("7y8UEyluchKVjyUsqNJQRQ", s.albumId); assertEquals(11, s.track); assertEquals(118, s.durationSec)
    }

    @Test fun recordedArtistGivesAlbumIds() =
        assertEquals(listOf("7y8UEyluchKVjyUsqNJQRQ"), SubsonicParse.artistAlbumIds(fixture("get_artist")))

    private fun album(vararg songs: String) = """{"subsonic-response":{"status":"ok","album":{"id":"al1","name":"Al","artist":"Ar","song":[${songs.joinToString(",")}]}}}"""
    private fun song(id: String, title: String, track: Int?, disc: Int? = null) =
        """{"id":"$id","title":"$title","track":${track ?: "null"},${if (disc != null) "\"discNumber\":$disc," else ""}"duration":100}"""

    @Test fun songsAreInDiscThenTrackOrder() {
        val songs = SubsonicParse.albumSongs(album(song("c", "C", 1, 2), song("b", "B", 2, 1), song("a", "A", 1, 1)))
        assertEquals(listOf("a", "b", "c"), songs.map { it.id })
    }

    @Test fun artistAndAlbumFallBackToTheAlbumsOwnFields() {
        val s = SubsonicParse.albumSongs(album(song("a", "A", 1))).single()
        assertEquals("Ar", s.artist); assertEquals("Al", s.album); assertEquals("al1", s.albumId)
    }

    @Test fun songsWithBadIdsAreDropped() {
        assertEquals(listOf("ok1"), SubsonicParse.albumSongs(album(song("ok1", "A", 1), song("bad/id", "B", 2), song("", "C", 3))).map { it.id })
    }

    @Test fun missingSongListIsEmpty() {
        assertTrue(SubsonicParse.albumSongs("""{"subsonic-response":{"status":"ok","album":{"id":"al1"}}}""").isEmpty())
    }

    @Test fun errorBodiesAreClassified() {
        fun problem(body: String) = assertThrows(SongSourceException::class.java) { SubsonicParse.albumSongs(body) }.problem
        fun failed(code: Int) = """{"subsonic-response":{"status":"failed","error":{"code":$code}}}"""
        assertEquals(SongSourceProblem.Unauthorised, problem(failed(40)))
        assertEquals(SongSourceProblem.NotFound, problem(failed(70)))
        assertEquals(SongSourceProblem.Other, problem(failed(0)))
        assertEquals(SongSourceProblem.Other, problem("not json"))
    }

    private fun source(code: Int = 200, body: String = "", seen: MutableList<String>? = null, fail: Boolean = false): SubsonicSongSource {
        val canned = Interceptor { chain ->
            seen?.add(chain.request().url.toString())
            if (fail) throw java.net.ConnectException("refused")
            Response.Builder().request(chain.request()).protocol(Protocol.HTTP_1_1).code(code).message("m")
                .body(body.toResponseBody("application/json".toMediaType())).build()
        }
        return SubsonicSongSource(OkHttpClient.Builder().addInterceptor(canned).build(), { Triple("https://navi.ts.net", "owner", "hunter2") }) { "salt" }
    }

    @Test fun requestIsSignedWithoutThePasswordAndAsksForJson() {
        val seen = mutableListOf<String>()
        source(body = album(song("a", "A", 1)), seen = seen).albumSongs("al1")
        val url = seen.single()
        assertTrue(url.startsWith("https://navi.ts.net/rest/getAlbum?")); assertTrue(url.contains("id=al1")); assertTrue(url.contains("f=json"))
        assertFalse(url.contains("hunter2"))
    }

    @Test fun badIdsNeverMakeARequest() {
        val seen = mutableListOf<String>()
        for (id in listOf("", "a/b", "a&x=1", "..")) {
            assertThrows(SongSourceException::class.java) { source(seen = seen).albumSongs(id) }
        }
        assertTrue(seen.isEmpty())
    }

    @Test fun httpAndNetworkFailuresAreClassified() {
        assertEquals(SongSourceProblem.Unauthorised, assertThrows(SongSourceException::class.java) { source(code = 401).albumSongs("al1") }.problem)
        assertEquals(SongSourceProblem.Other, assertThrows(SongSourceException::class.java) { source(code = 500).albumSongs("al1") }.problem)
        assertEquals(SongSourceProblem.Unreachable, assertThrows(SongSourceException::class.java) { source(fail = true).albumSongs("al1") }.problem)
    }

    @Test fun cleartextAddressIsRefused() {
        val s = SubsonicSongSource(OkHttpClient(), { Triple("http://navi.ts.net", "u", "p") })
        assertThrows(SongSourceException::class.java) { s.albumSongs("al1") }
    }

    @Test fun matchingPrefersTheTitleThenTheTrackNumber() {
        val songs = listOf(SongRef("a", "Intro", "x", "y", "al", 1, null, 10), SongRef("b", "Don't Stop", "x", "y", "al", 2, null, 10))
        assertEquals("b", matchSong(songs, "dont stop", 9)?.id)
        assertEquals("a", matchSong(songs, "Remastered Intro", 1)?.id)
        assertNull(matchSong(songs, "Nothing", 7))
        assertNull(matchSong(songs, "", null))
    }
}
