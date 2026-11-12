package app.discair

import app.discair.model.JobRun
import app.discair.model.JobStatus
import app.discair.model.ServerReads
import app.discair.model.ServiceCheck
import app.discair.model.ServiceId
import app.discair.model.parseCapabilities
import app.discair.model.parseJobStatus
import app.discair.model.parseServiceCheck
import app.discair.model.parseSlskdConfigured
import app.discair.data.HealthRead
import app.discair.data.answered
import app.discair.data.readHealth
import app.discair.net.ConnectionException
import app.discair.net.ConnectionFailure
import app.discair.ui.settings.ServerRules
import app.discair.ui.settings.ServerTone
import app.discair.ui.settings.StatusWord
import app.discair.ui.settings.SummaryKind
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** The Server screen (A7): decoders for the routes it reads, and the state table. Librarian down is Unknown, never failed. */
class ServerModelTest {
    private val nowMs = 1_800_000_000_000L
    private val nowSec = nowMs / 1000.0
    private fun body(name: String) = Json.parseToJsonElement(javaClass.classLoader!!.getResource("$name.json")!!.readText()).jsonObject["response"].toString()
    private val ok = ServiceCheck(true, "connected", "")

    private fun reads(
        up: Boolean = true, health: Boolean? = true, direct: Boolean? = null,
        slskd: Boolean? = true, lastfm: Boolean? = true, lb: Boolean? = true,
        tests: Map<ServiceId, ServiceCheck> = mapOf(ServiceId.Slskd to ok, ServiceId.LastFm to ok, ServiceId.ListenBrainz to ok),
        caps: String? = "broad", lenses: JobStatus? = null, popularity: JobStatus? = null,
    ) = ServerReads(
        up, health, direct, slskd, lastfm, lb, tests,
        caps?.let { app.discair.model.ServerCapabilities(it, false, true, 1, 3) }, lenses, popularity, nowMs,
    )

    private fun status(rows: List<app.discair.ui.settings.ServiceRow>, id: ServiceId) = rows.first { it.id == id }.status

    // ----- decoders -----------------------------------------------------------------------------------------------

    @Test fun `capabilities decode from the servers fixtures`() {
        val populated = parseCapabilities(body("capabilities_populated"))!!
        assertEquals(1, populated.contractVersion)
        assertEquals("none", parseCapabilities(body("capabilities_empty"))!!.graphCoverage)
        assertEquals("broad", parseCapabilities("""{"graph_coverage":"broad","sonic_available":true}""")!!.graphCoverage)
        assertEquals("none", parseCapabilities("""{"graph_coverage":"wide"}""")!!.graphCoverage)
        assertNull(parseCapabilities("not json"))
    }

    @Test fun `a test answer without a status is read from ok and its words`() {
        assertEquals("connected", parseServiceCheck("""{"ok":true,"status":"connected","message":"Connected"}""").status)
        assertEquals("authentication_failed", parseServiceCheck("""{"ok":false,"error":"Token rejected"}""").status)
        assertEquals("not_configured", parseServiceCheck("""{"ok":false,"error":"Add a token first"}""").status)
        assertEquals("connection_failed", parseServiceCheck("""{"ok":false,"message":"timed out"}""").status)
        assertEquals("connection_failed", parseServiceCheck("nonsense").status)
    }

    @Test fun `slskd is configured only with both an address and a key`() {
        assertEquals(true, parseSlskdConfigured("""{"slskd_url":"http://x","api_key_configured":true}"""))
        assertEquals(false, parseSlskdConfigured("""{"slskd_url":"","api_key_configured":true}"""))
        assertEquals(false, parseSlskdConfigured("""{"slskd_url":"http://x","api_key_configured":false}"""))
        assertNull(parseSlskdConfigured("""{"slskd_url":"http://x"}"""))
    }

    @Test fun `a job status decodes the newest run, the last good run and the wait`() {
        val j = parseJobStatus(
            """{"status":{"state":"failed","finished_at":1.5,"error":"boom","progress":{}},"last_good":{"state":"succeeded","finished_at":1700000000.0,"progress":{"pending":340}},"running":false,"retry_after":14400.0}""",
        )!!
        assertEquals("failed", j.status!!.state)
        assertEquals("boom", j.status.error)
        assertEquals(340.0, j.lastGood!!.progress["pending"]!!, 0.0)
        assertEquals(14400.0, j.retryAfter!!, 0.0)
        assertNull(parseJobStatus("""{"status":null,"last_good":null,"running":false}""")!!.status)
    }

