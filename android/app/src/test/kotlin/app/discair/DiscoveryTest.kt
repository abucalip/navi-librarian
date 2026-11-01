package app.discair

import app.discair.model.FeedbackAction
import app.discair.model.SearchEvent
import app.discair.model.feedbackBody
import app.discair.model.parseDiscovery
import app.discair.model.parseSearchEvent
import app.discair.ui.common.RowLead
import app.discair.ui.discover.releaseDateLead
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Phase 3: list parsing keeps the server's order, feedback bodies match the recorded request, search events decode. */
class DiscoveryTest {
    private fun fixture(name: String) = Json.parseToJsonElement(
        javaClass.classLoader!!.getResource("librarian/$name.json")!!.readText(),
    ).jsonObject

    private fun body(name: String) = fixture(name)["response"]!!.jsonObject["body"].toString()

    @Test fun personalListKeepsServerOrder() {
        val sent = fixture("discovery_personal")["response"]!!.jsonObject["body"]!!.jsonObject["recommendations"]!!
            .jsonArray.map { it.jsonObject["album"]!!.jsonPrimitive.content }
        val result = parseDiscovery(body("discovery_personal"))
        assertEquals(sent, result.entries.map { it.item.album })
        assertTrue(result.entries.all { it.item.artistName.isNotBlank() })
        // The raw row is kept whole, so feedback can return it as metadata.
        assertTrue(result.entries.first().raw.containsKey("discovery_score"))
    }

    @Test fun emptyListCarriesTheServerMessage() {
        val result = parseDiscovery(body("discovery_new_releases"))
        assertTrue(result.entries.isEmpty())
        assertTrue(result.message!!.startsWith("No saved list yet"))
    }

    @Test fun savedListReadsSavedFields() {
        val entry = parseDiscovery(body("discovery_for_me")).entries.single()
        assertEquals("Contract Fixture Album", entry.item.album)
        assertTrue(entry.item.savedAt!! > 0)
        assertFalse(entry.item.acquired)
    }

    @Test fun feedbackBodyMatchesRecordedRequest() {
        val recorded = fixture("discovery_feedback")["request"]!!.jsonObject["body"]!!.jsonObject
        val entry = parseDiscovery(body("discovery_for_me")).entries.single()
        val sent = Json.parseToJsonElement(
            feedbackBody(FeedbackAction.Save, "Contract Fixture Artist", "Contract Fixture Album", recorded["metadata"]!!.jsonObject),
        ).jsonObject
        assertEquals(recorded, sent)
        assertEquals("remove_for_me", FeedbackAction.RemoveSaved.wire)
        assertEquals("dismiss_artist", FeedbackAction.DismissArtist.wire)
        assertEquals("contract fixture artist/contract fixture album", entry.key)
    }

    @Test fun releaseDates() {
        assertEquals(RowLead.Date("5 Mar", "2026"), releaseDateLead("2026-03-05"))
        assertEquals(RowLead.Date("Mar", "2026"), releaseDateLead("2026-03"))
        assertEquals(RowLead.Date("", "2026"), releaseDateLead("2026"))
        assertNull(releaseDateLead("2026-13-01"))
        assertNull(releaseDateLead("soon"))
        assertNull(releaseDateLead(null))
    }

    @Test fun recordedSearchStreamDecodes() {
        val events = fixture("search_all")["response"]!!.jsonObject["body"]!!.jsonObject["sse_events"] as JsonArray
        val parsed = events.map {
            parseSearchEvent(it.jsonObject["event"]!!.jsonPrimitive.content, it.jsonObject["data"].toString())
        }
        assertTrue(parsed.all { it != null })
        assertTrue(parsed.first() is SearchEvent.Capabilities)
        assertTrue(parsed.last() is SearchEvent.Done)
        val results = parsed.filterIsInstance<SearchEvent.Result>().map { it.result }
        assertTrue(results.first().owned)
        // Owned results arrive first and keep their place.
        assertEquals(results.sortedByDescending { it.owned }.map { it.id }, results.map { it.id })
        assertEquals("album", results.first { it.type == "album" }.type)
        assertNull(parseSearchEvent("unknown", "{}"))
    }
}
