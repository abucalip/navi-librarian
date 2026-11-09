package app.discair

import app.discair.model.AlbumTab
import app.discair.model.PathCapped
import app.discair.model.albumPathsEmpty
import app.discair.model.albumTabDescription
import app.discair.model.albumTabs
import app.discair.model.parsePaths
import app.discair.model.parseSonicAlbumNeighbours
import app.discair.model.toAlbumAnswer
import app.discair.model.yearGap
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** What the album Paths sheet lists, built from the recorded album fixtures. */
class AlbumPathStepsTest {
    private fun body(name: String): String = Json.parseToJsonElement(
        javaClass.classLoader!!.getResource("librarian/$name.json")!!.readText(),
    ).jsonObject["response"]!!.jsonObject["body"].toString()

    @Test fun neighboursByEarIsOfferedOnlyWithSonic() {
        assertFalse(AlbumTab.NeighboursByEar in albumTabs(false))
        assertEquals(5, albumTabs(true).size)
        assertEquals(4, albumTabs(false).size)
    }

    @Test fun graphStepsKeepServerOrderAndNameThePersonInTheDetailLine() {
        val r = parsePaths(body("paths_album_crew"))
        val a = r.toAlbumAnswer()
        assertEquals(r.stops.map { it.name }, a.steps.map { it.album })
        assertEquals("Cannonball Adderley · Rudy van Gelder", a.steps.first().detail)
        assertTrue(a.steps.all { it.reasons.isNotEmpty() })
    }

    @Test fun emptyAnswerHasNoStepsAndStatesTheRule() {
        val a = parsePaths(body("paths_album_guests_empty")).toAlbumAnswer()
        assertTrue(a.steps.isEmpty())
        assertEquals(
            "No guest list path from A yet. A path appears only when every step has evidence.",
            albumPathsEmpty(AlbumTab.GuestList, "A"),
        )
    }

    @Test fun cappedIsSaidInWordsAndNeverHidden() {
        val json = """{"kind":"album_crew","status":"ok","capped":[{"via":"Rudy van Gelder","more":12},{"via":"Al","more":1}],
          "truncated":"time","stops":[{"entity":{"canonical_name":"X","type":"release","owned":true},"reasons":[{"code":"crew_on","text":"t"}]}]}"""
        val a = parsePaths(json).toAlbumAnswer()
        assertEquals(
            listOf(
                "12 more albums with Rudy van Gelder are not shown.", "1 more album with Al is not shown.",
                "The server stopped this path early (time limit), so later steps may be missing.",
            ),
            a.notes,
        )
        assertEquals(listOf(PathCapped("Rudy van Gelder", 12), PathCapped("Al", 1)), parsePaths(json).capped)
    }

    @Test fun neighboursShowTheCountOfMatchedTracksAndTheSkippedSeeds() {
        val a = parseSonicAlbumNeighbours(body("sonic_album_neighbours")).toAlbumAnswer()
        assertEquals(4, a.seeds)
        assertEquals("Amina · 4 of 4 tracks", a.steps.first().detail)
        val e = parseSonicAlbumNeighbours(body("sonic_album_neighbours_empty")).toAlbumAnswer()
        assertEquals(listOf("1 track has no sound analysis and was skipped."), e.notes)
    }

    @Test fun descriptionsNameTheAlbumAndTheSeedCount() {
        assertTrue(albumTabDescription(AlbumTab.StudioCrew, "X").contains("X"))
        assertEquals("Albums in your library that sound like X, found from 8 of its tracks.", albumTabDescription(AlbumTab.NeighboursByEar, "X", 8))
    }

    @Test fun yearGapReadsTheServersWording() {
        assertEquals("Within 1 year", yearGap("both, within 1 year of each other"))
        assertEquals("Within 2 years", yearGap("within 2 years"))
        assertEquals(null, yearGap("no number"))
    }
}