    // ----- reachability ---------------------------------------------------------------------------------------------

    @Test fun `a status answer means the Librarian is there, a network failure means it is not`() {
        assertTrue(answered(ConnectionException(ConnectionFailure.Server(503))))
        assertTrue(answered(ConnectionException(ConnectionFailure.Unauthorised())))
        assertFalse(answered(ConnectionException(ConnectionFailure.Unreachable)))
        assertFalse(answered(ConnectionException(ConnectionFailure.NoNetwork)))
        assertFalse(answered(java.io.IOException("reset")))
    }

    @Test fun `health 503 is the Librarian up with Navidrome not answering`() {
        assertEquals(HealthRead(true, true), readHealth { "{}" })
        assertEquals(HealthRead(true, false), readHealth { throw ConnectionException(ConnectionFailure.Server(503)) })
        assertEquals(HealthRead(true, null), readHealth { throw ConnectionException(ConnectionFailure.Server(500)) })
        assertEquals(HealthRead(false, null), readHealth { throw ConnectionException(ConnectionFailure.Unreachable) })
    }

    // ----- state table ---------------------------------------------------------------------------------------------

    @Test fun `everything working gives the all working summary`() {
        val v = ServerRules.build(reads(), "21:14")
        assertEquals(SummaryKind.Working, v.summary.kind)
        assertEquals("Everything is working", v.summary.title)
        assertEquals("Checked at 21:14.", v.summary.detail)
        assertEquals(listOf("Connected", "Connected", "Connected", "Connected", "Connected", "Loaded · broad"), v.services.map { it.status.word })
        assertTrue(v.attention.isEmpty())
    }

    @Test fun `Librarian down makes everything it reports Unknown, not failed, and keeps Navidrome's own state`() {
        val v = ServerRules.build(reads(up = false, health = null, direct = true, tests = emptyMap(), caps = null), "21:14")
        assertEquals(SummaryKind.Unreachable, v.summary.kind)
        assertEquals("Can't reach Librarian", v.summary.title)
        assertEquals(StatusWord.NoAnswer, status(v.services, ServiceId.Librarian))
        assertEquals(StatusWord.Connected, status(v.services, ServiceId.Navidrome))
        listOf(ServiceId.Slskd, ServiceId.LastFm, ServiceId.ListenBrainz, ServiceId.MusicBrainz).forEach {
            assertEquals(StatusWord.Unknown, status(v.services, it))
            assertFalse(v.services.first { r -> r.id == it }.status.failing)
        }
        assertTrue("jobs are not shown as failed while the Librarian is down", v.activity.isEmpty())
    }

    @Test fun `Navidrome before any check is Unknown and a failed health is No answer`() {
        assertEquals(StatusWord.Unknown, status(ServerRules.serviceRows(reads(up = false, health = null, direct = null)), ServiceId.Navidrome))
        assertEquals(StatusWord.NoAnswer, status(ServerRules.serviceRows(reads(health = false)), ServiceId.Navidrome))
        assertEquals(StatusWord.NoAnswer, status(ServerRules.serviceRows(reads(up = false, health = null, direct = false)), ServiceId.Navidrome))
    }

    @Test fun `a configured service that was not tested is Unknown, an unset one is Not set up`() {
        val rows = ServerRules.serviceRows(reads(tests = emptyMap(), lastfm = false))
        assertEquals(StatusWord.Unknown, status(rows, ServiceId.Slskd))
        assertEquals(StatusWord.NotSetUp, status(rows, ServiceId.LastFm))
    }

    @Test fun `a refused credential names the credential`() {
        val rows = ServerRules.serviceRows(
            reads(tests = mapOf(
                ServiceId.Slskd to ServiceCheck(false, "authentication_failed", ""),
                ServiceId.LastFm to ServiceCheck(false, "connection_failed", ""),
                ServiceId.ListenBrainz to ServiceCheck(false, "not_found", ""),
            )),
        )
        assertEquals("Key rejected", status(rows, ServiceId.Slskd).word)
        assertEquals("No answer", status(rows, ServiceId.LastFm).word)
        assertEquals("Username rejected", status(rows, ServiceId.ListenBrainz).word)
        assertTrue(rows.all { it.status.tone != ServerTone.Success || it.id !in listOf(ServiceId.Slskd, ServiceId.LastFm, ServiceId.ListenBrainz) })
    }

