package app.discair.lyrics

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

/** Placeholder text only: no real lyrics anywhere in the repository (contract 3.4). */
class LyricsParseTest {
    private fun line(start: Long?, value: String) = """{${if (start != null) "\"start\":$start," else ""}"value":"$value"}"""
    private fun entry(synced: Boolean, lines: List<String>, lang: String = "xxx", extra: String = "") =
        """{"displayArtist":"A","displayTitle":"T","lang":"$lang","synced":$synced$extra,"line":[${lines.joinToString(",")}]}"""
    private fun body(vararg entries: String) = """{"subsonic-response":{"status":"ok","lyricsList":{"structuredLyrics":[${entries.joinToString(",")}]}}}"""
    private fun found(b: String, lang: String = "en") = (LyricsParse.answer(b, lang) as LyricsAnswer.Found).lyrics
    private fun texts(l: Lyrics) = l.lines.map { it.text }

    @Test fun timedAnswerKeepsStartsAndText() {
        val l = found(body(entry(true, listOf(line(1000, "one"), line(2500, "two")))))
        assertTrue(l.timed); assertEquals(listOf(1000L, 2500L), l.lines.map { it.startMs }); assertEquals(listOf("one", "two"), texts(l))
    }

    @Test fun plainAnswerHasNoStarts() {
        val l = found(body(entry(false, listOf(line(null, "one"), line(null, "two")))))
        assertFalse(l.timed); assertTrue(l.lines.all { it.startMs == null })
    }

    @Test fun emptyAndMissingAnswersAreNone() {
        assertEquals(LyricsAnswer.None, LyricsParse.answer(body(), "en"))
        assertEquals(LyricsAnswer.None, LyricsParse.answer("""{"subsonic-response":{"status":"ok"}}""", "en"))
        assertEquals(LyricsAnswer.None, LyricsParse.answer(body(entry(true, emptyList())), "en"))
        assertEquals(LyricsAnswer.None, LyricsParse.answer(body(entry(false, listOf(line(null, "   ")))), "en"))
    }

    @Test fun timedIsPreferredOverPlainWhateverTheOrder() {
        val l = found(body(entry(false, listOf(line(null, "plain")), lang = "en"), entry(true, listOf(line(0, "a"), line(5, "b")), lang = "de")))
        assertTrue(l.timed)
    }

    @Test fun phoneLanguageWinsAmongTimedEntries() {
        val l = found(body(
            entry(true, listOf(line(0, "de1"), line(5, "de2")), lang = "deu"),
            entry(true, listOf(line(0, "en1"), line(5, "en2")), lang = "eng"),
        ), "en")
        assertEquals("en1", l.lines.first().text)
    }

    @Test fun withoutALanguageMatchTheFirstListedIsUsed() {
        val l = found(body(entry(true, listOf(line(0, "first"), line(5, "x")), "xxx"), entry(true, listOf(line(0, "second"), line(5, "y")), "fra")), "en")
        assertEquals("first", l.lines.first().text)
        assertEquals("first", found(body(entry(true, listOf(line(0, "first"), line(5, "x")), "xxx"), entry(true, listOf(line(0, "second"), line(5, "y")), "fra")), "xxx").lines.first().text)
    }

    @Test fun unsortedStartsAreSorted() {
        val l = found(body(entry(true, listOf(line(3000, "c"), line(1000, "a"), line(2000, "b"), line(4000, "d")))))
        // Not entirely backwards, so it stays timed and is sorted.
        assertTrue(l.timed); assertEquals(listOf("a", "b", "c", "d"), texts(l))
    }

    @Test fun missingOrNegativeStartsAreDropped() {
        val l = found(body(entry(true, listOf(line(null, "none"), line(-5, "neg"), line(100, "ok1"), line(200, "ok2")))))
        assertEquals(listOf("ok1", "ok2"), texts(l))
    }

