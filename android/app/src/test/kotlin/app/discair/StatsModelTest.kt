package app.discair

import app.discair.model.TasteResponse
import app.discair.model.parseTaste
import app.discair.ui.common.ChartState
import app.discair.ui.stats.AlbumStamp
import app.discair.ui.stats.StatsRange
import app.discair.ui.stats.StatsRead
import app.discair.ui.stats.StatsRules
import java.time.Instant
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Library stats (A7): the series and shares each chart draws; missing is never zero. */
class StatsModelTest {
    private val now = Instant.parse("2026-11-12T12:00:00Z")
    private fun daysAgo(d: Long): Instant = now.minusSeconds(d * 86_400)
    private fun taste(name: String): TasteResponse = parseTaste(
        Json.parseToJsonElement(javaClass.classLoader!!.getResource("$name.json")!!.readText()).jsonObject["response"].toString(),
    )

    private fun read(total: Int?, vararg stamps: AlbumStamp, complete: Boolean = true) = StatsRead(total, stamps.toList(), complete)
    private fun added(d: Long, year: Int? = null) = AlbumStamp(daysAgo(d), year)

    @Test fun `the last point of the collection is the server total and earlier points count back by added date`() {
        val r = read(10, added(1), added(40), added(100), added(400), added(800))
        val s = StatsRules.collection(r, StatsRange.OneYear, now)!!
        assertEquals(12, s.points.size)
        assertEquals(10.0, s.points.last().value, 0.0)
        // Everything added after the end of the first month of the window is out of the first point.
        assertTrue(s.points.first().value < s.points.last().value)
        assertEquals(s.points.map { it.value }.sorted(), s.points.map { it.value })
        assertEquals(10, s.total)
    }

    @Test fun `three months is thirteen weekly points`() {
        val s = StatsRules.collection(read(5, added(3), added(20), added(200)), StatsRange.ThreeMonths, now)!!
        assertEquals(13, s.points.size)
        assertEquals(5.0, s.points.last().value, 0.0)
        assertEquals(3.0, s.points.first().value, 0.0) // the albums added in the 84 days are not counted back there
    }

    @Test fun `five years is sixty monthly points and all runs from the oldest album`() {
        val r = read(4, added(1), added(30), added(500), added(1000))
        assertEquals(60, StatsRules.collection(r, StatsRange.FiveYears, now)!!.points.size)
        val all = StatsRules.collection(r, StatsRange.All, now)!!
        assertEquals(1.0, all.points.first().value, 0.0)
        assertEquals(4.0, all.points.last().value, 0.0)
    }

    @Test fun `a very long history is bucketed by three months past sixty buckets`() {
        val s = StatsRules.collection(read(2, added(1), added(365 * 8L)), StatsRange.All, now)!!
        assertTrue(s.points.size <= 40)
    }

    @Test fun `no total, a partial read or no added dates is not charted and says why`() {
        assertNull(StatsRules.collection(read(null, added(1)), StatsRange.OneYear, now))
        assertNull(StatsRules.collection(read(5, added(1), complete = false), StatsRange.OneYear, now))
        assertNull(StatsRules.collection(read(5, AlbumStamp(null, 1990)), StatsRange.OneYear, now))
        assertTrue(StatsRules.collectionState(null, read(null, added(1)), false) is ChartState.Unavailable)
        assertTrue(StatsRules.collectionState(null, read(5, added(1), complete = false), false) is ChartState.Unavailable)
        assertTrue(StatsRules.collectionState(null, read(5, AlbumStamp(null, 1990)), false) is ChartState.Insufficient)
        assertEquals(ChartState.Loading, StatsRules.collectionState(null, null, true))
    }

    @Test fun `decades are shares of dated albums, and listens are drawn only from a sound recent window`() {
        val r = read(4, added(1, 1991), added(2, 1994), added(3, 1977), added(4, null))
        val withoutTaste = StatsRules.decades(r, null)!!
        assertFalse(withoutTaste.hasListens)
        assertEquals(listOf("1970s", "1990s"), withoutTaste.rows.map { it.label })
        assertEquals(100.0 / 3, withoutTaste.rows[0].first, 1e-9)
        assertEquals(200.0 / 3, withoutTaste.rows[1].first, 1e-9)
        val withTaste = StatsRules.decades(r, taste("taste_context").profiles)!!
        assertTrue(withTaste.hasListens)
        assertEquals(listOf("1970s", "1980s", "1990s"), withTaste.rows.map { it.label })
        assertEquals(0.0, withTaste.rows[0].second, 0.0)
        assertEquals(50.625, withTaste.rows[2].second, 1e-9)
        assertEquals(100.0, withTaste.rows.sumOf { it.first }, 1e-9)
        // taste_rich flags its era dimension low-sample: albums only, no listens drawn from it.
        assertFalse(StatsRules.decades(r, taste("taste_rich").profiles)!!.hasListens)
    }

    @Test fun `a library with no years has no decade chart`() = assertNull(StatsRules.decades(read(1, AlbumStamp(daysAgo(1), null)), null))

    @Test fun `thin taste windows are not drawn as listens`() {
        val r = read(1, added(1, 1991))
        assertFalse(StatsRules.decades(r, taste("taste_thin_window").profiles)!!.hasListens)
    }

    @Test fun `time of day comes from the servers context lens in day order`() {
        val t = taste("taste_context")
        assertEquals("UTC", t.timeOfDayZone)
        val points = StatsRules.timeOfDay(t.timeOfDay)!!
        assertEquals(listOf("Night", "Morning", "Afternoon", "Evening"), points.map { it.label })
        // 60, 120, 90, 200 of 470
        assertEquals(listOf("13%", "26%", "19%", "43%"), points.map { it.display })
        assertEquals(ChartState.Ready, StatsRules.timeOfDayState(points, false))
    }

    @Test fun `time of day not served is not available, not zero`() {
        assertNull(taste("taste_empty").timeOfDay)
        assertNull(StatsRules.timeOfDay(null))
        assertTrue(StatsRules.timeOfDayState(null, false) is ChartState.Unavailable)
        assertTrue(StatsRules.timeOfDayState(StatsRules.timeOfDay(mapOf("night" to 0)), false) is ChartState.Insufficient)
        assertEquals(ChartState.Loading, StatsRules.timeOfDayState(null, true))
    }

    @Test fun `subtitles name the period and the zone`() {
        val s = StatsRules.collection(read(10, added(1), added(40)), StatsRange.OneYear, now)!!
        assertEquals("Albums in your library · Dec 2025 to today", StatsRules.collectionSubtitle(s))
        assertEquals("Share of listens by time of day, UTC · all time", StatsRules.timeOfDaySubtitle("UTC"))
        assertEquals("12 November 2026", StatsRules.dateWords(java.time.LocalDate.of(2026, 11, 12)))
    }
}
