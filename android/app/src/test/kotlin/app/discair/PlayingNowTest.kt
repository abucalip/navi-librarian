package app.discair

import app.discair.ui.player.PlayingNow
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** The album page marks only the version of a title that is playing. */
class PlayingNowTest {
    @Test fun twoVersionsOfOneTitleAreToldApartByTrack() {
        val now = PlayingNow("alb", "Impressions", true, track = 5, disc = 1)
        assertFalse(now.matches("alb", "Impressions", 2, 1))
        assertTrue(now.matches("alb", "impressions ", 5, 1))
    }

    @Test fun discsSeparateEqualTrackNumbers() {
        val now = PlayingNow("alb", "Naima", true, track = 3, disc = 2)
        assertFalse(now.matches("alb", "Naima", 3, 1))
        assertTrue(now.matches("alb", "Naima", 3, 2))
    }

    @Test fun unknownTrackOrDiscStillMatchesByTitleAndAlbum() {
        assertTrue(PlayingNow("alb", "Naima", false).matches("alb", "Naima", 3, 1))
        assertFalse(PlayingNow("alb", "Naima", false).matches("other", "Naima", 3, 1))
    }
}
