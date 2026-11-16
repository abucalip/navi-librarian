package app.discair.ui

import app.discair.model.RadioPlay
import app.discair.model.RadioStation
import app.discair.ui.home.FlowHomeRules.Tab
import app.discair.ui.home.GalleryHomeRules
import app.discair.ui.home.GalleryHomeRules.Trailing
import app.discair.ui.home.HeroFigures
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Instant
import java.time.ZoneId
import java.time.ZonedDateTime

/** Step G2 of docs/GALLERY_THEME.md: the pure rules behind Gallery's Home. */
class GalleryHomeRulesTest {
    private val zone = ZoneId.of("UTC")
    private val now = ZonedDateTime.of(2026, 11, 16, 21, 14, 0, 0, zone).toInstant()

    private fun at(y: Int, m: Int, d: Int, h: Int = 8, min: Int = 42) = ZonedDateTime.of(y, m, d, h, min, 0, 0, zone).toEpochSecond().toDouble()

    private fun play(id: Long, station: String = "FIP", artist: String? = "Cocteau Twins", heard: Double? = at(2026, 11, 16), grabbed: Boolean = false, inLibrary: Boolean = false) =
        RadioPlay(id, station, artist, "Song $id", null, grabbed, inLibrary, heard)

    private fun station(name: String) = RadioStation(name, name, true, "", null, "", false, emptyList(), null)

    @Test fun thePagerLabelHasAtLeastTwoDigits() {
        assertEquals("01 / 12", GalleryHomeRules.pagerLabel(0, 12))
        assertEquals("12 / 12", GalleryHomeRules.pagerLabel(11, 12))
        assertEquals("05 / 120", GalleryHomeRules.pagerLabel(4, 120))
    }

    @Test fun eachSourceHasItsCatalogueLine() {
        assertEquals("Pick for tonight", GalleryHomeRules.eyebrow(Tab.Picks))
        assertEquals("New in your library", GalleryHomeRules.eyebrow(Tab.New))
        assertEquals("Recently played", GalleryHomeRules.eyebrow(Tab.Played))
    }

    @Test fun thePlacardLinesKeepOnlyWhatIsKnown() {
        assertEquals("Bark Psychosis, 1994", GalleryHomeRules.by("Bark Psychosis", 1994))
        assertEquals("Bark Psychosis", GalleryHomeRules.by("Bark Psychosis", null))
        assertEquals("Post-rock · not in your library", GalleryHomeRules.status(Tab.Picks, "Post-rock", false))
        assertEquals("in your library", GalleryHomeRules.status(Tab.New, null, true))
    }

    @Test fun lastHeardIsWordsThenWeekdayThenDate() {
        assertEquals("Today", GalleryHomeRules.lastHeard(at(2026, 11, 16, 1, 0), now, zone))
        assertEquals("Yesterday", GalleryHomeRules.lastHeard(at(2026, 11, 15, 23, 0), now, zone))
        assertEquals(java.time.DayOfWeek.FRIDAY.getDisplayName(java.time.format.TextStyle.FULL, java.util.Locale.getDefault()), GalleryHomeRules.lastHeard(at(2026, 11, 13), now, zone))
        assertTrue(GalleryHomeRules.lastHeard(at(2026, 11, 2), now, zone).contains("2"))
        assertEquals("", GalleryHomeRules.lastHeard(null, now, zone))
    }

    @Test fun aPlateTakesTheNewestPlayOfItsStationAndMarksToday() {
        val stations = listOf(station("FIP"), station("NTS 1"), station("KEXP"), station("RP"), station("Fifth"))
        val plays = listOf(play(1, "FIP", heard = at(2026, 11, 14)), play(2, "FIP", heard = at(2026, 11, 16)), play(3, "NTS 1", heard = at(2026, 11, 15)))
        val plates = GalleryHomeRules.plates(stations, plays, now, zone)
        assertEquals(4, plates.size)
        assertEquals("Today", plates[0].heard)
        assertTrue(plates[0].today)
        assertEquals("Yesterday", plates[1].heard)
        assertEquals("", plates[2].heard)
        assertTrue(!plates[2].today)
    }

