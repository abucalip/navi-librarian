package app.discair

import app.discair.data.CacheMiss
import app.discair.model.PathKind
import app.discair.model.PathsView
import app.discair.model.heading
import app.discair.model.sentence
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
        assertEquals(29, r.stops.size) // 30 from the server, one of them the placeholder "[unknown]"
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

    @Test fun compositionNeverShowsATrackAsTheArtist() {
        val old = parsePaths("""{"kind":"composition_path","status":"ok","stops":[
            {"entity":{"canonical_name":"Cover title","type":"recording"},"reason_count":1,
             "reasons":[{"code":"same_work","text":"same work"}]}]}""").stops.single()
        assertEquals("Artist not listed", old.heading(PathKind.CompositionPath).title)
        assertEquals("Cover title", old.heading(PathKind.CompositionPath).detail)
        val new = parsePaths("""{"kind":"composition_path","status":"ok","stops":[
            {"entity":{"canonical_name":"Cover title","type":"recording"},"reason_count":1,
             "presentation":{"title":"Cover artist","context":"Cover title","artist":"Cover artist"},
             "reasons":[{"code":"same_work","text":"same work"}]}]}""").stops.single()
        assertEquals("Cover artist", new.heading(PathKind.CompositionPath).title)
    }

    @Test fun songsShowTheirAlbumAndAlbumsShowTheirArtist() {
        val song = parsePaths("""{"kind":"follow_the_musician","status":"ok","stops":[
            {"entity":{"canonical_name":"Song","type":"recording"},"reason_count":1,
             "presentation":{"title":"Player","context":"Anchor LP","album":"Song LP","album_artist":"The Band"},
             "reasons":[{"code":"shared_musician","text":"x","via":{"canonical_name":"Player","type":"artist","mbid":"m1"}}]}]}""").stops.single()
        assertEquals("Song", song.heading(PathKind.FollowTheMusician).title)
        assertEquals("Song LP", song.heading(PathKind.FollowTheMusician).detail)
        assertEquals("Player", song.reasons.single().via?.name)
        val album = parsePaths("""{"kind":"label_path","status":"ok","stops":[
            {"entity":{"canonical_name":"Album","type":"release"},"reason_count":1,
             "presentation":{"title":"Album","context":"A, B","album_artist":"A"},
             "reasons":[{"code":"same_label","text":"x"}]}]}""").stops.single()
        assertEquals("A", album.heading(PathKind.LabelPath).detail)
    }

    @Test fun compositionReasonNamesTheWorkAndTheLibraryRecording() {
        val r = parsePaths("""{"kind":"composition_path","status":"ok","stops":[
            {"entity":{"canonical_name":"Cover","type":"recording"},"reason_count":1,"reasons":[
             {"code":"same_work","text":"server text",
              "via":{"canonical_name":"Aranjuez","type":"work"},"anchor":{"canonical_name":"Aranjuez (Adagio)","type":"recording"}}]}]}""")
            .stops.single().reasons.single()
        assertEquals("Another recording of Aranjuez, the same work as Aranjuez (Adagio), a recording in your library.", r.sentence())
    }

    @Test fun sidemanNeverListsPlaceholderArtists() {
        val r = parsePaths("""{"kind":"sideman_to_leader","status":"ok","start":{"type":"group"},"stops":[
            {"entity":{"canonical_name":"[unknown]","type":"artist"},"reasons":[{"text":"x","code":"sideman_on"}]},
            {"entity":{"canonical_name":"Leader","type":"artist"},"reasons":[{"text":"x","code":"sideman_on"}]}]}""")
        assertEquals(listOf("Leader"), r.stops.map { it.name })
        assertEquals("group", r.startType)
    }

    @Test fun followTheMusicianKeepsOneRowPerArtistAndPerSong() {
        val r = parsePaths("""{"kind":"follow_the_musician","status":"ok","stops":[
            {"entity":{"canonical_name":"A","type":"recording"},"presentation":{"album_artist":"Band"},"reasons":[{"text":"x","code":"shared_musician"}]},
            {"entity":{"canonical_name":"B","type":"recording"},"presentation":{"album_artist":"band"},"reasons":[{"text":"x","code":"shared_musician"}]},
            {"entity":{"canonical_name":"Hush","type":"recording"},"reasons":[{"text":"x","code":"shared_musician"}]},
            {"entity":{"canonical_name":"hush","type":"recording"},"reasons":[{"text":"x","code":"shared_musician"}]}]}""")
        assertEquals(listOf("A", "Hush"), r.stops.map { it.name })
    }
}
