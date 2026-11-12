package app.discair

import app.discair.model.AcquisitionJob
import app.discair.model.InsightCard
import app.discair.model.InsightLens
import app.discair.model.InsightReason
import app.discair.model.InsightSubject
import app.discair.model.InsightsResponse
import app.discair.ui.common.ChartState
import app.discair.ui.home.DashModule
import app.discair.ui.home.DashboardRules
import app.discair.ui.home.LibraryRead
import java.time.Instant
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DashboardModelTest {
    private val now = Instant.parse("2026-11-12T12:00:00Z")
    private fun daysAgo(d: Long): Instant = now.minusSeconds(d * 86_400)
    private fun job(status: String, album: String = "A") = AcquisitionJob("Artist", album, status, 1.0, null, JsonObject(emptyMap()))

    @Test fun `hero counts the last 30 days against the 30 before`() {
        val read = LibraryRead(1284, listOf(daysAgo(1), daysAgo(10), daysAgo(29), daysAgo(31), daysAgo(45), daysAgo(70)), complete = true)
        val h = DashboardRules.hero(read, now)!!
        assertEquals(1284, h.count); assertEquals(3, h.added30); assertEquals(2, h.addedBefore30)
        assertEquals("3 added in the last 30 days · 2 in the 30 before", DashboardRules.heroSentence(h))
        assertEquals("Up", DashboardRules.heroTrend(h))
    }

    @Test fun `hero is missing, not zero, without a total`() = assertNull(DashboardRules.hero(LibraryRead(null, emptyList(), true), now))

    @Test fun `hero is missing when the read stopped inside the 60 days`() =
        assertNull(DashboardRules.hero(LibraryRead(100, listOf(daysAgo(1), daysAgo(20)), complete = false), now))

    @Test fun `an empty library has a hero of zero albums and zero added`() {
        val h = DashboardRules.hero(LibraryRead(0, emptyList(), true), now)!!
        assertEquals(0, h.count); assertEquals(0, h.added30)
    }

    @Test fun `growth counts back from the total and ends at it`() {
        val read = LibraryRead(100, listOf(daysAgo(5), daysAgo(40), daysAgo(100)), complete = true)
        val g = DashboardRules.growth(read, now)!!
        assertEquals(12, g.size)
        assertEquals(100.0, g.last().value, 0.0)
        assertEquals("Nov", g.last().label)
        // Nothing was added in the oldest month and everything after it is subtracted: 100 minus the three added since.
        assertEquals(97.0, g.first().value, 0.0)
        assertTrue(g.zipWithNext().all { (a, b) -> b.value >= a.value })
    }

    @Test fun `growth is unavailable when the read is incomplete or has no total`() {
        assertNull(DashboardRules.growth(LibraryRead(100, emptyList(), complete = false), now))
        assertNull(DashboardRules.growth(LibraryRead(null, emptyList(), complete = true), now))
        assertTrue(DashboardRules.growthState(null, false) is ChartState.Unavailable)
        assertEquals(ChartState.Loading, DashboardRules.growthState(null, true))
    }

    @Test fun `arrivals show active and failed first and at most two`() {
        val rows = DashboardRules.arrivals(listOf(job("imported", "Done"), job("downloading", "Live"), job("slskd_error", "Bad"), job("importing", "Also")))
        assertEquals(2, rows.size)
        assertEquals(listOf("Live", "Bad"), rows.map { it.job.album })
        assertEquals(1, rows[0].stage)
        assertTrue(rows[1].failed)
    }

    @Test fun `arrived albums follow and a song is never a row`() {
        val song = AcquisitionJob("Artist", "S", "imported", 1.0, null, JsonObject(mapOf("kind" to kotlinx.serialization.json.JsonPrimitive("track"))))
        val rows = DashboardRules.arrivals(listOf(song, job("imported", "Hats")))
        assertEquals(listOf("Hats"), rows.map { it.job.album })
        assertEquals(4, rows[0].stage)
        assertTrue(rows[0].detail.endsWith("Arrived"))
    }

    @Test fun `no jobs means no arrivals rows`() {
        assertTrue(DashboardRules.arrivals(null).isEmpty())
        assertTrue(DashboardRules.arrivals(emptyList()).isEmpty())
    }

    @Test fun `waiting is missing until the picks are read`() {
        assertNull(DashboardRules.waiting(null, emptyList()))
        assertEquals(7, DashboardRules.waiting(7, listOf(job("imported"), job("imported", "B")))!!.picks)
        assertEquals(2, DashboardRules.waiting(7, listOf(job("imported"), job("imported", "B")))!!.arrived)
    }

    private fun card(kind: String, key: String) = InsightCard(
        kind, "Title $key", "", InsightSubject(key, "album", "T", "Artist"), listOf(InsightReason("r", emptyMap())), true, 1.0, null, null, emptyList(),
    )

    @Test fun `the insight rotates by day across enabled lenses and skips off lenses and dismissed cards`() {
        val response = InsightsResponse(
            mapOf(
                "forgotten_gem" to InsightLens(true, listOf(card("forgotten_gem", "a"), card("forgotten_gem", "b"))),
                "blind_spot" to InsightLens(false, listOf(card("blind_spot", "x"))),
                "anniversary" to InsightLens(true, listOf(card("anniversary", "c"))),
            ), 1, 1,
        )
        val d0 = DashboardRules.insightOfTheDay(response, emptySet(), 0)!!
        val d1 = DashboardRules.insightOfTheDay(response, emptySet(), 1)!!
        assertEquals("forgotten_gem", d0.kind); assertEquals("anniversary", d1.kind)
        assertEquals("anniversary", DashboardRules.insightOfTheDay(response, setOf("forgotten_gem|a", "forgotten_gem|b"), 0)!!.kind)
        assertNull(DashboardRules.insightOfTheDay(response, setOf("forgotten_gem|a", "forgotten_gem|b", "anniversary|c"), 0))
        assertNull(DashboardRules.insightOfTheDay(null, emptySet(), 0))
    }

    @Test fun `server line and banner say what is wrong in words`() {
        assertEquals("Server: all quiet", DashboardRules.serverLine(null))
        assertEquals("Server: needs attention", DashboardRules.serverLine("Downloads could not be read."))
        assertNull(DashboardRules.banner(""))
        assertEquals("x", DashboardRules.banner("x"))
    }

    @Test fun `the order of the modules matches 8 1`() {
        assertEquals(
            listOf("Hero", "Stats", "Pick", "Arrivals", "Taste", "Insight", "Numbers", "Shelves", "Genres", "Radio", "Server"),
            DashModule.phone.map { it.name },
        )
        assertEquals(DashModule.phone.toSet(), (DashModule.primary + DashModule.secondary).toSet())
    }
}
