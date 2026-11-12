package app.discair.model

import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull

/*
 * What the Server screen reads (docs/redesign.md 8.2, step A7): the settings and test routes of the connected services, the
 * capabilities body and the two job-status routes. Parsing is forgiving: a missing field is "not known", never a default that
 * reads as working. No route here returns a secret.
 */

/** The answer of any `POST /api/settings/{service}/test`: 200 even when the service does not answer, so failure is [ok] false. */
data class ServiceCheck(val ok: Boolean, val status: String, val message: String)

/** `GET /api/capabilities`, only what the screen reads. [graphCoverage] is none, partial or broad. */
data class ServerCapabilities(
    val graphCoverage: String,
    val sonicAvailable: Boolean,
    val listenBrainzConnected: Boolean,
    val contractVersion: Int?,
    val generation: Int?,
)

/** One run of a background job. [state] is queued, running, succeeded, failed or skipped; [finishedAt] is Unix seconds. */
data class JobRun(val state: String, val finishedAt: Double?, val error: String?, val progress: Map<String, Double>)

/** A job route's answer: the newest run, the newest good run, whether one runs now, and seconds until the next (0 = now). */
data class JobStatus(val status: JobRun?, val lastGood: JobRun?, val running: Boolean, val retryAfter: Double?)

private fun JsonObject.str(name: String) = (this[name] as? JsonPrimitive)?.takeIf { it.isString }?.content
private fun JsonObject.bool(name: String) = (this[name] as? JsonPrimitive)?.booleanOrNull
private fun JsonObject.num(name: String) = (this[name] as? JsonPrimitive)?.doubleOrNull
private fun JsonObject.obj(name: String) = this[name] as? JsonObject

private fun root(body: String): JsonObject? = runCatching { ApiJson.parseToJsonElement(body) }.getOrNull() as? JsonObject

/** A settings body reduced to "is a secret or address stored", under the key each route uses; null when the body cannot be read. */
fun parseConfigured(body: String, key: String): Boolean? = root(body)?.bool(key)

/** The slskd route stores an address and a key: configured means both. */
fun parseSlskdConfigured(body: String): Boolean? {
    val o = root(body) ?: return null
    val key = o.bool("api_key_configured") ?: return null
    return key && !o.str("slskd_url").isNullOrBlank()
}

/** Last.fm is set up once an API key is stored. */
fun parseLastFmConfigured(body: String): Boolean? = parseConfigured(body, "api_key_configured")

/**
 * A test answer. Without a `status` the answer is read from `ok` and the words, as the Mac does: a refused credential is
 * authentication_failed, anything else that failed is connection_failed.
 */
fun parseServiceCheck(body: String): ServiceCheck {
    val o = root(body) ?: return ServiceCheck(false, "connection_failed", "")
    val ok = o.bool("ok") ?: false
    val text = o.str("message") ?: o.str("error") ?: ""
    val status = o.str("status") ?: when {
        ok -> "connected"
        text.contains("rejected", ignoreCase = true) -> "authentication_failed"
        text.contains("add a", ignoreCase = true) -> "not_configured"
        else -> "connection_failed"
    }
    return ServiceCheck(ok, status, text)
}

fun parseCapabilities(body: String): ServerCapabilities? {
    val o = root(body) ?: return null
    val coverage = o.str("graph_coverage")?.takeIf { it in listOf("none", "partial", "broad") } ?: "none"
    return ServerCapabilities(
        coverage, o.bool("sonic_available") ?: false, o.bool("listenbrainz_connected") ?: false,
        (o["contract_version"] as? JsonPrimitive)?.intOrNull, (o["generation"] as? JsonPrimitive)?.intOrNull,
    )
}

private fun parseRun(o: JsonObject?): JobRun? {
    o ?: return null
    return JobRun(
        o.str("state") ?: "failed", o.num("finished_at"), o.str("error"),
        o.obj("progress").orEmpty().mapNotNull { (k, v) -> (v as? JsonPrimitive)?.doubleOrNull?.let { k to it } }.toMap(),
    )
}

fun parseJobStatus(body: String): JobStatus? {
    val o = root(body) ?: return null
    return JobStatus(parseRun(o.obj("status")), parseRun(o.obj("last_good")), o.bool("running") ?: false, o.num("retry_after"))
}

enum class ServiceId { Librarian, Navidrome, Slskd, LastFm, ListenBrainz, MusicBrainz }

/** Everything one pass over the server's routes found. A null is "could not be read", never "off". */
data class ServerReads(
    /** True when the Librarian answered at all (even with an error status). */
    val librarianReachable: Boolean,
    /** `GET /api/health`: Navidrome as the Librarian sees it. Null when not read. */
    val navidromeViaLibrarian: Boolean?,
    /** The phone's own check of Navidrome; used when the Librarian does not answer. Null before the first check. */
    val navidromeDirect: Boolean?,
    val slskdConfigured: Boolean?,
    val lastFmConfigured: Boolean?,
    val listenBrainzConfigured: Boolean?,
    val tests: Map<ServiceId, ServiceCheck>,
    val capabilities: ServerCapabilities?,
    val lenses: JobStatus?,
    val popularity: JobStatus?,
    val checkedAtMillis: Long,
)

