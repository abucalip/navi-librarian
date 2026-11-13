package app.discair.ui

import app.discair.player.crossfade.CrossfadeSettings
import app.discair.ui.player.CoverStackEqRules
import app.discair.ui.settings.CoverStackAppearanceRules
import app.discair.ui.settings.ThemeGroups
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

    @Test fun themeGroupsSectionEveryPaletteOnce() {
        val all = Palettes.All
        assertEquals(listOf("Standard", "Flow", "Brut", "Tape", "Sheet", "Sticker", "Soft Brut"), ThemeGroups.All)
        assertEquals(all.size, ThemeGroups.All.sumOf { ThemeGroups.shown(all, it).size })
        assertTrue(ThemeGroups.All.all { ThemeGroups.shown(all, it).isNotEmpty() })
        assertEquals("Soft Brut", ThemeGroups.of(Palettes.byId("softbrut")))
        assertEquals("Standard", ThemeGroups.of(null))
    }

    @Test fun daySlotsShowLightPalettesAndNightSlotsDarkOnes() {
        val all = Palettes.All
        assertTrue(ThemeGroups.All.all { g -> ThemeGroups.shown(all, g, true).all { it.light } })
        assertTrue(ThemeGroups.All.all { g -> ThemeGroups.shown(all, g, false).none { it.light } })
        assertEquals(ThemeGroups.All, ThemeGroups.chips(all, null))
        assertEquals("Day theme", CoverStackAppearanceRules.slotTitle("day"))
        assertEquals("Appearance", CoverStackAppearanceRules.slotTitle(null))
    }

    @Test fun settingsGroupsKeepTheMockupOrder() {
        assertEquals(listOf("Look and sound", "Listening", "Playback"), CoverStackSettingsRules.eyebrows)
    }
}
