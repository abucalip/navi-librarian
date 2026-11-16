package app.discair.ui

import app.discair.ui.common.GalleryPagesRules as R
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** Step G3 of docs/GALLERY_THEME.md: the words behind Gallery's Album, Artist and Genre pages. */
class GalleryPagesRulesTest {
    @Test fun theAlbumCatalogueLineKeepsOnlyWhatIsKnown() {
        assertEquals("1991 · 6 songs · 43 min · FLAC", R.albumEyebrow(1991, 6, 43 * 60, "FLAC"))
        assertEquals("1994", R.albumEyebrow(1994, 0, 0, null))
        assertEquals("1 song · 4 min", R.albumEyebrow(null, 1, 240, " "))
        assertEquals("", R.albumEyebrow(null, 0, 0, null))
    }

    @Test fun lengthsRoundToMinutesAndRollIntoHours() {
        assertNull(R.length(0))
        assertEquals("1 min", R.length(20))
        assertEquals("43 min", R.length(2580))
        assertEquals("1 h 19 min", R.length(79 * 60))
        assertEquals("2 h", R.length(7200))
        assertEquals("3:07", R.clock(187))
        assertEquals("0:05", R.clock(5))
    }

    @Test fun theYearSpanNamesBothEndsOrOne() {
        assertEquals("1981 to 1991", R.yearSpan(listOf(1988, null, 1981, 1991)))
        assertEquals("1991", R.yearSpan(listOf(1991, 1991)))
        assertNull(R.yearSpan(listOf(null, null)))
        assertNull(R.yearSpan(emptyList()))
    }

    @Test fun theArtistCatalogueLine() {
        assertEquals("5 albums in your library · 1981 to 1991", R.artistEyebrow(true, 5, listOf(1981, 1991)))
        assertEquals("1 album in your library", R.artistEyebrow(true, 1, emptyList()))
        assertEquals("Not in your library", R.artistEyebrow(false, 0, listOf(1981)))
    }

    @Test fun theGenreCatalogueLineCountsBoth() {
        assertEquals("86 albums · 41 artists in your library", R.genreEyebrow(86, 41))
        assertEquals("1 album · 1 artist in your library", R.genreEyebrow(1, 1))
    }

    @Test fun captionsAndMissingAlbumsSayWhatTheyHave() {
        assertEquals("Floating Points, 2021", R.maker("Floating Points", 2021))
        assertEquals("Slowdive", R.maker("Slowdive", null))
        assertEquals("1995", R.maker("", 1995))
        assertEquals("1991 · 12K listens", R.missingSub(1991, 12_000))
        assertEquals("1991", R.missingSub(1991, 0))
        assertEquals("", R.missingSub(null, 0))
    }

    @Test fun theTabsFollowTheContent() {
        assertEquals(listOf("Songs", "Info", "Reviews", "Booklet"), R.albumTabs(true, true))
        assertEquals(listOf("Info", "Reviews"), R.albumTabs(false, false))
        assertEquals(listOf("Songs", "Info", "Reviews"), R.albumTabs(true, false))
    }

    @Test fun theFirstTabIsSongsThenReviewsWhenThereIsNothingToRead() {
        assertEquals(0, R.defaultTab(R.albumTabs(true, false), finished = true, noDescription = true))
        assertEquals(1, R.defaultTab(R.albumTabs(false, false), finished = true, noDescription = true))
        assertEquals(0, R.defaultTab(R.albumTabs(false, false), finished = false, noDescription = true))
        assertEquals(0, R.defaultTab(R.albumTabs(false, false), finished = true, noDescription = false))
    }

    @Test fun theNoteSaysWhyThereIsAGetButton() {
        assertEquals("Not in your library. Get it and its songs are listed here.", R.note(false, 0))
        assertEquals("1 song is not in your library.", R.note(true, 1))
        assertEquals("3 songs are not in your library.", R.note(true, 3))
        assertNull(R.note(true, 0))
    }
}
