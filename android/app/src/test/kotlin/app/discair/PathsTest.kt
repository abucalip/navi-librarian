package app.discair

import app.discair.data.CacheMiss
import app.discair.model.PathKind
import app.discair.model.PathsView
import app.discair.model.parsePaths
import app.discair.model.pathsAvailableFrom
import app.discair.model.pathsFailure
import app.discair.model.view
import app.discair.net.ConnectionException
import app.discair.net.ConnectionFailure
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Server V2 discovery paths: the recorded `GET /api/knowledge/paths` payloads and the status words the app shows. */
class PathsTest {
    /** The `response.body` of a recorded fixture, as JSON text. */
    private fun body(name: String): String = Json.parseToJsonElement(
        javaClass.classLoader!!.getResource("librarian/$name.json")!!.readText(),
    ).jsonObject["response"]!!.jsonObject["body"].toString()

    @Test fun followTheMusicianOkFixtureListsStepsWithReasons() {
        val r = parsePaths(body("paths_follow_the_musician"))
        assertEquals("follow_the_musician", r.kind)
        assertEquals("ok", r.status)
        assertEquals("Woghenei", r.stops.first().name)
        assertTrue(r.stops.first().reason.contains("credited"))
        val reason = r.stops.first().reasons.first()
        assertEquals("Temare Haregu", reason.via?.name)
        assertEquals("Dèwèl", reason.anchor?.name)
        assertEquals("instrument", reason.evidence.first().relation)
        assertEquals("drums (drum set)", reason.evidence.first().role)
        assertEquals("source_explicit", reason.evidence.first().evidenceClass)
        assertEquals("exact_mbid", reason.evidence.first().matchQuality)
        assertTrue(r.view() is PathsView.Stops)
    }

    @Test fun sidemanToLeaderOkFixtureListsArtistStepsWithSidemanReason() {
        val r = parsePaths(body("paths_sideman_to_leader"))
        assertEquals("sideman_to_leader", r.kind)
        assertEquals("ok", r.status)
        assertEquals(null, r.truncated)
        assertEquals(listOf("محمد القصبجي"), r.stops.map { it.name })
        assertTrue(r.stops.all { it.type == "artist" })
        assertTrue(r.stops.first().reason.contains("recording"))
        assertEquals(21, r.stops.first().reasonCount)
        assertTrue(r.view() is PathsView.Stops)
    }

    @Test fun sidemanToLeaderTruncatedFixtureKeepsTheStopsNote() {
        val r = parsePaths(body("paths_sideman_to_leader_truncated"))
        assertEquals("ok", r.status)
        assertEquals("stops", r.truncated)
        assertEquals(30, r.stops.size)
        assertTrue(r.stops.all { it.type == "artist" && it.reason.isNotBlank() })
    }

    @Test fun labelCompositionAndSceneOkFixturesAllHaveSteps() {
        for (name in listOf("paths_label_path", "paths_composition_path", "paths_scene_path")) {
            val r = parsePaths(body(name))
            assertEquals(name, "ok", r.status)
            assertTrue(name, r.stops.isNotEmpty())
            assertTrue(name, r.stops.all { it.name.isNotBlank() && it.reason.isNotBlank() })
        }
    }

    @Test fun emptyFixturesSayNothingToShow() {
        for (name in listOf("paths_follow_the_musician_empty", "paths_sideman_to_leader_empty", "paths_label_path_empty", "paths_composition_path_empty", "paths_scene_path_empty")) {
            val r = parsePaths(body(name))
            assertEquals(name, "empty", r.status)
            assertTrue(name, r.stops.isEmpty())
            assertEquals(name, PathsView.Empty, r.view())
        }
    }

    @Test fun pathFixturesRetainAllReasonsAndTheirEvidence() {
        val sideman = parsePaths(body("paths_sideman_to_leader")).stops.first().reasons.first()
        assertEquals("release", sideman.via?.type)
        assertEquals("recording", sideman.anchor?.type)
        assertEquals(listOf("performer", "track_on", "release_artist"), sideman.evidence.map { it.relation })

        val label = parsePaths(body("paths_label_path")).stops.first().reasons.first()
        assertEquals("Mazzika", label.via?.name)
        assertEquals("Aref Menen", label.anchor?.name)
        assertEquals("MAZ CD 137", label.evidence.first().catalogueNumber)

        val composition = parsePaths(body("paths_composition_path")).stops.first().reasons.first()
        assertEquals("work", composition.via?.type)
        assertTrue(composition.evidence.any { it.role == "cover, live" })

        val scene = parsePaths(body("paths_scene_path")).stops.first().reasons.first()
        assertEquals("Jimma", scene.via?.name)
        assertEquals("begin area", scene.evidence.first().relation)
    }

