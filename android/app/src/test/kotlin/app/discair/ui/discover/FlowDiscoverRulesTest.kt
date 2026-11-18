package app.discair.ui.discover

import app.discair.model.DiscoveryEntry
import app.discair.model.DiscoveryItem
import app.discair.model.DiscoveryList
import app.discair.model.DiscoveryResult
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Flow's one-switch Discover, step D1 (docs/archive/completed/Discover_page.md 4.1, 4.2, 8): the switch names, the dots and the sheet's rows. */
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

    // ----- D2: sections, keys and the third line (docs/archive/completed/Discover_page.md 4.3, 4.4, 4.5, 8) -----

    private fun entry(artist: String, album: String, row: String? = null) = DiscoveryEntry(DiscoveryItem(artist = artist, album = album, genreRowLabel = row), JsonObject(emptyMap()))
    private fun section(title: String?, vararg e: DiscoveryEntry, error: String? = null, message: String? = null, disabled: Boolean = false) =
        Section(title, "p", if (error == null) DiscoveryResult(e.toList(), disabled, message) else null, error)

    @Test fun dailyPicksHasOneSectionPerLensWithCountsAndNotesForFailedAndEmptyLenses() {
        val a = entry("A", "One"); val b = entry("B", "Two")
        val s = FlowDiscoverRules.sections(
            DiscoveryList.Daily,
            listOf(section("Repeated tracks", a, b), section("Deep cuts", error = "timeout"), section("Obsessions", message = "Nothing yet."), section("Current tastes")),
            mapOf(b.key to true),
        )
        assertEquals(listOf("Repeated tracks", "Deep cuts", "Obsessions", "Current tastes"), s.map { it.title })
        assertEquals(listOf(1, 0, 0, 0), s.map { it.count })
        assertEquals(listOf(null, "Deep cuts could not be loaded: timeout", "Nothing yet.", "No albums today."), s.map { it.note })
    }

    @Test fun dailyPicksTurnedOffIsOneUntitledEmptySectionSoTheScreenSaysItOnce() {
        val s = FlowDiscoverRules.sections(DiscoveryList.Daily, listOf(section("A", disabled = true), section("B", disabled = true)), emptyMap())
        assertEquals(1, s.size)
        assertEquals(null, s.single().title)
        assertTrue(s.single().entries.isEmpty())
    }

    @Test fun anAlbumInTwoLensSectionsGetsTwoKeys() {
        val a = entry("A", "One")
        val s = FlowDiscoverRules.sections(DiscoveryList.Daily, listOf(section("Deep cuts", a), section("Obsessions", a)), emptyMap())
        val keys = s.flatMap { sec -> sec.entries.map { FlowDiscoverRules.itemKey(sec, it) } }
        assertEquals(2, keys.toSet().size)
        assertEquals("Deep cuts:a/one", keys[0])
    }

    @Test fun deepDivesGroupsByGenreRowLabelAndCallsABlankOneMore() {
        val s = FlowDiscoverRules.sections(
            DiscoveryList.DeepDive,
            listOf(section(null, entry("A", "1", "Jazz"), entry("B", "2", ""), entry("C", "3", "Jazz"), entry("D", "4", "Ambient"))), emptyMap(),
        )
        assertEquals(listOf("Jazz", "More", "Ambient"), s.map { it.title })
        assertEquals(listOf(2, 1, 1), s.map { it.count })
    }

    @Test fun deepDivesWithNoLabelsIsOnePlainGridWithoutHeadings() {
        val s = FlowDiscoverRules.sections(DiscoveryList.DeepDive, listOf(section(null, entry("A", "1"), entry("B", "2"))), emptyMap())
        assertEquals(1, s.size)
        assertEquals(null, s.single().title)
        assertEquals(2, s.single().count)
    }

    @Test fun otherListsAreOneUntitledSectionWithoutDismissedAlbums() {
        val a = entry("A", "1"); val b = entry("B", "2")
        val s = FlowDiscoverRules.sections(DiscoveryList.Saved, listOf(section(null, a, b)), mapOf(a.key to true))
        assertEquals(listOf(b), s.single().entries)
    }

    @Test fun theThirdLineIsTheReasonElseInYourLibraryWhenOwnedElseNothing() {
        assertEquals("Shares genres with X", FlowDiscoverRules.thirdLine("Shares genres with X", true))
        assertEquals("In your library", FlowDiscoverRules.thirdLine("", true))
        assertEquals(null, FlowDiscoverRules.thirdLine("", false))
    }

    @Test fun theGridNumbersAreTheMockups() {
        assertEquals(14, FlowDiscoverRules.GRID_GAP_X)
        assertEquals(16, FlowDiscoverRules.GRID_GAP_Y)
        assertEquals(12, FlowDiscoverRules.GRID_COVER_RADIUS)
        assertEquals(34, FlowDiscoverRules.GET_ON_COVER)
    }

    @Test fun theInsightsNoteNamesOffAndEmptyLensesAndIsLeftOutWhenBothAreEmpty() {
        assertEquals("Off: Series, Blind spots.", FlowDiscoverRules.insightsNote(listOf("Series", "Blind spots"), emptyList()))
        assertEquals("Nothing today: Hidden canon.", FlowDiscoverRules.insightsNote(emptyList(), listOf("Hidden canon")))
        assertEquals("Off: Series, Blind spots. Nothing today: Hidden canon.", FlowDiscoverRules.insightsNote(listOf("Series", "Blind spots"), listOf("Hidden canon")))
        assertEquals(null, FlowDiscoverRules.insightsNote(emptyList(), emptyList()))
    }
}
