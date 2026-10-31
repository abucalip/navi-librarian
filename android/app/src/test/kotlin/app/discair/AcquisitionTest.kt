package app.discair

import app.discair.model.AcquisitionJob
import app.discair.model.GetState
import app.discair.model.Tone
import app.discair.model.activeCount
import app.discair.model.albumLaunchBody
import app.discair.model.formatBytes
import app.discair.model.formatSpeed
import app.discair.model.identityBody
import app.discair.model.launchOutcome
import app.discair.model.orderAcquisitions
import app.discair.model.parseAcquisitions
import app.discair.model.replyMessage
import app.discair.model.statusInfo
import app.discair.model.trackLaunchBody
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Phase 4: acquisition records, launch replies and request bodies against the recorded payloads. */
class AcquisitionTest {
    private fun fixture(name: String) = Json.parseToJsonElement(
        javaClass.classLoader!!.getResource("librarian/$name.json")!!.readText(),
    ).jsonObject

    private fun body(name: String) = fixture(name)["response"]!!.jsonObject["body"].toString()
    private fun requestBody(name: String) = fixture(name)["request"]!!.jsonObject["body"].toString()

    private fun job(status: String, created: Double = 0.0, details: String = "{}", artist: String = "A", album: String = "B") =
        parseAcquisitions(
            """{"acquisitions":[{"artist":"$artist","album":"$album","status":"$status","created_at":$created,"details":$details}]}""",
        ).single()

    @Test fun recordedSnapshotParsesAsASongRecord() {
        val jobs = parseAcquisitions(body("acquisitions"))
        val song = jobs.single()
        assertTrue(song.isSong)
        assertEquals("Contract Fixture Song", song.title)
        assertEquals("Contract Fixture Album", song.albumName)
        assertEquals("settings_required", song.status)
        assertEquals("Add the slskd API key in Discovery Settings first.", song.message)
        assertEquals(1, song.trackNumber)
        assertTrue(song.canRetry)
        assertTrue(song.updatedAt!! > 0)
    }

    @Test fun everyStreamEventDecodesLikeTheSnapshotRoute() {
        val events = fixture("acquisitions_stream")["response"]!!.jsonObject["body"]!!.jsonObject["sse_events"]!!
            .let { it as kotlinx.serialization.json.JsonArray }
        assertTrue(events.isNotEmpty())
        events.forEach { event ->
            val data = event.jsonObject["data"]!!.toString()
            assertEquals(1, parseAcquisitions(data).size)
        }
    }

    @Test fun anAlbumRecordIsNamedAfterTheAlbum() {
        val album = job("downloading", details = "{}", artist = "Artist", album = "Record")
        assertEquals("Record", album.title)
        assertEquals("Record", album.albumName)
        assertTrue(!album.isSong)
        assertEquals("Not reported", album.qualityProfile)
    }

    @Test fun statusWordsFollowTheWebTable() {
        assertEquals("Searching sources", statusInfo("searching").label)
        assertEquals(Tone.Ok, statusInfo("imported").tone)
        assertEquals(Tone.Error, statusInfo("no_matches").tone)
        assertEquals(Tone.Caution, statusInfo("queue_uncertain").tone)
        // Unknown statuses show their own name, never a blank.
        assertEquals("Some new state", statusInfo("some_new_state").label)
        assertEquals(Tone.Muted, statusInfo("some_new_state").tone)
    }

    @Test fun onlyTheWebRetryableStatusesOfferTryAgain() {
        listOf("no_matches", "queue_failed", "settings_required", "slskd_error").forEach { assertTrue(job(it).canRetry) }
        listOf("downloading", "imported", "download_failed", "dismissed").forEach { assertTrue(!job(it).canRetry) }
        assertTrue(!job("dismissed").canDismiss)
        assertTrue(job("imported").canDismiss)
    }

    @Test fun activeCountMatchesTheWebBadge() {
        val jobs = listOf("searching", "downloading", "imported", "no_matches", "monitoring").map { job(it, album = it) }
        assertEquals(3, activeCount(jobs))
    }

    @Test fun newestRequestFirstAndStableBetweenSnapshots() {
        val body = """{"acquisitions":[
            {"artist":"A","album":"old","status":"imported","created_at":10},
            {"artist":"A","album":"new","status":"downloading","created_at":30},
            {"artist":"A","album":"mid","status":"queued","created_at":20}]}"""
        assertEquals(listOf("new", "mid", "old"), orderAcquisitions(parseAcquisitions(body)).map { it.album })
    }

