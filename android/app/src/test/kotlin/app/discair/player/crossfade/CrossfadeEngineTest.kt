package app.discair.player.crossfade

import app.discair.player.RepeatMode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

private class Msg(val at: Long, val block: () -> Unit) { var cancelled = false; var done = false }

private class FakePlayer(override val name: String, val events: MutableList<String>) : FadePlayer {
    var current: JoinSong? = null
    var next: JoinSong? = null
    var library = mutableMapOf<String, JoinSong>()
    override val currentSong get() = current
    override val nextSong get() = next
    override var nextIsSameEntry = false
    override var repeat = RepeatMode.Off
    override var positionMs = 0L
    override var durationMs: Long? = null
    override var isReady = true
    override var bufferedMs = 60_000L
    override var playWhenReady = false
    override var volume = 1f
    var prepareThrows = false
    var prepared = mutableListOf<String>()
    private val messages = mutableListOf<Msg>()
    val pendingMessages get() = messages.count { !it.cancelled && !it.done }

    override fun setFocusHandling(on: Boolean) { events += "$name focus ${if (on) "on" else "off"}" }
    override fun prepareOn(songId: String): Boolean {
        if (prepareThrows) throw IllegalStateException("boom")
        prepared += songId
        current = library[songId] ?: JoinSong(songId, "x", 100_000)
        durationMs = current?.durationMs
        playWhenReady = false
        return true
    }
    override fun runAtPosition(positionMs: Long, block: () -> Unit): Cancelable {
        val m = Msg(positionMs, block); messages += m
        return Cancelable { m.cancelled = true }
    }
    fun advanceTo(pos: Long) {
        positionMs = pos
        messages.filter { !it.cancelled && !it.done && it.at <= pos }.sortedBy { it.at }.forEach { it.done = true; it.block() }
    }
}

private class ManualScheduler : Scheduler {
    var now = 0L
    private class Job(val due: Long, val block: () -> Unit) { var cancelled = false }
    private val jobs = mutableListOf<Job>()
    override fun nowMs() = now
    override fun postDelayed(delayMs: Long, block: () -> Unit): Cancelable {
        val j = Job(now + delayMs, block); jobs += j
        return Cancelable { j.cancelled = true }
    }
    fun advance(ms: Long) {
        val end = now + ms
        while (true) {
            val j = jobs.filter { !it.cancelled && it.due <= end }.minByOrNull { it.due } ?: break
            jobs.remove(j); now = j.due; j.block()
        }
        now = end
    }
}

private class FakeProvider(val second: FadePlayer) : TwinProvider {
    var acquired = 0
    val released = mutableListOf<FadePlayer>()
    var fails = false
    override fun acquire(from: FadePlayer): FadePlayer? { acquired++; return if (fails) null else second }
    override fun release(player: FadePlayer) { released += player }
}

class CrossfadeEngineTest {
    private val events = mutableListOf<String>()
    private val songA = JoinSong("A", "album1", 200_000)
    private val songB = JoinSong("B", "album2", 180_000)
    private val first = FakePlayer("player0", events).apply {
        current = songA; next = songB; durationMs = 200_000; playWhenReady = true; library["B"] = songB; library["A"] = songA
    }
    private val second = FakePlayer("player1", events).apply { library["B"] = songB; library["A"] = songA }
    private val provider = FakeProvider(second)
    private val clock = ManualScheduler()
    private var settings = CrossfadeSettings(enabled = true, seconds = 5, skipSameAlbum = true)
    private val swaps = mutableListOf<FadePlayer>()
    private val logs = mutableListOf<String>()
    private var swapThrows = false

    private val engine = CrossfadeEngine(first, { settings }, provider, { if (swapThrows) throw IllegalStateException("swap") else { swaps += it; events += "swap to ${it.name}" } }, clock, { logs += it })

    private fun startFade() {
        engine.onActiveChanged()
        first.advanceTo(190_000) // prepare point (fade at 195 s, ten seconds earlier)
        first.advanceTo(195_000)
    }

    @Test fun offNeverCreatesTheSecondPlayerAndSchedulesNothing() {
        settings = settings.copy(enabled = false)
        engine.onActiveChanged(); engine.onActiveReady(); engine.onSettingsChanged()
        assertEquals(0, provider.acquired); assertEquals(0, first.pendingMessages)
        first.advanceTo(199_000)
        assertTrue(swaps.isEmpty())
    }

    @Test fun aRefusedJoinNeverAsksForTheSecondPlayer() {
        first.next = songB.copy(albumId = "album1") // same album: stays gapless
        engine.onActiveChanged()
        assertEquals(0, provider.acquired); assertEquals(0, first.pendingMessages)
        first.next = null; engine.onActiveChanged()
        assertEquals(0, provider.acquired)
    }

