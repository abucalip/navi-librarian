package app.discair.player

import java.net.ServerSocket
import java.util.Collections
import kotlinx.coroutines.runBlocking
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** A one-thread HTTP server: records each request target and answers with a raw response. */
private class QueueFakeServer(private val respond: (String) -> String) {
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
                    requests += line.split(" ").getOrElse(1) { "" }
                    c.getOutputStream().apply { write(respond(line).toByteArray()); flush() }
                }
            }
        } catch (e: Exception) { /* closed */ }
    }.apply { isDaemon = true; start() }

    fun stop() { socket.close() }
}

private fun http(body: String) =
    "HTTP/1.1 200 X\r\nContent-Type: application/json\r\nContent-Length: ${body.toByteArray().size}\r\nConnection: close\r\n\r\n$body"

class NavidromeQueueSaverTest {
    private var server: QueueFakeServer? = null
    @After fun stop() { server?.stop() }

    private val ok = """{"subsonic-response":{"status":"ok","version":"1.16.1"}}"""
    private val failed = """{"subsonic-response":{"status":"failed","error":{"code":70,"message":"no"}}}"""

    private fun saver(reply: String): NavidromeQueueSaver {
        val s = QueueFakeServer { http(reply) }; server = s
        return NavidromeQueueSaver(OkHttpClient(), "http://127.0.0.1:${s.port}".toHttpUrl(), "owner", "hunter2") { "salt" }
    }

    @Test fun sendsEverySongIdTheCurrentSongAndThePositionUnderTheDiscairAndroidName() {
        val api = saver(ok)
        val accepted = runBlocking { api.save(RemotePlayQueue(listOf("s2", "s3"), "s2", 61_000)) }
        assertTrue(accepted)
        val uri = server!!.requests.single()
        assertTrue(uri.startsWith("/rest/savePlayQueue?"))
        assertTrue(uri.contains("id=s2&id=s3"))
        assertTrue(uri.contains("current=s2"))
        assertTrue(uri.contains("position=61000"))
        assertTrue(uri.contains("c=discair-android"))
        assertFalse(uri.contains("hunter2"))
    }

    @Test fun aFailedReplyIsNotAccepted() {
        val api = saver(failed)
        assertFalse(runBlocking { api.save(RemotePlayQueue(listOf("s1"), "s1", 0)) })
    }

    @Test fun onlyAnHttpsAddressIsUsedInProduction() {
        assertNotNull(NavidromeQueueSaver.create(OkHttpClient(), "https://music.example", "u", "p"))
        assertNull(NavidromeQueueSaver.create(OkHttpClient(), "http://music.example", "u", "p"))
    }
}
