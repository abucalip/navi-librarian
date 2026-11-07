package app.discair

import app.discair.data.CacheMiss
import app.discair.model.parseSonic
import app.discair.model.sonicAvailableFrom
import app.discair.model.sonicFailure
import app.discair.net.ConnectionException
import app.discair.net.ConnectionFailure
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Server V2 sonic similarity: the recorded `GET /api/sonic/similar` payloads and the words the app shows. */
class SonicTest {
    private fun body(name: String): String = Json.parseToJsonElement(
        javaClass.classLoader!!.getResource("librarian/$name.json")!!.readText(),
    ).jsonObject["response"]!!.jsonObject["body"].toString()

    @Test fun similarFixtureKeepsTheServersOrderAndFields() {
        val r = parseSonic(body("sonic_similar"))
        assertEquals("ok", r.status)
        assertEquals(6, r.tracks.size)
        assertTrue(r.tracks.all { it.songId.isNotBlank() && it.title.isNotBlank() && it.albumId.isNotBlank() })
        assertTrue(r.tracks.first().durationSec > 0)
    }

    @Test fun songWithoutAnalysisDataIsAnEmptyAnswer() {
        val r = parseSonic(body("sonic_similar_empty"))
        assertEquals("empty", r.status)
        assertTrue(r.tracks.isEmpty())
    }

    @Test fun pathStepsCarryNoScore() {
        assertTrue(parseSonic(body("sonic_path")).tracks.all { it.similarity == null })
    }

    @Test fun anUnreadableBodyIsEmptyNotACrash() {
        assertEquals("empty", parseSonic("<html>").status)
        assertTrue(parseSonic("[]").tracks.isEmpty())
        assertTrue(parseSonic("""{"status":"ok","tracks":[{"title":"no id"},"x",{"navidrome_id":"a"}]}""").tracks.map { it.songId } == listOf("a"))
    }

    @Test fun availabilityIsFalseWhenMissingOrUnreadable() {
        assertTrue(sonicAvailableFrom("""{"sonic_available": true}"""))
        assertFalse(sonicAvailableFrom("""{"sonic_available": false}"""))
        assertFalse(sonicAvailableFrom("""{"contract_version": 1}"""))
        assertFalse(sonicAvailableFrom("not json"))
    }

    @Test fun eachStatusHasItsOwnWords() {
        fun words(code: Int) = sonicFailure(ConnectionException(ConnectionFailure.Server(code, "raw"))).message
        assertEquals("The server doesn't know this song.", words(404))
        assertEquals("Sound matching isn't available right now. Try again later.", words(502))
        assertEquals("Sounds-like needs the server. It is not saved on this phone.", sonicFailure(CacheMiss()).message)
    }
}