    @Test fun progressFiguresAreClampedAndOptional() {
        val j = job(
            "downloading",
            details = """{"live_progress":{"percent":140,"speed_bytes_per_second":2621440,"total_tracks":10,"remaining_tracks":4,
                "total_size_bytes":104857600,"remaining_size_bytes":52428800}}""",
        )
        val p = j.progress!!
        assertEquals(100.0, p.percent!!, 0.0)
        assertEquals("2.5 MB/s", formatSpeed(p.speedBytesPerSecond))
        assertEquals("100 MB", formatBytes(p.totalSizeBytes))
        assertEquals("50.0 MB", formatBytes(p.remainingSizeBytes))
        assertNull(job("downloading").progress)
        assertNull(job("imported", details = """{"live_progress":{"percent":50}}""").progress)
        assertEquals("Speed unavailable", formatSpeed(null))
        assertEquals("812 KB/s", formatSpeed(812.0 * 1024))
    }

    @Test fun nextSourceCountsDownFromTheStallAndOnlyWhenOffered() {
        val stalled = job("downloading", details = """{"stall_detected_at":1000,"fallback_count":2}""")
        assertEquals(15, stalled.skipSecondsLeft(1000.0))
        assertEquals(5, stalled.skipSecondsLeft(1010.0))
        assertEquals(0, stalled.skipSecondsLeft(1100.0))
        assertNull(job("downloading", details = """{"stall_detected_at":1000,"fallback_count":0}""").skipSecondsLeft(1000.0))
        assertNull(job("downloading").skipSecondsLeft(1000.0))
        assertNull(job("queued", details = """{"stall_detected_at":1000,"fallback_count":2}""").skipSecondsLeft(1000.0))
    }

    @Test fun launchRepliesWithOkFalseAreFailuresNotSuccesses() {
        for (name in listOf("acquire_album", "acquire_track")) {
            val outcome = launchOutcome(body(name))
            assertTrue("$name should be a failure", outcome is GetState.Failed)
            assertEquals("Add the slskd API key in Discovery Settings first.", (outcome as GetState.Failed).message)
        }
    }

    @Test fun anAcceptedLaunchIsRequestedAndANoMatchSearchIsNot() {
        assertEquals(GetState.Requested("Queued 12 files."), launchOutcome("""{"ok":true,"status":"queued","message":"Queued 12 files."}"""))
        assertEquals(GetState.Requested(null), launchOutcome("""{"status":"downloading"}"""))
        val none = launchOutcome("""{"ok":true,"status":"no_matches","message":"Nothing found."}""")
        assertEquals(GetState.Failed("Nothing found."), none)
        assertTrue(launchOutcome("not json") is GetState.Failed)
    }

    @Test fun requestBodiesMatchTheRecordedRequests() {
        val album = requestBody("acquire_album")
        val sent = Json.parseToJsonElement(album).jsonObject
        val rebuilt = Json.parseToJsonElement(
            albumLaunchBody(
                "Contract Fixture Artist", "Contract Fixture Album",
                sent["metadata"]!!.jsonObject,
            ),
        ).jsonObject
        assertEquals(sent, rebuilt)
        assertEquals("true", rebuilt["auto_queue"].toString()) // a JSON boolean, not a string (contract 5.3)

        val track = Json.parseToJsonElement(requestBody("acquire_track")).jsonObject
        val rebuiltTrack = Json.parseToJsonElement(
            trackLaunchBody(
                "Contract Fixture Artist", "Contract Fixture Album", "Contract Fixture Song", 1, null,
                track["metadata"]!!.jsonObject,
            ),
        ).jsonObject
        assertEquals(track, rebuiltTrack)

        val identity = Json.parseToJsonElement(requestBody("acquisitions_dismiss")).jsonObject
        assertEquals(identity, Json.parseToJsonElement(identityBody("Contract Fixture Artist", "Contract Fixture Album")).jsonObject)
    }

    @Test fun optionalTrackFieldsAreLeftOutRatherThanSentEmpty() {
        val sent = Json.parseToJsonElement(trackLaunchBody("A", "B", "T", null, null, null)).jsonObject
        assertEquals(setOf("artist", "album", "title"), sent.keys)
        assertEquals(setOf("artist", "album", "title", "track_number", "year"), Json.parseToJsonElement(trackLaunchBody("A", "B", "T", 3, 1999, null)).jsonObject.keys)
    }

    @Test fun dismissReplyMessageIsRead() {
        assertEquals(
            "Acquisition dismissed and its safely identified download files were removed.",
            replyMessage(body("acquisitions_dismiss")),
        )
        assertNull(replyMessage("<html>"))
    }

    @Test fun retryReusesTheStoredMetadata() {
        val j: AcquisitionJob = job("no_matches", details = """{"metadata":{"source":"x","year":1999}}""")
        assertEquals("x", (j.metadata["source"] as kotlinx.serialization.json.JsonPrimitive).content)
        assertTrue(job("no_matches").metadata is JsonObject)
    }
}
