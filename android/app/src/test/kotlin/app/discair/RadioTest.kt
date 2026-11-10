package app.discair

import app.discair.model.RadioNow
import app.discair.model.RadioNowState
import app.discair.model.parseRadioFavourite
import app.discair.model.parseRadioNow
import app.discair.model.parseRadioNowAll
import app.discair.model.parseRadioStations
import app.discair.model.radioNowText
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Radio decoders (docs/RADIO_PLAYBACK_CONTRACT.md sections 3.1 to 3.5, 6) against the shared contract fixtures. */
class RadioTest {
    private fun body(name: String): String = Json.parseToJsonElement(
        javaClass.classLoader!!.getResource("librarian/$name.json")!!.readText(),
    ).jsonObject["response"]!!.jsonObject["body"].toString()

    @Test fun stationsKeepTheServersOrderAndFields() {
        val list = parseRadioStations(body("radio_stations"))
        assertEquals(listOf("11", "12", "13"), list.map { it.id })
        val first = list.first()
        assertTrue(first.favourite && first.proxied)
        assertEquals(listOf("rock", "local"), first.tags)
        assertEquals("/api/radio/stations/11/logo", first.logoUrl)
        assertTrue(first.playableUrl.endsWith("/radio/stream/fixturetoken"))
        assertNull(first.lastPlayedAt)
        assertEquals(1700000000.0, list[1].lastPlayedAt!!, 0.0)
        assertFalse(list.last().proxied)
    }

    @Test fun emptyOrUnreadableStationListsAreEmpty() {
        assertTrue(parseRadioStations(body("radio_stations_empty")).isEmpty())
        assertTrue(parseRadioStations("not json").isEmpty())
        assertTrue(parseRadioStations("[]").isEmpty())
    }

    @Test fun aStationWithoutAnIdOrAddressIsLeftOut() {
        val list = parseRadioStations("""{"items":[{"name":"A","playable_url":"http://a"},{"id":"1","name":"B"},{"id":"2","name":"C","stream_url":"http://c"}]}""")
        assertEquals(listOf("2"), list.map { it.id })
        assertEquals("/api/radio/stations/2/logo", list.single().logoUrl)
    }

    @Test fun everyNowStateDecodesAndOnlyOkWithAPlayIdCanDownload() {
        val ok = parseRadioNow(body("radio_now_ok"))
        assertEquals(RadioNowState.Ok, ok.state)
        assertTrue(ok.canDownload && ok.inLibrary)
        assertEquals("Pink Floyd - Time", ok.songLine)
        assertEquals("/api/owned/artwork/al-42", ok.coverUrl)

        val waiting = parseRadioNow(body("radio_now_ok_waiting"))
        assertEquals(RadioNowState.Ok, waiting.state)
        assertNull(waiting.playId)
        assertFalse(waiting.canDownload)

        mapOf(
            "radio_now_no_metadata" to RadioNowState.NoMetadata,
            "radio_now_unparsed" to RadioNowState.Unparsed,
            "radio_now_not_proxied" to RadioNowState.NotProxied,
            "radio_now_unavailable" to RadioNowState.Unavailable,
            "radio_now_idle" to RadioNowState.Idle,
        ).forEach { (file, state) ->
            val now = parseRadioNow(body(file))
            assertEquals(file, state, now.state)
            assertFalse(file, now.canDownload)
        }
    }

    @Test fun anUnknownStateOrBodyReadsAsUnreachableNotAsOk() {
        assertEquals(RadioNowState.Unavailable, parseRadioNow("""{"state":"from_the_future"}""").state)
        assertEquals(RadioNowState.Unavailable, parseRadioNow("nope").state)
        assertFalse(parseRadioNow("""{"state":"unparsed","play_id":4}""").canDownload)
    }

    @Test fun liveTitlesForAllStationsPairEachIdWithItsSong() {
        val all = parseRadioNowAll(body("radio_now_all"))
        assertEquals(listOf("11", "12"), all.map { it.stationId })
        assertEquals(RadioNowState.Ok, all[0].now.state)
        assertEquals(RadioNowState.Idle, all[1].now.state)
        assertNull(all[1].now.songLine)
    }

    @Test fun favouriteAnswerIsReadAndAnUnreadableOneIsNull() {
        assertEquals(true, parseRadioFavourite(body("radio_station_favourite")))
        assertNull(parseRadioFavourite("{}"))
    }

    @Test fun everyStateHasWordsNotColourAlone() {
        assertEquals("Pink Floyd - Time", radioNowText(parseRadioNow(body("radio_now_ok")), true))
        assertTrue(radioNowText(parseRadioNow(body("radio_now_no_metadata")), true).contains("no song titles"))
        assertTrue(radioNowText(parseRadioNow(body("radio_now_unparsed")), true).contains("could not be matched"))
        assertTrue(radioNowText(parseRadioNow(body("radio_now_unavailable")), true).contains("unreachable"))
        assertTrue(radioNowText(RadioNow.Unknown.copy(state = RadioNowState.Idle), true).contains("Tune in"))
    }
}
