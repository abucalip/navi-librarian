package app.discair.model

import java.io.File
import kotlinx.serialization.json.decodeFromJsonElement
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class PlaylistInboxTest {
    private val fixture = ApiJson.parseToJsonElement(
        File("../../tests/fixtures/listenbrainz_inbox_responses.json").readText(),
    ).jsonObject

    @Test fun shelfDecodesAvailableAndEmptyStates() {
        val shelf = ApiJson.decodeFromJsonElement<PlaylistInbox>(fixture.getValue("list"))
        assertEquals(listOf(2L, 1L), shelf.items.map { it.id })
        assertEquals(listOf(0, 2), shelf.items.map { it.ownedCount })
        assertNull(shelf.items.first().generatedAt)
        assertEquals("2027-01-08T08:00:00+00:00", shelf.items.last().generatedAt)
        for (key in listOf("empty", "unconfigured")) {
            val empty = ApiJson.decodeFromJsonElement<PlaylistInbox>(fixture.getValue(key))
            assertEquals(key, empty.state)
            assertTrue(empty.items.isEmpty())
        }
    }

    @Test fun mixedEditionPreservesEveryPositionAndQueuesOwnedRepeatsInOrder() {
        val edition = ApiJson.decodeFromJsonElement<InboxEdition>(fixture.getValue("mixed_detail"))
        assertEquals((0..5).toList(), edition.tracks.map { it.position })
        assertEquals(listOf("owned", "owned"), edition.playbackItems().map { it.songId })
        val withAnotherOwnedSong = edition.copy(tracks = edition.tracks.map {
            if (it.position == 2) it.copy(matchState = "owned", songId = "another") else it
        })
        assertEquals(listOf("owned", "another", "owned"), withAnotherOwnedSong.playbackItems().map { it.songId })
    }

    @Test fun existingAcquisitionRepliesCarryTheirSyntheticJobKey() {
        val reply = ApiJson.decodeFromString<InboxDownload>(
            """{"ok":false,"status":"already_in_progress","artist":"Artist","album":"Album","job_album":"Album [Track]"}""",
        )
        assertTrue(inboxDownloadActive(reply.status))
        assertEquals(InboxAcquisitionKey("Artist", "Album [Track]"), reply.acquisitionKey)
        assertNull(reply.copy(status = "identity_conflict").acquisitionKey)
        assertTrue(inboxDownloadRetryable("no_matches"))
    }

    @Test fun importedTrackStillNeedsConfirmedOwnershipToPlay() {
        val edition = ApiJson.decodeFromJsonElement<InboxEdition>(fixture.getValue("mixed_detail"))
        val withImport = edition.copy(tracks = edition.tracks.map {
            if (it.position == 1) it.copy(acquisitionStatus = "imported") else it
        })
        assertEquals(listOf("owned", "owned"), withImport.playbackItems().map { it.songId })
        val withOwnership = withImport.copy(tracks = withImport.tracks.map {
            if (it.position == 1) it.copy(matchState = "owned", songId = "imported") else it
        })
        assertEquals(listOf("owned", "imported", "owned"), withOwnership.playbackItems().map { it.songId })
    }

    @Test fun zeroAndUnknownOwnershipGiveNoPlaybackItems() {
        val zero = ApiJson.decodeFromJsonElement<InboxEdition>(fixture.getValue("zero_owned_detail"))
        assertEquals(0, zero.ownedCount)
        assertTrue(zero.playbackItems().isEmpty())
        val unknown = zero.copy(ownedCount = null, tracks = zero.tracks.map {
            it.copy(matchState = null, songId = "owned")
        })
        assertTrue(unknown.playbackItems().isEmpty())
        val invalid = zero.copy(tracks = zero.tracks.map { it.copy(matchState = "owned", songId = "radio:invalid") })
        assertTrue(invalid.playbackItems().isEmpty())
    }
}
