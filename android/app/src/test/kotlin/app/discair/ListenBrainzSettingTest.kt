package app.discair

import app.discair.data.FileResponseCache
import app.discair.data.LibrarianRepository
import app.discair.model.listenBrainzBody
import app.discair.model.parseListenBrainzAccount
import app.discair.net.LibrarianClient
import java.nio.file.Files
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** The Settings section for the server's ListenBrainz account: live reads, a PUT with username and token, then the server's own check. */
class ListenBrainzSettingTest {
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

    @Test fun readsTheAccountWithoutAToken() {
        replies += """{"username":"abc","token_configured":true}"""
        val a = repo().listenBrainz()
        assertTrue(a.connected && a.tokenConfigured && a.username == "abc")
        assertEquals("GET /api/settings/listenbrainz ", seen.last())
    }

    @Test fun anEmptyReplyMeansNotConnected() {
        assertFalse(parseListenBrainzAccount("{}").connected)
    }

    @Test fun connectSavesThenAsksTheServerToCheck() {
        replies += """{"ok":true,"username":"abc"}"""
        replies += """{"ok":true,"status":"connected","message":"ListenBrainz profile is reachable."}"""
        val check = repo().connectListenBrainz(" abc ", "tok_1")
        assertTrue(check.ok)
        assertEquals("""PUT /api/settings/listenbrainz {"username":"abc","token":"tok_1"}""", seen[0])
        assertEquals("POST /api/settings/listenbrainz/test {}", seen[1])
    }

    @Test fun aBlankTokenIsSentBlank() {
        assertEquals("""{"username":"abc","token":""}""", listenBrainzBody("abc", "  "))
    }
}
