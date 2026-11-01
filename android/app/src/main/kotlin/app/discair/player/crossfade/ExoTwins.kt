package app.discair.player.crossfade

import android.os.Handler
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.ForwardingPlayer
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.ShuffleOrder
import app.discair.player.RepeatMode

/** Extras key under which the app puts the album id on a media item (read here to apply the same-album rule). */
const val EXTRA_ALBUM_ID = "discair.albumId"

/** One ExoPlayer seen through the crossfade engine's eyes. */
@UnstableApi
class ExoFadePlayer(
    val exo: ExoPlayer,
    override val name: String,
    private val attrs: AudioAttributes,
    private val handler: Handler,
) : FadePlayer {
    private fun song(item: MediaItem, playerDurationMs: Long?) = JoinSong(
        songId = item.mediaId,
        albumId = item.mediaMetadata.extras?.getString(EXTRA_ALBUM_ID).orEmpty(),
        durationMs = playerDurationMs?.takeIf { it > 0 } ?: item.mediaMetadata.durationMs?.takeIf { it > 0 },
    )

    override val currentSong: JoinSong? get() = exo.currentMediaItem?.let { song(it, durationMs) }
    override val nextSong: JoinSong?
        get() = exo.nextMediaItemIndex.takeIf { it != C.INDEX_UNSET }?.let { song(exo.getMediaItemAt(it), null) }
    override val nextIsSameEntry: Boolean
        get() = exo.nextMediaItemIndex != C.INDEX_UNSET && exo.nextMediaItemIndex == exo.currentMediaItemIndex
    override val repeat: RepeatMode
        get() = when (exo.repeatMode) {
            Player.REPEAT_MODE_ONE -> RepeatMode.One
            Player.REPEAT_MODE_ALL -> RepeatMode.All
            else -> RepeatMode.Off
        }
    override val positionMs: Long get() = exo.currentPosition
    override val durationMs: Long? get() = exo.duration.takeIf { it != C.TIME_UNSET && it > 0 }
    override val isReady: Boolean get() = exo.playbackState == Player.STATE_READY
    override val bufferedMs: Long get() = exo.bufferedPosition
    override var playWhenReady: Boolean
        get() = exo.playWhenReady
        set(value) { exo.playWhenReady = value }
    override var volume: Float
        get() = exo.volume
        set(value) { exo.volume = value.coerceIn(0f, 1f) }

    override fun setFocusHandling(on: Boolean) = exo.setAudioAttributes(attrs, on)

    override fun prepareOn(songId: String): Boolean {
        val index = (0 until exo.mediaItemCount).firstOrNull { exo.getMediaItemAt(it).mediaId == songId } ?: return false
        exo.seekToDefaultPosition(index)
        exo.prepare()
        return true
    }

    override fun runAtPosition(positionMs: Long, block: () -> Unit): Cancelable {
        val message = exo.createMessage { _, _ -> block() }
            .setLooper(handler.looper)
            .setPosition(exo.currentMediaItemIndex, positionMs)
            .setDeleteAfterDelivery(true)
        message.send()
        return Cancelable { message.cancel() }
    }
}

/**
 * Keeps the partner player's playlist identical to this one's: every change the controller makes through the session
 * is applied to both. The partner never plays by itself; only the crossfade engine starts it. With no partner (crossfade
 * off) this is a plain pass-through.
 */
@UnstableApi
class TwinMirror(private val self: ExoPlayer) : ForwardingPlayer(self) {
    @Volatile var partner: ExoPlayer? = null

    private fun both(block: (ExoPlayer) -> Unit) { partner?.let(block) }
    private fun idle(p: ExoPlayer) { p.playWhenReady = false }

    private fun afterChange() { partner?.let { ExoTwins.syncShuffle(self, it) } }

