package app.discair.player.eq

import android.content.SharedPreferences

/** What is saved for the equalizer: the audio setting plus the name of the preset it came from. */
data class EqSettings(val config: EqConfig = EqConfig(), val presetId: String = PRESET_FLAT) {
    fun sanitized() = EqSettings(config.sanitized(), sanitizePresetId(presetId))

    companion object {
        const val PRESET_FLAT = "flat"
        const val PRESET_CUSTOM = "custom"
        private val ID = Regex("[a-z_]{1,32}")

        fun sanitizePresetId(id: String?): String = if (id != null && ID.matches(id)) id else PRESET_FLAT
    }
}

/** Per-device storage of [EqSettings]; the controller writes, the playback service listens (contract 6). */
interface EqSettingsStore {
    fun load(): EqSettings
    fun save(settings: EqSettings)

    /** Calls [onChange] after every save. Returns a function that removes the listener. */
    fun addListener(onChange: () -> Unit): () -> Unit
}

/** Anything the settings can be applied to; the Media3 processor is one. */
interface EqTarget {
    fun setConfig(config: EqConfig)
}

/**
 * Keeps an [EqTarget] in step with the saved settings: applies them at once, then after every change, until
 * [close]. Closing removes the listener so nothing survives the player's release.
 */
class EqBinding(private val store: EqSettingsStore, private val target: EqTarget) : AutoCloseable {
    private var remove: (() -> Unit)? = store.addListener { apply() }

    init { apply() }

    private fun apply() {
        try { target.setConfig(store.load().config) } catch (_: Exception) { /* a bad setting must never stop the music */ }
    }

    override fun close() { remove?.invoke(); remove = null }
}

class MemoryEqSettingsStore(private var current: EqSettings = EqSettings()) : EqSettingsStore {
    private val listeners = mutableListOf<() -> Unit>()
    val listenerCount: Int get() = listeners.size

    override fun load() = current.sanitized()
    override fun save(settings: EqSettings) { current = settings.sanitized(); listeners.toList().forEach { it() } }
    override fun addListener(onChange: () -> Unit): () -> Unit { listeners += onChange; return { listeners -= onChange } }
}

/**
 * Ordinary preferences (not secrets). The ten gains are one string so a change is saved in one write. Every value
 * is clamped on read; an unknown version or an unreadable value gives Flat and off (contract 6). Sign-out does not
 * clear this file: the equalizer belongs to the phone, not the account.
 */
class PrefsEqSettingsStore(private val prefs: SharedPreferences) : EqSettingsStore {
    override fun load(): EqSettings = try {
        if (prefs.getInt(KEY_VERSION, 0) != VERSION) EqSettings() else {
            val gains = prefs.getString(KEY_GAINS, null)?.split(',')?.map { it.trim().toDoubleOrNull() ?: 0.0 } ?: emptyList()
            EqSettings(
                EqConfig(
                    enabled = prefs.getBoolean(KEY_ENABLED, false),
                    bandGainsDb = gains,
                    preGainAuto = prefs.getBoolean(KEY_PRE_AUTO, true),
                    preGainDb = prefs.getFloat(KEY_PRE_DB, 0f).toDouble(),
                ),
                EqSettings.sanitizePresetId(prefs.getString(KEY_PRESET, null)),
            ).sanitized()
        }
    } catch (_: Exception) { EqSettings() } // for example a value of the wrong type

    override fun save(settings: EqSettings) {
        val s = settings.sanitized()
        prefs.edit()
            .putInt(KEY_VERSION, VERSION)
            .putBoolean(KEY_ENABLED, s.config.enabled)
            .putString(KEY_GAINS, s.config.bandGainsDb.joinToString(","))
            .putBoolean(KEY_PRE_AUTO, s.config.preGainAuto)
            .putFloat(KEY_PRE_DB, s.config.preGainDb.toFloat())
            .putString(KEY_PRESET, s.presetId)
            .apply()
    }

    override fun addListener(onChange: () -> Unit): () -> Unit {
        val l = SharedPreferences.OnSharedPreferenceChangeListener { _, _ -> onChange() }
        prefs.registerOnSharedPreferenceChangeListener(l) // held strongly here, so it is not garbage collected
        return { prefs.unregisterOnSharedPreferenceChangeListener(l) }
    }

    private companion object {
        const val VERSION = 1
        const val KEY_VERSION = "version"
        const val KEY_ENABLED = "enabled"
        const val KEY_GAINS = "band_gains_db"
        const val KEY_PRE_AUTO = "pre_gain_auto"
        const val KEY_PRE_DB = "pre_gain_db"
        const val KEY_PRESET = "preset_id"
    }
}
