package app.discair.player.crossfade

/**
 * Crossfade between two identical players (ANDROID_CROSSFADE_CONTRACT.md 4, 5 and 8, decided after the X1 spike).
 *
 * The outgoing song plays on to its natural end in its own player. About [PREP_BEFORE_MS] before the fade the other
 * player is moved to the next song, paused. At the fade point it starts that song from 0 and fades in while the
 * outgoing one fades out; the session is swapped to it at once. No song is ever handed from one player to the other,
 * so nothing has to be aligned.
 *
 * Every public call is guarded: a fault ends the fade, leaves the active player at full volume and the other one
 * paused, and playback continues as it does today (contract 3 rule 8). With crossfade off the second player is
 * never asked for.
 *
 * Rules learned in the X1 spike (contract 13): turn the outgoing player's focus handling off before the incoming one
 * asks for focus; pause the outgoing player just before its own end so it cannot advance by itself; send pause and
 * resume to both players; run the fade on a clock that stops while paused.
 */
class CrossfadeEngine(
    primary: FadePlayer,
    private val settings: () -> CrossfadeSettings,
    private val twin: TwinProvider,
    /** Called once at each fade start with the player the session must now face. */
    private val swapSession: (FadePlayer) -> Unit,
    private val scheduler: Scheduler,
    private val log: (String) -> Unit = {},
) {
    var active: FadePlayer = primary
        private set
    private var idle: FadePlayer? = null
    private var generation = 0
    private val pending = mutableListOf<Cancelable>()
    private var run: FadeRun? = null
    private var closed = false

    val isFading: Boolean get() = run != null

    private class FadeRun(
        val old: FadePlayer,
        val new: FadePlayer,
        val lengthMs: Long,
        var elapsedMs: Long = 0,
        var lastTickMs: Long,
        var tailStopped: Boolean = false,
        var ticker: Cancelable? = null,
    )

    // ---- events from the active player (the service forwards them) ----

    /** The active player moved to another song, by itself or by a command, or became ready. */
    fun onActiveChanged() = guarded("onActiveChanged") {
        if (closed) return@guarded
        if (run != null) interrupt("the active player changed song or position during the fade") else arm()
    }

    /** The active player became ready (a new song loaded). */
    fun onActiveReady() = guarded("onActiveReady") { if (!closed && run == null) arm() }

    /** The owner paused or resumed; during a fade the outgoing tail must follow. */
    fun onActivePlayWhenReady(value: Boolean) = guarded("onActivePlayWhenReady") {
        val r = run ?: return@guarded
        if (!r.tailStopped) r.old.playWhenReady = value
    }

    /** A seek, a skip, an error or anything else that ends the overlap at once (contract 8). */
    fun onActiveInterrupted(why: String) = guarded("onActiveInterrupted") { if (run != null) interrupt(why) }

    /** The settings changed; applies at the next join, never to the song that is playing (contract 5.4). */
    fun onSettingsChanged() = guarded("onSettingsChanged") { if (!closed && run == null) arm() }

    /** Releases the second player and cancels everything; safe to call twice. */
    fun close() {
        if (closed) return
        closed = true
        val others = listOfNotNull(idle, run?.old)
        try { cancelPending(); run?.let { stopTail(it); it.ticker?.cancel() }; run = null } catch (e: Throwable) { log("close: ${e.message}") }
        others.forEach { try { twin.release(it) } catch (e: Throwable) { log("close: release ${e.message}") } }
        idle = null
    }

    // ---- planning ----

    private fun arm() {
        cancelPending()
        val s = settings()
        if (!s.enabled) {
            idle?.let { idle = null; twin.release(it); log("crossfade off: second player released") }
            return
        }
        val decision = CrossfadePlanner.plan(s, context(active, buffered = Long.MAX_VALUE))
        if (decision !is CrossfadeDecision.Fade) {
            log("no fade: ${(decision as CrossfadeDecision.None).reason}")
            return
        }
        val other = idle ?: twin.acquire(active).also { idle = it } ?: run { log("no fade: second player unavailable"); return }
        val gen = ++generation
        val prepareAt = (decision.startAtMs - PREP_BEFORE_MS).coerceAtLeast(0)
        pending += active.runAtPosition(prepareAt) { guarded("prepare") { prepare(gen, other) } }
        pending += active.runAtPosition(decision.startAtMs) { guarded("fade") { start(gen, other) } }
        if (active.positionMs >= prepareAt) prepare(gen, other)
    }

    private fun context(p: FadePlayer, buffered: Long, automatic: Boolean = true) = JoinContext(
        current = p.currentSong?.copy(durationMs = p.durationMs ?: p.currentSong?.durationMs),
        next = p.nextSong,
        repeat = p.repeat,
        nextIsSameEntry = p.nextIsSameEntry,
        automatic = automatic,
        nextBufferedMs = buffered,
    )

    private fun prepare(gen: Int, other: FadePlayer) {
        if (gen != generation || closed) return
        val next = active.nextSong ?: return
        other.volume = 0f
        other.playWhenReady = false
        if (!other.prepareOn(next.songId)) log("the second player does not have ${next.songId}; the join plays as today")
    }

    private fun start(gen: Int, other: FadePlayer) {
        if (gen != generation || closed || run != null) return
        val old = active
        val next = old.nextSong
        // Check again with what is really buffered; a join that is not ready is played as today, with no wait (contract 5.1).
        val decision = CrossfadePlanner.plan(settings(), context(old, buffered = other.bufferedMs))
        val ready = other.isReady && next != null && other.currentSong?.songId == next.songId
        if (decision !is CrossfadeDecision.Fade || !ready) {
            log("fade skipped: ${(decision as? CrossfadeDecision.None)?.reason ?: "second player not on the next song or not ready"}")
            return
        }
        val length = decision.lengthMs
        other.volume = 0f
        old.setFocusHandling(false) // first, or the incoming player's focus request pauses the outgoing one
        other.setFocusHandling(true)
        other.playWhenReady = old.playWhenReady
        val r = FadeRun(old, other, length, lastTickMs = scheduler.nowMs())
        try {
            swapSession(other)
        } catch (e: Throwable) {
            // Nothing is committed yet: put focus and the second player back, and let the outgoing song play on as today.
            other.playWhenReady = false
            other.setFocusHandling(false)
            old.setFocusHandling(true)
            throw e
        }
        run = r
        active = other
        idle = null
        log("fade start: ${old.name} -> ${other.name}, $length ms")
        schedule(r)
    }

    private fun schedule(r: FadeRun) {
        r.ticker = scheduler.postDelayed(TICK_MS) { guarded("tick") { tick(r) } }
    }

    private fun tick(r: FadeRun) {
        if (run !== r || closed) return
        val now = scheduler.nowMs()
        if (r.new.playWhenReady) r.elapsedMs += (now - r.lastTickMs).coerceAtLeast(0)
        r.lastTickMs = now
        val t = FadeCurve.progress(r.elapsedMs, r.lengthMs)
        r.new.volume = FadeCurve.incoming(t)
        if (!r.tailStopped) r.old.volume = FadeCurve.outgoing(t)
        val left = r.old.durationMs?.let { it - r.old.positionMs }
        if (!r.tailStopped && left != null && left <= TAIL_GUARD_MS) stopTail(r)
        if (t >= 1.0) complete(r) else schedule(r)
    }

    private fun stopTail(r: FadeRun) {
        r.tailStopped = true
        r.old.playWhenReady = false
        r.old.volume = 0f
    }

    private fun complete(r: FadeRun) {
        finish(r, "complete")
    }

    private fun interrupt(why: String) {
        val r = run ?: return
        finish(r, "interrupted: $why")
    }

    private fun finish(r: FadeRun, how: String) {
        r.ticker?.cancel()
        run = null
        r.old.playWhenReady = false
        r.old.volume = 1f
        r.new.volume = 1f
        idle = r.old
        log("fade $how")
        if (!closed) arm()
    }

    private fun cancelPending() {
        pending.forEach { it.cancel() }
        pending.clear()
        generation++
    }

    /** A fault never stops the music: end any fade, leave the active player at full volume and the other paused. */
    private fun guarded(what: String, block: () -> Unit) {
        try {
            block()
        } catch (e: Throwable) {
            log("$what failed: ${e.javaClass.simpleName}: ${e.message}")
            try {
                cancelPending()
                val r = run
                run = null
                r?.ticker?.cancel()
                (r?.old ?: idle)?.let { it.playWhenReady = false; it.volume = 1f }
                active.volume = 1f
                r?.let { idle = it.old }
            } catch (inner: Throwable) {
                log("recovery after $what failed: ${inner.message}")
            }
        }
    }

    companion object {
        /** The second player is moved to the next song this long before the fade (the spike used 10 s). */
        const val PREP_BEFORE_MS = 10_000L
        const val TICK_MS = 10L

        /** The outgoing player is paused this close to its own end, so it cannot advance by itself (spike bug 2). */
        const val TAIL_GUARD_MS = 80L
    }
}