    override fun setMediaItems(mediaItems: MutableList<MediaItem>, startIndex: Int, startPositionMs: Long) {
        super.setMediaItems(mediaItems, startIndex, startPositionMs); both { it.setMediaItems(mediaItems, startIndex, startPositionMs); idle(it) }; afterChange()
    }
    override fun setMediaItems(mediaItems: MutableList<MediaItem>, resetPosition: Boolean) {
        super.setMediaItems(mediaItems, resetPosition); both { it.setMediaItems(mediaItems, resetPosition); idle(it) }; afterChange()
    }
    override fun setMediaItems(mediaItems: MutableList<MediaItem>) {
        super.setMediaItems(mediaItems); both { it.setMediaItems(mediaItems); idle(it) }; afterChange()
    }
    override fun addMediaItems(index: Int, mediaItems: MutableList<MediaItem>) {
        super.addMediaItems(index, mediaItems); both { it.addMediaItems(index, mediaItems) }; afterChange()
    }
    override fun addMediaItems(mediaItems: MutableList<MediaItem>) {
        super.addMediaItems(mediaItems); both { it.addMediaItems(mediaItems) }; afterChange()
    }
    override fun removeMediaItem(index: Int) { super.removeMediaItem(index); both { it.removeMediaItem(index) }; afterChange() }
    override fun removeMediaItems(fromIndex: Int, toIndex: Int) {
        super.removeMediaItems(fromIndex, toIndex); both { it.removeMediaItems(fromIndex, toIndex) }; afterChange()
    }
    override fun moveMediaItem(currentIndex: Int, newIndex: Int) {
        super.moveMediaItem(currentIndex, newIndex); both { it.moveMediaItem(currentIndex, newIndex) }; afterChange()
    }
    override fun replaceMediaItem(index: Int, mediaItem: MediaItem) {
        super.replaceMediaItem(index, mediaItem); both { it.replaceMediaItem(index, mediaItem) }; afterChange()
    }
    override fun clearMediaItems() { super.clearMediaItems(); both { it.clearMediaItems() } }
    override fun setShuffleModeEnabled(shuffleModeEnabled: Boolean) {
        super.setShuffleModeEnabled(shuffleModeEnabled); both { it.shuffleModeEnabled = shuffleModeEnabled }; afterChange()
    }
    override fun setRepeatMode(repeatMode: Int) { super.setRepeatMode(repeatMode); both { it.repeatMode = repeatMode } }
    override fun stop() { super.stop(); both { it.stop() } }
}

/** Builds, links and releases the two ExoPlayers behind the session. */
@UnstableApi
class ExoTwins(
    private val attrs: AudioAttributes,
    private val handler: Handler,
    /** Builds a player and returns it with what must be closed when it is released (its equalizer binding). */
    private val build: () -> Pair<ExoPlayer, () -> Unit>,
    private val log: (String) -> Unit = {},
) : TwinProvider {
    private class Slot(val fade: ExoFadePlayer, val mirror: TwinMirror, val close: () -> Unit)

    private val slots = LinkedHashMap<FadePlayer, Slot>()
    private var counter = 0

    /** Wraps the first player; the session is built on [mirrorOf] it. */
    fun adopt(exo: ExoPlayer, close: () -> Unit): ExoFadePlayer {
        val slot = Slot(ExoFadePlayer(exo, "player${counter++}", attrs, handler), TwinMirror(exo), close)
        slots[slot.fade] = slot
        return slot.fade
    }

    fun mirrorOf(player: FadePlayer): Player = slots.getValue(player).mirror

    override fun acquire(from: FadePlayer): FadePlayer? = try {
        val src = slots.getValue(from)
        val (exo, close) = build()
        val second = Slot(ExoFadePlayer(exo, "player${counter++}", attrs, handler), TwinMirror(exo), close)
        copyPlaylist(src.fade.exo, exo)
        src.mirror.partner = exo
        second.mirror.partner = src.fade.exo
        slots[second.fade] = second
        log("second player ${second.fade.name} created with ${exo.mediaItemCount} songs")
        second.fade
    } catch (e: Throwable) {
        log("second player could not be created: ${e.message}")
        null
    }

    override fun release(player: FadePlayer) {
        val slot = slots.remove(player) ?: return
        slots.values.forEach { if (it.mirror.partner === slot.fade.exo) it.mirror.partner = null }
        try { slot.close() } catch (e: Throwable) { log("close: ${e.message}") }
        try { slot.fade.exo.release() } catch (e: Throwable) { log("release: ${e.message}") }
    }

    /** Releases whatever is left; used with the service. */
    fun releaseAll() { slots.keys.toList().forEach { release(it) } }

    companion object {
        fun copyPlaylist(src: ExoPlayer, dst: ExoPlayer) {
            val items = (0 until src.mediaItemCount).map { src.getMediaItemAt(it) }
            dst.shuffleModeEnabled = src.shuffleModeEnabled
            dst.repeatMode = src.repeatMode
            if (items.isNotEmpty()) dst.setMediaItems(items, src.currentMediaItemIndex.coerceAtLeast(0), 0L)
            dst.playWhenReady = false
            syncShuffle(src, dst)
        }

        /** Gives [dst] the same shuffle order as [src] (the two choose random orders on their own otherwise). */
        fun syncShuffle(src: ExoPlayer, dst: ExoPlayer) {
            if (!src.shuffleModeEnabled) return
            val tl = src.currentTimeline
            if (tl.isEmpty || dst.mediaItemCount != tl.windowCount) return
            val order = ShuffleOrders.walk(tl.windowCount, tl.getFirstWindowIndex(true)) {
                tl.getNextWindowIndex(it, Player.REPEAT_MODE_OFF, true)
            } ?: return
            dst.setShuffleOrder(ShuffleOrder.DefaultShuffleOrder(order, 0L))
        }
    }
}
