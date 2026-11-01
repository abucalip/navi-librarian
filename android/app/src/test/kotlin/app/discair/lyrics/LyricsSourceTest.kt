package app.discair.lyrics

import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class LyricsSourceTest {
    private val extensionsYes = """{"subsonic-response":{"status":"ok","openSubsonicExtensions":[{"name":"songLyrics","versions":[1]}]}}"""
    private val extensionsNo = """{"subsonic-response":{"status":"ok","openSubsonicExtensions":[{"name":"transcoding","versions":[1]}]}}"""
    private val lyricsBody = """{"subsonic-response":{"status":"ok","lyricsList":{"structuredLyrics":[{"synced":false,"lang":"xxx","line":[{"value":"placeholder"}]}]}}}"""

    private class Rig(val urls: MutableList<String> = mutableListOf(), var timeoutSeen: Int = 0)

    private fun source(
        rig: Rig = Rig(), extensions: String = extensionsYes, lyrics: String = lyricsBody, lyricsCode: Int = 200, fail: Boolean = false,
        login: () -> Triple<String, String, String> = { Triple("https://navi.ts.net", "owner", "hunter2") },
    ): SubsonicLyricsSource {
        val canned = Interceptor { chain ->
            rig.urls += chain.request().url.toString()
            rig.timeoutSeen = chain.readTimeoutMillis()
            if (fail) throw java.net.ConnectException("refused to https://navi.ts.net/rest/x?u=owner&t=tok&s=salt")
            val isExt = chain.request().url.encodedPath.endsWith("getOpenSubsonicExtensions")
            Response.Builder().request(chain.request()).protocol(Protocol.HTTP_1_1).code(if (isExt) 200 else lyricsCode).message("m")
                .body((if (isExt) extensions else lyrics).toResponseBody("application/json".toMediaType())).build()
        }
        return SubsonicLyricsSource(OkHttpClient.Builder().addInterceptor(canned).build(), login, { "en" }) { "salt" }
    }

    @Test fun requestIsSignedWithoutThePasswordAndAsksForJson() {
        val rig = Rig()
        source(rig).lyrics("song1")
        val url = rig.urls.last()
        assertTrue(url.startsWith("https://navi.ts.net/rest/getLyricsBySongId?")); assertTrue(url.contains("id=song1")); assertTrue(url.contains("f=json"))
        assertFalse(url.contains("hunter2")); assertTrue(url.contains("s=salt")); assertTrue(url.contains("t="))
    }

    @Test fun foundAnswerComesBack() {
        val a = source().lyrics("song1")
        assertTrue(a is LyricsAnswer.Found)
    }

    @Test fun readTimeoutIsFortyFiveSeconds() {
        val rig = Rig(); source(rig).lyrics("song1")
        assertEquals(45_000, rig.timeoutSeen)
    }

    @Test fun badIdsMakeNoRequest() {
        val rig = Rig()
        for (id in listOf("", "a/b", "a&x=1", "..")) assertEquals(LyricsAnswer.None, source(rig).lyrics(id))
        assertTrue(rig.urls.isEmpty())
    }

    @Test fun extensionsAreAskedOncePerSession() {
        val rig = Rig(); val s = source(rig)
        s.lyrics("a"); s.lyrics("b")
        assertEquals(1, rig.urls.count { it.contains("getOpenSubsonicExtensions") }); assertEquals(2, rig.urls.count { it.contains("getLyricsBySongId") })
    }

    @Test fun missingExtensionMakesNoLyricsRequest() {
        val rig = Rig(); val s = source(rig, extensions = extensionsNo)
        assertEquals(LyricsAnswer.Unsupported, s.lyrics("a")); assertEquals(LyricsAnswer.Unsupported, s.lyrics("b"))
        assertTrue(rig.urls.none { it.contains("getLyricsBySongId") })
    }

    @Test fun errorCode70IsNone() {
        assertEquals(LyricsAnswer.None, source(lyrics = """{"subsonic-response":{"status":"failed","error":{"code":70}}}""").lyrics("a"))
    }

    @Test fun authCodesAreLoginRejected() {
        for (code in listOf(40, 41, 44, 50)) {
            val s = source(lyrics = """{"subsonic-response":{"status":"failed","error":{"code":$code}}}""")
            assertEquals(LyricsProblem.Unauthorised, assertThrows(LyricsException::class.java) { s.lyrics("a") }.problem)
        }
        assertEquals(LyricsProblem.Unauthorised, assertThrows(LyricsException::class.java) { source(lyricsCode = 401).lyrics("a") }.problem)
    }

    @Test fun networkFailureIsUnreachableAndLeaksNothing() {
        val e = assertThrows(LyricsException::class.java) { source(fail = true).lyrics("a") }
        assertEquals(LyricsProblem.Unreachable, e.problem)
        val text = e.message.orEmpty() + e.cause?.message.orEmpty() + e.toString()
        for (secret in listOf("hunter2", "tok", "navi.ts.net", "u=owner")) assertFalse(text.contains(secret))
    }

    @Test fun aSlowAnswerIsATimeoutNotUnreachable() {
        val slow = Interceptor { throw java.net.SocketTimeoutException("timeout https://navi.ts.net/rest/x?u=owner&t=tok&s=salt") }
        val s = SubsonicLyricsSource(OkHttpClient.Builder().addInterceptor(slow).build(), { Triple("https://navi.ts.net", "owner", "hunter2") }, { "en" }) { "salt" }
        val e = assertThrows(LyricsException::class.java) { s.lyrics("a") }
        assertEquals(LyricsProblem.TimedOut, e.problem)
        for (secret in listOf("hunter2", "tok", "navi.ts.net", "u=owner")) assertFalse((e.message.orEmpty() + e.cause?.message.orEmpty()).contains(secret))
    }

    @Test fun anEmptyLyricsListIsNone() {
        assertEquals(LyricsAnswer.None, source(lyrics = """{"subsonic-response":{"status":"ok","version":"1.16.1","lyricsList":{}}}""").lyrics("a"))
    }

    @Test fun otherFailuresCarryNoBodyOrLyrics() {
        val e = assertThrows(LyricsException::class.java) { source(lyricsCode = 500, lyrics = "placeholder lyric text").lyrics("a") }
        assertEquals(LyricsProblem.Other, e.problem); assertFalse(e.toString().contains("placeholder"))
        val bad = assertThrows(LyricsException::class.java) { source(lyrics = "placeholder lyric text").lyrics("a") }
        assertFalse(bad.toString().contains("placeholder"))
    }

    @Test fun cleartextAddressIsRefused() {
        val s = source(login = { Triple("http://navi.ts.net", "u", "p") })
        assertEquals(LyricsProblem.Other, assertThrows(LyricsException::class.java) { s.lyrics("a") }.problem)
    }
}
