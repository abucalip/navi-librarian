package app.discair.ui.settings

import app.discair.ui.theme.Family
import app.discair.ui.theme.Layout
import app.discair.ui.theme.Palette

/**
 * The seven themes the Appearance pickers are sectioned by, in the order the chips show them. Each holds that theme's palettes
 * (day and night). The three Appearance pages (Standard, Flow, Soft Brut) share this.
 */
object ThemeGroups {
    val All = listOf("Standard", "Flow", "Brut", "Tape", "Sheet", "Sticker", "Soft Brut")
    const val DEFAULT = "Standard"

    /** The theme a palette belongs to. Brut is the Brutal palettes that keep the standard layout. */
    fun of(p: Palette?): String = when (p?.layout) {
        null -> DEFAULT
        Layout.Flow -> "Flow"
        Layout.TapeDeck -> "Tape"
        Layout.SheetStack -> "Sheet"
        Layout.StickerWall -> "Sticker"
        Layout.CoverStack -> "Soft Brut"
        Layout.Standard -> if (p.family == Family.Brutal) "Brut" else DEFAULT
    }

    /** The palettes of one theme, in picker order. [light] limits them to day (true) or night (false) themes; null shows both. */
    fun shown(all: List<Palette>, group: String, light: Boolean? = null): List<Palette> =
        all.filter { of(it) == group && (light == null || it.light == light) }

    /** The chips a slot offers: all seven for the one fixed theme; for day or night only the themes that have a palette of that kind. */
    fun chips(all: List<Palette>, light: Boolean?): List<String> = All.filter { shown(all, it, light).isNotEmpty() }

    /** Which palettes a slot may hold: day light only, night dark only, the one theme either. */
    fun slotLight(slot: String): Boolean? = when (slot) { "day" -> true; "night" -> false; else -> null }
}
