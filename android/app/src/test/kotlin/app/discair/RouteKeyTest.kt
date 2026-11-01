package app.discair

import app.discair.ui.common.routeKey
import app.discair.ui.common.routePart
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class RouteKeyTest {
    @Test fun aSlashInAnAlbumNameDoesNotAddASegment() {
        val key = routeKey("Tony Allen", "Jealousy/Progress")
        assertEquals("tony allen/jealousy progress", key)
        assertEquals(2, key.split("/").size)
    }

    @Test fun aSlashInAnArtistNameDoesNotMoveTheSplit() {
        val key = routeKey("AC/DC", "Back in Black")
        assertEquals("ac dc/back in black", key)
        val (artist, album) = key.split("/", limit = 2)
        assertEquals("ac dc", artist); assertEquals("back in black", album)
    }

    @Test fun otherNamesAreUnchangedAndTrimmed() {
        assertEquals("the beatles/1", routeKey("  The Beatles ", "1"))
        assertEquals("tony allen", routePart("Tony Allen"))
        assertFalse(routePart("A/B/C").contains('/'))
    }
}