    @Test fun offsetIsAddedAndMissingOffsetAddsNothing() {
        val withOffset = found(body(entry(true, listOf(line(1000, "a"), line(2000, "b")), extra = ""","offset":-300""")))
        assertEquals(listOf(700L, 1700L), withOffset.lines.map { it.startMs })
        val none = found(body(entry(true, listOf(line(1000, "a"), line(2000, "b")))))
        assertEquals(listOf(1000L, 2000L), none.lines.map { it.startMs })
        val belowZero = found(body(entry(true, listOf(line(100, "a"), line(2000, "b")), extra = ""","offset":-500""")))
        assertEquals(0L, belowZero.lines.first().startMs)
    }

    @Test fun overLongLinesAreCutAndOverManyLinesAreCapped() {
        val long = "x".repeat(900)
        assertEquals(LyricsParse.MAX_LINE_CHARS, found(body(entry(false, listOf(line(null, long))))).lines.single().text.length)
        val many = (0 until 2500).map { line(it * 10L, "l$it") }
        val l = found(body(entry(true, many)))
        assertEquals(LyricsParse.MAX_LINES, l.lines.size); assertTrue(l.timed)
    }

    @Test fun controlCharactersAreRemovedAndMarkupStaysPlainText() {
        val l = found(body(entry(false, listOf(line(null, "a\\u0000b\\u0007c\\nd"), line(null, "<b>x</b>")))))
        assertEquals("abcd", l.lines[0].text); assertEquals("<b>x</b>", l.lines[1].text)
    }

    @Test fun emptyLinesAreKeptAsPauses() {
        val l = found(body(entry(true, listOf(line(0, "a"), line(1000, ""), line(2000, "b")))))
        assertEquals(listOf("a", "", "b"), texts(l))
    }

    @Test fun equalStartsAreTreatedAsPlain() {
        val l = found(body(entry(true, listOf(line(0, "a"), line(0, "b"), line(0, "c")))))
        assertFalse(l.timed); assertTrue(l.lines.all { it.startMs == null }); assertEquals(listOf("a", "b", "c"), texts(l))
    }

    @Test fun backwardStartsAreTreatedAsPlainInTheirOriginalOrder() {
        val l = found(body(entry(true, listOf(line(3000, "a"), line(2000, "b"), line(1000, "c")))))
        assertFalse(l.timed); assertEquals(listOf("a", "b", "c"), texts(l))
    }

    @Test fun unknownFieldsAreIgnored() {
        val b = """{"subsonic-response":{"status":"ok","version":"1.16.1","new":1,"lyricsList":{"structuredLyrics":[{"synced":false,"future":true,"line":[{"value":"a","extra":1}]}]}}}"""
        assertEquals(listOf("a"), texts(found(b)))
    }

    @Test fun errorBodiesAreClassifiedAndCode70IsNone() {
        fun failed(code: Int) = """{"subsonic-response":{"status":"failed","error":{"code":$code}}}"""
        assertEquals(LyricsAnswer.None, LyricsParse.answer(failed(70), "en"))
        for (code in listOf(40, 41, 44, 50)) assertEquals(LyricsProblem.Unauthorised, assertThrows(LyricsException::class.java) { LyricsParse.answer(failed(code), "en") }.problem)
        assertEquals(LyricsProblem.Other, assertThrows(LyricsException::class.java) { LyricsParse.answer(failed(0), "en") }.problem)
        assertEquals(LyricsProblem.Other, assertThrows(LyricsException::class.java) { LyricsParse.answer("not json", "en") }.problem)
    }

    @Test fun extensionListIsRead() {
        fun ext(vararg names: String) = """{"subsonic-response":{"status":"ok","openSubsonicExtensions":[${names.joinToString(",") { """{"name":"$it","versions":[1]}""" }}]}}"""
        assertTrue(LyricsParse.supportsLyrics(ext("transcoding", "songLyrics")))
        assertFalse(LyricsParse.supportsLyrics(ext("transcoding")))
        assertFalse(LyricsParse.supportsLyrics("""{"subsonic-response":{"status":"ok"}}"""))
    }

    @Test fun lyricsTextNeverAppearsInToString() {
        val l = found(body(entry(false, listOf(line(null, "secret words")))))
        assertFalse(l.toString().contains("secret")); assertFalse(l.lines.first().toString().contains("secret"))
    }
}
