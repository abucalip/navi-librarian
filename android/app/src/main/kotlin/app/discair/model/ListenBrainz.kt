package app.discair.model

import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonPrimitive

/** `GET /api/settings/listenbrainz`: the saved public username and whether a token is stored. The token is never returned. */
data class ListenBrainzAccount(val username: String, val tokenConfigured: Boolean) {
    val connected: Boolean get() = username.isNotBlank()
}

/** `POST /api/settings/listenbrainz/test`: whether the server can read the saved profile, with its own sentence. */
data class ListenBrainzCheck(val ok: Boolean, val message: String)

fun parseListenBrainzAccount(body: String): ListenBrainzAccount {
    val o = ApiJson.parseToJsonElement(body) as? JsonObject ?: return ListenBrainzAccount("", false)
    return ListenBrainzAccount(
        o["username"]?.jsonPrimitive?.contentOrNull.orEmpty().trim(),
        o["token_configured"]?.jsonPrimitive?.booleanOrNull ?: false,
    )
}

fun parseListenBrainzCheck(body: String): ListenBrainzCheck {
    val o = ApiJson.parseToJsonElement(body) as? JsonObject
    return ListenBrainzCheck(
        o?.get("ok")?.jsonPrimitive?.booleanOrNull ?: false,
        o?.get("message")?.jsonPrimitive?.contentOrNull ?: "The server did not say whether it could read the profile.",
    )
}

/** The PUT body; the username is trimmed here, and a blank token is sent blank so the server keeps the saved one. */
fun listenBrainzBody(username: String, token: String): String =
    buildJsonObject {
        put("username", JsonPrimitive(username.trim()))
        put("token", JsonPrimitive(token.trim()))
    }.toString()
