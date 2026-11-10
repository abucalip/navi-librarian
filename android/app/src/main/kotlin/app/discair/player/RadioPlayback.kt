package app.discair.player

import app.discair.model.RadioDownload
import app.discair.model.RadioGetResult
import app.discair.model.RadioNow
import app.discair.model.RadioNowState
import app.discair.model.RadioStation
import app.discair.model.radioDownloadState
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** What the radio screens draw: the station on air, the live song the server reports, and the state of each Download. */
data class RadioLive(
    val stationId: String? = null,
    val stationName: String = "",
    val proxied: Boolean = false,
    val logoUrl: String = "",
    val favourite: Boolean = false,
    val now: RadioNow? = null,
    /** Play ids whose Get was accepted on this device. The server's own `grabbed` flag is added by the Heard list. */
    val requested: Set<Long> = emptySet(),
    val working: Set<Long> = emptySet(),
    /** Play id to the server's refusal text, for a Try again. */
    val failed: Map<Long, String> = emptyMap(),
    /** The last Get outcome, as text for a live region. */
    val message: String? = null,
) {
    val active: Boolean get() = stationId != null

    /** The state of the Download control for the song on air. */
    val download: RadioDownload
        get() {
            val n = now
            return radioDownloadState(n?.playId, n?.inLibrary == true, n?.playId in requested, n?.playId in working, n?.playId in failed)
        }

    /** The state for a song in the Heard list; [grabbed] and [inLibrary] come from the server's row. */
    fun downloadFor(playId: Long, grabbed: Boolean, inLibrary: Boolean): RadioDownload =
        radioDownloadState(playId, inLibrary, grabbed || playId in requested, playId in working, playId in failed)
}

/** The line shown under the station name everywhere a song would show its artist (mini player, island, lock screen). */
fun radioLiveLine(now: RadioNow?): String = when {
    now == null -> "Live radio"
    now.state == RadioNowState.Unavailable -> "Station unreachable."
    else -> now.songLine ?: "Live radio"
}

/**
 * Plays a radio station through the one [PlayerController] and keeps the live song fresh (docs/RADIO_PLAYBACK_CONTRACT.md
 * sections 3.2 and 4). The server decides what is playing: this class only asks `/now` every [pollMs] while the stream is
 * sounding or buffering, shows the answer, and sends the Download request. It never splits an artist from a title and
 * never downloads anything itself. Call from the main thread; [nowFor], [getPlay] and [artwork] run on [io].
 */
class RadioPlayback(
    private val controller: PlayerController,
    private val scope: CoroutineScope,
    private val io: CoroutineDispatcher,
    private val nowFor: (String) -> RadioNow,
    private val getPlay: (Long) -> RadioGetResult,
    /** Saves a station's favourite flag and returns what the server kept. */
    private val saveFavourite: (String, Boolean) -> Boolean = { _, wanted -> wanted },
    private val absolute: (String) -> String,
    /** The bytes of a picture for the notification and lock screen; null when it cannot be loaded. */
    private val artwork: suspend (String) -> ByteArray? = { null },
    private val pollMs: Long = 5_000,
) {
    private val _state = MutableStateFlow(RadioLive())
    val state: StateFlow<RadioLive> = _state.asStateFlow()
    private var poll: Job? = null
    private var shownLine: String? = null
    private var shownCover: String? = null

    /** Starts [station], replacing whatever was playing. */
    fun play(station: RadioStation) {
        poll?.cancel()
        shownLine = null
        shownCover = null
        val logo = absolute(station.logoUrl) + "?size=512" // the logo route serves 128 or 512 only
        controller.playItems(
            listOf(
                QueueItem(
                    songId = RADIO_ID_PREFIX + station.id, title = station.name, artist = radioLiveLine(null), album = "Radio",
                    coverUrl = logo, liveUrl = absolute(station.playableUrl),
                ),
            ),
        )
        _state.update { RadioLive(station.id, station.name, station.proxied, logo, favourite = station.favourite, requested = it.requested, working = it.working, failed = it.failed) }
        // A station that is not relayed has no live title (contract section 6): nothing to ask.
        if (station.proxied) poll = scope.launch { pollLoop(station.id, logo) } else _state.update { it.copy(now = RadioNow.Unknown.copy(state = RadioNowState.NotProxied)) }
    }

    /** True while a station is the current item; false once a song or nothing replaces it. */
    private fun onAir(stationId: String) = controller.state.value.current?.songId == RADIO_ID_PREFIX + stationId

    private suspend fun pollLoop(stationId: String, logo: String) {
        while (true) {
            if (!onAir(stationId)) { _state.update { RadioLive(requested = it.requested, working = it.working, failed = it.failed) }; return }
            val s = controller.state.value
            // No question to the server while paused: nothing is heard, and an idle relay holds no title.
            if (s.isPlaying || s.buffering) refresh(stationId, logo)
            delay(pollMs)
        }
    }

    private suspend fun refresh(stationId: String, logo: String) {
        val now = try {
            withContext(io) { nowFor(stationId) }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            return // keep the last words; a failed poll is not a state of the station
        }
        if (!onAir(stationId)) return
        _state.update { it.copy(now = now) }
        val line = radioLiveLine(now)
        val cover = now.coverUrl?.let(absolute) ?: logo
        if (line == shownLine && cover == shownCover) return
        val bytes = if (cover != shownCover) try { withContext(io) { artwork(cover) } } catch (e: CancellationException) { throw e } catch (e: Exception) { null } else null
        shownLine = line
        shownCover = cover
        if (onAir(stationId)) controller.updateLive(stationId, line, cover, bytes)
    }

    /** Sends the Download for [playId] unless it is already working, requested or owned. The server's message is kept as text. */
    fun download(playId: Long) {
        val s = _state.value
        if (playId in s.working || playId in s.requested) return
        _state.update { it.copy(working = it.working + playId, failed = it.failed - playId, message = null) }
        scope.launch {
            val result = try {
                withContext(io) { getPlay(playId) }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                RadioGetResult(false, "The request could not be sent. Try again.")
            }
            _state.update {
                if (result.ok) it.copy(working = it.working - playId, requested = it.requested + playId, message = result.message)
                else it.copy(working = it.working - playId, failed = it.failed + (playId to result.message), message = result.message)
            }
        }
    }

    /** Flips the favourite of the station on air; shown at once and put back if the server did not save it. */
    fun toggleFavourite() {
        val s = _state.value
        val id = s.stationId ?: return
        val wanted = !s.favourite
        _state.update { it.copy(favourite = wanted, message = null) }
        scope.launch {
            try {
                val saved = withContext(io) { saveFavourite(id, wanted) }
                _state.update { if (it.stationId == id) it.copy(favourite = saved) else it }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                _state.update { if (it.stationId == id) it.copy(favourite = !wanted, message = "Could not save the favourite. Try again.") else it }
            }
        }
    }

    /** Stops asking the server; the controller owns the audio. */
    fun stop() {
        poll?.cancel()
        poll = null
        _state.update { RadioLive(requested = it.requested, working = it.working, failed = it.failed) }
    }
}
