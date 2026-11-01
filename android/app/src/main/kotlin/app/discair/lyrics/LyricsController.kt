package app.discair.lyrics

import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.runInterruptible

/** What the Lyrics view draws (contract 7). Every state is written out; none depends on colour alone. */
sealed interface LyricsUiState {
    /** The view is not open, or no song is chosen. */
    data object Idle : LyricsUiState
    data class Loading(val songId: String) : LyricsUiState

    /** [savedCopy] is true when the phone could not refresh and this is the saved copy. */
    class Ready(val songId: String, val lyrics: Lyrics, val savedCopy: Boolean = false) : LyricsUiState {
        override fun toString() = "Ready(songId=$songId, $lyrics, savedCopy=$savedCopy)"
    }
    data class None(val songId: String) : LyricsUiState
    data class Unsupported(val songId: String) : LyricsUiState

    /** [problem] decides the words; Try again is offered for every one of these. */
    data class Failed(val songId: String, val problem: LyricsProblem) : LyricsUiState
}

/** The words for a failed lookup, in the same terms as the rest of the app. */
fun lyricsFailureText(problem: LyricsProblem) = when (problem) {
    LyricsProblem.Unreachable -> "Can't reach Navidrome. Is Tailscale connected?"
    LyricsProblem.Unauthorised -> "Navidrome rejected the saved login. Sign in again from Settings."
    LyricsProblem.Other -> "Navidrome could not give the lyrics."
}

/**
 * Fetches lyrics for the song that is playing, only while the Lyrics view is open (contract 8):
 * cache first (a cached entry shows at once and is refreshed at most daily), one request at a time,
 * the next song's lyrics fetched in the background once the current ones are showing, and everything
 * cancelled when the view closes or the song changes. Call from one thread (main); lookups run on [io].
 */
class LyricsController(
    private val scope: CoroutineScope,
    private val source: LyricsSource,
    private val cache: LyricsCache,
    private val io: CoroutineDispatcher,
) {
    private val _state = MutableStateFlow<LyricsUiState>(LyricsUiState.Idle)
    val state: StateFlow<LyricsUiState> = _state.asStateFlow()

    private var job: Job? = null
    private var unsupported = false

    /** The view is open for [songId]; [nextSongId] is prefetched once these lyrics are showing. */
    fun open(songId: String, nextSongId: String?) {
        job?.cancel()
        job = scope.launch { load(songId, nextSongId) }
    }

    /** The view closed, or playback ended: nothing more is fetched. */
    fun close() {
        job?.cancel(); job = null
        _state.value = LyricsUiState.Idle
    }

    fun retry(songId: String, nextSongId: String?) = open(songId, nextSongId)

    private suspend fun load(songId: String, nextSongId: String?) {
        if (unsupported) { _state.value = LyricsUiState.Unsupported(songId); return }
        val cached = cache.get(songId)
        if (cached != null) {
            _state.value = fromCache(songId, cached)
            if (cached.needsRefresh) refresh(songId, keepShowing = cached) // a failed refresh keeps the saved copy
        } else {
            _state.value = LyricsUiState.Loading(songId)
            fetch(songId, keepShowing = null)
        }
        prefetch(nextSongId)
    }

    private fun fromCache(songId: String, c: CachedLyrics, savedCopy: Boolean = false): LyricsUiState =
        c.lyrics?.let { LyricsUiState.Ready(songId, it, savedCopy) } ?: LyricsUiState.None(songId)

    private suspend fun refresh(songId: String, keepShowing: CachedLyrics) = fetch(songId, keepShowing)

    /** One lookup. A failure with a saved copy keeps showing it, marked as a saved copy. */
    private suspend fun fetch(songId: String, keepShowing: CachedLyrics?) {
        val answer = try {
            runInterruptible(io) { source.lyrics(songId) }
        } catch (e: LyricsException) {
            _state.value = if (keepShowing != null) fromCache(songId, keepShowing, savedCopy = true) else LyricsUiState.Failed(songId, e.problem)
            return
        }
        when (answer) {
            is LyricsAnswer.Found -> { cache.put(songId, answer.lyrics); _state.value = LyricsUiState.Ready(songId, answer.lyrics) }
            LyricsAnswer.None -> { cache.put(songId, null); _state.value = LyricsUiState.None(songId) }
            LyricsAnswer.Unsupported -> { unsupported = true; _state.value = LyricsUiState.Unsupported(songId) }
        }
    }

    /** Quietly fills the cache for the next song; its result is never shown and its failure is ignored. */
    private suspend fun prefetch(nextSongId: String?) {
        if (nextSongId == null || unsupported) return
        val cached = cache.get(nextSongId)
        if (cached != null && !cached.needsRefresh) return
        try {
            when (val answer = runInterruptible(io) { source.lyrics(nextSongId) }) {
                is LyricsAnswer.Found -> cache.put(nextSongId, answer.lyrics)
                LyricsAnswer.None -> cache.put(nextSongId, null)
                LyricsAnswer.Unsupported -> unsupported = true
            }
        } catch (e: LyricsException) {
            // Prefetch is a convenience; the real lookup happens, with its states, when the song plays.
        }
    }
}
