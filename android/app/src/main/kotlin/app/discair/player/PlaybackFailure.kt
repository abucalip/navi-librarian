package app.discair.player

import java.io.IOException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

/** Why a song could not be played, in words the screen can show. Nothing here carries a URL or token. */
sealed interface PlaybackFailure {
    val message: String

    /** The song is gone or refused. Mark it unavailable and move on; never retry in a loop. */
    data class Unavailable(override val message: String = "This song is not available on the server.") : PlaybackFailure

    /** The stored login was rejected. Stop and say "Sign in again" once. */
    data class SignInAgain(override val message: String = "Sign in again.") : PlaybackFailure

    /** The connection dropped. Show buffering and resume from the position when it returns. */
    data class Network(override val message: String = "Connection lost. Waiting to resume.") : PlaybackFailure

    /** The device cannot decode the original file. Retry once with the mp3 fallback. */
    data class UnsupportedFormat(override val message: String = "This format is not supported. Trying MP3.") : PlaybackFailure

    data class Server(override val message: String = "The server had a problem.") : PlaybackFailure
}

private val AUTH_CODES = setOf(40, 41, 44, 50)
private const val NOT_FOUND_CODE = 70

/** Thrown by [RefusedBodyInterceptor] so the failure survives the player's own exception wrapping. */
class StreamRefusedException(val failure: PlaybackFailure) : IOException(failure.message)

object PlaybackFailures {
    /** Looks for the failure in a player error and its causes. */
    fun fromThrowable(error: Throwable?): PlaybackFailure? {
        var current: Throwable? = error
        var depth = 0
        while (current != null && depth++ < 10) {
            if (current is StreamRefusedException) return current.failure
            current = current.cause
        }
        return null
    }

    /** Status of a non-2xx answer from the stream call. */
    fun fromHttpStatus(code: Int): PlaybackFailure = when (code) {
        401, 403 -> PlaybackFailure.SignInAgain()
        404, 410 -> PlaybackFailure.Unavailable()
        else -> PlaybackFailure.Server("The server answered $code.")
    }

    /**
     * A 2xx answer whose content is JSON, XML or text is a Subsonic error, not audio.
     * An unreadable body is treated as unavailable so the player never loops on it.
     */
    fun fromErrorBody(body: String, json: Json = Json { ignoreUnknownKeys = true }): PlaybackFailure {
        val code = try {
            val root = json.parseToJsonElement(body).jsonObject["subsonic-response"] as? JsonObject
            (root?.get("error") as? JsonObject)?.get("code")?.jsonPrimitive?.intOrNull
        } catch (e: Exception) {
            xmlCode(body)
        }
        return when (code) {
            in AUTH_CODES -> PlaybackFailure.SignInAgain()
            NOT_FOUND_CODE -> PlaybackFailure.Unavailable()
            null -> PlaybackFailure.Unavailable()
            else -> PlaybackFailure.Server()
        }
    }

    private fun xmlCode(body: String): Int? =
        Regex("<error[^>]*\\bcode=\"(\\d+)\"").find(body)?.groupValues?.get(1)?.toIntOrNull()

    fun isAudioContentType(contentType: String?): Boolean {
        val type = contentType?.substringBefore(';')?.trim()?.lowercase() ?: return true
        return !(type.startsWith("text/") || type == "application/json" || type == "application/xml" ||
            type.endsWith("+json") || type.endsWith("+xml"))
    }

    /** Unsupported or undecodable format: the app retries that song once with `format=mp3`. */
    fun unsupportedFormat() = PlaybackFailure.UnsupportedFormat()

    fun network() = PlaybackFailure.Network()
}
