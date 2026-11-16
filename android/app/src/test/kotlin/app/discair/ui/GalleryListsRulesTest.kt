package app.discair.ui

import app.discair.ui.common.GalleryListsRules as R
import java.time.LocalDate
import java.util.Locale
import org.junit.Assert.assertEquals
import org.junit.Test

/** Step G4 of docs/GALLERY_THEME.md: the words behind Gallery's Discover, Library and Search pages. */
class GalleryListsRulesTest {
    @Test fun theDateLineNamesTheDayAndMonth() {
        assertEquals("Monday 16 November", R.dateLine(LocalDate.of(2026, 11, 16), Locale.ENGLISH))
        assertEquals("Sunday 1 February", R.dateLine(LocalDate.of(2026, 2, 1), Locale.ENGLISH))
    }

    @Test fun anEntryIsNumberedAndNamesItsGenreWhenItHasOne() {
        assertEquals("No. 01 · Post-rock", R.entryEyebrow(0, "Post-rock"))
        assertEquals("No. 12", R.entryEyebrow(11, null))
        assertEquals("No. 03", R.entryEyebrow(2, "  "))
        assertEquals("Shoegaze", R.entryGenre(listOf(" ", "Shoegaze"), "Row"))
        assertEquals("Row", R.entryGenre(emptyList(), "Row"))
        assertEquals(null, R.entryGenre(emptyList(), " "))
    }

    @Test fun theTasteHeadingNamesTheWindow() {
        assertEquals("Your taste · last 90 days", R.tasteHeading("90 days"))
        assertEquals("Your taste · past year", R.tasteHeading("Past year"))
        assertEquals("Your taste · all time", R.tasteHeading("All time"))
        assertEquals("1,240 listens of 48,912", R.listensLine(1240, 48912))
    }

    @Test fun theLibraryCountSaysOneInTheSingular() {
        assertEquals("312 artists", R.countEyebrow("artists", 312))
        assertEquals("1,284 albums", R.countEyebrow("albums", 1284))
        assertEquals("1 album", R.countEyebrow("albums", 1))
        assertEquals("", R.countEyebrow("albums", null))
    }

    @Test fun theSortLineReadsAsInTheMockup() {
        assertEquals("By name", R.sortLine("Name", "A to Z"))
        assertEquals("By name · Z to A", R.sortLine("Name", "Z to A"))
        assertEquals("Newest first", R.sortLine("Date added", "Newest first"))
        assertEquals("Oldest first", R.sortLine("Year", "Oldest first"))
        assertEquals("By album count · Most first", R.sortLine("Album count", "Most first"))
    }

    @Test fun aSearchResultHasOneLineForItsKind() {
        assertEquals("5 albums in your library", R.searchDetail("artist", true, null, null, null, 5, null))
        assertEquals("1 album · Dream pop", R.searchDetail("artist", false, null, null, null, 1, "Dream pop"))
        assertEquals("Talk Talk, 1991", R.searchDetail("album", true, "Talk Talk", null, 1991, null, null))
        assertEquals("Talk Talk", R.searchDetail("album", true, "Talk Talk", null, null, null, null))
        assertEquals("Talk Talk · Laughing Stock", R.searchDetail("song", true, "Talk Talk", "Laughing Stock", null, null, null))
        assertEquals("", R.searchDetail("genre", false, null, null, null, null, null))
    }
}
