package app.discair.player.crossfade

import app.discair.player.RepeatMode

/** The owner's crossfade choices (ANDROID_CROSSFADE_CONTRACT.md 6). Storage comes in phase X4. */
data class CrossfadeSettings(
    val enabled: Boolean = false,
    val seconds: Int = DEFAULT_SECONDS,
    val skipSameAlbum: Boolean = true,
) {
    val lengthMs: Long get() = sanitizeSeconds(seconds) * 1_000L

    companion object {
        const val MIN_SECONDS = 1
        const val MAX_SECONDS = 12
        const val DEFAULT_SECONDS = 5

        /** Anything out of range is clamped; a missing value gives the default. */
        fun sanitizeSeconds(raw: Int?): Int = raw?.coerceIn(MIN_SECONDS, MAX_SECONDS) ?: DEFAULT_SECONDS

        /** Stored or typed text: anything that is not a whole number (empty, "NaN", "1e9", a very long number) gives the default. */
        fun parseSeconds(text: String?): Int {
            val n = text?.trim()?.toLongOrNull() ?: return DEFAULT_SECONDS
            return n.coerceIn(MIN_SECONDS.toLong(), MAX_SECONDS.toLong()).toInt()
        }
    }
}

/** What the planner needs to know about one song. A null or non-positive duration means the length is unknown. */
data class JoinSong(val songId: String, val albumId: String = "", val durationMs: Long? = null)

/** Why a join plays as it does today, without a fade (contract 5.1 and 5.3). */
enum class NoFadeReason {
    Off,
    NotAutomatic,
    NoNextSong,
    SameEntry,
    UnknownDuration,
    TooShort,
    NextNotReady,
    SameAlbum,
}

sealed interface CrossfadeDecision {
    data class None(val reason: NoFadeReason) : CrossfadeDecision

    /** Fade for [lengthMs], starting [startAtMs] into the current song (that is, [lengthMs] before its end). */
    data class Fade(val lengthMs: Long, val startAtMs: Long) : CrossfadeDecision
}

/** Everything the planner decides from; the caller fills it from the queue and the players. */
data class JoinContext(
    val current: JoinSong?,
    val next: JoinSong?,
    val repeat: RepeatMode,
    /** True when the next entry of the queue is the current entry itself (a one-song queue on repeat all). */
    val nextIsSameEntry: Boolean,
    /** True only when the current song is reaching its end; false for a skip, a seek, a queue tap or a restart. */
    val automatic: Boolean,
    /** How much of the next song is buffered, from its start. */
    val nextBufferedMs: Long,
)

object CrossfadePlanner {
    /** The shortest fade worth making (contract 5.2); a join that cannot reach it has no fade. */
    const val MIN_FADE_MS = 1_000L

    /** Extra buffer wanted beyond the fade itself before the incoming song may start (contract 5.1). */
    const val READY_MARGIN_MS = 2_000L

    /** Contract 5.1 to 5.3 in one place. The order of the checks is the order the contract lists them. */
    fun plan(settings: CrossfadeSettings, join: JoinContext): CrossfadeDecision {
        if (!settings.enabled) return none(NoFadeReason.Off)
        if (!join.automatic) return none(NoFadeReason.NotAutomatic)
        val current = join.current
        val next = join.next
        if (current == null || next == null) return none(NoFadeReason.NoNextSong)
        if (join.repeat == RepeatMode.One || join.nextIsSameEntry) return none(NoFadeReason.SameEntry)

        val currentMs = current.durationMs?.takeIf { it > 0 }
        val nextMs = next.durationMs?.takeIf { it > 0 }
        if (currentMs == null || nextMs == null) return none(NoFadeReason.UnknownDuration)

        // A short song gets a shorter fade: never more than a third of the shorter song, never below the minimum.
        val length = minOf(settings.lengthMs, minOf(currentMs, nextMs) / 3)
        if (length < MIN_FADE_MS) return none(NoFadeReason.TooShort)

        if (settings.skipSameAlbum && current.albumId.isNotBlank() && current.albumId == next.albumId) {
            return none(NoFadeReason.SameAlbum)
        }
        if (join.nextBufferedMs < length + READY_MARGIN_MS) return none(NoFadeReason.NextNotReady)
        return CrossfadeDecision.Fade(lengthMs = length, startAtMs = currentMs - length)
    }

    private fun none(reason: NoFadeReason) = CrossfadeDecision.None(reason)
}
