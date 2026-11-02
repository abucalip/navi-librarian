package app.discair.ui.theme

import org.junit.Test
import org.junit.Assert.assertEquals

class AppearanceRulesTest {
    @Test fun defaultsFollowTheSystemWithSandAndNight() {
        val choice = AppearanceRules.sanitizeChoice(null)
        assertEquals(THEME_SYSTEM, choice)
        val day = AppearanceRules.sanitizeDay(null)
        val night = AppearanceRules.sanitizeNight(null)
        assertEquals("sand", AppearanceRules.resolve(choice, day, night, systemDark = false).id)
        assertEquals("night", AppearanceRules.resolve(choice, day, night, systemDark = true).id)
    }

    @Test fun aFixedThemeIgnoresThePhoneMode() {
        assertEquals("forest", AppearanceRules.resolve("forest", "sand", "night", systemDark = false).id)
        assertEquals("paper", AppearanceRules.resolve("paper", "sand", "night", systemDark = true).id)
    }

    @Test fun followingUsesTheChosenDayAndNightThemes() {
        assertEquals("mist", AppearanceRules.resolve(THEME_SYSTEM, "mist", "ember", systemDark = false).id)
        assertEquals("ember", AppearanceRules.resolve(THEME_SYSTEM, "mist", "ember", systemDark = true).id)
    }

    @Test fun unknownOrWrongKindFallsBack() {
        assertEquals(THEME_SYSTEM, AppearanceRules.sanitizeChoice("neon"))
        assertEquals("sand", AppearanceRules.sanitizeDay("forest")) // a dark theme is not a day theme
        assertEquals("night", AppearanceRules.sanitizeNight("paper")) // a light theme is not a night theme
        assertEquals("discair", AppearanceRules.sanitizeFont("comic"))
        assertEquals("transit", AppearanceRules.sanitizeFont("transit"))
        // A saved choice that no longer exists still resolves to something usable.
        assertEquals("sand", AppearanceRules.resolve("gone", "sand", "night", systemDark = false).id)
    }
}
