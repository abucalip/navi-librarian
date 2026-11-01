package app.discair.player

import java.io.IOException
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Request
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class PlaybackFailureTest {
    private fun err(code: Int) = """{"subsonic-response":{"status":"failed","version":"1.16.1","error":{"code":$code,"message":"x"}}}"""

    @Test fun subsonicErrorBodiesAreClassified() {
        for (c in listOf(40, 41, 44, 50)) assertTrue("$c", PlaybackFailures.fromErrorBody(err(c)) is PlaybackFailure.SignInAgain)
        assertTrue(PlaybackFailures.fromErrorBody(err(70)) is PlaybackFailure.Unavailable)
        assertTrue(PlaybackFailures.fromErrorBody(err(0)) is PlaybackFailure.Server)
        assertTrue(PlaybackFailures.fromErrorBody("garbage") is PlaybackFailure.Unavailable)
        assertTrue(PlaybackFailures.fromErrorBody("<subsonic-response status=\"failed\"><error code=\"40\" message=\"x\"/></subsonic-response>") is PlaybackFailure.SignInAgain)
    }

    @Test fun httpStatusesAreClassified() {
        assertTrue(PlaybackFailures.fromHttpStatus(401) is PlaybackFailure.SignInAgain)
        assertTrue(PlaybackFailures.fromHttpStatus(404) is PlaybackFailure.Unavailable)
        assertTrue(PlaybackFailures.fromHttpStatus(500) is PlaybackFailure.Server)
    }

    @Test fun audioContentTypes() {
        assertTrue(PlaybackFailures.isAudioContentType("audio/flac"))
        assertTrue(PlaybackFailures.isAudioContentType("application/octet-stream"))
        assertTrue(PlaybackFailures.isAudioContentType(null))
        for (t in listOf("application/json", "application/json; charset=utf-8", "text/xml", "text/html", "application/xml", "application/problem+json")) {
            assertFalse(t, PlaybackFailures.isAudioContentType(t))
        }
    }

    @Test fun failureIsFoundInsideWrappedExceptions() {
        val wrapped = RuntimeException("player", IOException("source", StreamRefusedException(PlaybackFailure.SignInAgain())))
        assertTrue(PlaybackFailures.fromThrowable(wrapped) is PlaybackFailure.SignInAgain)
        assertNull(PlaybackFailures.fromThrowable(IOException("x")))
        assertNull(PlaybackFailures.fromThrowable(null))
    }

    private fun client(code: Int, type: String, body: String): OkHttpClient {
        val canned = Interceptor { chain ->
            Response.Builder().request(chain.request()).protocol(Protocol.HTTP_1_1).code(code).message("m")
                .header("Content-Type", type).body(body.toResponseBody(type.toMediaType())).build()
        }
        return OkHttpClient.Builder().addInterceptor(RefusedBodyInterceptor()).addInterceptor(canned).build()
    }

    private fun get(c: OkHttpClient) =
        c.newCall(Request.Builder().url("https://navi.ts.net/rest/stream?u=owner&t=SECRET&s=SALT&id=a").build()).execute()

    private fun refusal(c: OkHttpClient): StreamRefusedException {
        try { get(c).close() } catch (e: StreamRefusedException) { return e }
        fail("expected a refusal"); throw IllegalStateException()
    }

    @Test fun errorAsOkJsonBecomesAFailureWithoutUrlOrToken() {
        val e = refusal(client(200, "application/json", err(70)))
        assertTrue(e.failure is PlaybackFailure.Unavailable)
        assertFalse(e.message.orEmpty().contains("SECRET")); assertFalse(e.message.orEmpty().contains("navi.ts.net"))
    }

    @Test fun errorAsOkXmlAuthIsSignInAgain() {
        val e = refusal(client(200, "text/xml", "<subsonic-response status=\"failed\"><error code=\"40\"/></subsonic-response>"))
        assertTrue(e.failure is PlaybackFailure.SignInAgain)
    }

    @Test fun nonSuccessStatusesAreRefused() {
        assertTrue(refusal(client(404, "text/plain", "no")).failure is PlaybackFailure.Unavailable)
        assertTrue(refusal(client(401, "text/plain", "no")).failure is PlaybackFailure.SignInAgain)
        assertTrue(refusal(client(502, "text/html", "<html>")).failure is PlaybackFailure.Server)
    }

    @Test fun audioAndPartialAudioPassThrough() {
        get(client(200, "audio/mpeg", "bytes")).use { assertEquals("bytes", it.body!!.string()) }
        get(client(206, "audio/flac", "part")).use { assertEquals(206, it.code) }
    }

    @Test fun unsatisfiableRangeIsLeftToThePlayer() {
        get(client(416, "audio/flac", "")).use { assertEquals(416, it.code) }
    }
}
