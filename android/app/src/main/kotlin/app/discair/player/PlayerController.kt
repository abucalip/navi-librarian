package app.discair.player

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** Everything the player screens draw. Text fields are words for the screen, never colour-only states. */
data class PlayerUiState(
    val queue: QueueState = QueueState(),
    val isPlaying: Boolean = false,
    val buffering: Boolean = false,
    val positionMs: Long = 0,
    val durationMs: Long = 0,
    /** A status the user should read (unavailable song, lost connection, unsupported format, queue cap). */
    val status: String? = null,
    /** Spoken once when the track changes (polite live region), not on every position update. */
    val announcement: String? = null,
    /** The stored login was rejected. Shown once; playback is paused. */
    val signInRequired: Boolean = false,
    /** A network failure paused playback; it resumes by itself when the connection returns, or by Retry. */
    val waitingForNetwork: Boolean = false,
) {
    val visible: Boolean get() = !queue.isEmpty
    val current: QueueItem? get() = queue.current
}

/**
 * The player's brain: it keeps the queue, mirrors it into the player, saves it, classifies failures and
 * feeds the scrobble coordinator. It holds no Android types, so it is tested with a fake [PlayerPort].
 * Call all methods from one thread (the main thread in the app).
 */
class PlayerController(
    private val port: PlayerPort,
    private val storage: QueueStorage,
    private val scrobbler: ScrobbleCoordinator,
    private val scope: CoroutineScope,
    private val clock: () -> Long = System::currentTimeMillis,
    private val tickMs: Long = 1_000,
    private val saveEveryTicks: Int = 5,
) : PortListener {
    private val _state = MutableStateFlow(PlayerUiState())
    val state: StateFlow<PlayerUiState> = _state.asStateFlow()

    private var ticker: Job? = null
    private var ticks = 0
    private var pendingStart = false
    private var fallbackTried = mutableSetOf<String>()
    private var restored = false

    init { port.listener = this }

    /** Restores the saved queue, paused. Safe to call once at start. */
    fun restore() {
        if (restored) return
        restored = true
        val saved = QueueCodec.decode(storage.read())
        if (saved.isEmpty) return
        _state.update { it.copy(queue = saved, positionMs = saved.positionMs) }
        port.setItems(saved.items, saved.index, saved.positionMs, playWhenReady = false)
        port.setShuffle(saved.shuffle)
        port.setRepeat(saved.repeat)
        port.setVolume(saved.volume)
    }

    // ---- Queue entry points (used by Phase 4's screens)

    /** Play album or play song: replaces the queue and starts at [startIndex]. */
    fun playItems(items: List<QueueItem>, startIndex: Int = 0) {
        if (items.isEmpty()) return
        val result = _state.value.queue.replace(items, startIndex)
        fallbackTried.clear()
        apply(result.state, capped = result.capped)
        scrobbler.endPlay()
        pendingStart = true
        port.setItems(result.state.items, result.state.index, 0, playWhenReady = true)
    }

    fun enqueue(items: List<QueueItem>) {
        val wasEmpty = _state.value.queue.isEmpty
        val result = _state.value.queue.enqueue(items)
        if (result.state.items.size == _state.value.queue.items.size) { notifyCap(result.capped); return }
        val added = result.state.items.drop(_state.value.queue.items.size)
        apply(result.state, capped = result.capped)
        if (wasEmpty) { pendingStart = true; port.setItems(result.state.items, 0, 0, playWhenReady = false) }
        else port.addItems(added, result.state.items.size - added.size)
    }

    fun playNext(items: List<QueueItem>) {
        val before = _state.value.queue
        if (before.isEmpty) { enqueue(items); return }
        val result = before.playNext(items)
        if (result.state.items.size == before.items.size) { notifyCap(result.capped); return }
        val count = result.state.items.size - before.items.size
        apply(result.state, capped = result.capped)
        port.addItems(result.state.items.subList(before.index + 1, before.index + 1 + count), before.index + 1)
    }

    fun remove(position: Int) {
        val before = _state.value.queue
        if (position !in before.items.indices) return
        val next = before.remove(position)
        val removedCurrent = position == before.index
        _state.update { it.copy(queue = next) }
        if (next.isEmpty) { clear(); return }
        port.removeAt(position)
        if (removedCurrent) { pendingStart = true }
        persist()
    }

    fun move(from: Int, to: Int) {
        val next = _state.value.queue.move(from, to)
        if (next == _state.value.queue) return
        _state.update { it.copy(queue = next) }
        port.move(from, to)
        persist()
    }

    /** Empties the queue and stops audio. */
    fun clear() {
        ticker?.cancel()
        scrobbler.endPlay()
        port.clear()
        storage.clear()
        pendingStart = false
        _state.update { PlayerUiState(queue = it.queue.clear()) }
    }

    /** Sign-out: same as clear, and nothing stays on disk. */
    fun signOut() = clear()

    // ---- Transport

    fun playPause() = if (_state.value.isPlaying) port.pause() else { _state.update { it.copy(waitingForNetwork = false) }; port.play() }
    fun next() = port.next()
    fun previous() = port.previous()

    fun skipTo(index: Int) {
        if (index !in _state.value.queue.items.indices) return
        pendingStart = true
        port.skipTo(index)
        port.play()
    }

    fun seekTo(ms: Long) {
        val target = ms.coerceIn(0, _state.value.durationMs.takeIf { it > 0 } ?: Long.MAX_VALUE)
        port.seekTo(target)
        scrobbler.onSeek(target)
        _state.update { it.copy(positionMs = target) }
    }

    fun setShuffle(on: Boolean) {
        port.setShuffle(on)
        _state.update { it.copy(queue = it.queue.copy(shuffle = on)) }
        persist()
    }

    fun cycleRepeat() {
        val next = when (_state.value.queue.repeat) { RepeatMode.Off -> RepeatMode.All; RepeatMode.All -> RepeatMode.One; RepeatMode.One -> RepeatMode.Off }
        port.setRepeat(next)
        _state.update { it.copy(queue = it.queue.withRepeat(next)) }
        persist()
    }

    fun setVolume(v: Float) {
        val next = _state.value.queue.withVolume(v)
        port.setVolume(next.volume)
        _state.update { it.copy(queue = next) }
    }

    fun dismissSignIn() = _state.update { it.copy(signInRequired = false) }
    fun dismissStatus() = _state.update { it.copy(status = null) }

    /** The connection came back: resume if a network failure had paused playback. */
    fun networkAvailable() { if (_state.value.waitingForNetwork) retryNow() }

    fun retryNow() {
        _state.update { it.copy(waitingForNetwork = false, status = null) }
        port.retry()
    }

    fun setScrobbling(on: Boolean) = scrobbler.setEnabled(on)

    // ---- Player events

    override fun onIsPlaying(playing: Boolean) {
        _state.update { it.copy(isPlaying = playing, status = if (playing) null else it.status, waitingForNetwork = if (playing) false else it.waitingForNetwork) }
        if (playing) {
            beginPlayIfPending()
            scrobbler.onPlaying()
            startTicker()
        } else {
            ticker?.cancel()
            scrobbler.onTick(port.positionMs, advancing = false)
            _state.update { it.copy(positionMs = port.positionMs) }
            persist()
        }
    }

    override fun onBuffering(buffering: Boolean) {
        _state.update { it.copy(buffering = buffering) }
        if (buffering) scrobbler.onStall()
    }

    override fun onItemChanged(index: Int, repeated: Boolean) {
        val queue = _state.value.queue
        if (index !in queue.items.indices) return
        val item = queue.items[index]
        _state.update { it.copy(queue = it.queue.skipTo(index), positionMs = port.positionMs, durationMs = 0, announcement = "${item.title} by ${item.artist}", status = null) }
        pendingStart = true
        if (port.isPlaying) beginPlayIfPending()
        persist()
    }

    override fun onEnded() {
        ticker?.cancel()
        scrobbler.endPlay()
        _state.update { it.copy(isPlaying = false) }
        persist()
    }

    override fun onDuration(durationMs: Long) {
        _state.update { it.copy(durationMs = durationMs) }
        if (durationMs > 0) scrobbler.onPlayerDuration((durationMs / 1000).toInt())
    }

    override fun onError(failure: PlaybackFailure, index: Int) {
        val queue = _state.value.queue
        val item = queue.items.getOrNull(index) ?: return
        when (failure) {
            is PlaybackFailure.UnsupportedFormat -> {
                if (fallbackTried.add(item.songId)) {
                    _state.update { it.copy(status = failure.message) }
                    port.reloadAsMp3(index, item, port.positionMs)
                } else {
                    markUnavailableAndSkip(item, queue)
                }
            }
            is PlaybackFailure.Unavailable -> markUnavailableAndSkip(item, queue)
            is PlaybackFailure.SignInAgain -> {
                port.pause()
                _state.update { it.copy(signInRequired = true, status = failure.message, isPlaying = false) }
            }
            is PlaybackFailure.Network -> {
                _state.update { it.copy(waitingForNetwork = true, buffering = false, status = failure.message) }
                scrobbler.onStall()
            }
            is PlaybackFailure.Server -> markUnavailableAndSkip(item, queue)
        }
    }

    // ---- Internals

    private fun markUnavailableAndSkip(item: QueueItem, queue: QueueState) {
        val marked = queue.markUnavailable(item.songId)
        val moved = port.skipPastFailure()
        _state.update {
            it.copy(
                queue = marked,
                status = if (moved) "\"${item.title}\" is not available. Skipped." else "\"${item.title}\" is not available.",
                isPlaying = if (moved) it.isPlaying else false,
            )
        }
        persist()
    }

    private fun beginPlayIfPending() {
        if (!pendingStart) return
        val item = _state.value.current ?: return
        pendingStart = false
        scrobbler.startPlay(item.songId, item.durationSec, clock())
        scrobbler.onPlaying()
    }

    private fun startTicker() {
        ticker?.cancel()
        ticker = scope.launch {
            while (true) {
                delay(tickMs)
                val pos = port.positionMs
                scrobbler.onTick(pos, advancing = port.isPlaying && !_state.value.buffering)
                val duration = port.durationMs.takeIf { it > 0 }
                _state.update { it.copy(positionMs = pos, durationMs = duration ?: it.durationMs) }
                duration?.let { scrobbler.onPlayerDuration((it / 1000).toInt()) }
                if (++ticks % saveEveryTicks == 0) persist()
            }
        }
    }

    private fun apply(queue: QueueState, capped: Boolean) {
        _state.update { it.copy(queue = queue, status = if (capped) "Queue is full at $MAX_QUEUE songs." else it.status) }
        persist()
    }

    private fun notifyCap(capped: Boolean) {
        if (capped) _state.update { it.copy(status = "Queue is full at $MAX_QUEUE songs.") }
    }

    private fun persist() {
        val s = _state.value
        val q = s.queue.withPosition(s.positionMs)
        if (q.isEmpty) return
        try { storage.write(QueueCodec.encode(q)) } catch (e: Exception) { /* never blocks playback */ }
    }
}
