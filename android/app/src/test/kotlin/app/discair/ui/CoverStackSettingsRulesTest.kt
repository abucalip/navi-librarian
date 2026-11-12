package app.discair.ui

import app.discair.player.crossfade.CrossfadeSettings
import app.discair.ui.player.CoverStackEqRules
import app.discair.ui.settings.CoverStackAppearanceRules
import app.discair.ui.settings.CoverStackSettingsRules
import app.discair.ui.theme.Palettes
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class CoverStackSettingsRulesTest {
    @Test fun bandColumnsFillFromTheBottomAndZeroIsHalf() {
        assertEquals(0.5f, CoverStackEqRules.fill(0.0), 0.0001f)
        assertEquals(1f, CoverStackEqRules.fill(12.0), 0.0001f)
        assertEquals(0f, CoverStackEqRules.fill(-12.0), 0.0001f)
        assertEquals(1f, CoverStackEqRules.fill(40.0), 0.0001f)
    }

    @Test fun aTouchOnAColumnIsSnappedToHalfADecibel() {
        assertEquals(12.0, CoverStackEqRules.gainAt(0f), 0.0)
        assertEquals(0.0, CoverStackEqRules.gainAt(0.5f), 0.0)
        assertEquals(-12.0, CoverStackEqRules.gainAt(1f), 0.0)
        assertEquals(-12.0, CoverStackEqRules.gainAt(3f), 0.0)
        assertEquals(6.0, CoverStackEqRules.gainAt(0.25f), 0.0)
        assertEquals(5.5, CoverStackEqRules.gainAt(0.2711f), 0.0)
    }

    @Test fun everyOtherBandIsNamedAndTheLastOne() {
        assertEquals(listOf(0, 2, 4, 6, 8, 9), (0 until 10).filter(CoverStackEqRules::showLabel))
    }

    @Test fun theLengthBarSpansTheShortestToTheLongestFade() {
        assertEquals(0f, CoverStackEqRules.lengthFill(CrossfadeSettings.MIN_SECONDS), 0f)
        assertEquals(1f, CoverStackEqRules.lengthFill(CrossfadeSettings.MAX_SECONDS), 0f)
        assertEquals(CrossfadeSettings.MIN_SECONDS, CoverStackEqRules.lengthAt(-1f))
        assertEquals(CrossfadeSettings.MAX_SECONDS, CoverStackEqRules.lengthAt(2f))
        assertTrue(CoverStackEqRules.lengthAt(0.5f) in CrossfadeSettings.MIN_SECONDS..CrossfadeSettings.MAX_SECONDS)
    }

    @Test fun themeFiltersAndSlotsFollowTheStandardPage() {
        val all = Palettes.All
        assertTrue(CoverStackAppearanceRules.shown(all, "Light").all { it.light })
        assertTrue(CoverStackAppearanceRules.shown(all, "Dark").none { it.light })
        assertEquals(all.size, CoverStackAppearanceRules.shown(all, "All").size)
        assertEquals("Light", CoverStackAppearanceRules.slotFilter("day"))
        assertEquals("Dark", CoverStackAppearanceRules.slotFilter("night"))
        assertEquals("All", CoverStackAppearanceRules.slotFilter("theme"))
        assertEquals("Appearance", CoverStackAppearanceRules.slotTitle(null))
        assertEquals("Day theme", CoverStackAppearanceRules.slotTitle("day"))
    }

    @Test fun settingsGroupsKeepTheMockupOrder() {
        assertEquals(listOf("Look and sound", "Listening", "Playback"), CoverStackSettingsRules.eyebrows)
    }
}
