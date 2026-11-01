package app.discair.data

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import app.discair.model.AcquisitionJob
import app.discair.model.GetState
import app.discair.model.activeCount
import app.discair.model.getKey
import app.discair.model.orderAcquisitions
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.isActive
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonObject

/** What a row's action is doing; a row with an entry here cannot be acted on again until the server answers. */
enum class RowBusy { Retrying, Skipping, Dismissing }

/**
 * Everything the app knows about acquisitions (contract 5.3), shared by the Get buttons and the
 * Downloads screen so they never disagree. The server decides; this class only relays and records
 * what it answered. Nothing is shown as requested, retried or dismissed before the server confirms.
 *
 * Live progress: while the Downloads screen is [watch]ed it reads the SSE stream and falls back to
 * polling the snapshot route if the stream drops. Otherwise the list is refreshed every
 * [BACKGROUND_POLL_MS] for the badge, as the web nav does. No notifications and no service (owner decision).
 */
class AcquisitionHub(
    private val repo: () -> AcquisitionApi,
    private val scope: CoroutineScope,
    private val io: CoroutineDispatcher,
) {
    private val gets = mutableStateMapOf<String, GetState>()
    private val busy = mutableStateMapOf<String, RowBusy>()

    /** Newest request first; null until the first snapshot arrives. */
    var jobs: List<AcquisitionJob>? by mutableStateOf(null)
        private set

    /** Set when the list could not be read; cleared by the next good snapshot. */
    var listProblem: String? by mutableStateOf(null)
        private set

    /** True while the SSE stream is delivering; false while polling or idle. */
    var live: Boolean by mutableStateOf(false)
        private set

    val activeDownloads: Int get() = jobs?.let(::activeCount) ?: 0

    private val _messages = MutableSharedFlow<String>(extraBufferCapacity = 8)

    /** One-line outcomes to announce (a Get that failed, a dismissal the server refused). */
    val messages: SharedFlow<String> = _messages.asSharedFlow()

    private var watchers = 0
    private var watchJob: Job? = null
    private var pollJob: Job? = null

    fun getState(artist: String, album: String, title: String? = null): GetState =
        gets[getKey(artist, album, title)] ?: GetState.Idle

    fun busy(job: AcquisitionJob): RowBusy? = busy[job.key]

    /** Album Get. A request already pending or accepted is not sent twice (ACQ-02). */
    fun getAlbum(artist: String, album: String, metadata: JsonObject) =
        launch(getKey(artist, album), "$album requested") { repo().acquireAlbum(artist, album, metadata) }

    /** Song Get; the server files the song with [album]. */
    fun getTrack(artist: String, album: String, title: String, trackNumber: Int?, year: Int?, metadata: JsonObject? = null) =
        launch(getKey(artist, album, title), "$title requested") {
            repo().acquireTrack(artist, album, title, trackNumber, year, metadata)
        }

    private fun launch(key: String, fallback: String, send: () -> GetState) {
        when (gets[key]) {
            GetState.Pending, is GetState.Requested -> return
            else -> Unit
        }
        gets[key] = GetState.Pending
        scope.launch {
            val outcome = try {
                withContext(io) { send() }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                GetState.Failed(e.message ?: "The request could not be sent.")
            }
            gets[key] = outcome
            when (outcome) {
                is GetState.Failed -> _messages.tryEmit(outcome.message)
                is GetState.Requested -> {
                    _messages.tryEmit(outcome.message ?: fallback)
                    refreshOnce()
                }
                else -> Unit
            }
        }
    }

    /** Try again on a failed record: the same request the web sends, with the metadata the server stored. */
    fun retry(job: AcquisitionJob) = act(job, RowBusy.Retrying) {
        val reply = if (job.isSong) {
            repo().acquireTrack(job.artist, job.albumName, job.title, job.trackNumber, job.year, job.metadata)
        } else {
            repo().acquireAlbum(job.artist, job.album, job.metadata)
        }
        (reply as? GetState.Failed)?.let { throw IllegalStateException(it.message) }
        (reply as? GetState.Requested)?.message
    }

    fun skipSource(job: AcquisitionJob) = act(job, RowBusy.Skipping) {
        repo().skipSource(job.artist, job.album) ?: "Source switch requested."
    }

    /** Removes the record and its download files. The caller has already asked the owner to confirm. */
    fun dismiss(job: AcquisitionJob, onResult: (Boolean) -> Unit = {}) = act(job, RowBusy.Dismissing, onResult) {
        val message = repo().dismissAcquisition(job.artist, job.album)
        // The server removed it; drop it now so the row does not linger until the next snapshot.
        jobs = jobs?.filterNot { it.key == job.key }
        // A Get remembered for this album may be asked again once the record is gone.
        gets.remove(getKey(job.artist, job.albumName))
        if (job.isSong) gets.remove(getKey(job.artist, job.albumName, job.title))
        message
    }

    /** Dismisses every imported record one by one; reports how many the server refused. */
    fun dismissImported() {
        val imported = jobs.orEmpty().filter { it.isImported }
        if (imported.isEmpty()) return
        scope.launch {
            var failed = 0
            for (job in imported) {
                busy[job.key] = RowBusy.Dismissing
                try {
                    withContext(io) { repo().dismissAcquisition(job.artist, job.album) }
                    jobs = jobs?.filterNot { it.key == job.key }
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    failed += 1
                } finally {
                    busy.remove(job.key)
                }
            }
            _messages.tryEmit(
                if (failed > 0) "$failed ${if (failed == 1) "import" else "imports"} could not be dismissed."
                else "Dismissed ${imported.size} ${if (imported.size == 1) "import" else "imports"}.",
            )
        }
    }

    private fun act(job: AcquisitionJob, kind: RowBusy, onResult: (Boolean) -> Unit = {}, send: () -> String?) {
        if (busy.containsKey(job.key)) return
        busy[job.key] = kind
        scope.launch {
            try {
                val message = withContext(io) { send() }
                message?.let { _messages.tryEmit(it) }
                onResult(true)
                if (kind != RowBusy.Dismissing) refreshOnce()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                // A 409 on Dismiss is a refusal, and says so in the server's words.
                val prefix = if (kind == RowBusy.Dismissing) "Not dismissed: " else ""
                _messages.tryEmit(prefix + (e.message ?: "The server did not accept this."))
                onResult(false)
            } finally {
                busy.remove(job.key)
            }
        }
    }

    /** One read of the snapshot route. Errors keep the rows already known and set [listProblem]. */
    suspend fun refreshOnce() {
        try {
            val fresh = withContext(io) { repo().acquisitions() }
            jobs = orderAcquisitions(fresh)
            listProblem = null
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            listProblem = e.message ?: "The downloads could not be read."
        }
    }

    /** Keeps the badge fresh whenever the signed-in shell is shown. */
    fun start() {
        if (pollJob?.isActive == true) return
        pollJob = scope.launch {
            while (true) {
                if (watchers == 0) refreshOnce()
                delay(BACKGROUND_POLL_MS)
            }
        }
    }

    /** The Downloads screen is visible: read the stream (polling if it drops). Balanced by [unwatch]. */
    fun watch() {
        watchers += 1
        if (watchJob?.isActive == true) return
        watchJob = scope.launch { followStream() }
    }

    fun unwatch() {
        watchers = (watchers - 1).coerceAtLeast(0)
        if (watchers == 0) {
            watchJob?.cancel()
            watchJob = null
            live = false
        }
    }

    fun stop() {
        pollJob?.cancel()
        watchJob?.cancel()
        pollJob = null
        watchJob = null
        live = false
    }

    private suspend fun followStream() {
        while (true) {
            currentCoroutineContext().ensureActive()
            refreshOnce() // an immediate picture, then the stream takes over
            try {
                withContext(io) {
                    val context = currentCoroutineContext()
                    repo().acquisitionStream(
                        onSnapshot = { snapshot ->
                            // Throwing ends the read and closes the connection once the screen has left.
                            if (!context.isActive) throw StopStream()
                            jobs = orderAcquisitions(snapshot)
                            listProblem = null
                            live = true
                        },
                        onProblem = { listProblem = it },
                    )
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                listProblem = e.message ?: "The live updates stopped."
            }
            live = false
            delay(POLL_FALLBACK_MS) // falls back to polling: the loop's refreshOnce, then a retry of the stream
        }
    }

    companion object {
        const val BACKGROUND_POLL_MS = 30_000L
        const val POLL_FALLBACK_MS = 5_000L
    }
}
