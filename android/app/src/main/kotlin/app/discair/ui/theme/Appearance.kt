package app.discair.ui.theme

import android.content.SharedPreferences
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

/** How the theme is picked: [SYSTEM] follows the phone's day/night setting, anything else is a palette id. */
const val THEME_SYSTEM = "system"

/** Pure rules for the Appearance choices, kept apart from storage so they are unit-testable. */
object AppearanceRules {
    fun sanitizeChoice(id: String?): String = if (id == THEME_SYSTEM || Palettes.byId(id) != null) id!! else THEME_SYSTEM
    fun sanitizeDay(id: String?): String = Palettes.Light.firstOrNull { it.id == id }?.id ?: Palettes.Light.first().id
    fun sanitizeNight(id: String?): String = Palettes.Dark.firstOrNull { it.id == id }?.id ?: Palettes.Dark.first().id
    fun sanitizeFont(id: String?): String = FontPairs.byId(id)?.id ?: FontPairs.Discair.id

    /** The font pair [palette] is drawn with when it is not the one in use, else null. A suggestion only: the owner's font is never changed. */
    fun suggestedFont(palette: Palette, currentFontId: String): FontPair? =
        FontPairs.byId(palette.suggestedFontId)?.takeIf { it.id != currentFontId }

    /** The palette to draw with: the chosen one, or by the phone's mode the day or night theme. */
    fun resolve(choice: String, day: String, night: String, systemDark: Boolean): Palette {
        val chosen = if (choice == THEME_SYSTEM) null else Palettes.byId(choice)
        return chosen ?: Palettes.byId(if (systemDark) sanitizeNight(night) else sanitizeDay(day))!!
    }
}

/**
 * The owner's Appearance choices, per device. Not secrets, so ordinary preferences. Each value is Compose
 * state, so changing one redraws the app at once. Defaults: follow the system, Sand by day, Night by night,
 * and the Discair fonts.
 */
class Appearance(private val prefs: SharedPreferences) {
    var themeChoice: String by mutableStateOf(AppearanceRules.sanitizeChoice(prefs.getString(KEY_THEME, null)))
        private set
    var dayTheme: String by mutableStateOf(AppearanceRules.sanitizeDay(prefs.getString(KEY_DAY, null)))
        private set
    var nightTheme: String by mutableStateOf(AppearanceRules.sanitizeNight(prefs.getString(KEY_NIGHT, null)))
        private set
    var fontPairId: String by mutableStateOf(AppearanceRules.sanitizeFont(prefs.getString(KEY_FONT, null)))
        private set

    fun chooseTheme(id: String) { themeChoice = AppearanceRules.sanitizeChoice(id); prefs.edit().putString(KEY_THEME, themeChoice).apply() }
    fun chooseDay(id: String) { dayTheme = AppearanceRules.sanitizeDay(id); prefs.edit().putString(KEY_DAY, dayTheme).apply() }
    fun chooseNight(id: String) { nightTheme = AppearanceRules.sanitizeNight(id); prefs.edit().putString(KEY_NIGHT, nightTheme).apply() }
    fun chooseFont(id: String) { fontPairId = AppearanceRules.sanitizeFont(id); prefs.edit().putString(KEY_FONT, fontPairId).apply() }

    fun palette(systemDark: Boolean): Palette = AppearanceRules.resolve(themeChoice, dayTheme, nightTheme, systemDark)
    val fonts: FontPair get() = FontPairs.byId(fontPairId) ?: FontPairs.Discair

    private companion object {
        const val KEY_THEME = "theme"
        const val KEY_DAY = "day_theme"
        const val KEY_NIGHT = "night_theme"
        const val KEY_FONT = "font_pair"
    }
}
