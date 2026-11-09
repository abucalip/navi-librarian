package app.discair

import app.discair.model.TasteCard
import app.discair.model.TasteCardState
import app.discair.model.parseTaste
import app.discair.model.parseTasteRefresh
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Server V2 Phase 6 taste presentation: the taste profiles decode from the server's own fixtures; the app adds no claims. */
class TasteTest {
    private fun body(name: String): String = Json.parseToJsonElement(
        javaClass.classLoader!!.getResource("$name.json")!!.readText(),
    ).jsonObject["response"].toString()

    @Test fun richFixtureDrawsTheServersHeadlineAndListedShifts() {
        val p = parseTaste(body("taste_rich")).profiles!!
        val state = TasteCard.state(p) as TasteCardState.Ready
        assertEquals("More jazz, less rock lately.", state.headline.text)
        assertEquals("recent", state.headline.window)
        assertEquals(listOf("jazz", "rock"), state.movers.map { it.value }.sorted())
        assertTrue(state.movers.all { it.window == "recent" })
        assertEquals(20, state.allTimeListens)
    }

    @Test fun moversAreBiggestMoveFirstAndOnlyThoseListed() {
        val p = parseTaste(body("taste_sparse_dimension")).profiles!!
        val movers = p.shifts("recent")
        assertTrue(movers.isNotEmpty())
        val sizes = movers.map { kotlin.math.abs(it.toShare - it.fromShare) }
        assertEquals(sizes.sortedDescending(), sizes)
        assertTrue(movers.all { it in p.shifts })
    }

    @Test fun thinRecentWindowFallsBackToTheServersPastYearHeadline() {
        val p = parseTaste(body("taste_thin_window")).profiles!!
        assertTrue(p.window("recent")!!.lowSample)
        val state = TasteCard.state(p) as TasteCardState.Ready
        assertEquals("More jazz, less rock this past year.", state.headline.text)
        assertEquals("Past year", TasteCard.windowLabel(state.headline.window, p.recentDays))
    }

    @Test fun lowSampleDimensionIsKeptAsFlaggedNotDropped() {
        val p = parseTaste(body("taste_sparse_dimension")).profiles!!
        val recent = p.window("recent")!!
        assertTrue(recent.isLowSample("genre"))
        assertFalse(recent.isLowSample("era"))
        assertTrue(recent.isLowSample("a_dimension_the_server_never_sent"))
    }

    @Test fun noSoundWindowIsProgressNotAFinding() {
        val p = parseTaste(body("taste_empty")).profiles!!
        assertNull(p.headline)
        val state = TasteCard.state(p) as TasteCardState.Thin
        assertEquals(2, state.have)
        assertEquals(4, state.need)
        assertEquals(0.5, TasteCard.progress(state.have, state.need), 0.0)
    }

    @Test fun notComputedYetIsEmpty() {
        assertEquals(TasteCardState.Empty, TasteCard.state(parseTaste("""{"profiles":null,"context":null,"data_version":0,"generation":0}""").profiles))
        assertEquals(TasteCardState.Empty, TasteCard.state(parseTaste("[]").profiles))
        assertEquals(TasteCardState.Empty, TasteCard.state(null))
    }

    @Test fun missingFlagsAndBadRowsAreForgiving() {
        val p = parseTaste(
            """{"profiles":{"headline":{"text":"  Leaning into jazz lately. ","kind":"up","window":"recent"},
            "windows":{"recent":{"listens":60,"dimensions":{"genre":[{"value":"jazz","count":3,"share":0.5},{"count":1}]}}},
            "shifts":[{"window":"recent","dimension":"genre","value":"jazz","direction":"up","from_share":0.1,"to_share":0.5},"junk",{"window":"recent"}]},
            "data_version":3,"generation":2}""",
        )
        assertEquals(3, p.dataVersion)
        val profiles = p.profiles!!
        assertEquals("Leaning into jazz lately.", profiles.headline!!.text)
        assertTrue(profiles.window("recent")!!.lowSample)          // an absent flag means not sound
        assertEquals(1, profiles.window("recent")!!.entries("genre").size)
        assertEquals(1, profiles.shifts.size)
        assertEquals(90, profiles.recentDays)
        assertEquals(50, profiles.minListens)
    }

    @Test fun progressAndPercentStayInRange() {
        assertEquals(1.0, TasteCard.progress(80, 50), 0.0)
        assertEquals(0.0, TasteCard.progress(-5, 50), 0.0)
        assertEquals(1.0, TasteCard.progress(0, 0), 0.0)
        assertEquals(30, TasteCard.percent(0.3))
        assertEquals(100, TasteCard.percent(1.0))
    }

    @Test fun refreshAnswersDecode() {
        val r = parseTasteRefresh("""{"state":"too_soon","changed":false,"retry_after":1800.5,"run_id":4}""")
        assertEquals("too_soon", r.state)
        assertFalse(r.changed)
        assertEquals(1800.5, r.retryAfter, 0.0)
        assertTrue(parseTasteRefresh("""{"state":"refreshed","changed":true}""").changed)
        assertEquals("failed", parseTasteRefresh("not an object").state)
    }
}