    @Test fun presentationKeepsArtistsSeparateFromAlbumAndRecordingTitles() {
        val json = """{"kind":"composition_path","status":"ok","stops":[
            {"entity":{"canonical_name":"Cover title","type":"recording","owned":false},
             "presentation":{"title":"Cover artist","context":"Cover title"},
             "reason_count":1,"reasons":[{"code":"same_work","text":"another recording of the same work"}]}]}"""
        val stop = parsePaths(json).stops.single()
        assertEquals("Cover title", stop.name)
        assertEquals("Cover artist", stop.displayTitle)
        assertEquals("Cover title", stop.displayContext)
    }

    @Test fun truncatedRowsIsKeptForTheNote() {
        val json = """{"kind":"scene_path","status":"ok","truncated":"rows","stops":[
            {"entity":{"canonical_name":"A","type":"artist","owned":true},"reason_count":1,
             "reasons":[{"code":"shared_scene","text":"Shares a scene with a band in your library"}]}]}"""
        val r = parsePaths(json)
        assertEquals("rows", r.truncated)
        assertEquals(1, (r.view() as PathsView.Stops).response.stops.size)
    }

    @Test fun stopWithoutAReasonIsLeftOut() {
        val json = """{"kind":"label_path","status":"ok","stops":[
            {"entity":{"canonical_name":"Unexplained","type":"artist","owned":false},"reason_count":0,"reasons":[]},
            {"entity":{"canonical_name":"Explained","type":"artist","owned":false},"reason_count":1,
             "reasons":[{"code":"same_label","text":"Released on the same label"}]}]}"""
        assertEquals(listOf("Explained"), parsePaths(json).stops.map { it.name })
    }

    @Test fun okWithNoUsableStopsIsEmptyNotBlank() {
        assertEquals(PathsView.Empty, parsePaths("""{"kind":"label_path","status":"ok","stops":[]}""").view())
    }

    @Test fun bodyThatIsNotAnObjectIsEmpty() {
        val r = parsePaths("<html>down</html>")
        assertEquals("", r.status)
        assertEquals(PathsView.Empty, r.view())
    }

    @Test fun exactlyTheFivePathKindsAreOffered() {
        assertEquals(
            listOf("follow_the_musician", "sideman_to_leader", "label_path", "composition_path", "scene_path"),
            PathKind.entries.map { it.wire },
        )
    }

    @Test fun capabilityFixtureFromTheServerHasPathsOff() {
        // The server's recorded capabilities body (intelligence/contract-fixtures) has no populated paths feature.
        val text = javaClass.classLoader!!.getResource("capabilities_populated.json")!!.readText()
        assertFalse(pathsAvailableFrom(Json.parseToJsonElement(text).jsonObject["response"]!!.toString()))
    }

    @Test fun capabilityPathsFeatureDecidesTheEntry() {
        assertTrue(pathsAvailableFrom("""{"features":{"paths":{"available":true,"resource":"musicbrainz_slice","data_version":1}}}"""))
        assertFalse(pathsAvailableFrom("""{"features":{"paths":{"available":false,"reason":"not_populated"}}}"""))
        assertFalse(pathsAvailableFrom("not json"))
    }

    @Test fun statusesHaveHonestWords() {
        assertEquals(
            "The server can't build this path for the artist.",
            pathsFailure(ConnectionException(ConnectionFailure.Server(400, "parked: too little data"))).message,
        )
        assertEquals(
            "This artist isn't in the server's knowledge store yet.",
            pathsFailure(ConnectionException(ConnectionFailure.Server(404, "Unknown entity."))).message,
        )
        assertEquals(
            "The server rejected the request.",
            pathsFailure(ConnectionException(ConnectionFailure.Server(422, null))).message,
        )
        assertEquals(
            "The server couldn't read its knowledge store. Try again later.",
            pathsFailure(ConnectionException(ConnectionFailure.Server(502, null))).message,
        )
    }

    @Test fun savedCopyOnlyReadSaysItNeedsTheServer() {
        assertTrue(pathsFailure(CacheMiss()).message.contains("not saved on this phone"))
    }

    @Test fun unreachableServerKeepsTheConnectionMessage() {
        assertEquals(ConnectionFailure.Unreachable.message, pathsFailure(ConnectionException(ConnectionFailure.Unreachable)).message)
    }
}