    @Test fun anOrdinaryJoinPreparesTheSecondPlayerPausedAndSilentThenFades() {
        engine.onActiveChanged()
        assertEquals(1, provider.acquired); assertEquals(2, first.pendingMessages)
        first.advanceTo(185_000)
        assertEquals(listOf("B"), second.prepared); assertEquals(0f, second.volume); assertFalse(second.playWhenReady)
        first.advanceTo(195_000)
        assertTrue(engine.isFading); assertSame(second, engine.active); assertEquals(listOf<FadePlayer>(second), swaps)
        assertTrue(second.playWhenReady)
        clock.advance(2_500)
        assertEquals(0.707f, second.volume, 0.02f); assertEquals(0.707f, first.volume, 0.02f)
        clock.advance(2_600)
        assertFalse(engine.isFading)
        assertEquals(1f, second.volume); assertEquals(1f, first.volume); assertFalse(first.playWhenReady); assertTrue(second.playWhenReady)
        assertEquals(1, provider.acquired)
        assertTrue(provider.released.isEmpty())
    }

    @Test fun theOutgoingPlayersFocusIsTurnedOffBeforeTheIncomingOneAsksForIt() {
        startFade()
        val a = events.indexOf("player0 focus off"); val b = events.indexOf("player1 focus on"); val c = events.indexOf("swap to player1")
        assertTrue(events.toString(), a in 0 until b)
        assertTrue(events.toString(), b in 0 until c || c > a)
    }

    @Test fun afterAFadeTheNextJoinIsPlannedOnTheNewActivePlayerWithoutANewSecondPlayer() {
        startFade(); clock.advance(5_100)
        second.next = songA; second.current = songB; second.durationMs = 180_000
        engine.onActiveChanged()
        assertEquals(1, provider.acquired)
        assertEquals(2, second.pendingMessages)
        second.advanceTo(175_000)
        assertEquals(listOf("A"), first.prepared)
    }

    @Test fun aSecondPlayerThatIsNotReadyMeansTheJoinPlaysAsToday() {
        engine.onActiveChanged(); first.advanceTo(185_000)
        second.isReady = false
        first.advanceTo(195_000)
        assertFalse(engine.isFading); assertTrue(swaps.isEmpty()); assertSame(first, engine.active)
        assertEquals(1f, first.volume); assertTrue(first.playWhenReady)
    }

    @Test fun aSecondPlayerThatIsBufferedTooLittleMeansNoFade() {
        engine.onActiveChanged(); first.advanceTo(185_000)
        second.bufferedMs = 6_000 // needs the fade plus two seconds
        first.advanceTo(195_000)
        assertTrue(swaps.isEmpty())
    }

    @Test fun aSecondPlayerPreparedOnTheWrongSongMeansNoFade() {
        engine.onActiveChanged(); first.advanceTo(185_000)
        second.current = JoinSong("Z", "q", 100_000)
        first.advanceTo(195_000)
        assertTrue(swaps.isEmpty())
    }

    @Test fun aSecondPlayerThatCannotBeMadeIsLoggedAndTheSongPlaysOn() {
        provider.fails = true
        engine.onActiveChanged()
        assertEquals(0, first.pendingMessages); assertTrue(logs.any { "unavailable" in it })
    }

    @Test fun aFaultWhilePreparingNeverEscapesAndLeavesTheActivePlayerAtFullVolume() {
        second.prepareThrows = true
        engine.onActiveChanged()
        first.advanceTo(185_000) // must not throw
        first.advanceTo(195_000)
        assertTrue(swaps.isEmpty()); assertEquals(1f, first.volume); assertTrue(first.playWhenReady); assertSame(first, engine.active)
        assertTrue(logs.any { "failed" in it })
    }

    @Test fun aSessionSwapThatFailsLeavesTheOutgoingSongPlayingAndFocusRestored() {
        engine.onActiveChanged(); first.advanceTo(185_000)
        swapThrows = true
        first.advanceTo(195_000)
        assertFalse(engine.isFading); assertSame(first, engine.active)
        assertFalse(second.playWhenReady); assertEquals(1f, first.volume); assertTrue(first.playWhenReady)
        assertEquals("player0 focus on", events.last { it.startsWith("player0") })
        assertEquals("player1 focus off", events.last { it.startsWith("player1") })
    }

