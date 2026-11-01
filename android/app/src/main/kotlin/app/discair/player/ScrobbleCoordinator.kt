package app.discair.player

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** What happened to one scrobble request. */
sealed interface SendOutcome {
    /** Navidrome accepted it. */
    data object Accepted : SendOutcome

    /** The request was provably never sent (no connection, DNS failure, connect timeout). Safe to retry. */
    data object NotSent : SendOutcome

    /** The request may have reached Navidrome (read timeout, reset, 5xx, error body). Never retried. */
    data object Ambiguous : SendOutcome
}

interface ScrobbleApi {
    suspend fun send(songId: String, submission: Boolean, timeMs: Long): SendOutcome
}

val SCROBBLE_RETRY_DELAYS_MS = listOf(2_000L, 10_000L, 30_000L)

/**
 * Decides when to send now-playing and the final scrobble, and sends them. Retry rules
 * (ANDROID_PLAYER_CONTRACT section 4): only a request that was provably not sent is retried, at most
 * three times, keeping the play's original start time; an ambiguous outcome drops the scrobble so a
 * lost response can never become a duplicate. Now-playing is never retried. Failures never reach playback.
 */
class ScrobbleCoordinator(
    private val api: ScrobbleApi,
    private val scope: CoroutineScope,
    private val newPlayId: () -> String = { java.util.UUID.randomUUID().toString() },
    private val retryDelaysMs: List<Long> = SCROBBLE_RETRY_DELAYS_MS,
    enabled: Boolean = true,
) {
    private var enabled = enabled
    private var current: ScrobbleTracker? = null
    private var currentSong: String? = null
    private var currentDurationSec = 0
    private var currentStartMs = 0L
    private var currentPlayerDurationSec: Int? = null
    private val submitted = mutableSetOf<String>()
    private val pending = mutableMapOf<String, Job>()

    /** A new play: a new queue entry, a repeat-one loop, or the same song chosen again. */
    @Synchronized
    fun startPlay(songId: String, serverDurationSec: Int, startTimeMs: Long) {
        currentSong = songId
        currentDurationSec = serverDurationSec
        currentStartMs = startTimeMs
        currentPlayerDurationSec = null
        current = if (enabled) ScrobbleTracker(Play(newPlayId(), songId, startTimeMs), serverDurationSec) else null
    }

    /** The queue was cleared or playback ended: nothing more counts for the current play. */
    @Synchronized
    fun endPlay() { current = null; currentSong = null }

    @Synchronized
    fun onPlayerDuration(sec: Int) {
        if (sec > 0) currentPlayerDurationSec = sec
        current?.onPlayerDuration(sec)
    }

    /** The item reached playing (not just the play intent). */
    @Synchronized
    fun onPlaying() {
        val tracker = current ?: return
        if (tracker.onPlaying()) {
            val play = tracker.play
            scope.launch { sendQuietly(play.songId, false, play.startTimeMs) }
        }
    }

    @Synchronized
    fun onTick(positionMs: Long, advancing: Boolean) {
        val tracker = current ?: return
        if (tracker.onTick(positionMs, advancing)) submit(tracker.play)
    }

    @Synchronized fun onSeek(positionMs: Long) { current?.onSeek(positionMs) }
    @Synchronized fun onStall() { current?.onStall() }

    /**
     * The Settings toggle. Off suppresses now-playing and the final scrobble, cancels every pending
     * retry and sends nothing for the current play even if the threshold was passed but unsent.
     * On mid-track counts from that moment with no backfill and does not send a now-playing ping.
     */
    @Synchronized
    fun setEnabled(on: Boolean) {
        if (on == enabled) return
        enabled = on
        if (!on) {
            pending.values.forEach { it.cancel() }
            pending.clear()
            current = null
        } else {
            val song = currentSong ?: return
            current = ScrobbleTracker(
                Play(newPlayId(), song, currentStartMs), currentDurationSec, nowPlayingAlreadySent = true,
            ).also { t -> currentPlayerDurationSec?.let(t::onPlayerDuration) }
        }
    }

    private fun submit(play: Play) {
        if (!submitted.add(play.playId)) return // sent once; only the retry path below sends again
        pending[play.playId] = scope.launch {
            var attempt = 0
            while (true) {
                when (sendQuietly(play.songId, true, play.startTimeMs)) {
                    SendOutcome.Accepted, SendOutcome.Ambiguous -> break
                    SendOutcome.NotSent -> {
                        if (attempt >= retryDelaysMs.size) break
                        delay(retryDelaysMs[attempt++])
                    }
                }
            }
            synchronized(this@ScrobbleCoordinator) { pending.remove(play.playId) }
        }
    }

    private suspend fun sendQuietly(songId: String, submission: Boolean, timeMs: Long): SendOutcome = try {
        api.send(songId, submission, timeMs)
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        // The failure is unknown, so treat it as ambiguous: never retried, never reaches playback.
        SendOutcome.Ambiguous
    }
}
