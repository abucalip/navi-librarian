package app.discair.ui

import app.discair.model.RadioNow
import app.discair.model.RadioNowState
import app.discair.model.RadioPlay
import app.discair.ui.player.GalleryPlayerRules as P
import app.discair.ui.radio.GalleryRadioRules as R
import java.time.Instant
import java.time.ZoneId
import java.util.Locale
import org.junit.Assert.assertEquals
import org.junit.Test

/** Step G5 of docs/GALLERY_THEME.md: the words and choices behind Gallery's Now Playing, Queue, Lyrics and Radio pages. */
class GalleryPlayerRulesTest {
    private val utc = ZoneId.of("UTC")

    @Test fun theBarNamesTheAlbumOnThePlayerAndThePageOnTheOthers() {
        assertEquals("Playing from Laughing Stock", P.barTitle(0, "Laughing Stock"))
        assertEquals("Now playing", P.barTitle(0, "  "))
        assertEquals("Queue", P.barTitle(2, "Laughing Stock"))
        assertEquals("Lyrics", P.barTitle(1, "Laughing Stock"))
    }

    @Test fun theTimeLeftHasATrueMinusSign() {
        assertEquals("−6:27", P.remaining(192_000, 579_000))
        assertEquals("−0:00", P.remaining(600_000, 579_000))
        assertEquals("--:--", P.remaining(0, 0))
    }

    @Test fun theQueueListsOnlyTheSongsAfterTheOnePlaying() {
        assertEquals(listOf(1, 2, 3, 4, 5), P.upcoming(0, 6))
        assertEquals(listOf(3), P.upcoming(2, 4))
        assertEquals(emptyList<Int>(), P.upcoming(3, 4))
        assertEquals(emptyList<Int>(), P.upcoming(-1, 4))
        assertEquals(emptyList<Int>(), P.upcoming(0, 0))
    }

    @Test fun theNextHeadingCountsSongs() {
        assertEquals("Next · 5 songs", P.nextHeading(5))
        assertEquals("Next · 1 song", P.nextHeading(1))
        assertEquals("Next · 0 songs", P.nextHeading(0))
    }

    @Test fun thePlayingLineSaysWhereTheSongIs() {
        assertEquals("Talk Talk · playing, 3:12 of 9:39", P.playingLine("Talk Talk", true, 192_000, 579_000))
        assertEquals("Talk Talk · paused, 0:05 of 9:39", P.playingLine("Talk Talk", false, 5_000, 579_000))
        assertEquals("playing", P.playingLine(" ", true, 0, 0))
    }

    @Test fun aLyricLineLooksSungWaitingOrCurrent() {
        assertEquals(P.LineLook.Sung, P.lineLook(true, 0, 2))
        assertEquals(P.LineLook.Current, P.lineLook(true, 2, 2))
        assertEquals(P.LineLook.Waiting, P.lineLook(true, 3, 2))
        assertEquals(P.LineLook.Waiting, P.lineLook(true, 0, -1))
        assertEquals(P.LineLook.Plain, P.lineLook(false, 4, 2))
    }

    @Test fun theStationCountSaysOneInTheSingular() {
        assertEquals("6 stations", R.stationCount(6))
        assertEquals("1 station", R.stationCount(1))
        assertEquals("", R.stationCount(0))
    }

    @Test fun theLiveLineNamesTheStationAndWhetherItPlays() {
        assertEquals("On air · FIP", R.airLine(true, "FIP"))
        assertEquals("Paused · FIP", R.airLine(false, "FIP"))
        assertEquals("On air", R.airLine(true, " "))
    }

    @Test fun theArtistIsTheLineUnderAParsedSongElseTheFallback() {
        val ok = RadioNow(RadioNowState.Ok, "Talk Talk - Life's What You Make It", "Talk Talk", "Life's What You Make It", 7L, false, null)
        val idle = ok.copy(state = RadioNowState.Idle)
        assertEquals("Talk Talk", R.byLine(ok, "FIP"))
        assertEquals("FIP", R.byLine(idle, "FIP"))
        assertEquals("FIP", R.byLine(null, "FIP"))
        assertEquals("FIP", R.byLine(ok.copy(artist = " "), "FIP"))
    }

    @Test fun theHeardPageNamesWhenTheNewestSongWasHeard() {
        val now = Instant.parse("2026-11-16T21:30:00Z")
        fun at(iso: String) = listOf(play(Instant.parse(iso).epochSecond.toDouble()))
        assertEquals("Tonight", R.heardEyebrow(at("2026-11-16T21:09:00Z"), now, utc, Locale.ENGLISH))
        assertEquals("This morning", R.heardEyebrow(at("2026-11-16T08:00:00Z"), now, utc, Locale.ENGLISH))
        assertEquals("This afternoon", R.heardEyebrow(at("2026-11-16T14:00:00Z"), now, utc, Locale.ENGLISH))
        assertEquals("Yesterday", R.heardEyebrow(at("2026-11-15T23:00:00Z"), now, utc, Locale.ENGLISH))
        assertEquals("3 November", R.heardEyebrow(at("2026-11-03T10:00:00Z"), now, utc, Locale.ENGLISH))
        assertEquals("", R.heardEyebrow(listOf(play(null)), now, utc, Locale.ENGLISH))
        assertEquals("Tonight", R.heardEyebrow(at("2026-11-16T21:09:00Z") + play(1.0), now, utc, Locale.ENGLISH))
    }

    @Test fun aSongWithNoArtistIsSetUpright() {
        assertEquals(true, R.italicTitle(play(null, artist = "Talk Talk")))
        assertEquals(false, R.italicTitle(play(null, artist = null)))
        assertEquals(false, R.italicTitle(play(null, artist = " ")))
    }

    private fun play(heardAt: Double?, artist: String? = "Talk Talk") =
        RadioPlay(id = 1, stationName = "FIP", artist = artist, title = "Song", album = null, grabbed = false, inLibrary = false, heardAt = heardAt)
}
