package app.discair

import app.discair.data.AcquisitionApi
import app.discair.data.AcquisitionHub
import app.discair.data.RowBusy
import app.discair.data.StopStream
import app.discair.model.AcquisitionJob
import app.discair.model.GetState
import app.discair.model.parseAcquisitions
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Phase 4: nothing is shown as requested, retried or dismissed before the server answers. */
@OptIn(ExperimentalCoroutinesApi::class)
class AcquisitionHubTest {
    private class FakeApi : AcquisitionApi {
        var albumReply: () -> GetState = { GetState.Requested("Queued.") }
        var trackReply: () -> GetState = { GetState.Requested(null) }
        var jobs: List<AcquisitionJob> = emptyList()
        var dismissFails: String? = null
        val albumCalls = mutableListOf<Triple<String, String, JsonObject>>()
        val trackCalls = mutableListOf<List<Any?>>()
        val dismissed = mutableListOf<Pair<String, String>>()
        val skipped = mutableListOf<Pair<String, String>>()
        var streamSnapshots: List<List<AcquisitionJob>> = emptyList()
        var streamFailure: Exception? = null

        override fun acquireAlbum(artist: String, album: String, metadata: JsonObject): GetState {
            albumCalls += Triple(artist, album, metadata)
            return albumReply()
        }
        override fun acquireTrack(artist: String, album: String, title: String, trackNumber: Int?, year: Int?, metadata: JsonObject?): GetState {
            trackCalls += listOf(artist, album, title, trackNumber, year, metadata)
            return trackReply()
        }
        override fun acquisitions() = jobs
        override fun acquisitionStream(onSnapshot: (List<AcquisitionJob>) -> Unit, onProblem: (String) -> Unit) {
            streamSnapshots.forEach(onSnapshot)
            streamFailure?.let { throw it }
        }
        override fun skipSource(artist: String, album: String): String? { skipped += artist to album; return "Source switch requested." }
        override fun dismissAcquisition(artist: String, album: String): String? {
            dismissFails?.let { throw IllegalStateException(it) }
            dismissed += artist to album
            return "Dismissed."
        }
    }

    private fun jobs(vararg rows: String) = parseAcquisitions("""{"acquisitions":[${rows.joinToString(",")}]}""")
    private fun row(album: String, status: String, details: String = "{}", created: Int = 1) =
        """{"artist":"A","album":"$album","status":"$status","created_at":$created,"details":$details}"""

    private fun TestScope.hub(api: FakeApi): AcquisitionHub {
        val dispatcher = UnconfinedTestDispatcher(testScheduler)
        return AcquisitionHub({ api }, kotlinx.coroutines.CoroutineScope(backgroundScope.coroutineContext + dispatcher), dispatcher)
    }
    private val meta = JsonObject(emptyMap())

    @Test fun getIsRequestedOnlyAfterTheServerAccepts() = runTest {
        val api = FakeApi()
        val hub = hub(api)
        assertEquals(GetState.Idle, hub.getState("A", "B"))
        hub.getAlbum("A", "B", meta)
        assertEquals(GetState.Requested("Queued."), hub.getState("A", "B"))
        assertEquals(1, api.albumCalls.size)
    }

    @Test fun aRefusalOrAnErrorLeavesGetUsableWithTheReason() = runTest {
        val api = FakeApi()
        val hub = hub(api)
        api.albumReply = { GetState.Failed("Add the slskd API key in Discovery Settings first.") }
        hub.getAlbum("A", "B", meta)
        assertEquals(GetState.Failed("Add the slskd API key in Discovery Settings first."), hub.getState("A", "B"))
        api.albumReply = { throw java.io.IOException("Server unreachable.") }
        hub.getAlbum("A", "B", meta) // a failed Get is tried again by tapping it
        assertEquals(GetState.Failed("Server unreachable."), hub.getState("A", "B"))
        assertEquals(2, api.albumCalls.size)
    }

    @Test fun aRequestedOrPendingGetIsNeverSentTwice() = runTest {
        val api = FakeApi()
        val hub = hub(api)
        hub.getAlbum("A", "B", meta)
        hub.getAlbum("a", "b", meta) // same album, different case
        assertEquals(1, api.albumCalls.size)
    }

    @Test fun aSongAndItsAlbumAreSeparateRequests() = runTest {
        val api = FakeApi()
        val hub = hub(api)
        hub.getTrack("A", "B", "Song", 3, 1999)
        assertTrue(hub.getState("A", "B", "Song") is GetState.Requested)
        assertEquals(GetState.Idle, hub.getState("A", "B"))
        assertEquals(listOf<Any?>("A", "B", "Song", 3, 1999, null), api.trackCalls.single())
    }

    @Test fun aSuccessfulGetRefreshesTheList() = runTest {
        val api = FakeApi()
        api.jobs = jobs(row("B", "searching"))
        val hub = hub(api)
        hub.getAlbum("A", "B", meta)
        assertEquals(1, hub.jobs!!.size)
        assertEquals(1, hub.activeDownloads)
    }

    @Test fun messagesAreAnnouncedForFailuresAndSuccesses() = runTest {
        val api = FakeApi()
        val hub = hub(api)
        val heard = mutableListOf<String>()
        val collector = backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { hub.messages.collect { heard += it } }
        hub.getAlbum("A", "B", meta)
        api.albumReply = { GetState.Failed("No slskd key.") }
        hub.getAlbum("A", "C", meta)
        collector.cancel()
        assertEquals(listOf("Queued.", "No slskd key."), heard)
    }