    @Test fun aSkipOrAnErrorDuringTheFadeEndsItAtOnceWithTheIncomingSongAtFullVolume() {
        startFade(); clock.advance(1_000)
        engine.onActiveChanged() // the active player moved to another song
        assertFalse(engine.isFading); assertEquals(1f, second.volume); assertFalse(first.playWhenReady); assertEquals(1f, first.volume)
        clock.advance(10_000)
        assertSame(second, engine.active); assertEquals(1f, second.volume)
    }

    @Test fun aSeekOrAnErrorEndsTheFadeToo() {
        startFade(); clock.advance(500)
        engine.onActiveInterrupted("seek")
        assertFalse(engine.isFading); assertEquals(1f, second.volume); assertFalse(first.playWhenReady)
        engine.onActiveInterrupted("seek") // nothing to end: no effect
    }

    @Test fun pauseAndResumeReachBothPlayersAndTheFadeClockStopsWhilePaused() {
        startFade(); clock.advance(1_000)
        second.playWhenReady = false; engine.onActivePlayWhenReady(false)
        assertFalse(first.playWhenReady)
        val v = second.volume
        clock.advance(4_000)
        assertTrue(engine.isFading); assertEquals(v, second.volume, 0.02f)
        second.playWhenReady = true; engine.onActivePlayWhenReady(true)
        assertTrue(first.playWhenReady)
        clock.advance(4_100)
        assertFalse(engine.isFading); assertEquals(1f, second.volume)
    }

    @Test fun theOutgoingPlayerIsPausedJustBeforeItsOwnEndSoItCannotAdvance() {
        startFade(); clock.advance(2_000)
        first.positionMs = 199_950
        clock.advance(20)
        assertFalse(first.playWhenReady); assertEquals(0f, first.volume)
        assertTrue(engine.isFading)
        clock.advance(3_100)
        assertFalse(engine.isFading); assertFalse(first.playWhenReady)
    }

    @Test fun repeatOneNeverFadesIntoItself() {
        first.repeat = RepeatMode.One
        engine.onActiveChanged()
        assertEquals(0, provider.acquired)
    }

    @Test fun turningCrossfadeOffReleasesTheSecondPlayerOnceAndCancelsTheJoin() {
        engine.onActiveChanged()
        settings = settings.copy(enabled = false)
        engine.onSettingsChanged()
        assertEquals(listOf<FadePlayer>(second), provider.released)
        first.advanceTo(199_000)
        assertTrue(swaps.isEmpty())
        engine.onSettingsChanged()
        assertEquals(1, provider.released.size)
    }

    @Test fun turningCrossfadeOnWhileASongPlaysTakesEffectAtThatSongsJoin() {
        settings = settings.copy(enabled = false)
        engine.onActiveChanged(); assertEquals(0, provider.acquired)
        settings = settings.copy(enabled = true)
        engine.onSettingsChanged()
        assertEquals(1, provider.acquired)
        first.advanceTo(185_000); first.advanceTo(195_000)
        assertTrue(engine.isFading)
    }

    @Test fun aSettingChangedDuringAFadeDoesNotTouchTheFadeThatIsRunning() {
        startFade(); clock.advance(1_000)
        settings = settings.copy(enabled = false)
        engine.onSettingsChanged()
        assertTrue(engine.isFading); assertTrue(provider.released.isEmpty())
        clock.advance(4_100)
        assertFalse(engine.isFading)
        assertEquals(listOf<FadePlayer>(first), provider.released) // released when the next join is planned with crossfade off
    }

    @Test fun closeReleasesTheIdlePlayerOnceStopsTheFadeAndIgnoresLaterEvents() {
        engine.onActiveChanged()
        engine.close(); engine.close()
        assertEquals(listOf<FadePlayer>(second), provider.released)
        engine.onActiveChanged(); first.advanceTo(195_000)
        assertTrue(swaps.isEmpty()); assertEquals(1, provider.acquired)
    }

    @Test fun closeInTheMiddleOfAFadeStopsTheTailAndReleasesTheOutgoingPlayer() {
        startFade(); clock.advance(1_000)
        engine.close()
        assertFalse(first.playWhenReady)
        assertEquals(listOf<FadePlayer>(first), provider.released)
        clock.advance(10_000)
        assertEquals(1, provider.released.size)
    }

    @Test fun anUnknownDurationOfTheActiveSongGivesNoFade() {
        first.durationMs = null; first.current = songA.copy(durationMs = null)
        engine.onActiveChanged()
        assertEquals(0, provider.acquired)
    }

    @Test fun thePlayersOwnDurationBeatsTheServersWhenKnown() {
        first.durationMs = 120_000 // the server said 200 s
        engine.onActiveChanged()
        first.advanceTo(105_000); first.advanceTo(115_000)
        assertTrue(engine.isFading)
    }
}
