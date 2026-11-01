package app.discair.player

import android.content.SharedPreferences

/** Per-device playback choices. Not secrets, so ordinary preferences; they are never sent to a server. */
interface PlayerSettings {
    /** Maximum bit rate in kbps from [ALLOWED_BIT_RATES], or null for the original file. */
    var maxBitRate: Int?

    /** Send now-playing and scrobbles to Navidrome. On by default. */
    var scrobbling: Boolean
}

val QUALITY_CHOICES: List<Int?> = listOf(null) + ALLOWED_BIT_RATES.sortedDescending()

fun qualityLabel(rate: Int?) = if (rate == null) "Original (no conversion)" else "$rate kbps"

class PrefsPlayerSettings(private val prefs: SharedPreferences) : PlayerSettings {
    override var maxBitRate: Int?
        get() = prefs.getInt(KEY_RATE, 0).takeIf { it in ALLOWED_BIT_RATES } // anything else, including 0, means original
        set(value) { prefs.edit().putInt(KEY_RATE, value?.takeIf { it in ALLOWED_BIT_RATES } ?: 0).apply() }

    override var scrobbling: Boolean
        get() = prefs.getBoolean(KEY_SCROBBLE, true)
        set(value) { prefs.edit().putBoolean(KEY_SCROBBLE, value).apply() }

    private companion object {
        const val KEY_RATE = "max_bit_rate"
        const val KEY_SCROBBLE = "scrobbling"
    }
}

class MemoryPlayerSettings(override var maxBitRate: Int? = null, override var scrobbling: Boolean = true) : PlayerSettings
