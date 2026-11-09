package app.discair

import app.discair.model.AlbumPathKind
import app.discair.model.PathCapped
import app.discair.model.PathsView
import app.discair.model.parsePaths
import app.discair.model.parseSonicAlbumNeighbours
import app.discair.model.view
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Album paths (`type=release`) and album sonic neighbours: the recorded payloads decode into what the sheet shows. */
class AlbumPathsTest {
    /** The `response.body` of a recorded fixture, as JSON text. */
    private fun body(name: String): String = Json.parseToJsonElement(
        javaClass.classLoader!!.getResource("librarian/$name.json")!!.readText(),
    ).jsonObject["response"]!!.jsonObject["body"].toString()

    @Test fun exactlyTheFourBuiltAlbumKindsAreOffered() {
        assertEquals(
            listOf("album_crew", "album_guests", "album_works", "album_moment"),
            AlbumPathKind.entries.map { it.wire },
        )
    }

    @Test fun albumKindsNotBuiltYetAreNotOffered() {
        val wires = AlbumPathKind.entries.map { it.wire }
        assertFalse("album_room" in wires)
        assertFalse("album_gaps" in wires)
    }

    @Test fun okAlbumFixturesListStepsWithReasonsAndOwnedAlbums() {
        for (kind in AlbumPathKind.entries) {
            val r = parsePaths(body("paths_${kind.wire}"))
            assertEquals(kind.wire, r.kind)
            assertEquals("ok", r.status)
            assertTrue("${kind.wire} has stops", r.stops.isNotEmpty())
            assertTrue(r.view() is PathsView.Stops)
            for (stop in r.stops) {
                assertTrue("${kind.wire} stop is owned", stop.owned)
                assertTrue("${kind.wire} stop has a reason", stop.reasons.isNotEmpty())
                assertTrue(stop.reasons.all { it.text.isNotBlank() && it.code.isNotBlank() })
            }
        }
    }

    @Test fun emptyAlbumFixturesSayNothingToShow() {
        for (kind in AlbumPathKind.entries) {
            val r = parsePaths(body("paths_${kind.wire}_empty"))
            assertEquals("empty", r.status)
            assertTrue(r.stops.isEmpty())
            assertEquals(PathsView.Empty, r.view())
        }
    }

    @Test fun crewFixtureReadsItsStartAndAnEmptyOverlapCount() {
        val r = parsePaths(body("paths_album_crew"))
        assertEquals(0, r.overlapDropped)
        assertTrue(r.capped.isEmpty())
        assertEquals("crew_on", r.stops.first().reasons.first().code)
    }

    @Test fun overlapDroppedAndCappedAreReadWhenTheServerSendsThem() {
        val json = """{"kind":"album_crew","status":"ok","overlap_dropped":3,"truncated":null,
            "capped":[{"via":"Rudy van Gelder","more":12},{"via":{"canonical_name":"Ron Carter","type":"person"},"more":4},
            {"via":"Nobody","more":0},{"via":"No count"},{"more":2}],
            "stops":[{"entity":{"canonical_name":"X","owned":true,"type":"release"},"reasons":[{"code":"crew_on","text":"t"}]}]}"""
        val r = parsePaths(json)
        assertEquals(3, r.overlapDropped)
        assertEquals(listOf(PathCapped("Rudy van Gelder", 12), PathCapped("Ron Carter", 4)), r.capped)
        assertEquals(1, r.stops.size)
    }

    @Test fun errorBodiesAreEmptyNotBlankForAlbumPaths() {
        val r = parsePaths(body("paths_error_album_room_not_built"))
        assertEquals(PathsView.Empty, r.view())
        assertEquals(0, r.overlapDropped)
    }

    @Test fun sonicAlbumNeighboursOkFixtureKeepsStartSeedsAndMatches() {
        val n = parseSonicAlbumNeighbours(body("sonic_album_neighbours"))
        assertEquals("ok", n.status)
        assertEquals("55o30LbumfEMwDlKctbZpI", n.start?.albumId)
        assertEquals("100% Arabica", n.start?.album)
        assertEquals(4, n.seeds.size)
        assertTrue(n.skipped.isEmpty())
        assertEquals(14, n.stops.size)
        val first = n.stops.first()
        assertEquals("Yalil", first.album)
        assertEquals(4, first.matchCount)
        assertEquals("Sounds like 4 of this album's tracks", first.reasonText)
        assertTrue(first.owned)
        assertNull(n.truncated)
    }

    @Test fun sonicAlbumNeighboursEmptyFixtureReportsTheSkippedSeed() {
        val n = parseSonicAlbumNeighbours(body("sonic_album_neighbours_empty"))
        assertEquals("empty", n.status)
        assertTrue(n.stops.isEmpty())
        assertTrue(n.seeds.isEmpty())
        assertEquals(1, n.skipped.size)
        assertEquals("no_analysis", n.skipped.single().reason)
        assertEquals("Love Me", n.skipped.single().title)
    }

    @Test fun sonicAlbumNeighboursNotFoundBodyIsEmpty() {
        val n = parseSonicAlbumNeighbours(body("sonic_album_neighbours_error_not_found"))
        assertEquals("", n.status)
        assertTrue(n.stops.isEmpty())
        assertNull(n.start)
    }

    @Test fun sonicAlbumNeighboursNeverReadsSimilarityAsASortKey() {
        // Stops keep the server's order even when a later stop carries a higher similarity value.
        val json = """{"status":"ok","stops":[
            {"album":"A","album_id":"a","owned":true,"match_count":1,"similarity":0.1,"reasons":[{"text":"x"}]},
            {"album":"B","album_id":"b","owned":true,"match_count":5,"similarity":0.99,"reasons":[{"text":"y"}]}]}"""
        assertEquals(listOf("A", "B"), parseSonicAlbumNeighbours(json).stops.map { it.album })
    }

    @Test fun sonicAlbumNeighboursLeavesOutStopsWithoutAnIdOrName() {
        val json = """{"status":"ok","stops":[{"album":"","album_id":"a"},{"album":"No id"},{"album":"Keep","album_id":"k"}]}"""
        assertEquals(listOf("Keep"), parseSonicAlbumNeighbours(json).stops.map { it.album })
    }
}
