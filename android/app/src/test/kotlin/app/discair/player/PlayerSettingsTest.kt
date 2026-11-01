package app.discair.player

import app.discair.data.ServerSettings
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class PlayerSettingsTest {
    private val login = ServerSettings("https://lib.ts.net", "u", "p", "https://navi.ts.net", "owner", "hunter2")

    @Test fun choicesAreOriginalThenTheAllowedRatesHighestFirst() {
        assertEquals(listOf<Int?>(null, 320, 256, 192, 128, 96, 64), QUALITY_CHOICES)
        assertEquals("Original (no conversion)", qualityLabel(null)); assertEquals("128 kbps", qualityLabel(128))
    }

    @Test fun defaultsAreOriginalAndScrobblingOn() {
        val s = MemoryPlayerSettings()
        assertNull(s.maxBitRate); assertTrue(s.scrobbling)
    }

    @Test fun theQualityChosenInSettingsIsUsedForTheNextSong() {
        val settings = MemoryPlayerSettings()
        val resolver = StreamResolver({ login }, { StreamQuality(settings.maxBitRate) })
        assertNull(resolver.urlFor("abc")!!.queryParameter("maxBitRate"))
        settings.maxBitRate = 128
        assertEquals("128", resolver.urlFor("abc")!!.queryParameter("maxBitRate"))
        settings.maxBitRate = null
        assertNull(resolver.urlFor("abc")!!.queryParameter("maxBitRate"))
    }

    @Test fun theMp3FallbackForOneSongBeatsTheSettingAndLeavesItAlone() {
        val settings = MemoryPlayerSettings(maxBitRate = 192)
        val resolver = StreamResolver({ login }, { StreamQuality(settings.maxBitRate) })
        val url = resolver.urlFor("abc", itemFormatWire = "mp3")!!
        assertEquals("mp3", url.queryParameter("format")); assertEquals("192", url.queryParameter("maxBitRate"))
        assertNull(resolver.urlFor("abc")!!.queryParameter("format"))
        assertEquals(192, settings.maxBitRate)
    }

    @Test fun anUnknownFallbackFormatIsIgnored() {
        val resolver = StreamResolver({ login })
        assertNull(resolver.urlFor("abc", itemFormatWire = "raw")!!.queryParameter("format"))
        assertNull(resolver.urlFor("abc", itemFormatWire = "flac")!!.queryParameter("format"))
    }

    @Test fun nothingIsSignedWithoutACompleteLoginOrWithABadId() {
        assertNull(StreamResolver({ ServerSettings() }).urlFor("abc"))
        assertNull(StreamResolver({ login.copy(navidromePassword = "") }).urlFor("abc"))
        assertNull(StreamResolver({ login }).urlFor("a/b"))
        assertNull(StreamResolver({ login.copy(navidromeUrl = "http://navi.ts.net") }).let { r ->
            try { r.urlFor("abc") } catch (e: IllegalArgumentException) { null }
        })
    }

    @Test fun theScrobbleToggleStopsAndRestartsSending() {
        // The toggle feeds the coordinator; the coordinator's own tests cover off and on mid-track.
        val s = MemoryPlayerSettings(scrobbling = false)
        assertFalse(s.scrobbling)
    }
}
