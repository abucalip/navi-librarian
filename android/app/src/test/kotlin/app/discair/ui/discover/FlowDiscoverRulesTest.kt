package app.discair.ui.discover

import app.discair.model.DiscoveryList
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Flow's one-switch Discover, step D1 (docs/Discover_page.md 4.1, 4.2, 8): the switch names, the dots and the sheet's rows. */
class FlowDiscoverRulesTest {
    @Test fun theSheetHasOneRowPerListInEntryOrderWithTheFullLabel() {
        val rows = FlowDiscoverRules.sheetRows
        assertEquals(DiscoveryList.entries, rows.map { it.list })
        assertEquals(DiscoveryList.entries.map { it.label }, rows.map { it.list.label })
        assertTrue(rows.all { it.subtitle.isNotBlank() })
    }

    @Test fun savedAndInsightsAreTheOnlyRowsUnderYours() {
        assertEquals(listOf(DiscoveryList.Saved, DiscoveryList.Insights), DiscoveryList.entries.filter { FlowDiscoverRules.isYours(it) })
    }

    @Test fun theSwitchNamesAreTheShortOnesAndFitBesideTheDots() {
        val expected = mapOf(
            DiscoveryList.Daily to "Daily picks", DiscoveryList.DeepDive to "Deep dives", DiscoveryList.NewReleases to "New releases",
            DiscoveryList.Classics to "Collection", DiscoveryList.Personal to "Personal", DiscoveryList.Saved to "Saved", DiscoveryList.Insights to "Insights",
        )
        for (l in DiscoveryList.entries) {
            assertEquals(expected[l], FlowDiscoverRules.switchName(l))
            assertTrue(FlowDiscoverRules.switchName(l).length <= 12)
        }
    }

    @Test fun theDotIndexIsTheEntryOrdinalAndTheDescriptionUsesTheFullLabel() {
        for (l in DiscoveryList.entries) assertEquals(l.ordinal, FlowDiscoverRules.dotIndex(l))
        assertEquals("Add to your collection, list 4 of 7. Change list", FlowDiscoverRules.switchDescription(DiscoveryList.Classics))
        assertEquals("Insights, list 7 of 7. Change list", FlowDiscoverRules.switchDescription(DiscoveryList.Insights))
    }

    @Test fun theNumbersAreTheMockups() {
        assertEquals(48, FlowDiscoverRules.SWITCH_HEIGHT)
        assertEquals(6, FlowDiscoverRules.DOT)
        assertEquals(18, FlowDiscoverRules.DOT_CURRENT)
    }
}
