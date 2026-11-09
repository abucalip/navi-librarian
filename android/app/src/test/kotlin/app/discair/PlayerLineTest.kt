package app.discair

import app.discair.model.PEAK_MAX
import app.discair.model.PeaksResult
import app.discair.model.PlayerFact
import app.discair.model.fold
import app.discair.model.mixFacts
import app.discair.model.parsePeaks
import app.discair.model.parseSongFacts
import app.discair.player.MemoryPlayerSettings
import app.discair.player.PlayerLine
import app.discair.player.PlayerLineRules
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PlayerLineTest {
    private fun fact(t: String, server: Boolean = false) = PlayerFact("k", t, if (server) "MusicBrainz" else "Your library", server)

    @Test fun timedLyricShowsTheLine() {
        assertEquals(PlayerLine.Lyric("Hello"), PlayerLineRules.choose(true, true, true, " Hello ", fact("a")))
    }

    @Test fun betweenTimedLinesTheFieldStaysEmpty() {
        assertEquals(PlayerLine.Empty, PlayerLineRules.choose(true, true, true, "", fact("a")))
        assertEquals(PlayerLine.Empty, PlayerLineRules.choose(true, true, true, null, fact("a")))
    }

    @Test fun withoutTimedLyricsAFactShows() {
        assertEquals(PlayerLine.Fact(fact("a")), PlayerLineRules.choose(true, true, false, null, fact("a")))
    }

    @Test fun quoteSwitchOffLetsFactsTakeTheField() {
        assertEquals(PlayerLine.Fact(fact("a")), PlayerLineRules.choose(false, true, true, "Hello", fact("a")))
    }

    @Test fun bothSwitchesOffOrNoFactIsEmpty() {
        assertEquals(PlayerLine.Empty, PlayerLineRules.choose(false, false, true, "Hello", fact("a")))
        assertEquals(PlayerLine.Empty, PlayerLineRules.choose(true, true, false, null, null))
    }

    @Test fun factsAlternateServerFirstWithoutRepeats() {
        val out = mixFacts(listOf(fact("s1", true), fact("s2", true)), listOf(fact("l1"), fact("s1", true), fact("l2")))
        assertEquals(listOf("s1", "l1", "s2", "l2"), out.map { it.text })
    }

    @Test fun mixStopsAtFourteen() {
        assertEquals(14, mixFacts(List(20) { fact("s$it", true) }, List(20) { fact("l$it") }).size)
    }

    @Test fun songFactsKeepGoodLinesAndDropBadOnes() {
        val body = """{"facts":[{"kind":"producer","text":"Produced by Pat","source":"MusicBrainz"},{"kind":"x","text":""},7,{"text":"Recorded in London"}]}"""
        val out = parseSongFacts(body)
        assertEquals(listOf("Produced by Pat", "Recorded in London"), out.map { it.text })
        assertTrue(out.all { it.fromServer && it.source == "MusicBrainz" })
        assertTrue(parseSongFacts("not json").isEmpty())
    }

    @Test fun peaksByStatus() {
        assertEquals(PeaksResult.Pending, parsePeaks(202, """{"status":"pending"}"""))
        assertEquals(PeaksResult.None, parsePeaks(404, ""))
        assertEquals(PeaksResult.None, parsePeaks(200, "oops"))
        val ready = parsePeaks(200, """{"bins":3,"peaks":[0,32767,65535]}""") as PeaksResult.Ready
        assertEquals(1f, ready.peaks[2], 0f)
        assertEquals(32767 / PEAK_MAX, ready.peaks[1], 0.0001f)
    }

    @Test fun foldKeepsTheLoudestOfEachSlice() {
        assertEquals(listOf(0.5f, 0.9f), floatArrayOf(0.1f, 0.5f, 0.2f, 0.9f).fold(2).toList())
        assertEquals(4, floatArrayOf(0.1f, 0.5f, 0.2f, 0.9f).fold(10).size)
    }

    @Test fun switchesDefaultOnAndNotifyChanges() {
        val s = MemoryPlayerSettings()
        assertTrue(s.showLyricLine && s.showFacts)
        var n = 0
        s.onChange { n++ }.use { s.showFacts = false; s.showLyricLine = false }
        assertEquals(2, n)
    }
}
