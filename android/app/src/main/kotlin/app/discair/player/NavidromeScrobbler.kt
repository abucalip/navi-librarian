package app.discair.player

import app.discair.net.Subsonic
import java.io.IOException
import java.util.concurrent.atomic.AtomicBoolean
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.Call
import okhttp3.EventListener
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import okhttp3.Request

/**
 * Calls Navidrome's `scrobble` directly. Whether a request was sent is recorded by the HTTP client at
 * the moment it starts writing the request, so a failure before that point is [SendOutcome.NotSent] and
 * every failure after it is [SendOutcome.Ambiguous]. The password, token and URL never appear in an outcome.
 */
class NavidromeScrobbler(
    private val http: OkHttpClient,
    private val base: HttpUrl,
    private val username: String,
    private val password: String,
    private val newSalt: () -> String = { java.util.UUID.randomUUID().toString().replace("-", "").take(12) },
) : ScrobbleApi {
    override suspend fun send(songId: String, submission: Boolean, timeMs: Long): SendOutcome {
        if (!isValidSongId(songId)) return SendOutcome.Ambiguous
        val salt = newSalt()
        val url = base.newBuilder()
            .addPathSegments("rest/scrobble")
            .addQueryParameter("u", username)
            .addQueryParameter("t", Subsonic.token(password, salt))
            .addQueryParameter("s", salt)
            .addQueryParameter("v", Subsonic.API_VERSION)
            .addQueryParameter("c", Subsonic.CLIENT)
            .addQueryParameter("f", "json")
            .addQueryParameter("id", songId)
            .addQueryParameter("time", timeMs.toString())
            .addQueryParameter("submission", submission.toString())
            .build()
        val sent = AtomicBoolean(false)
        val client = http.newBuilder()
            .followRedirects(false)
            .followSslRedirects(false)
            .eventListenerFactory {
                object : EventListener() {
                    override fun requestHeadersStart(call: Call) { sent.set(true) }
                }
            }
            .build()
        return withContext(Dispatchers.IO) {
            try {
                client.newCall(Request.Builder().url(url).get().build()).execute().use { response ->
                    val text = response.body?.string().orEmpty()
                    if (response.isSuccessful && isOk(text)) SendOutcome.Accepted else SendOutcome.Ambiguous
                }
            } catch (e: IOException) {
                if (sent.get()) SendOutcome.Ambiguous else SendOutcome.NotSent
            }
        }
    }

    private fun isOk(body: String): Boolean = try {
        val root = Json.parseToJsonElement(body).jsonObject["subsonic-response"] as? JsonObject
        root?.get("status")?.jsonPrimitive?.contentOrNull == "ok"
    } catch (e: Exception) {
        false
    }

    companion object {
        /** Production entry point: https only. */
        fun create(http: OkHttpClient, baseUrl: String, username: String, password: String): NavidromeScrobbler? {
            val base = baseUrl.toHttpUrlOrNull()?.takeIf { it.isHttps } ?: return null
            return NavidromeScrobbler(http, base, username, password)
        }
    }
}
