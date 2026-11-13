package app.discair.ui

import app.discair.model.Pick
import app.discair.model.ShelfAlbum
import app.discair.ui.home.FlowHomeRules
import app.discair.ui.home.FlowHomeRules.Tab
import app.discair.ui.home.HeroFigures
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Step F2 of docs/ANDROID_ART_THEMES_PROPOSAL.md: the pure rules behind Flow's Home. */
class FlowHomeRulesTest {
    @Test fun theControlHasPicksNewPlayedInThatOrder() {
        assertEquals(listOf("Picks", "New", "Played"), FlowHomeRules.labels)
    }

    @Test fun aRememberedTabComesBackAndAnythingElseIsPicks() {
        assertEquals(Tab.Played, FlowHomeRules.tabOf("Played"))
        assertEquals(Tab.New, FlowHomeRules.tabOf("New"))
        assertEquals(Tab.Picks, FlowHomeRules.tabOf(null))
        assertEquals(Tab.Picks, FlowHomeRules.tabOf("Gone"))
    }

    @Test fun neighboursWrapAndNeverRepeatTheCentre() {
        assertEquals(6 to 1, FlowHomeRules.neighbours(0, 7))
        assertEquals(5 to 0, FlowHomeRules.neighbours(6, 7))
        assertEquals(0 to 2, FlowHomeRules.neighbours(1, 3))
        assertEquals(null to 1, FlowHomeRules.neighbours(0, 2))
        assertEquals(null to 0, FlowHomeRules.neighbours(1, 2))
        assertEquals(null to null, FlowHomeRules.neighbours(0, 1))
        assertEquals(null to null, FlowHomeRules.neighbours(0, 0))
    }

    @Test fun stepWrapsAndClampKeepsTheIndexInside() {
        assertEquals(1, FlowHomeRules.step(0, 7, 1))
        assertEquals(6, FlowHomeRules.step(0, 7, -1))
        assertEquals(0, FlowHomeRules.step(6, 7, 1))
        assertEquals(0, FlowHomeRules.step(3, 0, 1))
        assertEquals(2, FlowHomeRules.clamp(5, 3))
        assertEquals(0, FlowHomeRules.clamp(-1, 3))
        assertEquals(0, FlowHomeRules.clamp(4, 0))
    }

    @Test fun aSwipeNeedsFortyEightDp() {
        assertEquals(1, FlowHomeRules.swipeDelta(-48f))
        assertEquals(-1, FlowHomeRules.swipeDelta(120f))
        assertNull(FlowHomeRules.swipeDelta(47.9f))
        assertNull(FlowHomeRules.swipeDelta(-10f))
    }

    @Test fun theLineKeepsTheOrderAndLeavesOutWhatIsMissing() {
        assertEquals("Bark Psychosis · 1994 · Post-rock", FlowHomeRules.line(FlowHomeRules.Item("Bark Psychosis", "Hex", 1994, "Post-rock", null, null)))
        assertEquals("Talk Talk · 1991", FlowHomeRules.line(FlowHomeRules.Item("Talk Talk", "Laughing Stock", 1991, null, "a1", null)))
        assertEquals("Talk Talk", FlowHomeRules.line(FlowHomeRules.Item("Talk Talk", "Laughing Stock", null, " ", null, null)))
    }

    @Test fun itemsCarryTheOwnedAlbumIdOnlyForShelves() {
        val pick = FlowHomeRules.items(Pick(artist = "A", album = "B", year = 2001, genres = listOf("Dream pop", "Ambient")))
        assertNull(pick.albumId); assertEquals("Dream pop", pick.genre)
        val shelf = FlowHomeRules.items(ShelfAlbum(id = "x9", name = "B", artist = "A", year = 2001, artworkUrl = "u"))
        assertEquals("x9", shelf.albumId); assertEquals("u", shelf.artworkUrl); assertNull(shelf.genre)
        assertNull(FlowHomeRules.items(ShelfAlbum(id = "", name = "B", artist = "A")).albumId)
    }

    @Test fun onlyPicksCanBeGotAndEveryTabSaysWhenItIsEmpty() {
        assertTrue(FlowHomeRules.hasGet(Tab.Picks)); assertFalse(FlowHomeRules.hasGet(Tab.New)); assertFalse(FlowHomeRules.hasGet(Tab.Played))
        Tab.entries.forEach { assertTrue(FlowHomeRules.empty(it).isNotBlank()) }
    }

    @Test fun theLibraryLineNeverInventsAFigure() {
        assertEquals("1,284 albums · 12 new this month", FlowHomeRules.libraryLine(HeroFigures(1284, 12, 5)))
        assertEquals("Stats", FlowHomeRules.libraryLine(null))
    }

    @Test fun carouselSizesMatchTheMockup() {
        assertEquals(220, FlowHomeRules.CENTER_DP); assertEquals(160, FlowHomeRules.SIDE_DP)
        assertEquals(0.75f, FlowHomeRules.SIDE_ALPHA, 0f); assertEquals(70, FlowHomeRules.SIDE_OVERHANG_DP); assertEquals(236, FlowHomeRules.CAROUSEL_HEIGHT_DP)
    }
}
