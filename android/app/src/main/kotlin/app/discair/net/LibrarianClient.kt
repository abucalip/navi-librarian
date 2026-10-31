package app.discair.net

import java.util.concurrent.TimeUnit
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import okhttp3.CookieJar
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Response

private val JSON = "application/json".toMediaType()
private val lenient = Json { ignoreUnknownKeys = true }

fun httpClient(cookies: CookieJar = CookieJar.NO_COOKIES): OkHttpClient = OkHttpClient.Builder()
    .cookieJar(cookies)
    .connectTimeout(10, TimeUnit.SECONDS)
    .readTimeout(30, TimeUnit.SECONDS)
    .build()

/** Pulls the server's `detail` text out of an error body, if there is one. */
fun errorDetail(body: String): String? = try {
    lenient.parseToJsonElement(body).jsonObject["detail"]?.jsonPrimitive?.contentOrNull
} catch (e: Exception) {
    null
}

/** Librarian account state as reported by `GET /api/auth/status`. */
fun parseSetupRequired(body: String): Boolean? = try {
    lenient.parseToJsonElement(body).jsonObject["setup_required"]?.jsonPrimitive?.content?.toBooleanStrictOrNull()
} catch (e: Exception) {
    null
}

/**
 * Librarian sign-in (contract section 4.1). A 401 on any call triggers one re-login with the
 * stored credentials; a 429 is reported and never retried automatically.
 */
class LibrarianClient(
    private val http: OkHttpClient,
    private val baseUrl: String,
    private val username: String,
    private val password: String,
) {
    /** Signs in and confirms the session by calling the health route. Throws [ConnectionException]. */
    fun signIn() {
        val status = send(Request.Builder().url("$baseUrl/api/auth/status").get().build())
        if (parseSetupRequired(status) == true) {
            throw ConnectionException(
                ConnectionFailure.Server(409, "Create the Librarian account in the web UI first."),
            )
        }
        login()
        send(Request.Builder().url("$baseUrl/api/health").get().build())
    }

    /** Runs a GET with the one-time re-login on 401. */
    fun get(path: String): String {
        val request = Request.Builder().url("$baseUrl$path").get().build()
        return try {
            send(request)
        } catch (e: ConnectionException) {
            if (e.failure !is ConnectionFailure.Unauthorised) throw e
            login()
            send(request)
        }
    }

    fun signOut() {
        try {
            send(Request.Builder().url("$baseUrl/api/auth/logout").post("{}".toRequestBody(JSON)).build())
        } catch (e: Exception) {
            // The local session is discarded regardless; the server cookie expires on its own.
        }
    }

    private fun login() {
        val body = buildJsonObject {
            put("username", username)
            put("password", password)
        }.toString().toRequestBody(JSON)
        send(Request.Builder().url("$baseUrl/api/auth/login").post(body).build())
    }

    private fun send(request: Request): String {
        http.newCall(request).execute().use { response: Response ->
            val text = response.body?.string().orEmpty()
            val failure = classifyStatus(response.code, errorDetail(text))
            if (failure != null) throw ConnectionException(failure)
            return text
        }
    }
}

/** Navidrome reachability and credential check through the Subsonic `ping` call. */
class NavidromeClient(
    private val http: OkHttpClient,
    private val baseUrl: String,
    private val username: String,
    private val password: String,
    private val newSalt: () -> String = { java.util.UUID.randomUUID().toString().replace("-", "").take(12) },
) {
    fun ping() {
        val salt = newSalt()
        val parsed = baseUrl.toHttpUrlOrNull()
            ?: throw ConnectionException(ConnectionFailure.Server(0, "Invalid Navidrome address."))
        val target = parsed.newBuilder()
            .addPathSegments("rest/ping")
            .addQueryParameter("u", username)
            .addQueryParameter("t", Subsonic.token(password, salt))
            .addQueryParameter("s", salt)
            .addQueryParameter("v", Subsonic.API_VERSION)
            .addQueryParameter("c", Subsonic.CLIENT)
            .addQueryParameter("f", "json")
            .build()
        http.newCall(Request.Builder().url(target).get().build()).execute().use { response ->
            val text = response.body?.string().orEmpty()
            if (response.code == 401 || response.code == 403) {
                throw ConnectionException(ConnectionFailure.Unauthorised())
            }
            if (!response.isSuccessful) throw ConnectionException(ConnectionFailure.Server(response.code))
            Subsonic.pingFailure(text)?.let { throw ConnectionException(it) }
        }
    }
}
