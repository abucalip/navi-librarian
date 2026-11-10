package app.discair.ui.radio

import app.discair.model.RadioNow
import app.discair.model.RadioNowState
import app.discair.model.RadioStation
import org.junit.Assert.assertTrue
import org.junit.Test

class RadioScreenTest {
    private fun station(proxied: Boolean) = RadioStation("1", "FM", proxied, "http://x", null, "/api/radio/stations/1/logo", false, emptyList(), null)

    @Test fun aStationThatIsNotRelayedSaysWhyThereIsNoTitle() {
        assertTrue(stripText(station(false), null).contains("relay"))
    }

    @Test fun aRelayedStationWithNoLiveAnswerInvitesTuningIn() {
        assertTrue(stripText(station(true), null).contains("Tune in"))
    }

    @Test fun aLiveSongIsShownAsArtistAndTitle() {
        val now = RadioNow(RadioNowState.Ok, "A - B", "A", "B", null, false, null)
        assertTrue(stripText(station(true), now) == "A - B")
    }
}
