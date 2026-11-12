package app.discair.data

import app.discair.model.ServerReads
import app.discair.model.ServiceCheck
import app.discair.model.ServiceId
import app.discair.model.parseCapabilities
import app.discair.model.parseConfigured
import app.discair.model.parseJobStatus
import app.discair.model.parseLastFmConfigured
import app.discair.model.parseServiceCheck
import app.discair.model.parseSlskdConfigured
import app.discair.net.ConnectionException
import app.discair.net.ConnectionFailure
import app.discair.net.LibrarianClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.runBlocking

/** The Librarian answered with a status (even an error) instead of not answering at all. */
internal fun answered(e: Throwable): Boolean = e is ConnectionException && when (e.failure) {
    ConnectionFailure.NoNetwork, ConnectionFailure.Unreachable, is ConnectionFailure.Certificate -> false
    else -> true
}

/** What `GET /api/health` says: whether the Librarian answered, and whether Navidrome does behind it (null when not said). */
internal data class HealthRead(val reachable: Boolean, val navidromeOk: Boolean?)

internal fun readHealth(get: () -> String): HealthRead = try {
    get(); HealthRead(true, true)
} catch (e: Exception) {
    when {
        // The route answers 503 exactly when Navidrome does not answer the Librarian.
        e is ConnectionException && (e.failure as? ConnectionFailure.Server)?.code == 503 -> HealthRead(true, false)
        else -> HealthRead(answered(e), null)
    }
}

/**
 * Reads the routes behind the Server screen (docs/redesign.md 8.2) with one request each, all at once. Reads only: a test route
 * is called for a service whose settings say it is set up, and nothing is saved. A route that fails leaves its field null.
 */
internal fun readServer(client: LibrarianClient, navidromeDirect: Boolean?, clock: () -> Long = System::currentTimeMillis): ServerReads =
    runBlocking(Dispatchers.IO) {
        fun <T> attempt(block: () -> T): T? = try { block() } catch (e: Exception) { null }

        val health = async { readHealth { client.get(listOf("api", "health")) } }
        val slskd = async { attempt { parseSlskdConfigured(client.get(listOf("api", "settings", "slskd"))) } }
        val lastFm = async { attempt { parseLastFmConfigured(client.get(listOf("api", "settings", "lastfm"))) } }
        val listenBrainz = async { attempt { parseConfigured(client.get(listOf("api", "settings", "listenbrainz")), "token_configured") } }
        val caps = async { attempt { parseCapabilities(client.get(listOf("api", "capabilities"))) } }
        val lenses = async { attempt { parseJobStatus(client.get(listOf("api", "insights", "refresh", "status"))) } }
        val popularity = async { attempt { parseJobStatus(client.get(listOf("api", "insights", "popularity", "status"))) } }
        val h = health.await()
        val configured = mapOf(ServiceId.Slskd to slskd.await(), ServiceId.LastFm to lastFm.await(), ServiceId.ListenBrainz to listenBrainz.await())

        // A test is asked only of a service that is set up, and only while the Librarian answers.
        val tests: Map<ServiceId, ServiceCheck> = if (!h.reachable) emptyMap() else configured.filterValues { it == true }.keys.map { id ->
            async {
                val path = when (id) { ServiceId.Slskd -> "slskd"; ServiceId.LastFm -> "lastfm"; else -> "listenbrainz" }
                attempt { parseServiceCheck(client.post(listOf("api", "settings", path, "test"), "{}")) }?.let { id to it }
            }
        }.awaitAll().filterNotNull().toMap()

        ServerReads(
            librarianReachable = h.reachable, navidromeViaLibrarian = h.navidromeOk, navidromeDirect = navidromeDirect,
            slskdConfigured = configured[ServiceId.Slskd], lastFmConfigured = configured[ServiceId.LastFm],
            listenBrainzConfigured = configured[ServiceId.ListenBrainz], tests = tests, capabilities = caps.await(),
            lenses = lenses.await(), popularity = popularity.await(), checkedAtMillis = clock(),
        )
    }
