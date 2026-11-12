package app.discair.ui

import app.discair.ui.theme.Layout
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class NavRulesTest {
    @Test fun theRailReplacesTheBottomNavigationFromSixHundredDp() {
        assertFalse(NavRules.railShown(599))
        assertTrue(NavRules.railShown(600))
        assertTrue(NavRules.railShown(839))
        assertTrue(NavRules.railShown(840))
    }

    @Test fun onlyTheCassetteDeckBarCarriesDiscoverSoEveryOtherLayoutKeepsItInTheTopBar() {
        assertTrue(NavRules.discoverInBar(Layout.TapeDeck))
        for (layout in Layout.values().filter { it != Layout.TapeDeck }) {
            assertFalse(NavRules.discoverInBar(layout))
            assertTrue(NavRules.discoverInTopBar(layout, rail = false))
        }
    }

    @Test fun discoverLeavesTheTopBarOnTheRailBecauseTheRailHasIt() {
        for (layout in Layout.values()) assertFalse(NavRules.discoverInTopBar(layout, rail = true))
        assertFalse(NavRules.discoverInTopBar(Layout.TapeDeck, rail = false))
    }

    @Test fun thePlayerButtonStaysInTheNavigationExceptOnTheCassetteDeckWithItsMiniPlayer() {
        assertFalse(NavRules.playerButtonShown(Layout.TapeDeck))
        for (layout in Layout.values().filter { it != Layout.TapeDeck }) assertTrue(NavRules.playerButtonShown(layout))
    }

    @Test fun theFourDestinationsAreHomeDiscoverLibrarySearchInOrder() {
        assertEquals(listOf("Home", "Discover", "Library", "Search"), NavRules.destinations)
    }
}
