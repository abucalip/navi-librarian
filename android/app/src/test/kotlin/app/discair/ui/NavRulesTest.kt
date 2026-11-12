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

    @Test fun onlyTheCassetteDeckAndCoverStackBarsCarryDiscoverSoEveryOtherLayoutKeepsItInTheTopBar() {
        assertTrue(NavRules.discoverInBar(Layout.TapeDeck))
        assertTrue(NavRules.discoverInBar(Layout.CoverStack))
        for (layout in Layout.values().filter { it != Layout.TapeDeck && it != Layout.CoverStack }) {
            assertFalse(NavRules.discoverInBar(layout))
            assertTrue(NavRules.discoverInTopBar(layout, rail = false))
        }
    }

    @Test fun discoverLeavesTheTopBarOnTheRailBecauseTheRailHasIt() {
        for (layout in Layout.values()) assertFalse(NavRules.discoverInTopBar(layout, rail = true))
        assertFalse(NavRules.discoverInTopBar(Layout.TapeDeck, rail = false))
        assertFalse(NavRules.discoverInTopBar(Layout.CoverStack, rail = false))
    }

    @Test fun thePlayerButtonStaysInTheNavigationExceptWhereALayoutHasAMiniPlayer() {
        assertFalse(NavRules.playerButtonShown(Layout.TapeDeck))
        assertFalse(NavRules.playerButtonShown(Layout.CoverStack))
        for (layout in Layout.values().filter { it != Layout.TapeDeck && it != Layout.CoverStack }) assertTrue(NavRules.playerButtonShown(layout))
    }

    @Test fun theFourDestinationsAreHomeDiscoverLibrarySearchInOrder() {
        assertEquals(listOf("Home", "Discover", "Library", "Search"), NavRules.destinations)
    }
}