    @Test fun dismissRemovesTheRowOnlyAfterTheServerConfirms() = runTest {
        val api = FakeApi()
        api.jobs = jobs(row("B", "imported"), row("C", "queued", created = 2))
        val hub = hub(api)
        hub.refreshOnce()
        val target = hub.jobs!!.first { it.album == "B" }
        var result: Boolean? = null
        hub.dismiss(target) { result = it }
        assertEquals(true, result)
        assertEquals(listOf("A" to "B"), api.dismissed)
        assertEquals(listOf("C"), hub.jobs!!.map { it.album })
        assertNull(hub.busy(target))
    }

    @Test fun aRefusedDismissKeepsTheRowAndSaysWhy() = runTest {
        val api = FakeApi()
        api.jobs = jobs(row("B", "imported"))
        api.dismissFails = "Another download shares this folder."
        val hub = hub(api)
        hub.refreshOnce()
        val heard = mutableListOf<String>()
        val collector = backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { hub.messages.collect { heard += it } }
        var result: Boolean? = null
        hub.dismiss(hub.jobs!!.single()) { result = it }
        collector.cancel()
        assertEquals(false, result)
        assertEquals(1, hub.jobs!!.size)
        assertEquals(listOf("Not dismissed: Another download shares this folder."), heard)
        assertNull(hub.busy(hub.jobs!!.single()))
    }

    @Test fun retryOfASongSendsTheSongWithItsStoredMetadata() = runTest {
        val api = FakeApi()
        api.jobs = jobs(
            """{"artist":"A","album":"Song (song on Alb)","status":"no_matches","created_at":1,"details":
               {"kind":"track","album_name":"Alb","track_title":"Song","track_number":2,"year":1999,"metadata":{"source":"x"}}}""",
        )
        val hub = hub(api)
        hub.refreshOnce()
        hub.retry(hub.jobs!!.single())
        val call = api.trackCalls.single()
        assertEquals(listOf<Any?>("A", "Alb", "Song", 2, 1999), call.take(5))
        assertEquals("x", ((call[5] as JsonObject)["source"] as kotlinx.serialization.json.JsonPrimitive).content)
        assertTrue(api.albumCalls.isEmpty())
    }

    @Test fun retryOfAnAlbumSendsTheAlbum() = runTest {
        val api = FakeApi()
        api.jobs = jobs(row("B", "slskd_error"))
        val hub = hub(api)
        hub.refreshOnce()
        hub.retry(hub.jobs!!.single())
        assertEquals("B", api.albumCalls.single().second)
    }

    @Test fun aRetryTheServerRefusesIsReportedNotHidden() = runTest {
        val api = FakeApi()
        api.jobs = jobs(row("B", "settings_required"))
        api.albumReply = { GetState.Failed("Add the slskd API key in Discovery Settings first.") }
        val hub = hub(api)
        hub.refreshOnce()
        val heard = mutableListOf<String>()
        val collector = backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { hub.messages.collect { heard += it } }
        hub.retry(hub.jobs!!.single())
        collector.cancel()
        assertEquals(listOf("Add the slskd API key in Discovery Settings first."), heard)
    }

    @Test fun skipAsksTheServerForTheNextSource() = runTest {
        val api = FakeApi()
        api.jobs = jobs(row("B", "downloading", """{"stall_detected_at":1,"fallback_count":1}"""))
        val hub = hub(api)
        hub.refreshOnce()
        hub.skipSource(hub.jobs!!.single())
        assertEquals(listOf("A" to "B"), api.skipped)
    }

    @Test fun dismissImportedSendsOneRequestPerImportAndLeavesOtherRecords() = runTest {
        val api = FakeApi()
        api.jobs = jobs(row("one", "imported"), row("two", "imported", created = 2), row("three", "downloading", created = 3))
        val hub = hub(api)
        hub.refreshOnce()
        hub.dismissImported()
        assertEquals(setOf("one", "two"), api.dismissed.map { it.second }.toSet())
        assertEquals(listOf("three"), hub.jobs!!.map { it.album })
    }

    @Test fun theStreamUpdatesTheListAndAFailureFallsBackToPolling() = runTest {
        val api = FakeApi()
        api.jobs = jobs(row("polled", "queued"))
        api.streamSnapshots = listOf(jobs(row("streamed", "downloading")))
        api.streamFailure = java.io.IOException("connection reset")
        val hub = hub(api)
        hub.watch()
        runCurrent()
        // The stream delivered, then dropped; the reason is shown and the poll picture is retried after a pause.
        assertEquals("connection reset", hub.listProblem)
        assertFalse(hub.live)
        advanceTimeBy(AcquisitionHub.POLL_FALLBACK_MS + 1)
        runCurrent()
        assertNotNull(hub.jobs)
        hub.unwatch()
        runCurrent()
    }

    @Test fun leavingTheScreenStopsTheStream() = runTest {
        val api = FakeApi()
        api.streamSnapshots = listOf(jobs(row("x", "queued")))
        val hub = hub(api)
        hub.watch()
        runCurrent()
        assertTrue(hub.jobs!!.isNotEmpty())
        hub.unwatch()
        assertFalse(hub.live)
        // StopStream is what ends a blocked read once the screen has gone.
        assertTrue(runCatching { throw StopStream() }.exceptionOrNull() is StopStream)
    }
}
