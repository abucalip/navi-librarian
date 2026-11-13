package app.discair

import app.discair.model.AlbumTab
import app.discair.model.PathCapped
import app.discair.model.PathHistory
import app.discair.model.historyNotes
import app.discair.model.reasonEyebrow
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
        assertEquals(7, albumTabs(true).size)
        assertEquals(6, albumTabs(false).size)
    }

    @Test fun graphStepsKeepServerOrderAndTheDetailLineIsTheArtistOnly() {
        val r = parsePaths(body("paths_album_crew"))
        val a = r.toAlbumAnswer()
        assertEquals(r.stops.map { it.name }, a.steps.map { it.album })
        assertEquals("Cannonball Adderley", a.steps.first().detail)
        assertTrue(a.steps.all { it.reasons.isNotEmpty() })
    }

    @Test fun sameRoomNamesThePlaceAndLabelsItRecordedAt() {
        val a = parsePaths(body("paths_album_room")).toAlbumAnswer()
        assertEquals("Herbie Hancock", a.steps.first().detail)
        assertEquals("Recorded at", reasonEyebrow(a.steps.first().reasons.first().code))
        assertTrue(a.steps.all { it.play == null })
    }

    @Test fun gapsShowThePlayLabelAndStayInServerOrder() {
        val r = parsePaths(body("paths_album_gaps"))
        val a = r.toAlbumAnswer()
        assertEquals(r.stops.map { it.name }, a.steps.map { it.album })
        assertEquals("Opeth · Not played", a.steps.first().detail)
        assertEquals("Not played", a.steps.first().play)
        assertTrue(a.notes.isEmpty())
    }

    @Test fun gapsWithUnavailableHistorySayEveryAlbumIsListed() {
        val a = parsePaths(body("paths_album_gaps_unavailable")).toAlbumAnswer()
        assertTrue(a.steps.isNotEmpty())
        assertTrue(a.steps.all { it.play == null })
        assertTrue(a.notes.single().contains("could not be read"))
        assertTrue(a.notes.single().contains("played or not"))
    }

    @Test fun gapsThinHistoryIsNeverAnUnplayedClaim() {
        val notes = historyNotes(PathHistory("thin", 5, 0, 0, 2))
        assertTrue(notes.single().contains("too short"))
    }

    @Test fun gapsEmptyBecauseEverythingWasPlayedSaysSo() {
        val a = parsePaths(body("paths_album_gaps_empty")).toAlbumAnswer()
        assertTrue(a.steps.isEmpty())
        assertTrue(a.empty!!.startsWith("Every album these credits reach is one you have already played"))
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
        assertEquals(4, a.steps.first().matchCount)
        assertTrue(a.steps.first().detail.startsWith("Amina"))
        assertFalse(a.steps.first().detail.contains("tracks"))
        val e = parseSonicAlbumNeighbours(body("sonic_album_neighbours_empty")).toAlbumAnswer()
        assertEquals(listOf("1 track has no sound analysis and was skipped."), e.notes)
    }

    @Test fun stepsCarryWhetherTheAlbumIsInTheLibrary() {
        val r = parsePaths(body("paths_album_crew"))
        assertEquals(r.stops.map { it.owned }, r.toAlbumAnswer().steps.map { it.owned })
        val json = """{"kind":"album_crew","status":"ok","stops":[{"entity":{"canonical_name":"Away","type":"release","owned":false},"reason_count":1,"reasons":[{"code":"crew_on","text":"t","via":{"name":"P","type":"person"}}]}]}"""
        assertFalse(parsePaths(json).toAlbumAnswer().steps.single().owned)
    }

    @Test fun descriptionsDoNotClaimTheResultsAreInTheLibrary() {
        for (t in AlbumTab.entries) assertFalse(albumTabDescription(t, "X", 3).contains("in your library"))
    }

    @Test fun descriptionsNameTheAlbumAndTheSeedCount() {
        assertTrue(albumTabDescription(AlbumTab.StudioCrew, "X").contains("X"))
        assertEquals("Albums that sound like X, found from 8 of its tracks.", albumTabDescription(AlbumTab.NeighboursByEar, "X", 8))
    }

    @Test fun yearGapReadsTheServersWording() {
        assertEquals("Within 1 year", yearGap("both, within 1 year of each other"))
        assertEquals("Within 2 years", yearGap("within 2 years"))
        assertEquals(null, yearGap("no number"))
    }
}
