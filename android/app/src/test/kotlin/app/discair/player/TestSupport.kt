package app.discair.player

internal class FakePort : PlayerPort {
    override var listener: PortListener? = null
    val log = mutableListOf<String>()
    var items = listOf<String>()
    var index = 0
    override var positionMs = 0L
    override var durationMs = 200_000L
    override var isPlaying = false
    var hasNext = true
    var released = false

    override fun setItems(items: List<QueueItem>, startIndex: Int, positionMs: Long, playWhenReady: Boolean) {
        this.items = items.map { it.songId }; index = startIndex; this.positionMs = positionMs
        log += "set ${items.size} @$startIndex play=$playWhenReady"
        listener?.onItemChanged(startIndex, false)
        if (playWhenReady) { isPlaying = true; listener?.onIsPlaying(true) }
    }
    override fun addItems(items: List<QueueItem>, at: Int) { log += "add ${items.map { it.songId }} @$at" }
    override fun removeAt(index: Int) { log += "remove $index" }
    override fun move(from: Int, to: Int) { log += "move $from->$to" }
    override fun skipTo(index: Int) { log += "skipTo $index"; this.index = index; listener?.onItemChanged(index, false) }
    override fun reloadAsMp3(index: Int, item: QueueItem, positionMs: Long) { log += "mp3 $index ${item.songId}" }
    override fun skipPastFailure(): Boolean { log += "skipPastFailure"; return hasNext }
    override fun retry() { log += "retry" }
    override fun play() { log += "play"; isPlaying = true; listener?.onIsPlaying(true) }
    override fun pause() { log += "pause"; isPlaying = false; listener?.onIsPlaying(false) }
    override fun seekTo(ms: Long) { log += "seek $ms"; positionMs = ms }
    override fun next() { log += "next" }
    override fun previous() { log += "previous" }
    override fun setShuffle(on: Boolean) { log += "shuffle $on" }
    override fun setRepeat(mode: RepeatMode) { log += "repeat $mode" }
    override fun setVolume(volume: Float) { log += "volume $volume" }
    override fun clear() { log += "clear"; items = emptyList(); isPlaying = false }
    override fun release() { released = true }
}

internal class MemoryStorage(var text: String? = null) : QueueStorage {
    override fun read() = text
    override fun write(text: String) { this.text = text }
    override fun clear() { text = null }
}

internal class RecordingApi : ScrobbleApi {
    val calls = mutableListOf<Triple<String, Boolean, Long>>()
    override suspend fun send(songId: String, submission: Boolean, timeMs: Long): SendOutcome {
        calls += Triple(songId, submission, timeMs); return SendOutcome.Accepted
    }
}

