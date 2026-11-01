package app.discair.player.crossfade

import app.discair.player.RepeatMode

/** Something that can be cancelled once; cancelling twice or after it ran does nothing. */
fun interface Cancelable { fun cancel() }

/** Time and delayed calls, on the player's own thread in the service and under test control in tests. */
interface Scheduler {
    fun nowMs(): Long
    fun postDelayed(delayMs: Long, block: () -> Unit): Cancelable
}

/**
 * The few things the crossfade engine needs from one player (ANDROID_CROSSFADE_CONTRACT.md 4 and 13).
 * The service implements it over an ExoPlayer; tests implement it with a fake. No Android types here.
 */
interface FadePlayer {
    val name: String

    /** The song being played, or null when the queue is empty. */
    val currentSong: JoinSong?

    /** The song that follows in playback order (shuffle and repeat applied), or null at the end of the queue. */
    val nextSong: JoinSong?

    /** True when [nextSong] is the current queue entry itself (a one-song queue on repeat all). */
    val nextIsSameEntry: Boolean
    val repeat: RepeatMode

    /** Position and length of the current song; the length is null while unknown. */
    val positionMs: Long
    val durationMs: Long?

    /** True when the current song is loaded and can play now. */
    val isReady: Boolean

    /** How much of the current song is buffered, counted from its start. */
    val bufferedMs: Long

    var playWhenReady: Boolean

    /** 0..1; set only through the player, never the system volume. */
    var volume: Float

    /** Turns the player's own audio-focus handling on or off. */
    fun setFocusHandling(on: Boolean)

    /** Moves to the queue entry with this song id, at its start, paused, and starts loading it. False if it is not in the queue. */
    fun prepareOn(songId: String): Boolean

    /** Calls [block] once when the current song reaches [positionMs]; nothing happens if the song changes first. */
    fun runAtPosition(positionMs: Long, block: () -> Unit): Cancelable
}

/** Gives the engine the second player when it is needed and takes it back when crossfade is off (contract 5.4). */
interface TwinProvider {
    /** A second player filled with the same playlist as [from] and kept identical to it; null if it cannot be made. */
    fun acquire(from: FadePlayer): FadePlayer?

    /** Releases one player that is not the active one. Safe to call twice for the same player. */
    fun release(player: FadePlayer)
}
