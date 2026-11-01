package app.discair.player

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/** Tracks shorter than this never scrobble (they still send now-playing). */
const val MIN_SCROBBLE_TRACK_SEC = 30
const val MAX_SCROBBLE_THRESHOLD_MS = 240_000L

/** One tick may credit at most this much played time, so a jump (a seek or a stall) is never credited. */
const val MAX_TICK_CREDIT_MS = 2_000L

/** If the server and the player disagree on duration by more than this share, the larger applies. */
const val DURATION_DISAGREEMENT = 0.10

/** A play is one run of one queue entry. Repeat-one loops and replays are new plays. */
data class Play(val playId: String, val songId: String, val startTimeMs: Long)

object ScrobbleRules {
    /** The duration to judge by, or null when neither source knows it. */
    fun effectiveDurationSec(serverSec: Int, playerSec: Int?): Int? {
        val server = serverSec.takeIf { it > 0 }
        val player = playerSec?.takeIf { it > 0 }
        return when {
            server != null && player != null ->
                if (abs(server - player).toDouble() / max(server, player) > DURATION_DISAGREEMENT) max(server, player) else server
            server != null -> server
            else -> player
        }
    }

    /** Unknown duration is eligible: the threshold then falls back to the four-minute limit. */
    fun isEligible(durationSec: Int?) = durationSec == null || durationSec >= MIN_SCROBBLE_TRACK_SEC

    fun thresholdMs(durationSec: Int?): Long =
        if (durationSec == null) MAX_SCROBBLE_THRESHOLD_MS else min(durationSec * 500L, MAX_SCROBBLE_THRESHOLD_MS)
}

/**
 * Counts the media time actually played for one play. It never reads the clock: the player reports
 * its position, and only small forward steps while advancing are credited. Seeks, pauses and
 * buffering add nothing and subtract nothing, and playback speed does not matter because the
 * position is media time.
 */
class ScrobbleTracker(
    val play: Play,
    private val serverDurationSec: Int,
    nowPlayingAlreadySent: Boolean = false,
) {
    private var playerDurationSec: Int? = null
    private var lastPositionMs: Long? = null
    private var nowPlayingSent = nowPlayingAlreadySent
    private var due = false

    var playedMs: Long = 0
        private set

    /** The player's own duration, once it is finite and positive. */
    fun onPlayerDuration(sec: Int) { if (sec > 0) playerDurationSec = sec }

    /** True the first time the item reaches playing: the caller sends now-playing exactly once. */
    fun onPlaying(): Boolean {
        if (nowPlayingSent) return false
        nowPlayingSent = true
        return true
    }

    /** The user sought: the next tick starts from the new position. */
    fun onSeek(positionMs: Long) { lastPositionMs = positionMs }

    /** Buffering or a stall: the next tick starts from where playback resumes. */
    fun onStall() { lastPositionMs = null }

    /** True once, when the play has reached the threshold. */
    fun onTick(positionMs: Long, advancing: Boolean): Boolean {
        if (!advancing) { lastPositionMs = positionMs; return false }
        val last = lastPositionMs
        lastPositionMs = positionMs
        if (last != null) {
            val delta = positionMs - last
            if (delta in 1..MAX_TICK_CREDIT_MS) playedMs += delta
        }
        if (due) return false
        val duration = ScrobbleRules.effectiveDurationSec(serverDurationSec, playerDurationSec)
        if (!ScrobbleRules.isEligible(duration)) return false
        if (playedMs < ScrobbleRules.thresholdMs(duration)) return false
        due = true
        return true
    }
}
