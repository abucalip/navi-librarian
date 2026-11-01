package app.discair.player

import app.discair.net.Subsonic
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull

/** Maximum bit rates the stream call may ask for, in kbps. `null` in [StreamQuality] means the original file. */
val ALLOWED_BIT_RATES: Set<Int> = setOf(64, 96, 128, 192, 256, 320)

/** Transcode formats the stream call may ask for. Original is expressed by omitting the parameter. */
enum class TranscodeFormat(val wire: String) { Mp3("mp3"), Opus("opus") }

/** What the owner chose in Settings: the original file, or a bit-rate cap. */
data class StreamQuality(val maxBitRate: Int? = null) {
    init {
        require(maxBitRate == null || maxBitRate in ALLOWED_BIT_RATES) { "Unsupported bit rate." }
    }

    companion object { val Original = StreamQuality() }
}

private val SONG_ID = Regex("^[A-Za-z0-9_-]{1,128}$")

fun isValidSongId(id: String): Boolean = SONG_ID.matches(id)

/**
 * Builds Subsonic `stream` URLs. Only `id`, an allowlisted `maxBitRate` and an allowlisted `format`
 * can ever be emitted; values are written from the allowlist, never copied from the caller.
 * A fresh salt is used for every URL and the password is never part of the URL.
 */
class StreamUrlBuilder(
    private val baseUrl: String,
    private val username: String,
    private val password: String,
    private val newSalt: () -> String = { java.util.UUID.randomUUID().toString().replace("-", "").take(12) },
) {
    fun build(songId: String, quality: StreamQuality = StreamQuality.Original, format: TranscodeFormat? = null): HttpUrl {
        require(isValidSongId(songId)) { "Invalid song id." }
        val base = baseUrl.toHttpUrlOrNull()
        require(base != null && base.isHttps) { "The Navidrome address must be https." }
        val salt = newSalt()
        val builder = base.newBuilder()
            .addPathSegments("rest/stream")
            .addQueryParameter("u", username)
            .addQueryParameter("t", Subsonic.token(password, salt))
            .addQueryParameter("s", salt)
            .addQueryParameter("v", Subsonic.API_VERSION)
            .addQueryParameter("c", Subsonic.CLIENT)
            .addQueryParameter("id", songId)
        quality.maxBitRate?.let { builder.addQueryParameter("maxBitRate", ALLOWED_BIT_RATES.first { r -> r == it }.toString()) }
        format?.let { builder.addQueryParameter("format", it.wire) }
        return builder.build()
    }
}

private val SECRET_PARAMS = Regex("([?&;](?:u|t|s|p|password|token|salt)=)[^&\\s\"'<>]*", RegexOption.IGNORE_CASE)

/** Removes credential parameters from any text that may contain a stream URL (errors, logs). */
fun redactSecrets(text: String?): String = text.orEmpty().replace(SECRET_PARAMS, "$1***")
