package app.discair.player

import android.content.SharedPreferences
import app.discair.player.crossfade.CrossfadeSettings

/** Per-device playback choices. Not secrets, so ordinary preferences; they are never sent to a server. */
interface PlayerSettings {
    /** Maximum bit rate in kbps from [ALLOWED_BIT_RATES], or null for the original file. */
    var maxBitRate: Int?

    /** Send now-playing and scrobbles to Navidrome. On by default. */
    var scrobbling: Boolean

    /** Crossfade choices (ANDROID_CROSSFADE_CONTRACT.md 6): off by default, 5 s, albums kept gapless. */
    var crossfadeEnabled: Boolean
    var crossfadeSeconds: Int
    var crossfadeSkipSameAlbum: Boolean

    /** The quote and i switches of the player line (the synced lyric, and facts). Both on by default, as on the Mac. */
    var showLyricLine: Boolean
    var showFacts: Boolean

    /** The session and booklet photos drifting behind the lyrics on Now Playing (docs/artwork.md, idea 4). On by default. */
    var showSlideshow: Boolean

    /** Called after any setting is saved; close the result to stop. */
    fun onChange(listener: () -> Unit): AutoCloseable
}

val PlayerSettings.crossfade: CrossfadeSettings
    get() = CrossfadeSettings(crossfadeEnabled, CrossfadeSettings.sanitizeSeconds(crossfadeSeconds), crossfadeSkipSameAlbum)

val QUALITY_CHOICES: List<Int?> = listOf(null) + ALLOWED_BIT_RATES.sortedDescending()

fun qualityLabel(rate: Int?) = if (rate == null) "Original (no conversion)" else "$rate kbps"

class PrefsPlayerSettings(private val prefs: SharedPreferences) : PlayerSettings {
    override var maxBitRate: Int?
        get() = prefs.getInt(KEY_RATE, 0).takeIf { it in ALLOWED_BIT_RATES } // anything else, including 0, means original
        set(value) { prefs.edit().putInt(KEY_RATE, value?.takeIf { it in ALLOWED_BIT_RATES } ?: 0).apply() }

    override var scrobbling: Boolean
        get() = prefs.getBoolean(KEY_SCROBBLE, true)
        set(value) { prefs.edit().putBoolean(KEY_SCROBBLE, value).apply() }

    override var crossfadeEnabled: Boolean
        get() = prefs.getBoolean(KEY_XFADE, false)
        set(value) { prefs.edit().putBoolean(KEY_XFADE, value).apply() }

    override var crossfadeSeconds: Int
        get() = CrossfadeSettings.sanitizeSeconds(runCatching { prefs.getInt(KEY_XFADE_SECONDS, CrossfadeSettings.DEFAULT_SECONDS) }.getOrNull())
        set(value) { prefs.edit().putInt(KEY_XFADE_SECONDS, CrossfadeSettings.sanitizeSeconds(value)).apply() }

    override var crossfadeSkipSameAlbum: Boolean
        get() = prefs.getBoolean(KEY_XFADE_ALBUM, true)
        set(value) { prefs.edit().putBoolean(KEY_XFADE_ALBUM, value).apply() }

    override var showLyricLine: Boolean
        get() = prefs.getBoolean(KEY_LINE_LYRICS, true)
        set(value) { prefs.edit().putBoolean(KEY_LINE_LYRICS, value).apply() }

    override var showFacts: Boolean
        get() = prefs.getBoolean(KEY_LINE_FACTS, true)
        set(value) { prefs.edit().putBoolean(KEY_LINE_FACTS, value).apply() }

    override var showSlideshow: Boolean
        get() = prefs.getBoolean(KEY_SLIDESHOW, true)
        set(value) { prefs.edit().putBoolean(KEY_SLIDESHOW, value).apply() }

    override fun onChange(listener: () -> Unit): AutoCloseable {
        val l = SharedPreferences.OnSharedPreferenceChangeListener { _, _ -> listener() }
        prefs.registerOnSharedPreferenceChangeListener(l)
        return AutoCloseable { prefs.unregisterOnSharedPreferenceChangeListener(l) }
    }

    private companion object {
        const val KEY_RATE = "max_bit_rate"
        const val KEY_SCROBBLE = "scrobbling"
        const val KEY_XFADE = "crossfade_enabled"
        const val KEY_XFADE_SECONDS = "crossfade_seconds"
        const val KEY_XFADE_ALBUM = "crossfade_skip_same_album"
        const val KEY_LINE_LYRICS = "player_line_lyrics"
        const val KEY_LINE_FACTS = "player_line_facts"
        const val KEY_SLIDESHOW = "player_slideshow"
    }
}

class MemoryPlayerSettings(
    override var maxBitRate: Int? = null,
    override var scrobbling: Boolean = true,
    crossfadeEnabled: Boolean = false,
    crossfadeSeconds: Int = CrossfadeSettings.DEFAULT_SECONDS,
    crossfadeSkipSameAlbum: Boolean = true,
) : PlayerSettings {
    private val listeners = mutableListOf<() -> Unit>()
    private fun changed() = listeners.toList().forEach { it() }

    override var crossfadeEnabled: Boolean = crossfadeEnabled
        set(value) { field = value; changed() }
    override var crossfadeSeconds: Int = CrossfadeSettings.sanitizeSeconds(crossfadeSeconds)
        set(value) { field = CrossfadeSettings.sanitizeSeconds(value); changed() }
    override var crossfadeSkipSameAlbum: Boolean = crossfadeSkipSameAlbum
        set(value) { field = value; changed() }
    override var showLyricLine: Boolean = true
        set(value) { field = value; changed() }
    override var showFacts: Boolean = true
        set(value) { field = value; changed() }
    override var showSlideshow: Boolean = true
        set(value) { field = value; changed() }

    override fun onChange(listener: () -> Unit): AutoCloseable {
        listeners += listener
        return AutoCloseable { listeners -= listener }
    }
}
