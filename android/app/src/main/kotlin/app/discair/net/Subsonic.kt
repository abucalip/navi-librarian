package app.discair.net

import java.security.MessageDigest
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

/** Subsonic token authentication: token = md5(password + salt). The password is never sent. */
object Subsonic {
    const val API_VERSION = "1.16.1"
    const val CLIENT = "discair"

    fun token(password: String, salt: String): String =
        MessageDigest.getInstance("MD5").digest((password + salt).toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }

    /** Subsonic error 40 and 41 are bad credentials / token auth unsupported; 50 is not authorised. */
    private val authCodes = setOf(40, 41, 44, 50)

    /** Interprets a ping body. Returns null on success, otherwise the failure. */
    fun pingFailure(body: String, json: Json = Json { ignoreUnknownKeys = true }): ConnectionFailure? {
        val root = try {
            json.parseToJsonElement(body).jsonObject["subsonic-response"] as? JsonObject
        } catch (e: Exception) {
            null
        } ?: return ConnectionFailure.Server(200, "That address did not answer like Navidrome.")
        if (root["status"]?.jsonPrimitive?.contentOrNull == "ok") return null
        val error = root["error"] as? JsonObject
        val code = error?.get("code")?.jsonPrimitive?.intOrNull
        val message = error?.get("message")?.jsonPrimitive?.contentOrNull
        return if (code in authCodes) ConnectionFailure.Unauthorised(message)
        else ConnectionFailure.Server(200, message)
    }
}
