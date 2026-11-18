package app.discair.ui

import app.discair.model.GetState
import app.discair.ui.common.IndexDatum
import app.discair.ui.common.IndexGet
import app.discair.ui.common.indexGetOf
import app.discair.ui.home.FlowHomeRules
import app.discair.ui.home.IndexHomeRules
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** docs/INDEX_THEME.md section 9: the pure rules behind Index's Home. */
class IndexHomeRulesTest {
    @Test fun theCountIsTheSourceSizeOrADashWhileUnknown() {
        assertEquals("12", IndexHomeRules.count(12))
        assertEquals("0", IndexHomeRules.count(0))
        assertEquals("—", IndexHomeRules.count(null))
    }

    @Test fun catalogueNumbersHaveTwoDigitsAtLeast() {
        assertEquals("01", IndexHomeRules.number(0))
        assertEquals("05", IndexHomeRules.number(4))
        assertEquals("12", IndexHomeRules.number(11))
        assertEquals("105", IndexHomeRules.number(104))
    }

    @Test fun theStripShowsTheFourAlbumsAfterTheLeadInListOrder() {
        assertEquals(listOf(1, 2, 3, 4), IndexHomeRules.strip(10, 0))
        assertEquals(listOf(1, 2), IndexHomeRules.strip(3, 0))
        assertEquals(emptyList<Int>(), IndexHomeRules.strip(1, 0))
        assertEquals(emptyList<Int>(), IndexHomeRules.strip(0, 0))
    }

    @Test fun aLongPressedAlbumLeavesTheStripAndKeepsItsNumberForTheLead() {
        // Album 03 (index 2) becomes the lead: the strip closes up round it, and the others keep their own numbers.
        val strip = IndexHomeRules.strip(10, 2)
        assertEquals(listOf(0, 1, 3, 4), strip)
        assertEquals(listOf("01", "02", "04", "05"), strip.map(IndexHomeRules::number))
        assertEquals("03", IndexHomeRules.number(2))
    }

    @Test fun theLeadStaysInsideAListThatShrank() {
        assertEquals(2, IndexHomeRules.leadAt(2, 5))
        assertEquals(3, IndexHomeRules.leadAt(7, 4))
        assertEquals(0, IndexHomeRules.leadAt(3, 0))
        assertEquals(0, IndexHomeRules.leadAt(-1, 4))
    }

    @Test fun theDataListSaysOwnedAlwaysAndLeavesUnknownLinesOut() {
        assertEquals(
            listOf(IndexDatum("Artist", "Bark Psychosis"), IndexDatum("Year", "1994"), IndexDatum("Genre", "Post-rock"), IndexDatum("Owned", "No", accent = true)),
            IndexHomeRules.dataRows("Bark Psychosis", 1994, "Post-rock", owned = false),
        )
        assertEquals(
            listOf(IndexDatum("Artist", "Talk Talk"), IndexDatum("Owned", "Yes")),
            IndexHomeRules.dataRows("Talk Talk", null, " ", owned = true),
        )
        assertEquals(listOf(IndexDatum("Owned", "No", accent = true)), IndexHomeRules.dataRows("", null, null, owned = false))
    }

    @Test fun playCountsAreHiddenWhenTheServerCouldNotReadTheListens() {
        assertEquals("14 plays", IndexHomeRules.plays(14))
        assertEquals("1 play", IndexHomeRules.plays(1))
        assertEquals("0 plays", IndexHomeRules.plays(0))
        assertNull(IndexHomeRules.plays(null))
    }

    @Test fun aPlayedRowsMetaLineKeepsOnlyWhatIsKnown() {
        assertEquals("Talk Talk · 1991", IndexHomeRules.meta("Talk Talk", 1991))
        assertEquals("Talk Talk", IndexHomeRules.meta("Talk Talk", null))
        assertEquals("1991", IndexHomeRules.meta("", 1991))
    }

    @Test fun theInsightNumeralIsTheFirstNumberThatIsNotAYear() {
        assertEquals("35", IndexHomeRules.insightNumeral("Blue Lines turns 35"))
        assertEquals("7", IndexHomeRules.insightNumeral("7 albums you have not played"))
        assertNull(IndexHomeRules.insightNumeral("Released in 1991"))
        assertNull(IndexHomeRules.insightNumeral("Nothing numbered here"))
        assertNull(IndexHomeRules.insightNumeral("1,284 albums"))
    }

    @Test fun theTrackerLightsTheStepAnArrivalIsOn() {
        assertEquals(1, IndexHomeRules.trackerReached(0))
        assertEquals(2, IndexHomeRules.trackerReached(1))
        assertEquals(3, IndexHomeRules.trackerReached(2))
        assertEquals(4, IndexHomeRules.trackerReached(4))
    }

    @Test fun theLibraryLineNamesOnlyWhatIsKnown() {
        assertEquals("1,284 albums · 312 artists · 7 new this month", IndexHomeRules.libraryLine(1284, 312, 7))
        assertEquals("1 album · 1 artist", IndexHomeRules.libraryLine(1, 1, null))
        assertEquals("Library stats", IndexHomeRules.libraryLine(null, null, null))
    }

    @Test fun anEmptySourceHasItsOwnSentence() {
        assertEquals("Nothing played yet.", IndexHomeRules.empty(FlowHomeRules.Tab.Played))
        assertEquals("Play a few albums. What you play most is indexed here.", IndexHomeRules.NOTHING_PLAYED)
    }

    @Test fun aGetStateMapsToTheControlItDraws() {
        assertEquals(IndexGet.Idle, indexGetOf(GetState.Idle))
        assertEquals(IndexGet.Pending, indexGetOf(GetState.Pending))
        assertEquals(IndexGet.Requested, indexGetOf(GetState.Requested(null)))
        assertEquals(IndexGet.Failed, indexGetOf(GetState.Failed("x")))
    }
}
