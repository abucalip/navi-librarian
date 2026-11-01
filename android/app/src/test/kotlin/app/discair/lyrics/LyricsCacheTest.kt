package app.discair.lyrics

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class LyricsCacheTest {
    @get:Rule val tmp = TemporaryFolder()
    private var clock = 1_000_000_000L
    private var scope = "https://navi.ts.net|owner"

    private fun cache(maxEntries: Int = 300, maxBytes: Long = 5L * 1024 * 1024, dir: File = File(tmp.root, "lyrics")) =
        LyricsCache(dir, { scope }, maxEntries, maxBytes) { clock }
    private fun lyrics(text: String = "placeholder") = Lyrics(true, listOf(LyricLine(0, text), LyricLine(500, "b")))

    @Test fun missThenHit() {
        val c = cache()
        assertNull(c.get("a"))
        c.put("a", lyrics("one"))
        val hit = c.get("a")!!
        assertTrue(hit.lyrics!!.timed); assertEquals("one", hit.lyrics!!.lines.first().text); assertEquals(500L, hit.lyrics!!.lines[1].startMs)
    }

    @Test fun plainLyricsRoundTrip() {
        val c = cache(); c.put("a", Lyrics(false, listOf(LyricLine(null, "x"), LyricLine(null, ""))))
        val l = c.get("a")!!.lyrics!!
        assertFalse(l.timed); assertEquals(listOf("x", ""), l.lines.map { it.text })
    }

    @Test fun anotherServerOrUserNeverReadsIt() {
        val c = cache(); c.put("a", lyrics())
        scope = "https://other.ts.net|owner"; assertNull(c.get("a"))
        scope = "https://navi.ts.net|someone"; assertNull(c.get("a"))
        scope = "https://navi.ts.net|owner"; assertNotNull(c.get("a"))
    }

    @Test fun countLimitRemovesTheOldest() {
        val c = cache(maxEntries = 3)
        for (i in 1..5) { c.put("s$i", lyrics()); clock += 1000 }
        assertNull(c.get("s1")); assertNull(c.get("s2")); assertNotNull(c.get("s3")); assertNotNull(c.get("s5"))
    }

    @Test fun sizeLimitRemovesTheOldest() {
        val c = cache(maxBytes = 600)
        for (i in 1..6) { c.put("s$i", lyrics("x".repeat(100))); clock += 1000 }
        val files = File(tmp.root, "lyrics").listFiles()!!.filter { !it.name.endsWith(".tmp") }
        assertTrue(files.sumOf { it.length() } <= 600)
        assertNull(c.get("s1")); assertNotNull(c.get("s6"))
    }

    @Test fun clearEmptiesEverything() {
        val c = cache(); c.put("a", lyrics()); c.put("b", null)
        c.clear()
        assertNull(c.get("a")); assertNull(c.get("b")); assertTrue(File(tmp.root, "lyrics").listFiles().orEmpty().isEmpty())
    }

    @Test fun noneAnswerIsKeptForADayThenExpires() {
        val c = cache(); c.put("a", null)
        clock += DAY_MS - 1
        val hit = c.get("a")!!; assertNull(hit.lyrics)
        clock += 1
        assertNull(c.get("a"))
    }

    @Test fun foundEntryNeedsRefreshAfterADayButStillShows() {
        val c = cache(); c.put("a", lyrics())
        assertFalse(c.get("a")!!.needsRefresh)
        clock += DAY_MS
        val hit = c.get("a")!!
        assertTrue(hit.needsRefresh); assertNotNull(hit.lyrics)
    }

    @Test fun damagedEntryIsAMiss() {
        val c = cache(); c.put("a", lyrics())
        File(tmp.root, "lyrics").listFiles()!!.single().writeText("not json")
        assertNull(c.get("a"))
    }

    @Test fun cachedFilesDoNotNameTheSongOrServer() {
        val c = cache(); c.put("song-id-123", lyrics())
        val name = File(tmp.root, "lyrics").listFiles()!!.single().name
        assertFalse(name.contains("song-id-123")); assertFalse(name.contains("navi"))
    }
}
