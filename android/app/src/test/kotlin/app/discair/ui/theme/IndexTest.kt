package app.discair.ui.theme

import androidx.compose.ui.graphics.Color
import app.discair.ui.NavRules
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexShellRules
import app.discair.ui.common.IndexTones
import app.discair.ui.settings.ThemeGroups
import java.io.File
import java.time.LocalDate
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.double
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Step I1 of docs/plans/INDEX_THEME.md: the Index palettes and the tones (pinned to docs/design/index/tokens.json), the font pair, the icons and the shell rules. */
class IndexTest {
    private val graphiteIds = listOf("blue", "cyan", "mint", "lime", "yellow", "violet", "pink", "coral").map { "index_graphite_$it" }
    private val ids = listOf("index", "index_newsprint", "index_graphite", "index_field") + graphiteIds
    private val index = ids.map { Palettes.byId(it) ?: error("missing $it") }

    private fun hex(c: Color) = "#%02X%02X%02X".format((c.red * 255 + 0.5f).toInt(), (c.green * 255 + 0.5f).toInt(), (c.blue * 255 + 0.5f).toInt())
    private fun ratio(a: Color, b: Color) = Contrast.ratio(a, b)

    private val tokens: JsonObject by lazy {
        val file = listOf("../../docs/design/index/tokens.json", "docs/design/index/tokens.json").map(::File).first { it.exists() }
        Json.parseToJsonElement(file.readText()).jsonObject
    }

    private fun palettes(): Map<String, JsonObject> = tokens.getValue("palettes").jsonArray.map { it.jsonObject }.associateBy { it.getValue("id").jsonPrimitive.content }

    @Test fun thePalettesAreInThePickerAndKeepTheLayout() {
        assertEquals(12, index.size)
        assertEquals(listOf("index", "index_newsprint", "index_field"), Palettes.Light.filter { it.layout == Layout.Index }.map { it.id })
        assertEquals(listOf("index_graphite") + graphiteIds, Palettes.Dark.filter { it.layout == Layout.Index }.map { it.id })
        for (p in index) {
            assertEquals(Layout.Index, p.layout); assertEquals("Index", p.layout.label)
            assertEquals(Family.Classic, p.family); assertNull(p.shape); assertFalse(p.brutal)
            assertEquals("index", p.suggestedFontId)
            assertEquals(4.5, p.minAccentContrast, 0.0)
            assertEquals(Layout.Index, p.overArtwork(Palettes.Night).layout)
            assertEquals("${p.id}: no mats", p.surface, p.mat)
        }
        assertEquals("Index", ThemeGroups.of(index.first()))
        assertEquals(3, ThemeGroups.shown(Palettes.All, "Index", true).size)
        assertEquals(9, ThemeGroups.shown(Palettes.All, "Index", false).size)
        assertTrue("Index" in ThemeGroups.chips(Palettes.All, true) && "Index" in ThemeGroups.chips(Palettes.All, false))
        // Signal Blue leads the day palettes and Graphite Orange the night ones of the theme: they are what "Follow the phone" offers first (decision I5).
        assertEquals("index", ThemeGroups.shown(Palettes.All, "Index", true).first().id)
        assertEquals("index_graphite", ThemeGroups.shown(Palettes.All, "Index", false).first().id)
    }

    @Test fun graphiteChoicesSurviveAppearanceResolution() {
        for (id in graphiteIds) {
            assertEquals(id, AppearanceRules.sanitizeChoice(id))
            assertEquals(id, AppearanceRules.sanitizeNight(id))
            assertEquals(id, AppearanceRules.resolve(id, "index", "index_graphite", false).id)
            assertEquals(id, AppearanceRules.resolve(THEME_SYSTEM, "index", id, true).id)
            assertEquals("index", AppearanceRules.resolve(THEME_SYSTEM, "index", id, false).id)
        }
    }

    @Test fun graphiteVariantsKeepNeutralAndSemanticTokens() {
        val base = palettes().getValue("index_graphite")
        val replaced = setOf("id", "label", "name", "defaultDark", "accent", "control", "tones")
        for (id in graphiteIds) {
            val variant = palettes().getValue(id)
            assertFalse(variant.containsKey("defaultDark"))
            for ((role, value) in base.filterKeys { it !in replaced }) assertEquals("$id $role", value, variant[role])
            val tones = variant.getValue("tones").jsonObject
            for (role in listOf("strip", "onStrip", "stripMuted", "onInsight"))
                assertEquals("$id $role", base.getValue("tones").jsonObject[role], tones[role])
            val p = Palettes.byId(id)!!
            assertEquals(p.accent, p.control)
            assertEquals(tint(p.accent, p.surface), p.accentDim)
            assertEquals(p.accent, p.accent2); assertEquals(p.accent, p.accent3); assertEquals(p.accent, p.accent4)
        }
    }

