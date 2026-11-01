package app.discair.player

/** What the controller needs from a player. The Media3 adapter implements it; tests use a fake. */
interface PlayerPort {
    var listener: PortListener?

    /** Replaces the playlist with [songIds] (display order) and starts at [startIndex]. */
    fun setItems(items: List<QueueItem>, startIndex: Int, positionMs: Long, playWhenReady: Boolean)
    fun addItems(items: List<QueueItem>, at: Int)
    fun removeAt(index: Int)
    fun move(from: Int, to: Int)
    fun skipTo(index: Int)

    /** Reloads one item with the MP3 fallback, keeping position. */
    fun reloadAsMp3(index: Int, item: QueueItem, positionMs: Long)

    /** After a failed item: move on to the next one and keep playing; false when there is none. */
    fun skipPastFailure(): Boolean

    /** After a dropped connection: prepare again and resume from the current position. */
    fun retry()

    fun play()
    fun pause()
    fun seekTo(ms: Long)
    fun next()
    fun previous()
    fun setShuffle(on: Boolean)
    fun setRepeat(mode: RepeatMode)
    fun setVolume(volume: Float)
    fun clear()
    fun release()

    val positionMs: Long
    val durationMs: Long
    val isPlaying: Boolean
}

interface PortListener {
    fun onIsPlaying(playing: Boolean)
    fun onBuffering(buffering: Boolean)

    /** The current item changed; [repeated] is true when repeat-one started it again. */
    fun onItemChanged(index: Int, repeated: Boolean)

    /** The queue ended with repeat off. */
    fun onEnded()
    fun onError(failure: PlaybackFailure, index: Int)
    fun onDuration(durationMs: Long)
}
