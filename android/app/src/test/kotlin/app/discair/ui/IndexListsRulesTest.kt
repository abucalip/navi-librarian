package app.discair.ui

import app.discair.model.ApiJson
import app.discair.model.DiscoveryList
import app.discair.model.LibraryArtist
import app.discair.model.Page
import app.discair.model.SearchResult
import app.discair.ui.common.IndexListsRules
import app.discair.ui.common.IndexListsRules.SearchGroup
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** docs/INDEX_THEME.md step I4: the words and numbers of Index's Discover, Library and Search, and the I0 `plays` field they read (section 11a.3). */
class IndexListsRulesTest {
    @Test fun discoverTabsFollowTheListOrderSoASwipeMovesTheSameWay() {
        assertEquals(DiscoveryList.entries.size, IndexListsRules.tabs.size)
        assertEquals("Daily picks", IndexListsRules.tabs.first())
        assertEquals("Insights", IndexListsRules.tabs.last())
        assertEquals("Collection", IndexListsRules.tabLabel(DiscoveryList.Classics))
    }

    @Test fun theDiscoverCountIsEveryEntryShownAndNothingWhileUnknownOrEmpty() {
        assertEquals("10", IndexListsRules.headCount(DiscoveryList.Daily, listOf(4, 3, 3)))
        assertNull(IndexListsRules.headCount(DiscoveryList.Daily, null))
        assertNull(IndexListsRules.headCount(DiscoveryList.Personal, listOf(0)))
        assertNull(IndexListsRules.headCount(DiscoveryList.Insights, listOf(5)))
    }

    @Test fun numbersAndMakerLines() {
        assertEquals("01", IndexListsRules.number(0))
        assertEquals("12", IndexListsRules.number(11))
        assertEquals("Cocteau Twins · 1990", IndexListsRules.maker("Cocteau Twins", 1990))
        assertEquals("Cocteau Twins", IndexListsRules.maker("Cocteau Twins", null))
        assertEquals("1990", IndexListsRules.maker(" ", 1990))
    }

    @Test fun libraryTabsCarryACountOnlyOnceKnown() {
        assertEquals("Artists 312", IndexListsRules.libraryTab("Artists", 312))
        assertEquals("Albums", IndexListsRules.libraryTab("Albums", null))
        assertEquals(48, IndexListsRules.genreCount(48))
        // The server answers at most 60 genres by default: a full answer may be cut off, so no number is shown.
        assertNull(IndexListsRules.genreCount(60))
    }

    @Test fun theSortLinePointsTheWayTheListRuns() {
        assertEquals("Sort · Date added ↓", IndexListsRules.sortLine("Date added", true))
        assertEquals("Sort · Name ↑", IndexListsRules.sortLine("Name", false))
    }

    @Test fun artistRowsLeaveOutPlaysAnOlderServerDoesNotSend() {
        assertEquals("5 albums · 212 plays", IndexListsRules.artistMeta(5, 212))
        assertEquals("1 album · 1 play", IndexListsRules.artistMeta(1, 1))
        assertEquals("2 albums", IndexListsRules.artistMeta(2, null))
        assertEquals("1 album", IndexListsRules.albumCount(1))
    }

    @Test fun lettersFileEachNameAndTheRailKeepsTheFirstRowOfEach() {
        assertEquals("A", IndexListsRules.letter("alice Coltrane"))
        assertEquals("#", IndexListsRules.letter("5.6.7.8's"))
        assertEquals("#", IndexListsRules.letter("!!!"))
        assertEquals("M", IndexListsRules.letter("  (Mdou) Moctar"))
        assertEquals("A", IndexListsRules.letter("Ädelweiss"))
        assertEquals(
            listOf("#" to 0, "A" to 1, "C" to 3),
            IndexListsRules.letters(listOf("764-HERO", "Alice Coltrane", "Arooj Aftab", "Cocteau Twins")),
        )
        // The rail is built from the server's sort keys; should a row still fall out of order, the rail never runs backwards.
        assertEquals(
            listOf("#" to 0, "A" to 1, "B" to 4),
            IndexListsRules.letters(listOf("764 hero", "a weather", "abyssinians", "agypten", "bark psychosis")),
        )
        assertEquals(listOf("A" to 0, "C" to 1), IndexListsRules.letters(listOf("alice", "cocteau twins", "beta")))
    }

    @Test fun theRailLetterUnderAFingerIsClampedToTheEnds() {
        assertEquals(0, IndexListsRules.letterAt(-5f, 100f, 4))
        assertEquals(1, IndexListsRules.letterAt(30f, 100f, 4))
        assertEquals(3, IndexListsRules.letterAt(100f, 100f, 4))
        assertEquals(0, IndexListsRules.letterAt(10f, 0f, 4))
    }

    @Test fun searchGroupsArtistsThenOwnedThenMissingInTheServersOrder() {
        val results = listOf(
            SearchResult(type = "album", owned = false, id = "x1", name = "A LA SALA"),
            SearchResult(type = "artist", owned = true, id = "a1", name = "Khruangbin"),
            SearchResult(type = "album", owned = true, id = "o1", name = "Mordechai"),
            SearchResult(type = "song", owned = true, id = "s1", name = "Pelota"),
            SearchResult(type = "album", owned = false, id = "x2", name = "Texas Sun"),
            SearchResult(type = "album", owned = false, id = "x1", name = "A LA SALA"), // streamed twice
        )
        val groups = IndexListsRules.searchGroups(results)
        assertEquals(listOf(SearchGroup.Artist, SearchGroup.InLibrary, SearchGroup.NotInLibrary), groups.map { it.first })
        assertEquals(listOf("Mordechai", "Pelota"), groups[1].second.map { it.name })
        assertEquals(listOf("A LA SALA", "Texas Sun"), groups[2].second.map { it.name })
        assertEquals("Artist", SearchGroup.Artist.title(1))
        assertEquals("Artists", SearchGroup.Artist.title(2))
        assertEquals(emptyList<Any>(), IndexListsRules.searchGroups(emptyList()))
    }

    @Test fun searchMetaLines() {
        assertEquals("Album · 2020", IndexListsRules.searchMeta(SearchResult(type = "album", owned = true, artist = "Khruangbin", year = 2020)))
        assertEquals("Album · Khruangbin · 2024", IndexListsRules.searchMeta(SearchResult(type = "album", owned = false, artist = "Khruangbin", year = 2024)))
        assertEquals("Song · Mordechai · 3:51", IndexListsRules.searchMeta(SearchResult(type = "song", album = "Mordechai", duration = 231)))
        assertEquals("3 albums", IndexListsRules.searchMeta(SearchResult(type = "artist", albumCount = 3)))
        assertEquals("Genre", IndexListsRules.searchMeta(SearchResult(type = "genre")))
        assertNull(IndexListsRules.duration(0))
    }

    @Test fun tasteMetaNamesTheWindow() {
        assertEquals("Last 90 days", IndexListsRules.tasteMeta("90 days"))
        assertEquals("Past year", IndexListsRules.tasteMeta("Past year"))
        assertEquals("All time", IndexListsRules.tasteMeta("All time"))
    }

    @Test fun libraryArtistsDecodePlaysAndAnOlderServerLeavesThemNull() {
        val page = ApiJson.decodeFromString(
            Page.serializer(LibraryArtist.serializer()),
            """{"items":[{"id":"1","key":"alice coltrane","name":"Alice Coltrane","album_count":5,"plays":212},{"id":"2","key":"k","name":"K","album_count":1}]}""",
        )
        assertEquals(212, page.items[0].plays)
        assertNull(page.items[1].plays)
    }
}
