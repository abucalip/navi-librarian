package app.discair.lyrics

import app.discair.net.Subsonic
import app.discair.player.isValidSongId
import java.io.IOException
import java.util.concurrent.TimeUnit
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import okhttp3.Request

/** Where lyrics come from: the owner's Navidrome only (contract 4). */
interface LyricsSource {
    /** Throws [LyricsException]. An invalid song id makes no request and answers [LyricsAnswer.None]. */
    fun lyrics(songId: String): LyricsAnswer
}

/**
 * `getLyricsBySongId` with the login saved on the device, signed like [app.discair.player.SubsonicSongSource]:
 * a fresh salt per request, no password in the address, https only, no redirects. Whether the server lists
 * `songLyrics` is asked once per instance (one session) and a "no" stops every later lyrics request.
 */
class SubsonicLyricsSource(
    private val http: OkHttpClient,
    private val login: () -> Triple<String, String, String>,
    private val phoneLanguage: () -> String = { java.util.Locale.getDefault().language },
    private val newSalt: () -> String = { java.util.UUID.randomUUID().toString().replace("-", "").take(12) },
) : LyricsSource {
    @Volatile private var supported: Boolean? = null

    private fun url(call: String, id: String?): HttpUrl {
        val (base, user, password) = login()
        val parsed = base.toHttpUrlOrNull()?.takeIf { it.isHttps }
            ?: throw LyricsException(LyricsProblem.Other, "The Navidrome address is not set.")
        val salt = newSalt()
        val builder = parsed.newBuilder().addPathSegments("rest/$call")
            .addQueryParameter("u", user).addQueryParameter("t", Subsonic.token(password, salt)).addQueryParameter("s", salt)
            .addQueryParameter("v", Subsonic.API_VERSION).addQueryParameter("c", Subsonic.CLIENT).addQueryParameter("f", "json")
        if (id != null) builder.addQueryParameter("id", id)
        return builder.build()
    }

    private fun get(call: String, id: String?): String {
        val client = http.newBuilder().followRedirects(false).followSslRedirects(false)
            .readTimeout(READ_TIMEOUT_SECONDS, TimeUnit.SECONDS).build()
        try {
            client.newCall(Request.Builder().url(url(call, id)).get().build()).execute().use { response ->
                if (response.code == 401 || response.code == 403) throw LyricsException(LyricsProblem.Unauthorised, "Navidrome rejected the saved login.")
                if (!response.isSuccessful) throw LyricsException(LyricsProblem.Other, "Navidrome answered ${response.code}.")
                // A cap, so an odd answer cannot fill memory.
                return response.peekBody(MAX_BODY_BYTES).string()
            }
        } catch (e: java.net.SocketTimeoutException) {
            throw LyricsException(LyricsProblem.TimedOut, "Navidrome took too long to answer.")
        } catch (e: IOException) {
            // The IOException is dropped: its text can carry the request address.
            throw LyricsException(LyricsProblem.Unreachable, "Can't reach Navidrome. Is Tailscale connected?")
        }
    }

    private fun serverSupportsLyrics(): Boolean {
        supported?.let { return it }
        val answer = LyricsParse.supportsLyrics(get("getOpenSubsonicExtensions", null))
        supported = answer
        return answer
    }

    override fun lyrics(songId: String): LyricsAnswer {
        if (!isValidSongId(songId)) return LyricsAnswer.None
        if (!serverSupportsLyrics()) return LyricsAnswer.Unsupported
        return LyricsParse.answer(get("getLyricsBySongId", songId), phoneLanguage())
    }

    companion object {
        // Measured on the owner's server: songs with no lyrics can take over 23 s to be answered.
        const val READ_TIMEOUT_SECONDS = 45L
        const val MAX_BODY_BYTES = 1_000_000L
    }
}
