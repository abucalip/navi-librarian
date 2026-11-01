package app.discair.player.eq

import java.util.Locale
import kotlin.math.abs
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/** A built-in curve (ANDROID_EQ_CONTRACT.md 5.3). Gains follow [EQ_BAND_HZ], in dB, in 0.5 dB steps. */
data class EqPreset(val id: String, val label: String, val gainsDb: List<Double>)

val EQ_PRESETS: List<EqPreset> = listOf(
    EqPreset("flat", "Flat", listOf(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
    EqPreset("bass_boost", "Bass boost", listOf(6.0, 5.0, 4.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
    EqPreset("bass_reduce", "Bass reduce", listOf(-6.0, -5.0, -4.0, -2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
    EqPreset("treble_boost", "Treble boost", listOf(0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 2.0, 4.0, 5.0, 6.0)),
    EqPreset("vocal", "Vocal", listOf(-2.0, -2.0, -1.0, 1.0, 3.0, 3.5, 3.0, 1.0, 0.0, -1.0)),
    EqPreset("rock", "Rock", listOf(4.0, 3.0, 2.0, 1.0, -1.0, -1.0, 1.0, 3.0, 4.0, 4.5)),
    EqPreset("classical", "Classical", listOf(4.0, 3.0, 2.0, 2.0, -1.0, -1.0, 0.0, 2.0, 3.0, 4.0)),
    EqPreset("electronic", "Electronic", listOf(5.0, 4.0, 1.0, 0.0, -2.0, 2.0, 1.0, 2.0, 4.0, 5.0)),
    // Gentle low and high cut for low listening levels: less thump through walls, less hiss and edge.
    EqPreset("late_night", "Late night", listOf(-4.0, -3.0, -2.0, 0.0, 0.0, 0.0, 0.0, -1.0, -2.0, -3.0)),
)

fun presetLabel(id: String): String =
    if (id == EqSettings.PRESET_CUSTOM) "Custom" else EQ_PRESETS.firstOrNull { it.id == id }?.label ?: "Flat"

/** Hertz as shown under a band: "62 Hz", "1 kHz". */
fun bandLabel(hz: Int): String = if (hz >= 1000) "${hz / 1000} kHz" else "$hz Hz"

/** Hertz as spoken by TalkBack: "62 hertz", "1 kilohertz". */
fun bandSpoken(hz: Int): String = if (hz >= 1000) "${hz / 1000} kilohertz" else "$hz hertz"

/** "+3.5 dB", "-2 dB", "0 dB". Uses a real minus sign so it is read and drawn clearly. */
fun formatDb(db: Double, spoken: Boolean = false): String {
    val v = abs(db)
    val num = if (v % 1.0 == 0.0) "%d".format(Locale.ROOT, v.toInt()) else "%.1f".format(Locale.ROOT, v)
    val unit = if (spoken) "decibels" else "dB"
    return when {
        db > 0 -> (if (spoken) "plus " else "+") + "$num ${if (spoken && v == 1.0) "decibel" else unit}"
        db < 0 -> (if (spoken) "minus " else "−") + "$num ${if (spoken && v == 1.0) "decibel" else unit}"
        else -> "0 $unit"
    }
}

/** What the Now Playing sheet and Settings say about the state, in words. */
fun eqSummary(s: EqSettings): String =
    if (!s.config.enabled) "Equalizer: off" else "Equalizer: ${presetLabel(s.presetId)}"

/** What the playback service reports about the song being played (contract 7, 8). */
data class EqRuntimeStatus(val appliesToThisSong: Boolean = true, val faulted: Boolean = false)

fun eqStatusLine(enabled: Boolean, status: EqRuntimeStatus): String? = when {
    !enabled -> null
    status.faulted -> "Equalizer unavailable for this song."
    !status.appliesToThisSong -> "Not applied to this song."
    else -> null
}

/**
 * The rules of the Equalizer screen, with no Android types. Every change is saved at once through the store,
 * which the playback service listens to.
 */
class EqEditor(private val store: EqSettingsStore) {
    private val flow = MutableStateFlow(store.load())
    val state: StateFlow<EqSettings> get() = flow

    private fun commit(next: EqSettings) { val s = next.sanitized(); store.save(s); flow.value = s }
    private val cur get() = flow.value

    fun setEnabled(on: Boolean) = commit(cur.copy(config = cur.config.copy(enabled = on)))

    /** Choosing a preset sets the ten bands; Custom restores the last hand-made curve. */
    fun selectPreset(id: String) {
        val gains = if (id == EqSettings.PRESET_CUSTOM) cur.customGainsDb
        else (EQ_PRESETS.firstOrNull { it.id == id } ?: EQ_PRESETS[0]).gainsDb
        commit(cur.copy(config = cur.config.copy(bandGainsDb = gains), presetId = if (id == EqSettings.PRESET_CUSTOM) id else EQ_PRESETS.firstOrNull { it.id == id }?.id ?: "flat"))
    }

    /** Moving any band switches to Custom and keeps the curve there. Presets themselves are never changed. */
    fun setBand(index: Int, db: Double) {
        if (index !in 0 until EQ_BAND_COUNT) return
        val gains = cur.config.bandGainsDb.toMutableList().also { it[index] = db }
        val clean = EqConfig(bandGainsDb = gains).sanitized().bandGainsDb
        commit(cur.copy(config = cur.config.copy(bandGainsDb = clean), presetId = EqSettings.PRESET_CUSTOM, customGainsDb = clean))
    }

    fun nudgeBand(index: Int, steps: Int) {
        if (index !in 0 until EQ_BAND_COUNT) return
        setBand(index, cur.config.bandGainsDb[index] + steps * EQ_STEP_DB)
    }

    fun setPreGainAuto(auto: Boolean) = commit(cur.copy(config = cur.config.copy(preGainAuto = auto)))
    fun setPreGain(db: Double) = commit(cur.copy(config = cur.config.copy(preGainDb = db)))
    fun nudgePreGain(steps: Int) = setPreGain(cur.config.preGainDb + steps * EQ_STEP_DB)

    /** Flat bands, no Custom curve, automatic pre-gain. Whether the equalizer is on is left alone. */
    fun reset() = commit(EqSettings(EqConfig(enabled = cur.config.enabled)))
}
