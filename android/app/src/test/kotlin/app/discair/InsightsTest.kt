package app.discair

import app.discair.model.InsightNarrative
import app.discair.model.InsightVerb
import app.discair.model.insightWriteBody
import app.discair.model.parseInsights
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Server V2 Phase 3: the insight cards decode from the server's own fixtures and explain themselves in plain words. */
class InsightsTest {
    private fun body(name: String): String = Json.parseToJsonElement(
        javaClass.classLoader!!.getResource("$name.json")!!.readText(),
    ).jsonObject["response"].toString()

    @Test fun allOffFixtureHasFiveLensesAndNoCards() {
        val r = parseInsights(body("insights_all_off"))
        assertEquals(listOf("forgotten_gem", "series_completion", "blind_spot", "hidden_canon", "anniversary"), r.orderedKinds)
        assertTrue(r.lenses.values.all { !it.enabled && it.cards.isEmpty() })
    }

    @Test fun enabledLensesCarryExplainableCards() {
        val r = parseInsights(body("insights_three_on"))
        val on = r.orderedKinds.filter { r.lenses.getValue(it).enabled }
        assertEquals(listOf("series_completion", "hidden_canon", "anniversary"), on)
        for (kind in on) {
            val card = r.lenses.getValue(kind).cards.single()
            assertEquals(kind, card.kind)
            assertTrue(card.title.isNotEmpty() && card.body.isNotEmpty() && card.subject.key.isNotEmpty())
            assertTrue(card.reasons.isNotEmpty() && card.dismissible)
        }
        assertFalse(r.lenses.getValue("blind_spot").enabled)
    }

    @Test fun seriesCardKeepsCountersAndMissingRuns() {
        val card = parseInsights(body("insights_three_on")).lenses.getValue("series_completion").cards.single()
        assertEquals(2, card.owned)
        assertEquals(4, card.total)
        assertEquals("series_completion:fx-series", card.subject.key)
        val run = card.missingRuns.single()
        assertEquals(3, run.firstPosition)
        assertEquals(4, run.lastPosition)
        assertEquals(listOf("Title 2 (2002)", "Title 3 (2003)"), run.labels)
    }

    @Test fun aCardWithoutAKeyOrReasonsIsDroppedAndUnknownLensesFollow() {
        val json = """{"lenses":{"zeta":{"enabled":true,"cards":[
            {"kind":"zeta","title":"No key","body":"x","subject":{"key":""},"reasons":[{"kind":"r"}]},
            {"kind":"zeta","title":"No reasons","body":"x","subject":{"key":"k"},"reasons":[]},
            {"kind":"zeta","title":"Fine","body":"x","subject":{"key":"k2"},"reasons":[{"kind":"r"}],"surprise":1}]},
          "anniversary":{"enabled":false,"cards":[]}},"data_version":1,"generation":1}"""
        val r = parseInsights(json)
        assertEquals(listOf("Fine"), r.lenses.getValue("zeta").cards.map { it.title })
        assertEquals(listOf("anniversary", "zeta"), r.orderedKinds)
    }

    @Test fun anUnexpectedBodyGivesAnEmptyResponse() {
        assertTrue(parseInsights("[]").lenses.isEmpty())
        assertTrue(parseInsights("""{"lenses":{"a":5}}""").lenses.isEmpty())
    }

    @Test fun whyReadsFromTheCardsNumbers() {
        val r = parseInsights(body("insights_three_on"))
        fun why(kind: String) = InsightNarrative.why(r.lenses.getValue(kind).cards.single())
        assertEquals(
            "Example label catalogue is a series on MusicBrainz with 4 releases, and your library holds 2 of them. " +
                "The 2 you do not have form one run (positions 3 to 4: Title 2 (2002) and Title 3 (2003)).",
            why("series_completion"),
        )
        assertEquals(
            "Loveless by My Bloody Valentine (1991) has been listened to 5,000 times on ListenBrainz. " +
                "It belongs to shoegaze, which is your top genre, and it is not in your library.",
            why("hidden_canon"),
        )
        assertEquals(
            "Example Album by Example Artist was released on 1 June 2016, which is 10 years ago today.",
            why("anniversary"),
        )
    }

    @Test fun anUnknownLensExplainsItselfFromItsReasons() {
        val json = """{"lenses":{"zeta":{"enabled":true,"cards":[{"kind":"zeta","title":"Odd","body":"b",
            "subject":{"key":"k"},"reasons":[{"kind":"made_up","evidence":{"n":3,"label":"x"}}]}]}}}"""
        assertEquals("Odd is shown because of made up (label x, n 3).", InsightNarrative.why(parseInsights(json).lenses.getValue("zeta").cards.single()))
    }

    @Test fun writeBodiesCarryTheCardsOwnKindAndKey() {
        assertEquals("""{"kind":"hidden_canon","key":"hidden_canon:fx-w1"}""", insightWriteBody("hidden_canon", "hidden_canon:fx-w1"))
        assertEquals(listOf("dismiss", "restore", "accept"), InsightVerb.entries.map { it.wire })
    }
}