    @Test fun aRadioRowEndsInLibraryRequestedGetOrNothing() {
        assertEquals(Trailing.InLibrary, GalleryHomeRules.trailing(play(1, inLibrary = true, grabbed = true)))
        assertEquals(Trailing.Requested, GalleryHomeRules.trailing(play(2, grabbed = true)))
        assertEquals(Trailing.Get, GalleryHomeRules.trailing(play(3)))
        assertEquals(Trailing.None, GalleryHomeRules.trailing(play(4, artist = null)))
        assertEquals(Trailing.None, GalleryHomeRules.trailing(play(5, artist = " ")))
    }

    @Test fun theNewestTwoPlaysAreShownNewestFirst() {
        val plays = listOf(play(1, heard = at(2026, 11, 16, 7)), play(2, heard = at(2026, 11, 16, 9)), play(3, heard = at(2026, 11, 15, 9)), play(4, heard = null))
        assertEquals(listOf(2L, 1L), GalleryHomeRules.newestPlays(plays).map { it.id })
        assertTrue(GalleryHomeRules.newestPlays(emptyList()).isEmpty())
    }

    @Test fun theHeardHeadingSaysWhenInWords() {
        assertEquals("Heard on FIP this morning", GalleryHomeRules.heardHeading(play(1, heard = at(2026, 11, 16, 8)), now, zone))
        assertEquals("Heard on FIP this afternoon", GalleryHomeRules.heardHeading(play(1, heard = at(2026, 11, 16, 14)), now, zone))
        assertEquals("Heard on FIP this evening", GalleryHomeRules.heardHeading(play(1, heard = at(2026, 11, 16, 19)), now, zone))
        assertEquals("Heard on FIP yesterday", GalleryHomeRules.heardHeading(play(1, heard = at(2026, 11, 15, 8)), now, zone))
        assertEquals("Heard on radio", GalleryHomeRules.heardHeading(null, now, zone))
        assertEquals("Heard on radio this morning", GalleryHomeRules.heardHeading(play(1, station = "", heard = at(2026, 11, 16, 8)), now, zone))
    }

    @Test fun aPlayLineIsTheArtistAndTheTime() {
        assertEquals("Cocteau Twins · 08:42", GalleryHomeRules.playLine(play(1), zone))
        assertEquals("08:42", GalleryHomeRules.playLine(play(1, artist = null), zone))
        assertEquals("Cocteau Twins", GalleryHomeRules.playLine(play(1, heard = null), zone))
    }

    @Test fun initialsFitAPlate() {
        assertEquals("FIP", GalleryHomeRules.initials("FIP"))
        assertEquals("RP", GalleryHomeRules.initials("Radio Paradise"))
        assertEquals("NI", GalleryHomeRules.initials("Nightwave"))
        assertEquals("", GalleryHomeRules.initials(" "))
    }

    @Test fun theLibraryLineNeverInventsAFigure() {
        assertEquals("1,284 albums · 312 artists · 7 new this month", GalleryHomeRules.libraryLine(HeroFigures(1284, 7, 3), 312))
        assertEquals("1,284 albums · 7 new this month", GalleryHomeRules.libraryLine(HeroFigures(1284, 7, 3), null))
        assertEquals("312 artists", GalleryHomeRules.libraryLine(null, 312))
        assertEquals("Library stats", GalleryHomeRules.libraryLine(null, null))
    }

    @Test fun anArtistsAlbumCountIsLeftOutWhenUnknown() {
        assertEquals("5 albums", GalleryHomeRules.albumCount(5))
        assertEquals("1 album", GalleryHomeRules.albumCount(1))
        assertEquals(null, GalleryHomeRules.albumCount(null))
    }
}
