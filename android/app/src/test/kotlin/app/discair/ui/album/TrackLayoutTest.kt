package app.discair.ui.album

import app.discair.model.ApiJson
import app.discair.model.Track
import kotlinx.serialization.builtins.ListSerializer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class TrackLayoutTest {
    private fun t(number: Int?, disc: Int?) = Track(number = number, title = "t", disc = disc)

    private val twoDiscs = listOf(t(1, 1), t(2, 1), t(1, 2), t(2, 2))

    @Test fun twoDiscsAreShownDiscByDisc() {
        assertTrue(showsDiscs(twoDiscs))
        assertEquals(listOf(true, false, true, false), twoDiscs.indices.map { startsDisc(twoDiscs, it) })
    }

    @Test fun oneDiscOrMissingDiscsStayOneList() {
        assertFalse(showsDiscs(listOf(t(1, 1), t(2, 1))))
        assertFalse(showsDiscs(listOf(t(1, null), t(2, null))))
        assertFalse(showsDiscs(listOf(t(1, 1), t(2, null), t(1, 2))))
        assertFalse(showsDiscs(emptyList()))
        assertFalse(startsDisc(listOf(t(1, null), t(2, null)), 0))
    }

    @Test fun aMissingNumberIsItsPlaceInTheDiscOrTheList() {
        val noNumbers = listOf(t(null, 1), t(null, 1), t(null, 2))
        assertEquals(listOf(1, 2, 1), noNumbers.indices.map { trackNumberShown(noNumbers, it) })
        val flat = listOf(t(null, null), t(null, null))
        assertEquals(listOf(1, 2), flat.indices.map { trackNumberShown(flat, it) })
        assertEquals(2, trackNumberShown(twoDiscs, 3))
    }

    @Test fun serverTracksDecodeDiscAndQualityAndOlderAnswersStillDecode() {
        val json = """[{"track_number":1,"title":"A","duration_seconds":100,"owned":true,"disc_number":2,"quality":"FLAC 16/44"},
                       {"track_number":2,"title":"B","duration_seconds":100,"owned":false}]"""
        val tracks = ApiJson.decodeFromString(ListSerializer(Track.serializer()), json)
        assertEquals(2, tracks[0].disc)
        assertEquals("FLAC 16/44", tracks[0].quality)
        assertNull(tracks[1].disc)
        assertNull(tracks[1].quality)
    }
}
