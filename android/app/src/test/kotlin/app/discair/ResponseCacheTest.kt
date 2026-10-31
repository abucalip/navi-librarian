package app.discair

import app.discair.data.FileResponseCache
import java.nio.file.Files
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ResponseCacheTest {
    private fun dir() = Files.createTempDirectory("cache").toFile().also { it.deleteOnExit() }

    @Test fun storesAndReadsBackBodyAndTime() {
        val cache = FileResponseCache(dir(), now = { 1234L })
        assertNull(cache.get("k"))
        assertFalse(cache.hasContent())
        cache.put("k", "{\"a\":1}\nsecond line")
        val got = cache.get("k")!!
        assertEquals("{\"a\":1}\nsecond line", got.body)
        assertEquals(1234L, got.savedAtMillis)
        assertTrue(cache.hasContent())
    }

    @Test fun newerAnswerReplacesOlder() {
        val cache = FileResponseCache(dir())
        cache.put("k", "old"); cache.put("k", "new")
        assertEquals("new", cache.get("k")!!.body)
    }

    @Test fun clearRemovesEverything() {
        val cache = FileResponseCache(dir())
        cache.put("a", "1"); cache.put("b", "2")
        cache.clear()
        assertNull(cache.get("a"))
        assertFalse(cache.hasContent())
    }

    @Test fun oldestEntriesGoWhenOverTheLimit() {
        val d = dir()
        val cache = FileResponseCache(d, maxBytes = 100)
        cache.put("first", "x".repeat(60))
        d.listFiles()!!.forEach { it.setLastModified(1000) }
        cache.put("second", "y".repeat(60))
        assertNull(cache.get("first"))
        assertEquals("y".repeat(60), cache.get("second")!!.body)
    }

    @Test fun damagedEntryReadsAsMissing() {
        val d = dir()
        val cache = FileResponseCache(d)
        cache.put("k", "ok")
        d.listFiles()!!.single().writeText("not a time\nbody")
        assertNull(cache.get("k"))
    }
}
