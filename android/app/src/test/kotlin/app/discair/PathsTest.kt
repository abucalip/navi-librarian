package app.discair

import app.discair.data.CacheMiss
import app.discair.model.PathKind
import app.discair.model.PathLink
import app.discair.model.PathPane
import app.discair.model.PathReason
import app.discair.model.PathRef
import app.discair.model.PathStop
import app.discair.model.links
import app.discair.model.pane
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

    // ---- detail panes: each path shows its own shape, from the fields the server sent

    private fun firstPane(fixture: String, kind: PathKind) = parsePaths(body(fixture)).stops.first().pane(kind)

    @Test fun followPaneNamesTheMusicianInEachReasonAndCountsTheRest() {
        val pane = firstPane("paths_follow_the_musician", PathKind.FollowTheMusician) as PathPane.Song
        assertEquals("Woghenei", pane.title)
        assertEquals(3, pane.credits.size)
        assertEquals("Temare Haregu", pane.credits.first().who?.name)
        assertTrue(pane.credits.first().text.startsWith("Temare Haregu"))
        assertEquals(24, pane.moreReasons) // 27 reasons, 3 shown
    }

    @Test fun followPaneOpensTheAlbumFirstAndKeepsTheAlbumArtistNeutral() {
        val stop = PathStop("Song", "recording", false, 1, "r", album = "Red Clay", albumArtist = "Freddie Hubbard")
        val pane = stop.pane(PathKind.FollowTheMusician) as PathPane.Song
        assertEquals(PathLink(true, "Red Clay", "Freddie Hubbard"), pane.primary)
        assertEquals(listOf(PathLink(false, "Freddie Hubbard")), pane.secondary)
        // No album: the artist is the main button, and nothing repeats under it.
        val bare = PathStop("Song", "recording", false, 1, "r", albumArtist = "Freddie Hubbard").pane(PathKind.FollowTheMusician)
        assertEquals(PathLink(false, "Freddie Hubbard"), bare.primary)
        assertTrue(bare.secondary.isEmpty())
    }

    @Test fun sidemanPaneListsTheRecordsWithTheirRecording() {
        val pane = firstPane("paths_sideman_to_leader", PathKind.SidemanToLeader) as PathPane.Leader
        assertEquals("Artist", pane.typeLabel)
        assertEquals(1, pane.records.size) // three reasons, all on one release
        assertEquals("محمد القصبجي", pane.records.first().release)
        assertEquals("أيقظت في عواطفي", pane.records.first().carries)
        assertEquals(PathLink(false, "محمد القصبجي", null, "4b2d8124-1b45-48ee-8b84-da106b7f5eba"), pane.primary)
        assertEquals(18, pane.moreReasons) // 21 reasons, 3 sent
    }

    @Test fun labelPaneNamesTheLabelAndTheLibraryAlbumThatSharesIt() {
        val pane = firstPane("paths_label_path", PathKind.LabelPath) as PathPane.LabelAlbum
        assertEquals("Mazzika", pane.reasons.single().label)
        assertEquals("Aref Menen", pane.reasons.single().anchor)
        assertFalse(pane.reasons.single().related)
        assertEquals(0, pane.moreReasons)
    }

    @Test fun labelPaneKeepsAnAlbumWithoutItsArtistUnopened() {
        val stop = PathStop("Album", "release", false, 1, "r", reasons = listOf(PathReason("t", "related_label", PathRef("Blue Note", "label", null), PathRef("Mine", "release", null))))
        val pane = stop.pane(PathKind.LabelPath) as PathPane.LabelAlbum
        assertEquals(null, pane.primary)
        assertTrue(pane.reasons.single().related)
    }

    @Test fun compositionPaneSetsTheWorkBetweenYourRecordingAndThisOne() {
        val stop = parsePaths(body("paths_composition_path")).stops.first()
        val pane = stop.pane(PathKind.CompositionPath) as PathPane.Recording
        assertEquals("Yègellé tezeta", pane.work)
        assertEquals("Yègellé tezeta", pane.yours)
        assertEquals("Ethanopium (live at Snowy's)", pane.track)
        assertFalse(pane.related)
        assertEquals(1, pane.moreReasons)
        // The server gives no album for a recording, so only the performer can be opened.
        assertTrue(stop.links(PathKind.CompositionPath).none { it.album })
    }

    @Test fun scenePaneSplitsThePlaceAndTheEra() {
        val pane = firstPane("paths_scene_path", PathKind.ScenePath) as PathPane.Place
        assertEquals("Jimma", pane.place)
        assertEquals("ሙላቱ አስታጥቄ", pane.anchor)
        assertEquals(10, pane.years)
    }

    @Test fun scenePaneWithUnfamiliarWordingKeepsTheServerSentence() {
        val stop = PathStop("Artist", "artist", false, 1, "r", reasons = listOf(PathReason("from Jimma, a town", "same_area", PathRef("Jimma", "area", null), PathRef("Start", "artist", null))))
        val pane = stop.pane(PathKind.ScenePath) as PathPane.Place
        assertEquals(null, pane.years)
        assertEquals("from Jimma, a town", pane.sentence)
    }

    @Test fun linksKeepTheOrderTheSheetAlwaysOffered() {
        val stop = PathStop(
            "Song", "recording", false, 2, "r", album = "Red Clay", albumArtist = "Freddie Hubbard",
            reasons = listOf(
                PathReason("t", "shared_musician", PathRef("Ron Carter", "artist", "m1"), null),
                PathReason("t", "shared_musician", PathRef("Ron Carter", "artist", "m1"), null),
            ),
        )
        assertEquals(
            listOf(PathLink(false, "Ron Carter", null, "m1"), PathLink(true, "Red Clay", "Freddie Hubbard"), PathLink(false, "Freddie Hubbard")),
            stop.links(PathKind.FollowTheMusician),
        )
    }

    @Test fun followPaneWithoutAnAlbumOpensTheFirstMusicianTheReasonsName() {
        val pane = firstPane("paths_follow_the_musician", PathKind.FollowTheMusician) as PathPane.Song
        assertEquals(PathLink(false, "Temare Haregu", null, pane.credits.first().who?.mbid), pane.primary)
        assertTrue(pane.secondary.isEmpty())
    }

    @Test fun anchorAlbumAndArtistComeFromTheServerWhenItSendsThem() {
        val body = """{"kind":"composition_path","status":"ok","stops":[{"entity":{"canonical_name":"Cover","type":"recording","owned":false},
            "reason_count":1,"presentation":{"title":"X","artist":"Cover artist","album":"Cover LP","album_artist":"Cover LP Artist"},
            "reasons":[{"code":"same_work","text":"another recording of Song","via":{"canonical_name":"Song","type":"work"},
            "anchor":{"canonical_name":"Mine","type":"recording"},"anchor_presentation":{"album":"Mine LP","album_artist":"Me"}}]}]}"""
        val pane = parsePaths(body).stops.first().pane(PathKind.CompositionPath) as PathPane.Recording
        assertEquals("Mine LP", pane.yoursAlbum)
        assertEquals("Me", pane.yoursArtist)
        assertEquals("Cover LP", pane.album)
        assertEquals("Cover LP Artist", pane.albumArtist)
        // An older server sends neither: the pane has no album to look a cover up by.
        val old = firstPane("paths_composition_path", PathKind.CompositionPath) as PathPane.Recording
        assertEquals(null, old.yoursAlbum)
        assertEquals(null, old.album)
    }
}