    @Test fun everyPaletteMatchesTokensJson() {
        val t = palettes()
        assertEquals(ids.toSet(), t.keys)
        for (p in index) {
            val k = t.getValue(p.id)
            fun same(role: String, c: Color) = assertEquals("${p.id} $role", k.getValue(role).jsonPrimitive.content.uppercase(), hex(c))
            same("rail", p.rail); same("ink", p.ink); same("surface", p.surface); same("mat", p.mat); same("raised", p.raised)
            same("edge", p.edge); same("edgeStrong", p.edgeStrong); same("text", p.text); same("textMuted", p.textMuted)
            same("control", p.control); same("onControl", p.onControl); same("accent", p.accent); same("onAccent", p.onAccent)
            same("chartRed", p.chartRed); same("chartRedText", p.chartRedText); same("ok", p.ok); same("caution", p.caution); same("info", p.info)
            same("chart2", p.chart2); same("chart3", p.chart3)
            assertEquals("${p.id} label", k.getValue("label").jsonPrimitive.content, p.label)
            assertEquals("${p.id} light", k.getValue("light").jsonPrimitive.boolean, p.light)
            assertEquals(p.accent, p.chart1); assertEquals(p.raised, p.chartGhost); assertEquals(p.edge, p.chartGrid); assertEquals(p.edgeStrong, p.chartBase)
        }
    }

    @Test fun everyToneMatchesTokensJson() {
        val t = palettes()
        for (p in index) {
            val k = t.getValue(p.id).getValue("tones").jsonObject
            val tones = IndexTones.of(p.id)
            fun same(role: String, c: Color) = assertEquals("${p.id} tone $role", k.getValue(role).jsonPrimitive.content.uppercase(), hex(c))
            same("strip", tones.strip); same("onStrip", tones.onStrip); same("stripMuted", tones.stripMuted); same("stripProgress", tones.stripProgress)
            same("insight", tones.insight); same("onInsight", tones.onInsight); same("insightLabel", tones.insightLabel)
        }
        assertEquals(ids.toSet(), IndexTones.byId.keys)
        // An id that is not an Index palette falls back to Signal Blue rather than missing.
        assertEquals(IndexTones.SignalBlue, IndexTones.of("sand")); assertEquals(IndexTones.SignalBlue, IndexTones.of(null))
    }

    @Test fun contrastMeetsTheSpecChecks() {
        for (p in index) {
            for ((name, bg) in listOf("ink" to p.ink, "surface" to p.surface, "raised" to p.raised, "rail" to p.rail)) {
                for ((role, c) in listOf("text" to p.text, "muted" to p.textMuted, "error" to p.chartRedText, "caution" to p.caution, "ok" to p.ok, "control" to p.control, "accent" to p.accent))
                    assertTrue("${p.id}: $role on $name is %.2f".format(ratio(c, bg)), ratio(c, bg) >= 4.5)
            }
            assertTrue("${p.id}: onAccent on accent", ratio(p.onAccent, p.accent) >= 4.5)
            assertTrue("${p.id}: onControl on control", ratio(p.onControl, p.control) >= 4.5)
            assertTrue("${p.id}: strong edge on page", ratio(p.edgeStrong, p.ink) >= 3.0)
            val tones = IndexTones.of(p.id)
            assertTrue("${p.id}: onStrip on strip", ratio(tones.onStrip, tones.strip) >= 4.5)
            assertTrue("${p.id}: stripMuted on strip", ratio(tones.stripMuted, tones.strip) >= 4.5)
            assertTrue("${p.id}: stripProgress on strip", ratio(tones.stripProgress, tones.strip) >= 3.0)
            assertTrue("${p.id}: onInsight on insight", ratio(tones.onInsight, tones.insight) >= 4.5)
            assertTrue("${p.id}: insightLabel on insight", ratio(tones.insightLabel, tones.insight) >= 4.5)
        }
    }

    @Test fun motionTakesTheStandardFamily() {
        assertEquals(MotionFamily.Standard, MotionRules.familyFor(Layout.Index))
    }

    @Test fun theBarCarriesFourDestinationsAndNoPlayerCell() {
        assertEquals(NavRules.destinations, IndexRules.cells)
        assertTrue(NavRules.discoverInBar(Layout.Index))
        assertFalse(NavRules.discoverInTopBar(Layout.Index, rail = false))
        assertFalse(NavRules.playerButtonShown(Layout.Index))
    }

