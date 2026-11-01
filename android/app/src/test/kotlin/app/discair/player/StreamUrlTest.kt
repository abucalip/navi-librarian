package app.discair.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class StreamUrlTest {
    private var n = 0
    private fun builder(base: String = "https://navi.ts.net") =
        StreamUrlBuilder(base, "owner", "hunter2") { "salt${n++}" }

    @Test fun originalHasNoQualityParameters() {
        val url = builder().build("abc123")
        assertEquals("https://navi.ts.net/rest/stream", url.toString().substringBefore('?'))
        assertEquals("abc123", url.queryParameter("id"))
        assertNull(url.queryParameter("maxBitRate"))
        assertNull(url.queryParameter("format"))
    }

    @Test fun passwordIsNeverInTheUrl() {
        val text = builder().build("abc123").toString()
        assertFalse(text.contains("hunter2"))
        assertEquals(app.discair.net.Subsonic.token("hunter2", "salt0"), StreamUrlBuilder("https://navi.ts.net", "owner", "hunter2") { "salt0" }.build("x1").queryParameter("t"))
    }

    @Test fun freshSaltForEveryUrl() {
        val b = builder()
        assertTrue(b.build("a").queryParameter("s") != b.build("a").queryParameter("s"))
    }

    @Test fun allowedBitRatesAndFormatsAreEmitted() {
        for (rate in ALLOWED_BIT_RATES) {
            assertEquals(rate.toString(), builder().build("a", StreamQuality(rate)).queryParameter("maxBitRate"))
        }
        assertEquals("mp3", builder().build("a", format = TranscodeFormat.Mp3).queryParameter("format"))
        assertEquals("opus", builder().build("a", format = TranscodeFormat.Opus).queryParameter("format"))
    }

    @Test fun unknownBitRateIsRefused() {
        for (bad in listOf(0, 1, 100, 321, -1, 999)) {
            assertThrows(IllegalArgumentException::class.java) { StreamQuality(bad) }
        }
    }

    @Test fun badIdsAreRefused() {
        for (id in listOf("", " ", "a/b", "..", "a b", "a&format=raw", "a?x=1", "a\nb", "é", "x".repeat(129))) {
            assertThrows("id <$id>", IllegalArgumentException::class.java) { builder().build(id) }
        }
    }

    @Test fun injectedParametersCannotReachTheUrl() {
        // The only id characters allowed cannot add a parameter.
        assertThrows(IllegalArgumentException::class.java) { builder().build("a&maxBitRate=1") }
    }

    @Test fun cleartextAddressIsRefused() {
        assertThrows(IllegalArgumentException::class.java) { builder("http://navi.ts.net").build("a") }
        assertThrows(IllegalArgumentException::class.java) { builder("not a url").build("a") }
    }

    @Test fun redactionRemovesCredentialValues() {
        val url = builder().build("abc123").toString()
        val cleaned = redactSecrets("Unable to connect to $url, retry")
        assertFalse(cleaned.contains("salt"))
        assertFalse(cleaned.contains(app.discair.net.Subsonic.token("hunter2", "salt0")))
        assertFalse(cleaned.contains("owner"))
        assertTrue(cleaned.contains("id=abc123"))
        assertEquals("", redactSecrets(null))
    }
}
