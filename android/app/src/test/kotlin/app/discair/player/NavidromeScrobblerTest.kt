package app.discair.player

import java.net.ServerSocket
import java.util.Collections
import kotlinx.coroutines.runBlocking
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** A tiny one-thread HTTP server: records each request target and answers with a raw response, or none. */
private class FakeServer(private val respond: (String) -> String?) {
    val requests: MutableList<String> = Collections.synchronizedList(mutableListOf())
    private val socket = ServerSocket(0, 50, java.net.InetAddress.getByName("127.0.0.1"))
    val port get() = socket.localPort
    private val thread = Thread {
        try {
            while (true) {
                val client = socket.accept()
                client.use { c ->
                    val reader = c.getInputStream().bufferedReader()
                    val line = reader.readLine() ?: return@use
                    while (reader.readLine().let { it != null && it.isNotEmpty() }) { /* skip headers */ }
                    val target = line.split(" ").getOrElse(1) { "" }
                    requests += target
                    respond(target)?.let { c.getOutputStream().apply { write(it.toByteArray()); flush() } }
                }
            }
        } catch (e: Exception) { /* closed */ }
    }.apply { isDaemon = true; start() }

    fun stop() { socket.close() }
}

private fun http(code: Int, body: String, extra: String = "") =
    "HTTP/1.1 $code X\r\nContent-Type: application/json\r\nContent-Length: ${body.toByteArray().size}\r\nConnection: close\r\n$extra\r\n$body"

class NavidromeScrobblerTest {
    private var server: FakeServer? = null
    private val http = OkHttpClient()
    private val requests get() = server!!.requests

    @After fun stop() { server?.stop() }

    private fun serve(respond: (String) -> String?): NavidromeScrobbler {
        val s = FakeServer(respond); server = s
        return NavidromeScrobbler(http, "http://127.0.0.1:${s.port}".toHttpUrl(), "owner", "hunter2") { "salt" }
    }

    private val ok = """{"subsonic-response":{"status":"ok","version":"1.16.1"}}"""

    @Test fun acceptedRequestCarriesIdTimeAndSubmissionWithoutThePassword() {
        val api = serve { http(200, ok) }
        assertEquals(SendOutcome.Accepted, runBlocking { api.send("abc", true, 1234L) })
        val uri = requests.single()
        assertTrue(uri.startsWith("/rest/scrobble?"))
        assertTrue(uri.contains("id=abc")); assertTrue(uri.contains("time=1234")); assertTrue(uri.contains("submission=true"))
        assertFalse(uri.contains("hunter2"))
        runBlocking { api.send("abc", false, 1234L) }
        assertTrue(requests.last().contains("submission=false"))
    }

    @Test fun errorBodyAndServerErrorsAreAmbiguousNotRetryable() {
        val failed = serve { http(200, """{"subsonic-response":{"status":"failed","error":{"code":70}}}""") }
        assertEquals(SendOutcome.Ambiguous, runBlocking { failed.send("abc", true, 1L) })
        stop()
        val broken = serve { http(500, "oops") }
        assertEquals(SendOutcome.Ambiguous, runBlocking { broken.send("abc", true, 1L) })
        stop()
        val junk = serve { http(200, "not json") }
        assertEquals(SendOutcome.Ambiguous, runBlocking { junk.send("abc", true, 1L) })
    }

    @Test fun requestSentButResponseLostIsAmbiguous() {
        // The server receives the request and then drops the connection without answering.
        val api = serve { null }
        assertEquals(SendOutcome.Ambiguous, runBlocking { api.send("abc", true, 1L) })
        assertEquals(1, requests.size) // it did reach the server once
    }

    @Test fun connectionRefusedBeforeAnyRequestIsNotSent() {
        val port = ServerSocket(0).use { it.localPort } // a port that is now closed
        val api = NavidromeScrobbler(http, "http://127.0.0.1:$port".toHttpUrl(), "owner", "hunter2")
        assertEquals(SendOutcome.NotSent, runBlocking { api.send("abc", true, 1L) })
    }

    @Test fun badIdsNeverReachTheServer() {
        val api = serve { http(200, ok) }
        for (id in listOf("", "a/b", "a&x=1")) assertEquals(SendOutcome.Ambiguous, runBlocking { api.send(id, true, 1L) })
        assertTrue(requests.isEmpty())
    }

    @Test fun redirectsAreNotFollowed() {
        val api = serve { http(302, "", "Location: http://127.0.0.1:1/x\r\n") }
        assertEquals(SendOutcome.Ambiguous, runBlocking { api.send("abc", true, 1L) })
        assertEquals(1, requests.size)
    }

    @Test fun productionFactoryRequiresHttps() {
        assertNull(NavidromeScrobbler.create(http, "http://navi.ts.net", "u", "p"))
        assertNull(NavidromeScrobbler.create(http, "nonsense", "u", "p"))
        assertTrue(NavidromeScrobbler.create(http, "https://navi.ts.net", "u", "p") != null)
    }
}
