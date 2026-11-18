package app.discair.ui.theme

import androidx.compose.ui.graphics.Color
import app.discair.ui.NavRules
import app.discair.ui.common.GalleryRules
import app.discair.ui.settings.ThemeGroups
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Step G1 of docs/archive/completed/GALLERY_THEME.md: the eight palettes (pinned to docs/design/gallery/tokens.json), the new roles, the font pair and the shell rules. */
class GalleryTest {
    private val ids = listOf("gallery", "gallery_celadon", "gallery_mist", "gallery_blush", "gallery_butter", "gallery_graphite", "gallery_oxblood", "gallery_moss")
    private val gallery = ids.map { Palettes.byId(it) ?: error("missing $it") }

    private fun hex(c: Color) = "#%02X%02X%02X".format((c.red * 255 + 0.5f).toInt(), (c.green * 255 + 0.5f).toInt(), (c.blue * 255 + 0.5f).toInt())
    private fun ratio(a: Color, b: Color) = Contrast.ratio(a, b)

    /** tokens.json, read without a JSON library: each palette object is one `{ ... }` holding `"key": "value"` pairs. */
    private fun tokens(): Map<String, Map<String, String>> {
        val file = listOf("../../docs/design/gallery/tokens.json", "docs/design/gallery/tokens.json").map(::File).first { it.exists() }
        val text = file.readText()
        val block = text.substring(text.indexOf("\"palettes\""), text.indexOf("\"type\""))
        val pair = Regex("\"(\\w+)\":\\s*(\"[^\"]*\"|true|false|null|\\[[^\\]]*\\])")
        return Regex("\\{[^{}]*\"id\"[^{}]*\\}").findAll(block).associate { m ->
            val kv = pair.findAll(m.value).associate { it.groupValues[1] to it.groupValues[2].trim('"') }
            kv.getValue("id") to kv
        }
    }

    @Test fun theEightPalettesAreInThePickerAndKeepTheLayout() {
        assertEquals(8, gallery.size)
        assertEquals(setOf("gallery", "gallery_celadon", "gallery_mist", "gallery_blush", "gallery_butter"), Palettes.Light.filter { it.layout == Layout.Gallery }.map { it.id }.toSet())
        assertEquals(setOf("gallery_graphite", "gallery_oxblood", "gallery_moss"), Palettes.Dark.filter { it.layout == Layout.Gallery }.map { it.id }.toSet())
        assertEquals("gallery", Palettes.Light.first { it.layout == Layout.Gallery }.id) // Day 1 leads, so it is the default of its group
        for (p in gallery) {
            assertEquals(Layout.Gallery, p.layout); assertEquals("Gallery", p.layout.label)
            assertEquals(Family.Classic, p.family); assertNull(p.shape); assertFalse(p.brutal)
            assertEquals("gallery", p.suggestedFontId)
            assertEquals(Layout.Gallery, p.overArtwork(Palettes.Night).layout)
        }
        assertEquals("Gallery", ThemeGroups.of(gallery.first()))
        assertEquals(5, ThemeGroups.shown(Palettes.All, "Gallery", true).size)
        assertEquals(3, ThemeGroups.shown(Palettes.All, "Gallery", false).size)
        assertTrue("Gallery" in ThemeGroups.chips(Palettes.All, true) && "Gallery" in ThemeGroups.chips(Palettes.All, false))
    }

    @Test fun everyPaletteMatchesTokensJson() {
        val t = tokens()
        assertEquals(ids.toSet(), t.keys)
        for (p in gallery) {
            val k = t.getValue(p.id)
            fun same(role: String, c: Color) = assertEquals("${p.id} $role", k.getValue(role).uppercase(), hex(c))
            same("rail", p.rail); same("ink", p.ink); same("surface", p.surface); same("mat", p.mat); same("raised", p.raised)
            same("edge", p.edge); same("edgeStrong", p.edgeStrong); same("text", p.text)
            same("textMuted", p.textMuted)
            same("control", p.control); same("onControl", p.onControl); same("accent", p.accent); same("onAccent", p.onAccent)
            same("chartRedText", p.chartRedText); same("chartRedText", p.chartRed); same("ok", p.ok); same("caution", p.caution); same("info", p.info)
            same("chart2", p.chart2); same("chart3", p.chart3)
            assertEquals("${p.id} label", k.getValue("label"), p.label)
            assertEquals("${p.id} light", k.getValue("light").toBoolean(), p.light)
            // The derived roles of spec 4.1.
            assertEquals(p.accent, p.chart1); assertEquals(p.raised, p.chartGhost); assertEquals(p.edge, p.chartGrid); assertEquals(p.edgeStrong, p.chartBase)
        }
    }

    @Test fun theNewRolesDefaultSoNoOtherPaletteChanges() {
        for (p in Palettes.All.filter { it.layout != Layout.Gallery && it.layout != Layout.Index }) {
            assertEquals("${p.id} control", p.text, p.control)
            assertEquals("${p.id} onControl", p.ink, p.onControl)
            assertEquals("${p.id} mat", p.surface, p.mat)
        }
        val night = Palettes.GalleryGraphite
        val over = Palettes.Gallery.overArtwork(Palettes.Night)
        assertEquals(Palettes.Gallery.control, over.control); assertEquals(Palettes.Gallery.mat, over.mat); assertEquals(Palettes.Gallery.onControl, over.onControl)
        assertNotNull(night)
    }

    @Test fun dimsAreTheDerivedTenPercentDefault() {
        for (p in gallery) {
            val want = androidx.compose.ui.graphics.lerp(p.surface, p.accent, 0.10f)
            assertEquals("${p.id} accentDim", hex(want), hex(p.accentDim))
        }
    }

