package app.discair.lyrics

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

/**
 * Which line is current for a playback position (contract 6). Pure: no clock, no player.
 * The current line is the last line whose start is at or before the position; before the first line,
 * and for plain or empty lyrics, no line is current ([NONE]). Offsets are already applied by [LyricsParse].
 */
class LyricsTimeline(lyrics: Lyrics?) {
    private val starts: LongArray =
        if (lyrics != null && lyrics.timed) LongArray(lyrics.lines.size) { lyrics.lines[it].startMs ?: Long.MAX_VALUE } else LongArray(0)

    val isTimed: Boolean get() = starts.isNotEmpty()

    /** Index of the current line, or [NONE]. */
    fun lineAt(positionMs: Long): Int {
        var low = 0
        var high = starts.size // first index whose start is after the position
        while (low < high) {
            val mid = (low + high) ushr 1
            if (starts[mid] <= positionMs) low = mid + 1 else high = mid
        }
        return low - 1
    }

    companion object { const val NONE = -1 }
}

/**
 * Keeps the current line up to date (contract 6). A check every [tickMs] runs only while the Lyrics view is
 * visible, the song is playing and a timed timeline is set; it stops otherwise, so it costs no battery in the
 * background. It is separate from the scrobble ticker and never touches it. A seek, skip or restart is shown
 * at once by calling [refresh]; a pause freezes the marker. Call everything from one thread (the main thread).
 */
class LyricsFollower(
    private val scope: CoroutineScope,
    private val position: () -> Long,
    private val tickMs: Long = 250,
) {
    private val _line = MutableStateFlow(LyricsTimeline.NONE)
    val line: StateFlow<Int> = _line

    private var timeline: LyricsTimeline? = null
    private var visible = false
    private var playing = false
    private var job: Job? = null

    /** True while the periodic check is running (for tests and diagnostics). */
    val isChecking: Boolean get() = job?.isActive == true

    fun setTimeline(value: LyricsTimeline?) { timeline = value; refresh(); reschedule() }
    fun setVisible(value: Boolean) { visible = value; if (value) refresh(); reschedule() }
    fun setPlaying(value: Boolean) { playing = value; reschedule() }

    /** Recomputes once from the player now: after a seek, a skip, a restart or a new song. */
    fun refresh() { _line.value = timeline?.lineAt(position()) ?: LyricsTimeline.NONE }

    private fun reschedule() {
        val shouldRun = visible && playing && timeline?.isTimed == true
        if (!shouldRun) { job?.cancel(); job = null; return }
        if (job?.isActive == true) return
        job = scope.launch {
            while (true) {
                refresh()
                delay(tickMs)
            }
        }
    }
}
