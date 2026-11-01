package app.discair.player

import android.content.ComponentName
import android.content.Context
import android.os.Bundle
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import app.discair.player.crossfade.EXTRA_ALBUM_ID
import androidx.media3.session.SessionToken
import com.google.common.util.concurrent.MoreExecutors

/** Key in a media item's request extras that asks the service for the MP3 fallback for that item only. */
const val EXTRA_FORMAT = "discair.format"

/**
 * Talks to [PlaybackService] through a [MediaController]. Commands given before the connection is up
 * wait in order and run once it connects. Items carry only the song id (as the media id) and display
 * text; the service builds the signed stream URL.
 */
class Media3Port(context: Context) : PlayerPort {
    private val appContext = context.applicationContext
    private var controller: MediaController? = null
    private val waiting = ArrayDeque<(MediaController) -> Unit>()
    private var released = false
    override var listener: PortListener? = null

    private val playerListener = object : Player.Listener {
        override fun onIsPlayingChanged(isPlaying: Boolean) { listener?.onIsPlaying(isPlaying) }

        override fun onPlaybackStateChanged(state: Int) {
            listener?.onBuffering(state == Player.STATE_BUFFERING)
            if (state == Player.STATE_ENDED) listener?.onEnded()
            if (state == Player.STATE_READY) controller?.duration?.takeIf { it > 0 }?.let { listener?.onDuration(it) }
        }

        override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
            val c = controller ?: return
            listener?.onItemChanged(c.currentMediaItemIndex, reason == Player.MEDIA_ITEM_TRANSITION_REASON_REPEAT)
        }

        override fun onPlayerError(error: PlaybackException) {
            val c = controller ?: return
            val failure = PlaybackFailures.fromThrowable(error) ?: when (error.errorCode) {
                PlaybackException.ERROR_CODE_DECODING_FORMAT_UNSUPPORTED,
                PlaybackException.ERROR_CODE_DECODER_INIT_FAILED,
                PlaybackException.ERROR_CODE_DECODING_FAILED,
                PlaybackException.ERROR_CODE_PARSING_CONTAINER_UNSUPPORTED,
                PlaybackException.ERROR_CODE_PARSING_CONTAINER_MALFORMED,
                -> PlaybackFailures.unsupportedFormat()
                PlaybackException.ERROR_CODE_IO_NETWORK_CONNECTION_FAILED,
                PlaybackException.ERROR_CODE_IO_NETWORK_CONNECTION_TIMEOUT,
                -> PlaybackFailures.network()
                PlaybackException.ERROR_CODE_IO_BAD_HTTP_STATUS -> PlaybackFailure.Server()
                else -> PlaybackFailure.Unavailable()
            }
            listener?.onError(failure, c.currentMediaItemIndex)
        }
    }

    init {
        val token = SessionToken(appContext, ComponentName(appContext, PlaybackService::class.java))
        val future = MediaController.Builder(appContext, token).buildAsync()
        future.addListener({
            try {
                val c = future.get()
                if (released) { c.release(); return@addListener }
                c.addListener(playerListener)
                controller = c
                while (waiting.isNotEmpty()) waiting.removeFirst()(c)
            } catch (e: Exception) {
                waiting.clear() // the service could not start; the screens simply show no playback
            }
        }, MoreExecutors.directExecutor())
    }

    private fun run(block: (MediaController) -> Unit) {
        val c = controller
        if (c != null) block(c) else waiting.addLast(block)
    }

    private fun mediaItem(item: QueueItem, mp3: Boolean = false): MediaItem {
        val extras = Bundle().apply { if (mp3) putString(EXTRA_FORMAT, TranscodeFormat.Mp3.wire) }
        // The album id and the server's length let the service apply the crossfade rules without a server call.
        val meta = Bundle().apply { if (item.albumId.isNotBlank()) putString(EXTRA_ALBUM_ID, item.albumId) }
        return MediaItem.Builder()
            .setMediaId(item.songId)
            .setRequestMetadata(MediaItem.RequestMetadata.Builder().setExtras(extras).build())
            .setMediaMetadata(
                MediaMetadata.Builder().setTitle(item.title).setArtist(item.artist).setAlbumTitle(item.album)
                    .setExtras(meta).apply { if (item.durationSec > 0) setDurationMs(item.durationSec * 1000L) }.build(),
            )
            .build()
    }

    override fun setItems(items: List<QueueItem>, startIndex: Int, positionMs: Long, playWhenReady: Boolean) = run { c ->
        c.setMediaItems(items.map { mediaItem(it) }, startIndex, positionMs)
        c.prepare()
        c.playWhenReady = playWhenReady
    }

    override fun addItems(items: List<QueueItem>, at: Int) = run { c -> c.addMediaItems(at, items.map { mediaItem(it) }) }
    override fun removeAt(index: Int) = run { it.removeMediaItem(index) }
    override fun move(from: Int, to: Int) = run { it.moveMediaItem(from, to) }
    override fun skipTo(index: Int) = run { it.seekToDefaultPosition(index) }

    override fun reloadAsMp3(index: Int, item: QueueItem, positionMs: Long) = run { c ->
        c.replaceMediaItem(index, mediaItem(item, mp3 = true))
        c.seekTo(index, positionMs)
        c.prepare()
        c.play()
    }

    override fun skipPastFailure(): Boolean {
        val c = controller ?: return false
        if (!c.hasNextMediaItem()) return false
        c.seekToNextMediaItem()
        c.prepare()
        c.play()
        return true
    }

    override fun retry() = run { it.prepare(); it.play() }
    override fun play() = run { it.play() }
    override fun pause() = run { it.pause() }
    override fun seekTo(ms: Long) = run { it.seekTo(ms) }
    override fun next() = run { it.seekToNextMediaItem() }
    override fun previous() = run { it.seekToPreviousMediaItem() }
    override fun setShuffle(on: Boolean) = run { it.shuffleModeEnabled = on }
    override fun setRepeat(mode: RepeatMode) = run {
        it.repeatMode = when (mode) {
            RepeatMode.Off -> Player.REPEAT_MODE_OFF
            RepeatMode.All -> Player.REPEAT_MODE_ALL
            RepeatMode.One -> Player.REPEAT_MODE_ONE
        }
    }
    override fun setVolume(volume: Float) = run { it.volume = volume }
    override fun clear() = run { it.stop(); it.clearMediaItems() }

    override fun release() {
        released = true
        waiting.clear()
        controller?.release()
        controller = null
    }

    override val positionMs: Long get() = controller?.currentPosition ?: 0
    override val durationMs: Long get() = controller?.duration?.takeIf { it > 0 } ?: 0
    override val isPlaying: Boolean get() = controller?.isPlaying ?: false
}
