package app.discair.ui

import app.discair.model.RadioPlay
import app.discair.model.RadioStation
import app.discair.ui.player.CoverStackPlayerRules
import app.discair.ui.player.IndexPlayerRules
import app.discair.ui.radio.IndexRadioRules
import java.time.Instant
import java.time.ZoneId
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** docs/plans/INDEX_THEME.md step I5: the words and numbers of Index's Now Playing, Queue, Lyrics and Radio pages. */
class IndexPlayerRadioRulesTest {
    private val zone = ZoneId.of("Europe/Paris")
    private val now = Instant.parse("2026-11-17T15:00:00Z") // Tuesday 17 Nov, 16:00 in Paris

    private fun at(iso: String): Double = Instant.parse(iso).epochSecond.toDouble()

    // ----- player

    @Test fun theBarSaysThePlaceInTheQueueOrTheViewName() {
        assertEquals("Now playing · 05 / 10", IndexPlayerRules.barTitle(CoverStackPlayerRules.VIEW_PLAYER, 4, 10))
        assertEquals("Now playing · 05 / 120", IndexPlayerRules.barTitle(CoverStackPlayerRules.VIEW_PLAYER, 4, 120))
        assertEquals("Now playing", IndexPlayerRules.barTitle(CoverStackPlayerRules.VIEW_PLAYER, -1, 10))
        assertEquals("Now playing", IndexPlayerRules.barTitle(CoverStackPlayerRules.VIEW_PLAYER, 0, 0))
        assertEquals("Queue · 14", IndexPlayerRules.barTitle(CoverStackPlayerRules.VIEW_QUEUE, 4, 14))
        assertEquals("Queue", IndexPlayerRules.barTitle(CoverStackPlayerRules.VIEW_QUEUE, -1, 0))
        assertEquals("Lyrics", IndexPlayerRules.barTitle(CoverStackPlayerRules.VIEW_LYRICS, 4, 14))
    }

    @Test fun upNextRowsContinueTheQueueNumbering() {
        assertEquals("06", IndexPlayerRules.number(5))
        assertEquals("10", IndexPlayerRules.number(9))
        assertEquals("120", IndexPlayerRules.number(119))
    }

    @Test fun thePlayingBandSaysNowOrPausedWithTheTimeOnlyWhenTheLengthIsKnown() {
        assertEquals("Now · 1:37 / 3:51", IndexPlayerRules.nowLine(true, 97_000, 231_000))
        assertEquals("Paused · 1:37 / 3:51", IndexPlayerRules.nowLine(false, 97_000, 231_000))
        assertEquals("Now", IndexPlayerRules.nowLine(true, 97_000, 0))
    }

    @Test fun aQueueRowNamesTheArtistAndTheLengthWhenKnown() {
        assertEquals("Khruangbin · 5:07", IndexPlayerRules.rowMeta("Khruangbin", 307))
        assertEquals("Khruangbin", IndexPlayerRules.rowMeta(" Khruangbin ", 0))
        assertEquals("4:39", IndexPlayerRules.rowMeta("", 279))
    }

    @Test fun theSeekLineShowsTheWholeLengthNotTheTimeLeft() {
        assertEquals("3:51", IndexPlayerRules.total(231_000))
        assertEquals("--:--", IndexPlayerRules.total(0))
    }

    @Test fun lyricStampsOnlyForTimedLines() {
        assertEquals("0:12", IndexPlayerRules.stamp(12_000))
        assertEquals("1:06", IndexPlayerRules.stamp(66_400))
        assertNull(IndexPlayerRules.stamp(null))
    }

    @Test fun theFourToolsAreSpokenInFull() {
        assertEquals(listOf("Lyrics", "Queue", "EQ", "Fade"), IndexPlayerRules.tools.map { it.first })
        assertEquals(listOf("Lyrics", "Queue", "Equalizer", "Crossfade"), IndexPlayerRules.tools.map { it.second })
    }

    // ----- radio

    private fun station(name: String, lastPlayedAt: Double? = null) = RadioStation("s-$name", name, true, "", null, "/logo", false, emptyList(), lastPlayedAt)
    private fun play(artist: String?, station: String = "FIP", heardAt: Double? = null) = RadioPlay(1, station, artist, "Movie", null, false, false, heardAt)

    @Test fun aStationWasLastHeardAtItsLatestPlayOrSong() {
        val songs = listOf(play("Tom Misch", "FIP", at("2026-11-17T07:00:00Z")), play("Nala", "KEXP", at("2026-11-17T12:00:00Z")))
        assertEquals(at("2026-11-17T07:00:00Z"), IndexRadioRules.lastHeardAt(station("FIP", at("2026-11-15T07:00:00Z")), songs))
        assertEquals(at("2026-11-17T09:00:00Z"), IndexRadioRules.lastHeardAt(station("FIP", at("2026-11-17T09:00:00Z")), songs))
        assertNull(IndexRadioRules.lastHeardAt(station("NTS 1"), songs))
    }

    @Test fun aStationRowSaysWhenItWasLastHeardUnlessItIsOnAir() {
        assertEquals("Last heard · Today", IndexRadioRules.stationMeta(false, "Today", "No live titles"))
        assertEquals("Tom Misch — Movie", IndexRadioRules.stationMeta(true, "Today", "Tom Misch — Movie"))
        assertEquals("No live titles", IndexRadioRules.stationMeta(false, "", "No live titles"))
    }

    @Test fun aHeardSongSaysWhenItWasHeard() {
        assertEquals("08:12", IndexRadioRules.heardWhen(at("2026-11-17T07:12:00Z"), now, zone))
        assertEquals("Yesterday 22:40", IndexRadioRules.heardWhen(at("2026-11-16T21:40:00Z"), now, zone))
        assertEquals("12 Nov 22:40", IndexRadioRules.heardWhen(at("2026-11-12T21:40:00Z"), now, zone))
        assertNull(IndexRadioRules.heardWhen(null, now, zone))
    }

    @Test fun aHeardRowLeavesOutAMissingArtist() {
        assertEquals("Massive Attack · FIP · 08:12", IndexRadioRules.heardMeta(play("Massive Attack"), "08:12"))
        assertEquals("FIP Groove · Yesterday 22:40", IndexRadioRules.heardMeta(play(null, "FIP Groove"), "Yesterday 22:40"))
        assertEquals("FIP", IndexRadioRules.heardMeta(play(" "), null))
    }

    @Test fun theLivePageSaysTheStationAndWhetherItIsPlaying() {
        assertEquals("FIP Groove · now", IndexRadioRules.airLine("FIP Groove", true))
        assertEquals("FIP Groove · paused", IndexRadioRules.airLine("FIP Groove ", false))
        assertEquals("now", IndexRadioRules.airLine("", true))
    }

    @Test fun rowsAreNumberedFromOne() {
        assertEquals("01", IndexRadioRules.number(0))
        assertEquals("12", IndexRadioRules.number(11))
        assertEquals(listOf("Stations", "Heard"), IndexRadioRules.tabs)
    }
}
