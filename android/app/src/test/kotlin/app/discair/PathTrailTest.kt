package app.discair

import app.discair.model.AlbumStep
import app.discair.model.AlbumStepReason
import app.discair.model.AlbumTab
import app.discair.model.PathCreditFact
import app.discair.model.PathKind
import app.discair.model.PathReason
import app.discair.model.PathRef
import app.discair.model.PathStop
import app.discair.model.TrailLink
import app.discair.model.groupByLink
import app.discair.model.parsePaths
import app.discair.model.shownOrder
import app.discair.model.toAlbumAnswer
import app.discair.model.trailLink
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** The link of each Paths tab and how steps group under their links (docs/pathsredesign.md, section 5). */
class PathTrailTest {
    private fun body(name: String): String = Json.parseToJsonElement(
        javaClass.classLoader!!.getResource("librarian/$name.json")!!.readText(),
    ).jsonObject["response"]!!.jsonObject["body"].toString()

    private fun ref(name: String, type: String = "person") = PathRef(name, type, null)

    private fun album(
        code: String, via: PathRef?, credits: List<PathCreditFact> = emptyList(), matchCount: Int = 0, name: String = "Album",
    ) = AlbumStep(
        album = name, artist = "Artist", year = null, albumId = null, detail = "Artist",
        reasons = listOf(AlbumStepReason(code, "sentence", via, ref("Mine", "release"), credits)), matchCount = matchCount,
    )

    private fun stop(code: String, via: PathRef?, name: String = "Step") = PathStop(
        name = name, type = "artist", owned = false, reasonCount = 1, reason = "sentence",
        reasons = listOf(PathReason("sentence", code, via, ref("Mine", "recording"))),
    )

    // ---- album links

    @Test fun studioCrewNamesThePersonAndTheRoleOfTheCreditOnTheStart() {
        fun link(relation: String?) = album("crew_on", ref("Fred Plaut"), listOfNotNull(relation?.let { PathCreditFact(it, null) }))
            .trailLink(AlbumTab.StudioCrew)
        assertEquals(TrailLink("Fred Plaut", "producer credit"), link("producer"))
        assertEquals(TrailLink("Fred Plaut", "engineer credit"), link("engineer"))
        assertEquals(TrailLink("Fred Plaut", "mixing credit"), link("mix"))
        assertEquals(TrailLink("Fred Plaut", "mastering credit"), link("mastering"))
        assertEquals(TrailLink("Fred Plaut", "production credit"), link(null)) // no evidence: the old wording
        assertEquals("Fred Plaut · producer credit", link("producer").text)
        assertEquals("Fred Plaut, producer credit", link("producer").spoken)
    }

    @Test fun studioCrewRoleComesFromTheRecordedServerAnswer() {
        val steps = parsePaths(body("paths_album_crew")).toAlbumAnswer().steps
        val links = steps.map { it.trailLink(AlbumTab.StudioCrew) }
        assertTrue(links.all { it.name == "Rudy van Gelder" })
        // The credit on the start comes first in the evidence: "mix" for the first reasons, so that is the role.
        assertEquals("mixing credit", links.first().kind)
    }

    @Test fun otherAlbumTabsNameTheViaAndTheKindOfLink() {
        assertEquals(TrailLink("Bob", "guest credit"), album("guest_on", ref("Bob")).trailLink(AlbumTab.GuestList))
        assertEquals(TrailLink("So What", "same work"), album("same_work", ref("So What", "work")).trailLink(AlbumTab.CoversAndSources))
        assertEquals(TrailLink("Nardis", "related work"), album("derived_work", ref("Nardis", "work")).trailLink(AlbumTab.CoversAndSources))
        assertEquals(TrailLink("Columbia", "same label"), album("same_period_label", ref("Columbia", "label")).trailLink(AlbumTab.SameYearSameScene))
        assertEquals(TrailLink("Paris", "same area"), album("same_period_area", ref("Paris", "area")).trailLink(AlbumTab.SameYearSameScene))
        assertEquals(TrailLink("Someone", "shared artist"), album("same_period_credit", ref("Someone")).trailLink(AlbumTab.SameYearSameScene))
        assertEquals(TrailLink("Van Gelder Studio", "recorded at"), album("recorded_at", ref("Van Gelder Studio", "place")).trailLink(AlbumTab.SameRoom))
        assertEquals(TrailLink("Fred Plaut", "production credit"), album("crew_on", ref("Fred Plaut")).trailLink(AlbumTab.ListenThroughGaps))
        assertEquals(TrailLink("Bob", "guest credit"), album("guest_on", ref("Bob")).trailLink(AlbumTab.ListenThroughGaps))
    }

    @Test fun neighboursByEarCountTheMatchedTracks() {
        val step = album("sonic_neighbour", null, matchCount = 3)
        assertEquals(TrailLink("3 of 5 tracks", "sound alike"), step.trailLink(AlbumTab.NeighboursByEar, seeds = 5))
        assertEquals(TrailLink("3 tracks", "sound alike"), step.trailLink(AlbumTab.NeighboursByEar, seeds = 0))
        assertEquals(TrailLink("1 track", "sound alike"), album("sonic_neighbour", null, matchCount = 1).trailLink(AlbumTab.NeighboursByEar))
    }

