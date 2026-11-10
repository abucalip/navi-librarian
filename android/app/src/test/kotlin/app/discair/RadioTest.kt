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

    @Test fun playsParseWithGrabbedAndMissingFields() {
        val plays = app.discair.model.parseRadioPlays(
            """{"items":[{"id":7,"station_name":"Rock","artist":"A","title":"T","album":null,"grabbed":1,"heard_at":5.0},
               {"id":8,"station_name":"Rock","artist":null,"title":"Only title","grabbed":0},{"title":"no id"}]}""",
        )
        assertEquals(listOf(7L, 8L), plays.map { it.id })
        assertTrue(plays[0].grabbed && plays[0].hasArtist && !plays[0].inLibrary)
        assertFalse(plays[1].hasArtist)
        assertTrue(app.discair.model.parseRadioPlays("nope").isEmpty())
    }

    @Test fun getAnswersBecomeTextAndOutcome() {
        assertTrue(app.discair.model.parseRadioGet("""{"ok":true,"status":"started","message":"Looking for it."}""").ok)
        val none = app.discair.model.parseRadioGet("""{"ok":true,"status":"no_matches"}""")
        assertFalse(none.ok); assertEquals("No source had this song.", none.message)
        assertEquals("Could not find which album this song is on.", app.discair.model.parseRadioGet("""{"ok":false,"message":"Could not find which album this song is on."}""").message)
        assertFalse(app.discair.model.parseRadioGet("garbage").ok)
    }

    @Test fun downloadStatesFollowTheContractRule() {
        val s = { p: Long?, o: Boolean, r: Boolean, w: Boolean, f: Boolean -> app.discair.model.radioDownloadState(p, o, r, w, f) }
        assertEquals(app.discair.model.RadioDownload.Waiting, s(null, false, false, false, false))
        assertEquals(app.discair.model.RadioDownload.Ready, s(3, false, false, false, false))
        assertEquals(app.discair.model.RadioDownload.Working, s(3, false, false, true, false))
        assertEquals(app.discair.model.RadioDownload.Done, s(3, false, true, false, false))
        assertEquals(app.discair.model.RadioDownload.Failed, s(3, false, false, false, true))
        assertEquals(app.discair.model.RadioDownload.Owned, s(3, true, true, false, false))
        assertFalse(app.discair.model.RadioDownload.Waiting.enabled || app.discair.model.RadioDownload.Owned.enabled)
    }

    @Test fun scrobblingAnswerReadsSwitchAndSetup() {
        val on = app.discair.model.parseRadioScrobbling("""{"enabled":true,"configured":true}""")
        assertTrue(on.enabled && on.configured)
        val off = app.discair.model.parseRadioScrobbling("""{"enabled":false,"configured":false}""")
        assertFalse(off.enabled || off.configured)
        val bad = app.discair.model.parseRadioScrobbling("nope") // unreadable never reads as on
        assertFalse(bad.enabled || bad.configured)
    }

    @Test fun appAddressIsReadOrBlank() {
        assertEquals("http://100.64.0.1:8080", app.discair.model.parseRadioAppUrl("""{"app_url":"http://100.64.0.1:8080"}"""))
        assertEquals("", app.discair.model.parseRadioAppUrl("""{"app_url":null}"""))
        assertEquals("", app.discair.model.parseRadioAppUrl("garbage"))
    }

    @Test fun logoRequestCarriesTheChangeMarkerOnlyAfterAChange() {
        app.discair.model.RadioLogoVersion.bump()
        assertTrue(app.discair.model.radioLogoRequest("https://x/logo", 512).startsWith("https://x/logo?size=512&v="))
    }

    @Test fun scrobblingWordsAreHonestWhenLastFmIsNotSetUp() {
        assertTrue(app.discair.ui.settings.scrobblingText(app.discair.model.RadioScrobbling(false, false), null).contains("not set up"))
        assertTrue(app.discair.ui.settings.scrobblingText(app.discair.model.RadioScrobbling(true, true), null).startsWith("On."))
        assertEquals("boom", app.discair.ui.settings.scrobblingText(null, "boom"))
    }

    @Test fun logoReaderStopsOneByteOverTheCap() {
        val big = java.io.ByteArrayInputStream(ByteArray(app.discair.data.RADIO_LOGO_MAX_BYTES + 500))
        assertEquals(app.discair.data.RADIO_LOGO_MAX_BYTES + 1, app.discair.ui.settings.readLogo { big }!!.size)
        assertEquals(null, app.discair.ui.settings.readLogo { null })
    }
}