    @Test fun theShellKeepsTheSpecNumbers() {
        val space = tokens.getValue("space").jsonObject
        assertEquals(space.getValue("gutter").jsonPrimitive.double.toFloat(), IndexRules.GUTTER)
        assertEquals(space.getValue("ruleHeavy").jsonPrimitive.double.toFloat(), IndexRules.RULE_HEAVY)
        assertEquals(space.getValue("ruleLight").jsonPrimitive.double.toFloat(), IndexRules.RULE_LIGHT)
        assertEquals(space.getValue("rowMin").jsonPrimitive.double.toFloat(), IndexRules.ROW_MIN)
        assertEquals(space.getValue("trackRowMin").jsonPrimitive.double.toFloat(), IndexRules.ROW_MIN_TRACKS)
        assertEquals(space.getValue("touchMin").jsonPrimitive.double.toFloat(), IndexRules.TOUCH_MIN)
        assertEquals(space.getValue("iconButton").jsonPrimitive.double.toFloat(), IndexRules.ICON_BUTTON)
        val shape = tokens.getValue("shape").jsonObject
        assertEquals(shape.getValue("button").jsonPrimitive.double.toFloat(), IndexRules.BUTTON_RADIUS)
        assertEquals(shape.getValue("sheetTop").jsonPrimitive.double.toFloat(), IndexRules.SHEET_TOP_RADIUS)
        val icon = tokens.getValue("icon").jsonObject
        assertEquals(icon.getValue("size").jsonPrimitive.double.toFloat(), IndexRules.ICON)
        assertEquals(icon.getValue("inButton").jsonPrimitive.double.toFloat(), IndexRules.ICON_INLINE)
        assertEquals(icon.getValue("transport").jsonPrimitive.double.toFloat(), IndexRules.ICON_TRANSPORT)
        assertEquals(44f, IndexRules.BUTTON_HEIGHT); assertEquals(36f, IndexRules.BUTTON_SMALL_HEIGHT)
        assertEquals(54f, IndexRules.HOME_BAR); assertEquals(52f, IndexRules.PAGE_BAR); assertEquals(56f, IndexRules.DOCK_STRIP); assertEquals(60f, IndexRules.DOCK_BAR)
        assertEquals(40f, IndexRules.TABS_HEIGHT); assertEquals(52f, IndexRules.SNACK_HEIGHT); assertEquals(6f, IndexRules.SEEK)
    }

    @Test fun theFontPairIsInterTightInterIbmPlexMonoAndSuggestedNeverForced() {
        val f = FontPairs.Index
        assertEquals("index", f.id); assertEquals("Index", f.label); assertEquals("Inter Tight", f.titleName); assertEquals("Inter", f.bodyName); assertEquals("IBM Plex Mono", f.monoName)
        assertEquals(androidx.compose.ui.text.font.FontWeight.ExtraBold, f.titleWeight); assertEquals(androidx.compose.ui.text.font.FontWeight.ExtraBold, f.numeralWeight)
        assertTrue(FontPairs.All.contains(f))
        assertEquals(f.id, AppearanceRules.sanitizeFont(f.id))
    }

    @Test fun theIconSetHasAll48Glyphs() {
        val glyphs = IndexIcons::class.java.declaredMethods.count { it.name.startsWith("get") && it.returnType == androidx.compose.ui.graphics.vector.ImageVector::class.java }
        assertEquals(48, glyphs)
        assertEquals(2f, strokeWidth(IndexIcons.Home))
    }

    private fun strokeWidth(v: androidx.compose.ui.graphics.vector.ImageVector): Float {
        val path = v.root.firstOrNull() as androidx.compose.ui.graphics.vector.VectorPath
        return path.strokeLineWidth
    }

    @Test fun theDateAndTheStripReadLikeTheMockups() {
        assertEquals("TUE 17.11", IndexShellRules.dateLabel(LocalDate.of(2026, 11, 17)))
        assertEquals("SUN 01.02", IndexShellRules.dateLabel(LocalDate.of(2026, 2, 1)))
        assertEquals("1:37", IndexShellRules.clock(97_000)); assertEquals("0:05", IndexShellRules.clock(5_400)); assertEquals("0:00", IndexShellRules.clock(-1))
        assertEquals("Khruangbin · 1:37 / 3:51", IndexShellRules.stripMeta("Khruangbin", 97_000, 231_000, showTime = true))
        assertEquals("Buffering…", IndexShellRules.stripMeta("Buffering…", 97_000, 231_000, showTime = false))
        assertEquals("FIP", IndexShellRules.stripMeta("FIP", 0, 0, showTime = true))
        assertEquals(0.42f, IndexShellRules.progress(42, 100), 0.0001f); assertEquals(0f, IndexShellRules.progress(10, 0)); assertEquals(1f, IndexShellRules.progress(500, 100))
        assertEquals(0, IndexShellRules.selectedCell(true, false, false, false)); assertEquals(3, IndexShellRules.selectedCell(false, false, false, true))
        assertEquals(-1, IndexShellRules.selectedCell(false, false, false, false))
    }
}
