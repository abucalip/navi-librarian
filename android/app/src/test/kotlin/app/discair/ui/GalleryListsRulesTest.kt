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

    @Test fun aTileShowsTheReasonElseOwnershipElseNothing() {
        assertEquals("Because you play Talk Talk", R.tileReason("Because you play Talk Talk", owned = false))
        assertEquals("Because you play Talk Talk", R.tileReason("  Because you play Talk Talk ", owned = true))
        assertEquals("In your library", R.tileReason("", owned = true))
        assertEquals(null, R.tileReason(" ", owned = false))
    }

    @Test fun theTileButtonsSayWhatTheyDo() {
        assertEquals("Save Spirit of Eden", R.saveDescription("Spirit of Eden", saved = false, failed = false))
        assertEquals("Remove Spirit of Eden from saved", R.saveDescription("Spirit of Eden", saved = true, failed = false))
        assertEquals("Could not save Spirit of Eden. Try again", R.saveDescription("Spirit of Eden", saved = false, failed = true))
        assertEquals("Not requested", R.getState(app.discair.model.GetState.Idle))
        assertEquals("Requested. Follow it under Downloads", R.getState(app.discair.model.GetState.Requested(null)))
    }

    @Test fun anInsightsCardNamesItsLens() {
        assertEquals("Anniversary", R.lensLine("Anniversaries", anniversary = true))
        assertEquals("Gaps", R.lensLine("Gaps", anniversary = false))
    }

    @Test fun theSwitchHasOneDashPerListAndTheReasonHasRoom() {
        assert(R.DASH_CURRENT_DP > R.DASH_DP)
        assert(R.REASON_LINES >= 3)
        assert(R.SWITCH_DP >= 48)
    }

    @Test fun aTileSaysWhyFromWhateverTheServerSent() {
        // The pick's own reason first, then the server's sentence.
        assertEquals("Because you listen to Talk Talk", R.tileReason("Because you listen to Talk Talk", "Released in 2026", null, null, null, false))
        assertEquals("Released in 2026 by an artist with a full album in your library",
            R.tileReason("", "Released in 2026 by an artist with a full album in your library", null, null, null, false))
        // A lens album says which lens and seed tag brought it.
        assertEquals("From the acid house you keep repeating", R.tileReason("", "", "repeated_tracks", "acid house", null, false))
        assertEquals("From your jazz obsession", R.tileReason("", "", "obsessions", "jazz", null, false))
        assertEquals("A lesser-known record from the rock you play", R.tileReason("", "", "deep_cuts", "rock", null, false))
        assertEquals("Close to the classical you play lately", R.tileReason("", "", "current_tastes", "classical", null, false))
        assertEquals("Through the dub you play", R.tileReason("", "", "something_new", "dub", null, false))
        // Collection: the artist's albums already in the library.
        assertEquals("A well-known album; you have 1 album by this artist", R.tileReason("", "", null, null, 1, false))
        assertEquals("A well-known album; you have 3 albums by this artist", R.tileReason("", "", null, " ", 3, false))
        // Nothing else: owned, or no line at all.
        assertEquals("In your library", R.tileReason("", "", null, null, 0, true))
        assertEquals(null, R.tileReason("", " ", "deep_cuts", null, null, false))
        assertEquals("1 album", R.countLine(1))
        assertEquals("10 albums", R.countLine(10))
    }
}
