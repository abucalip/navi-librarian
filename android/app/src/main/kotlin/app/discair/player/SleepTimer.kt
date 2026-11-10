package app.discair.player

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** The lengths offered, in minutes. A live stream has no "end of song", so there are only fixed lengths. */
val SLEEP_TIMER_MINUTES = listOf(15, 30, 45, 60, 90)

/**
 * Stops playback after a chosen time (docs/RADIO_PLAYBACK_CONTRACT.md section 4). The app had no sleep timer before radio, so
 * this is the first one; it is not tied to radio, and the shell cancels it when a station is no longer playing. When time is up
 * it calls [onExpire] once (the shell passes the controller's pause, which also ends any wait to reconnect). Call from the main thread.
 */
class SleepTimer(
    private val scope: CoroutineScope,
    private val onExpire: () -> Unit,
    private val clock: () -> Long = System::currentTimeMillis,
    private val tickMs: Long = 1_000,
) {
    private val _remainingMs = MutableStateFlow<Long?>(null)

    /** Time left, or null when no timer is running. */
    val remainingMs: StateFlow<Long?> = _remainingMs.asStateFlow()
    private var job: Job? = null

    /** Starts, or restarts, a timer of [minutes]. */
    fun start(minutes: Int) {
        job?.cancel()
        val ms = minutes.coerceAtLeast(1) * 60_000L
        val endAt = clock() + ms
        _remainingMs.value = ms
        job = scope.launch {
            while (true) {
                delay(tickMs)
                val left = endAt - clock()
                if (left <= 0) {
                    _remainingMs.value = null
                    job = null
                    onExpire()
                    return@launch
                }
                _remainingMs.value = left
            }
        }
    }

    fun cancel() {
        job?.cancel()
        job = null
        _remainingMs.value = null
    }
}

/** The words for the timer control: what is set, or that it is off. Minutes are rounded up so "1 min" is the last thing shown. */
fun sleepTimerText(remainingMs: Long?): String {
    if (remainingMs == null) return "Sleep timer: off"
    val minutes = ((remainingMs + 59_999) / 60_000).toInt().coerceAtLeast(1)
    return "Sleep timer: stops in $minutes min"
}