    @Test fun `ListenBrainz falls back to the capabilities flag when its settings were not read`() {
        val rows = ServerRules.serviceRows(reads(lb = null, tests = mapOf(ServiceId.ListenBrainz to ok)))
        assertEquals(StatusWord.Connected, status(rows, ServiceId.ListenBrainz))
        val none = ServerRules.serviceRows(reads(lb = null, tests = emptyMap(), caps = null))
        assertEquals(StatusWord.Unknown, status(none, ServiceId.ListenBrainz))
    }

    @Test fun `MusicBrainz data is Not loaded with no coverage and Unknown when capabilities were not read`() {
        assertEquals(StatusWord.NotLoaded, status(ServerRules.serviceRows(reads(caps = "none")), ServiceId.MusicBrainz))
        assertEquals(StatusWord.Unknown, status(ServerRules.serviceRows(reads(caps = null)), ServiceId.MusicBrainz))
    }

    @Test fun `one failing service is one that needs attention`() {
        val v = ServerRules.build(reads(tests = mapOf(ServiceId.Slskd to ServiceCheck(false, "connection_failed", ""), ServiceId.LastFm to ok, ServiceId.ListenBrainz to ok)), "9:05")
        assertEquals(SummaryKind.Attention, v.summary.kind)
        assertEquals("One service needs attention", v.summary.title)
        assertEquals("slskd: No answer. Checked at 9:05.", v.summary.detail)
        val two = ServerRules.build(reads(health = false, slskd = false), "9:05")
        assertEquals("2 services need attention", two.summary.title)
    }

    // ----- activity -------------------------------------------------------------------------------------------------

    private fun run(state: String = "succeeded", finished: Double? = nowSec - 7200, pending: Double? = null, error: String? = null) =
        JobRun(state, finished, error, if (pending != null) mapOf("pending" to pending) else emptyMap())

    @Test fun `insight lenses say when they refreshed and when they are next due`() {
        val row = ServerRules.lensRow(JobStatus(run(), run(), false, 14_400.0), nowMs)
        assertEquals("Done", row.status.word)
        assertEquals("Refreshed 2 hours ago · next in 4 hours", row.line)
        assertEquals("Refreshed 2 hours ago · next due now", ServerRules.lensRow(JobStatus(run(), run(), false, 0.0), nowMs).line)
        assertEquals("Not loaded", ServerRules.lensRow(null, nowMs).status.word)
        assertEquals("Not loaded", ServerRules.lensRow(JobStatus(null, null, false, 0.0), nowMs).status.word)
    }

    @Test fun `a failed lens refresh says so and keeps the earlier time`() {
        val row = ServerRules.lensRow(JobStatus(run("failed", error = "x"), run(), false, 100.0), nowMs)
        assertEquals("Not updating", row.status.word)
        assertTrue(row.line.startsWith("The last refresh failed. Refreshed 2 hours ago"))
        assertTrue(ServerRules.lensRow(JobStatus(run("running", null), run(), true, 100.0), nowMs).line.startsWith("Refreshing now"))
    }

    @Test fun `artist popularity says how many artists are left and that it runs only on request`() {
        val paused = ServerRules.popularityRow(JobStatus(run("queued", pending = 340.0), run(), false, null), nowMs)
        assertEquals("Paused", paused.status.word)
        assertEquals("340 artists left · runs only when you ask", paused.line)
        assertEquals("Paused", ServerRules.popularityRow(JobStatus(null, null, false, null), nowMs).status.word)
        assertEquals("Done", ServerRules.popularityRow(JobStatus(run(pending = 0.0), run(pending = 0.0), false, null), nowMs).status.word)
        assertEquals("Not updating", ServerRules.popularityRow(JobStatus(run("failed", error = "limit"), run(), false, null), nowMs).status.word)
        assertEquals("Not loaded", ServerRules.popularityRow(null, nowMs).status.word)
    }

    @Test fun `times are relative under a day and a date beyond it`() {
        assertEquals("just now", ServerRules.ago(nowMs, nowSec - 30))
        assertEquals("35 minutes ago", ServerRules.ago(nowMs, nowSec - 35 * 60))
        assertTrue(ServerRules.ago(nowMs, nowSec - 3 * 86_400).startsWith("on "))
        assertEquals("1 minute", ServerRules.duration(40.0))
        assertEquals("2 hours", ServerRules.duration(7200.0))
    }
}
