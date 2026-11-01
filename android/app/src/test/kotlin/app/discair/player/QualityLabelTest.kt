package app.discair.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class QualityLabelTest {
    private fun item(suffix: String = "", kbps: Int? = null, depth: Int? = null, rate: Int? = null) =
        QueueItem("s1", "T", "A", "B", suffix = suffix, bitRateKbps = kbps, bitDepth = depth, samplingRateHz = rate)

    @Test fun mp3ShowsOnlyTheBitRate() = assertEquals("320Kbps", qualityLabel(item("mp3", 320)))
    @Test fun flacShowsDepthAndRate() {
        assertEquals("FLAC 16/44.1", qualityLabel(item("flac", 900, 16, 44100)))
        assertEquals("FLAC 24/96", qualityLabel(item("FLAC", 2400, 24, 96000)))
    }
    @Test fun flacWithoutDetailsShowsTheName() = assertEquals("FLAC", qualityLabel(item("flac", 900)))
    @Test fun otherLossyKeepsItsType() = assertEquals("OGG 192Kbps", qualityLabel(item("ogg", 192)))
    @Test fun unknownGivesNothing() = assertNull(qualityLabel(item()))

    @Test fun songParsingReadsYearAndQuality() {
        val body = """{"subsonic-response":{"status":"ok","album":{"id":"al","name":"B","artist":"A","year":1999,"song":[
          {"id":"x1","title":"T","track":1,"bitRate":320,"suffix":"mp3"},
          {"id":"x2","title":"U","track":2,"year":2001,"suffix":"flac","bitDepth":24,"samplingRate":96000,"bitRate":2000}]}}}"""
        val (a, b) = SubsonicParse.albumSongs(body)
        assertEquals(1999, a.year); assertEquals(320, a.bitRateKbps); assertEquals("mp3", a.suffix)
        assertEquals(2001, b.year); assertEquals(24, b.bitDepth); assertEquals(96000, b.samplingRateHz)
    }
}
