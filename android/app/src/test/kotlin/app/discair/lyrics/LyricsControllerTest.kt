package app.discair.lyrics

import java.io.File
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

@OptIn(ExperimentalCoroutinesApi::class)
class LyricsControllerTest {
    @get:Rule val tmp = TemporaryFolder()
    private var clock = 1_000_000_000L

    private class FakeSource(val answers: MutableMap<String, Any> = mutableMapOf()) : LyricsSource {
        val calls = mutableListOf<String>()
        override fun lyrics(songId: String): LyricsAnswer {
            calls += songId
            val a = answers[songId] ?: LyricsAnswer.None
            if (a is LyricsException) throw a
            return a as LyricsAnswer
        }
    }

    private fun lyrics(text: String = "x") = Lyrics(true, listOf(LyricLine(0, text), LyricLine(100, "y")))
    private fun cache() = LyricsCache(File(tmp.root, "c"), { "s" }) { clock }
    private fun TestScope.controller(source: LyricsSource, cache: LyricsCache) =
        LyricsController(this, source, cache, StandardTestDispatcher(testScheduler))

    @Test fun missShowsLoadingThenFetchesStoresAndShowsReady() = runTest {
        val src = FakeSource(mutableMapOf("a" to LyricsAnswer.Found(lyrics())))
        val cache = cache(); val c = controller(src, cache)
        val seen = mutableListOf<LyricsUiState>()
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { c.state.toList(seen) }
        c.open("a", null)
        advanceUntilIdle()
        assertEquals(listOf("Idle", "Loading", "Ready"), seen.map { it::class.simpleName })
        assertEquals(listOf("a"), src.calls); assertTrue(cache.get("a") != null)
    }

    @Test fun cachedEntryShowsWithoutARequest() = runTest {
        val cache = cache(); cache.put("a", lyrics())
        val src = FakeSource()
        val c = controller(src, cache); c.open("a", null); advanceUntilIdle()
        assertTrue(c.state.value is LyricsUiState.Ready); assertTrue(src.calls.isEmpty())
    }

    @Test fun cachedNoneShowsNoneWithoutARequest() = runTest {
        val cache = cache(); cache.put("a", null)
        val src = FakeSource(); val c = controller(src, cache); c.open("a", null); advanceUntilIdle()
        assertEquals(LyricsUiState.None("a"), c.state.value); assertTrue(src.calls.isEmpty())
    }

    @Test fun noneAnswerIsCachedSoItIsNotAskedAgain() = runTest {
        val src = FakeSource(); val cache = cache(); val c = controller(src, cache)
        c.open("a", null); advanceUntilIdle(); c.close(); c.open("a", null); advanceUntilIdle()
        assertEquals(LyricsUiState.None("a"), c.state.value); assertEquals(1, src.calls.size)
    }

    @Test fun failureWithNothingSavedShowsTheProblem() = runTest {
        val src = FakeSource(mutableMapOf("a" to LyricsException(LyricsProblem.Unreachable, "m")))
        val c = controller(src, cache()); c.open("a", null); advanceUntilIdle()
        assertEquals(LyricsUiState.Failed("a", LyricsProblem.Unreachable), c.state.value)
    }

    @Test fun staleSavedCopyStaysOnScreenMarkedWhenTheRefreshFails() = runTest {
        val cache = cache(); cache.put("a", lyrics()); clock += DAY_MS
        val src = FakeSource(mutableMapOf("a" to LyricsException(LyricsProblem.Unreachable, "m")))
        val c = controller(src, cache); c.open("a", null); advanceUntilIdle()
        val s = c.state.value as LyricsUiState.Ready
        assertTrue(s.savedCopy); assertEquals(1, src.calls.size)
    }

    @Test fun staleCopyIsReplacedByTheRefresh() = runTest {
        val cache = cache(); cache.put("a", lyrics("old")); clock += DAY_MS
        val src = FakeSource(mutableMapOf("a" to LyricsAnswer.Found(lyrics("new"))))
        val c = controller(src, cache); c.open("a", null); advanceUntilIdle()
        val s = c.state.value as LyricsUiState.Ready
        assertEquals(false, s.savedCopy); assertEquals("new", s.lyrics.lines.first().text)
    }

    @Test fun unsupportedServerStopsAllLaterRequests() = runTest {
        val src = FakeSource(mutableMapOf("a" to LyricsAnswer.Unsupported))
        val c = controller(src, cache()); c.open("a", "b"); advanceUntilIdle()
        assertEquals(LyricsUiState.Unsupported("a"), c.state.value)
        c.open("c", null); advanceUntilIdle()
        assertEquals(LyricsUiState.Unsupported("c"), c.state.value); assertEquals(listOf("a"), src.calls)
    }

    @Test fun nextSongIsPrefetchedAfterTheCurrentOneShows() = runTest {
        val src = FakeSource(mutableMapOf("a" to LyricsAnswer.Found(lyrics()), "b" to LyricsAnswer.Found(lyrics("b"))))
        val cache = cache(); val c = controller(src, cache)
        c.open("a", "b"); advanceUntilIdle()
        assertEquals(listOf("a", "b"), src.calls)
        assertEquals("a", (c.state.value as LyricsUiState.Ready).songId) // the prefetch never replaces what is shown
        assertEquals("b", cache.get("b")!!.lyrics!!.lines.first().text)
    }

    @Test fun prefetchSkipsFreshCacheAndIgnoresFailure() = runTest {
        val cache = cache(); cache.put("b", lyrics())
        val src = FakeSource(mutableMapOf("a" to LyricsAnswer.Found(lyrics())))
        controller(src, cache).also { it.open("a", "b"); advanceUntilIdle() }
        assertEquals(listOf("a"), src.calls)
        val failing = FakeSource(mutableMapOf("a" to LyricsAnswer.Found(lyrics()), "z" to LyricsException(LyricsProblem.Other, "m")))
        val c2 = controller(failing, cache()); c2.open("a", "z"); advanceUntilIdle()
        assertTrue(c2.state.value is LyricsUiState.Ready)
    }

    @Test fun nothingIsFetchedWhileTheViewIsClosed() = runTest {
        val src = FakeSource(); val c = controller(src, cache())
        advanceUntilIdle()
        assertTrue(src.calls.isEmpty()); assertEquals(LyricsUiState.Idle, c.state.value)
    }

    @Test fun closingBeforeTheLookupRunsFetchesNothing() = runTest {
        val src = FakeSource(mutableMapOf("a" to LyricsAnswer.Found(lyrics())))
        val cache = cache(); val c = controller(src, cache)
        c.open("a", "b"); c.close(); advanceUntilIdle()
        assertEquals(LyricsUiState.Idle, c.state.value)
        assertTrue(src.calls.isEmpty()); assertTrue(cache.get("a") == null && cache.get("b") == null)
    }

    @Test fun changingSongCancelsTheEarlierLookup() = runTest {
        val src = FakeSource(mutableMapOf("a" to LyricsAnswer.Found(lyrics("a")), "b" to LyricsAnswer.Found(lyrics("b"))))
        val c = controller(src, cache())
        c.open("a", null); c.open("b", null); advanceUntilIdle()
        assertEquals("b", (c.state.value as LyricsUiState.Ready).songId)
    }

    @Test fun failureTextsAreFixedWords() {
        for (p in LyricsProblem.values()) assertTrue(lyricsFailureText(p).isNotBlank())
    }
}
