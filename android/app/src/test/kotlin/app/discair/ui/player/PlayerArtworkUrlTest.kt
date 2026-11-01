package app.discair.ui.player

import org.junit.Test
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull

class PlayerArtworkUrlTest {
    @Test fun requestsTheLargeSize() =
        assertEquals("https://h/api/owned/artwork/al-1?size=1000", playerArtworkUrl("https://h/api/owned/artwork/al-1"))

    @Test fun appendsToAnExistingQuery() =
        assertEquals("https://h/a?x=1&size=1000", playerArtworkUrl("https://h/a?x=1"))

    @Test fun keepsAnExplicitSize() =
        assertEquals("https://h/a?size=128", playerArtworkUrl("https://h/a?size=128"))

    @Test fun blankMeansNoArtwork() = assertNull(playerArtworkUrl(""))
}
