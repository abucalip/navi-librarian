package app.discair.player

import okhttp3.Interceptor
import okhttp3.Response

/**
 * Subsonic reports stream errors as a normal answer with a JSON or XML body. This interceptor reads
 * a small part of such a body, turns it into a [PlaybackFailure], closes the response and throws, so
 * the player never tries to decode an error as audio. Non-2xx answers are mapped from the status.
 * The thrown message never contains the request URL.
 */
class RefusedBodyInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val response = chain.proceed(chain.request())
        if (!response.isSuccessful && response.code != 416) {
            response.close()
            throw StreamRefusedException(PlaybackFailures.fromHttpStatus(response.code))
        }
        if (PlaybackFailures.isAudioContentType(response.header("Content-Type"))) return response
        val text = response.use { it.peekBody(MAX_ERROR_BODY).string() }
        throw StreamRefusedException(PlaybackFailures.fromErrorBody(text))
    }

    private companion object { const val MAX_ERROR_BODY = 4096L }
}