    @Test fun aStepWhoseFirstReasonNamesNothingShowsTheKindAlone() {
        val link = album("crew_on", null).trailLink(AlbumTab.StudioCrew)
        assertNull(link.name)
        assertEquals("Production credit", link.text)
        assertEquals("Production credit", link.spoken)
        val bare = AlbumStep("A", "B", null, null, "B", emptyList()).trailLink(AlbumTab.SameRoom)
        assertEquals("Recorded at", bare.text)
    }

    // ---- artist links

    @Test fun artistTabsBuildTheirLinkFromTheFirstReason() {
        assertEquals(TrailLink("Herbie Hancock", "musician"), stop("shared_musician", ref("Herbie Hancock")).trailLink(PathKind.FollowTheMusician))
        assertEquals(TrailLink("Cookin'", "a record they led"), stop("sideman_on", ref("Cookin'", "release")).trailLink(PathKind.SidemanToLeader))
        assertEquals(TrailLink("Columbia", "same label"), stop("same_label", ref("Columbia", "label")).trailLink(PathKind.LabelPath))
        assertEquals(TrailLink("Columbia", "related label"), stop("related_label", ref("Columbia", "label")).trailLink(PathKind.LabelPath))
        assertEquals(TrailLink("So What", "composed by Miles Davis"), stop("same_work", ref("So What", "work")).trailLink(PathKind.CompositionPath, "Miles Davis"))
        assertEquals(TrailLink("Nardis", "related work"), stop("related_work", ref("Nardis", "work")).trailLink(PathKind.CompositionPath, "Miles Davis"))
        assertEquals(TrailLink("St. Louis", "same place"), stop("same_area", ref("St. Louis", "area")).trailLink(PathKind.ScenePath))
    }

    @Test fun artistLinkFallsBackToTheKindAloneWhenTheReasonNamesNothingToLinkThrough() {
        assertEquals(TrailLink(null, "musician"), stop("shared_musician", null).trailLink(PathKind.FollowTheMusician))
        // A via that is not an artist cannot be the musician; one that is not a release is not the record.
        assertEquals(TrailLink(null, "musician"), stop("shared_musician", ref("A label", "label")).trailLink(PathKind.FollowTheMusician))
        assertEquals(TrailLink(null, "a record they led"), stop("sideman_on", ref("Someone")).trailLink(PathKind.SidemanToLeader))
        assertEquals("Musician", TrailLink(null, "musician").text)
    }

    @Test fun everyRecordedArtistFixtureGivesEveryStepALink() {
        for (kind in PathKind.entries) {
            val r = parsePaths(body("paths_${kind.wire}"))
            assertTrue("${kind.wire} has stops", r.stops.isNotEmpty())
            r.stops.forEach { assertTrue(it.trailLink(kind, "Start").kind.isNotBlank()) }
        }
    }

    // ---- grouping

    @Test fun stepsWithTheSameLinkShareOneGroupInOrderOfFirstAppearance() {
        val named = listOf("a" to "Columbia", "b" to "Prestige", "c" to "Columbia", "d" to "Blue Note", "e" to "Prestige")
        val groups = groupByLink(named) { TrailLink(it.second, "same label") }
        assertEquals(listOf("Columbia", "Prestige", "Blue Note"), groups.map { it.link.name })
        // Steps keep the server's order inside a group, and a step moves up to join its group (D1).
        assertEquals(listOf("a", "c"), groups[0].steps.map { it.item.first })
        assertEquals(listOf("b", "e"), groups[1].steps.map { it.item.first })
        assertEquals(listOf("a", "c", "b", "e", "d"), groups.shownOrder().map { it.item.first })
    }

    @Test fun sameNameWithAnotherKindIsAnotherLink() {
        val items = listOf("same work", "related work", "same work")
        val groups = groupByLink(items) { TrailLink("So What", it) }
        assertEquals(listOf("same work", "related work"), groups.map { it.link.kind })
        assertEquals(listOf(0, 2), groups[0].steps.map { it.index })
    }

    @Test fun aSavedStepIndexStillFindsItsStepAfterGrouping() {
        val items = listOf("Columbia", "Prestige", "Columbia", "Blue Note")
        val groups = groupByLink(items) { TrailLink(it, "same label") }
        val saved = 2 // an index into the server's list, not into the grouped order
        assertEquals("Columbia", groups.shownOrder().first { it.index == saved }.item)
        assertEquals(items.indices.toList(), groups.shownOrder().map { it.index }.sorted())
    }

    @Test fun noStepsMakeNoGroups() {
        assertTrue(groupByLink(emptyList<String>()) { TrailLink(it, "x") }.isEmpty())
    }
}
