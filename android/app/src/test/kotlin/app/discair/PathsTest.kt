package app.discair

import app.discair.data.CacheMiss
import app.discair.model.PathAlbum
import app.discair.model.PathCreditFact
import app.discair.model.PathKind
import app.discair.model.Span
import app.discair.model.creditPhrase
import app.discair.model.eraOf
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

    private val seeded get() = kotlin.random.Random(7)
    private fun firstPane(fixture: String, kind: PathKind, start: String = "Start") =
        parsePaths(body(fixture)).stops.first().pane(kind, start, seeded)
    private fun text(spans: List<Span>) = spans.joinToString("") { it.text }

    private fun credit(via: String, anchor: String, mine: PathCreditFact?, theirs: PathCreditFact?) =
        PathReason("t", "shared_musician", PathRef(via, "artist", "m-$via"), PathRef(anchor, "recording", null), credits = listOfNotNull(mine, theirs))

    @Test fun followStoryNamesTheMusicianTheirInstrumentAndTheSongs() {
        val drums = PathCreditFact("instrument", "drums (drum set)")
        val stop = PathStop("Take Five", "recording", false, 3, "r", reasons = listOf(
            credit("Joe Morello", "Song A", drums, drums), credit("Joe Morello", "Song B", drums, drums), credit("Joe Morello", "Song C", drums, drums),
        ))
        val pane = stop.pane(PathKind.FollowTheMusician, "Dave", seeded) as PathPane.Song
        assertEquals("Joe Morello", pane.musician?.name)
        val story = text(pane.story)
        assertTrue(story, story.startsWith("Joe Morello, who plays drums on "))
        assertTrue(story, story.contains(" by Dave, also plays drums on Take Five."))
        assertTrue(story, listOf("Song A", "Song B", "Song C").all { story.contains(it) })
        assertTrue(pane.story.filter { it.title }.map { it.text }.contains("Take Five"))
    }

    @Test fun followStoryNamesTheArtistOfTheSongBeingSuggested() {
        val tuba = PathCreditFact("instrument", "tuba")
        val stop = PathStop("Satellite of Love", "recording", false, 1, "r", albumArtist = "Lou Reed",
            reasons = listOf(credit("Herbie Flowers", "Let's Dance", tuba, tuba)))
        val story = text((stop.pane(PathKind.FollowTheMusician, "David Bowie", seeded) as PathPane.Song).story)
        assertTrue(story, story.endsWith("also plays tuba on Satellite of Love by Lou Reed."))
    }

    @Test fun followStoryAdaptsToVocalsAndOtherCredits() {
        val sing = PathCreditFact("vocal", "lead vocals")
        val vocal = PathStop("S", "recording", false, 1, "r", reasons = listOf(credit("Ella", "A", sing, sing)))
        assertTrue(text((vocal.pane(PathKind.FollowTheMusician, "X", seeded) as PathPane.Song).story).startsWith("Ella, who sings on A by X, also sings on S"))
        val made = PathCreditFact("producer", null)
        val producer = PathStop("S", "recording", false, 1, "r", reasons = listOf(credit("Rudy", "A", made, made)))
        assertTrue(text((producer.pane(PathKind.FollowTheMusician, "X", seeded) as PathPane.Song).story).startsWith("Rudy, who produces A by X, also produces S"))
        assertEquals("is credited on", creditPhrase(null, past = false))
        assertEquals("plays guitar on", creditPhrase(PathCreditFact("instrument", "additional, guitar"), past = false))
    }

    @Test fun followPaneVariesWhichMusicianIsShown() {
        val one = PathCreditFact("instrument", "piano")
        val stop = PathStop("S", "recording", false, 6, "r", reasons = (1..6).map { credit("Player $it", "Song $it", one, one) })
        val shown = (1..40).map { (stop.pane(PathKind.FollowTheMusician, "X", kotlin.random.Random(it)) as PathPane.Song).musician?.name }.toSet()
        assertTrue(shown.size > 1)
    }

    @Test fun followPaneKeepsTheAlbumAndItsFallbackCovers() {
        val stop = PathStop("Song", "recording", false, 1, "r", album = "Red Clay", albumArtist = "Freddie Hubbard")
        val pane = stop.pane(PathKind.FollowTheMusician) as PathPane.Song
        assertEquals(listOf(PathAlbum("Red Clay", "Freddie Hubbard")), pane.covers)
        val more = parsePaths("""{"kind":"follow_the_musician","status":"ok","stops":[{"entity":{"canonical_name":"S","type":"recording"},
            "presentation":{"album":"A","album_artist":"B","albums":[{"album":"A","album_artist":"B"},{"album":"A (Deluxe)","album_artist":"B"}]},
            "reasons":[{"code":"shared_musician","text":"x","via":{"canonical_name":"P","type":"artist"},"anchor":{"canonical_name":"M","type":"recording"},
              "evidence":[{"relation":"instrument","role":"bass"},{"relation":"vocal","role":null}]}]}]}""").stops.single()
        assertEquals(2, more.albums.size)
        assertEquals(listOf(PathCreditFact("instrument", "bass"), PathCreditFact("vocal", null)), more.reasons.single().credits)
    }

    @Test fun sidemanPaneListsTheRecordsWithHowTheStartArtistWorkedOnThem() {
        val pane = firstPane("paths_sideman_to_leader", PathKind.SidemanToLeader) as PathPane.Leader
        assertEquals("Artist", pane.typeLabel)
        assertEquals(1, pane.records.size) // three reasons, all on one release
        assertEquals("محمد القصبجي", pane.records.first().release)
        assertEquals("أيقظت في عواطفي", pane.records.first().carries)
        assertEquals("4b2d8124-1b45-48ee-8b84-da106b7f5eba", pane.mbid)
        assertEquals("played on", creditPhrase(PathCreditFact("instrument", null), past = true))
        assertEquals("played trumpet on", creditPhrase(PathCreditFact("instrument", "trumpet"), past = true))
        assertEquals("produced", creditPhrase(PathCreditFact("producer", null), past = true))
    }

    @Test fun labelPanePicksALabelAndTheLibraryAlbumThatSharesIt() {
        val pane = firstPane("paths_label_path", PathKind.LabelPath) as PathPane.LabelAlbum
        assertEquals("Mazzika", pane.reason?.label)
        assertEquals("Aref Menen", pane.reason?.anchor)
        assertFalse(pane.reason!!.related)
    }

    @Test fun labelPaneMarksARelatedLabel() {
        val stop = PathStop("Album", "release", false, 1, "r", reasons = listOf(PathReason("t", "related_label", PathRef("Blue Note", "label", null), PathRef("Mine", "release", null))))
        assertTrue((stop.pane(PathKind.LabelPath) as PathPane.LabelAlbum).reason!!.related)
    }

    @Test fun compositionPaneNamesTheWorkAndKeepsTheRecording() {
        val stop = parsePaths(body("paths_composition_path")).stops.first()
        val pane = stop.pane(PathKind.CompositionPath, "Start", seeded) as PathPane.Recording
        assertEquals("Yègellé tezeta", pane.work)
        assertEquals("Ethanopium (live at Snowy's)", pane.track)
        assertFalse(pane.related)
        // The server gives no album for a recording, so only the performer can be opened.
        assertTrue(stop.links(PathKind.CompositionPath).none { it.album })
    }

    @Test fun scenePaneShowsTheEraTheTwoCareersShare() {
        val pane = firstPane("paths_scene_path", PathKind.ScenePath) as PathPane.Place
        assertEquals("Jimma", pane.place)
        assertEquals("ሙላቱ አስታጥቄ", pane.anchor)
        assertEquals(10, pane.years)
        assertEquals(null, pane.era) // an older server sends no years
        assertEquals("1960s", eraOf(1962, 1968))
        assertEquals("1970s", eraOf(1968, 1976))
        val stop = parsePaths("""{"kind":"scene_path","status":"ok","stops":[{"entity":{"canonical_name":"A","type":"artist"},
            "presentation":{"begin_year":1965,"anchor_begin_year":1961},"reasons":[{"code":"same_area","text":"from Jimma, within 10 years","via":{"canonical_name":"Jimma","type":"area"}}]}]}""").stops.single()
        assertEquals("1960s", (stop.pane(PathKind.ScenePath) as PathPane.Place).era)
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