    @Test fun contrastMeetsTheSpecChecks() {
        for (p in gallery) {
            for ((name, bg) in listOf("ink" to p.ink, "surface" to p.surface, "raised" to p.raised, "rail" to p.rail)) {
                for ((role, c) in listOf("text" to p.text, "muted" to p.textMuted, "error" to p.chartRedText, "caution" to p.caution, "ok" to p.ok, "control" to p.control))
                    assertTrue("${p.id}: $role on $name", ratio(c, bg) >= 4.5)
            }
            assertTrue("${p.id}: text on mat", ratio(p.text, p.mat) >= 4.5)
            assertTrue("${p.id}: onAccent on accent", ratio(p.onAccent, p.accent) >= 4.5)
            assertTrue("${p.id}: onControl on control", ratio(p.onControl, p.control) >= 4.5)
            assertTrue("${p.id}: text on accent tint", ratio(p.text, p.accentDim) >= 4.5)
            assertTrue("${p.id}: accent on page", ratio(p.accent, p.ink) >= 4.5)
            assertTrue("${p.id}: accent on surface", ratio(p.accent, p.surface) >= 4.5)
            assertTrue("${p.id}: strong edge on page", ratio(p.edgeStrong, p.ink) >= 3.0)
            assertTrue("${p.id}: strong edge on surface", ratio(p.edgeStrong, p.surface) >= 3.0)
        }
    }

    @Test fun motionTakesTheStandardFamily() {
        assertEquals(MotionFamily.Standard, MotionRules.familyFor(Layout.Gallery))
    }

    @Test fun theBarCarriesFourDestinationsAndNoPlayerCell() {
        assertEquals(NavRules.destinations, GalleryRules.cells)
        assertTrue(NavRules.discoverInBar(Layout.Gallery))
        assertFalse(NavRules.discoverInTopBar(Layout.Gallery, rail = false))
        assertFalse(NavRules.playerButtonShown(Layout.Gallery))
    }

    @Test fun printsAndShellKeepTheSpecNumbers() {
        assertEquals(11f, GalleryRules.mat(246f)); assertEquals(11f, GalleryRules.mat(228f)); assertEquals(14f, GalleryRules.mat(300f, player = true))
        assertEquals(5f, GalleryRules.mat(71f)); assertEquals(5f, GalleryRules.mat(48f)); assertEquals(5f, GalleryRules.mat(76f - 10f))
        assertEquals(2, GalleryRules.shadow(large = true, light = true).size)
        assertEquals(26f, GalleryRules.shadow(true, true)[1].dy); assertEquals(-24f, GalleryRules.shadow(true, true)[1].spread); assertEquals(0.5f, GalleryRules.shadow(true, true)[1].alpha)
        assertEquals(12f, GalleryRules.shadow(false, true)[1].dy); assertEquals(0.45f, GalleryRules.shadow(false, true)[1].alpha)
        assertEquals(1, GalleryRules.shadow(true, false).size); assertTrue(GalleryRules.shadow(true, false)[0].black); assertEquals(0.9f, GalleryRules.shadow(true, false)[0].alpha)
        assertEquals(0.85f, GalleryRules.shadow(false, false)[0].alpha)
        assertEquals(44f, GalleryRules.BUTTON_HEIGHT); assertEquals(36f, GalleryRules.BUTTON_SMALL_HEIGHT); assertEquals(2f, GalleryRules.BUTTON_RADIUS)
        assertEquals(58f, GalleryRules.DOCK_MINI); assertEquals(62f, GalleryRules.DOCK_BAR); assertEquals(54f, GalleryRules.HOME_BAR); assertEquals(52f, GalleryRules.PAGE_BAR)
        assertEquals(14f, GalleryRules.SHEET_TOP_RADIUS); assertEquals(64f, GalleryRules.ROW_MIN); assertEquals(56f, GalleryRules.ROW_MIN_TRACKS)
    }

    @Test fun onlyTheNightPalettesHaveASpot() {
        for (p in gallery) assertEquals(p.id, !p.light, GalleryRules.spot(p) != null)
        assertEquals(0.08f, GalleryRules.spot(Palettes.GalleryGraphite)!!.alpha, 0.01f)
        assertEquals(0.07f, GalleryRules.spot(Palettes.GalleryMoss)!!.alpha, 0.01f)
        assertNull(GalleryRules.spot(Palettes.Sand))
    }

    @Test fun theFontPairIsFrauncesManropeDmMonoAndSuggestedNeverForced() {
        val f = FontPairs.Gallery
        assertEquals("gallery", f.id); assertEquals("Gallery", f.label); assertEquals("Fraunces", f.titleName); assertEquals("Manrope", f.bodyName); assertEquals("DM Mono", f.monoName)
        assertEquals("gallery", FontPairs.byId("gallery")?.id)
        assertEquals("gallery", AppearanceRules.suggestedFont(Palettes.Gallery, FontPairs.Discair.id)?.id)
        assertNull(AppearanceRules.suggestedFont(Palettes.Gallery, "gallery"))
        assertEquals("gallery", AppearanceRules.sanitizeFont("gallery"))
    }

    @Test fun appearanceAcceptsTheGalleryPalettesInTheirSlots() {
        assertEquals("gallery_celadon", AppearanceRules.sanitizeDay("gallery_celadon"))
        assertEquals("gallery_moss", AppearanceRules.sanitizeNight("gallery_moss"))
        assertEquals(Palettes.Light.first().id, AppearanceRules.sanitizeDay("gallery_moss"))
        assertEquals("gallery_oxblood", AppearanceRules.resolve("gallery_oxblood", "sand", "night", systemDark = false).id)
    }
}
