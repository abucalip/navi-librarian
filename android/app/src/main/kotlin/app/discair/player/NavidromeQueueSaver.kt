package app.discair.player

import app.discair.net.Subsonic
import java.io.IOException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import okhttp3.Request

/**
 * Calls Navidrome's `savePlayQueue` with the owner's login, so the Mac app can offer "playing on your phone"
 * (redesign D5). Same signing and https-only rule as [NavidromeScrobbler]. The password and token are never
 * returned or logged.
 */
class NavidromeQueueSaver(
    private val http: OkHttpClient,
    private val base: HttpUrl,
    private val username: String,
    private val password: String,
    private val newSalt: () -> String = { java.util.UUID.randomUUID().toString().replace("-", "").take(12) },
) : RemotePlayQueueApi {
    override suspend fun save(queue: RemotePlayQueue): Boolean {
        val salt = newSalt()
        val url = base.newBuilder()
            .addPathSegments("rest/savePlayQueue")
            .addQueryParameter("u", username)
            .addQueryParameter("t", Subsonic.token(password, salt))
            .addQueryParameter("s", salt)
            .addQueryParameter("v", Subsonic.API_VERSION)
            .addQueryParameter("c", Subsonic.PHONE_CLIENT)
            .addQueryParameter("f", "json")
            .addQueryParameter("current", queue.currentId)
            .addQueryParameter("position", queue.positionMs.toString())
        queue.songIds.forEach { url.addQueryParameter("id", it) }
        val request = Request.Builder().url(url.build()).get().build()
        return withContext(Dispatchers.IO) {
            try {
                http.newCall(request).execute().use { response ->
                    response.isSuccessful && Subsonic.pingFailure(response.body?.string().orEmpty()) == null
                }
            } catch (e: IOException) {
                false
            }
        }
    }

    companion object {
        /** Production entry point: https only. Null when the saved address is not https. */
        fun create(http: OkHttpClient, baseUrl: String, username: String, password: String): NavidromeQueueSaver? {
            val base = baseUrl.toHttpUrlOrNull()?.takeIf { it.isHttps } ?: return null
            return NavidromeQueueSaver(http, base, username, password)
        }
    }
}
