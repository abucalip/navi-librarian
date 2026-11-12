package app.discair.ui.theme

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * Step 0 of docs/ANDROID_ART_THEMES_PROPOSAL.md: every theme that exists today resolves to the layout and the shape it has always had,
 * so adding a layout (or letting BrutalShape hold fractions) changes no existing theme.
 */
class ExistingLayoutsTest {
    private val standard = setOf(
        "night", "sand", "paper", "mist", "sage", "blush", "amoled", "forest", "ocean", "ember", "graphite", "contrast",
        "brutlavender", "brutmint", "brutlemon", "brutcream", "brutsky", "brutposter", "brutink", "brutmidnight",
    )
    private val layouts = mapOf(
        "tapelime" to Layout.TapeDeck, "tapecobalt" to Layout.TapeDeck, "tapetangerine" to Layout.TapeDeck,
        "sheetviolet" to Layout.SheetStack, "sheetacid" to Layout.SheetStack, "sheetdaylight" to Layout.SheetStack,
        "stickerpeach" to Layout.StickerWall,
    ) + standard.associateWith { Layout.Standard }

    /** radius, outline, shadow */
    private val shapes = mapOf(
        "brutlavender" to Triple(6f, 2f, 4f), "brutmint" to Triple(6f, 2f, 4f), "brutlemon" to Triple(6f, 2f, 4f),
        "brutcream" to Triple(16f, 3f, 5f), "brutsky" to Triple(18f, 2f, 3f), "brutposter" to Triple(0f, 4f, 8f),
        "brutink" to Triple(6f, 2f, 4f), "brutmidnight" to Triple(12f, 2f, 4f),
        "tapelime" to Triple(2f, 2f, 5f), "tapecobalt" to Triple(2f, 2f, 5f), "tapetangerine" to Triple(2f, 2f, 5f),
        "sheetviolet" to Triple(14f, 2f, 4f), "sheetacid" to Triple(14f, 2f, 4f), "sheetdaylight" to Triple(14f, 2f, 4f),
        "stickerpeach" to Triple(18f, 3f, 5f),
    )

    @Test fun everyExistingPaletteKeepsItsLayout() {
        val existing = Palettes.All.filter { it.id in layouts }
        assertEquals(layouts.size, existing.size)
        for (p in existing) assertEquals("${p.id} layout", layouts.getValue(p.id), p.layout)
    }

    @Test fun everyExistingPaletteKeepsItsShape() {
        for (p in Palettes.All.filter { it.id in layouts }) {
            val want = shapes[p.id]
            if (want == null) { assertNull("${p.id} is Classic", p.shape); continue }
            val s = assertNotNull(p.shape).let { p.shape!! }
            assertEquals("${p.id} shape", want, Triple(s.radius, s.outline, s.shadow))
        }
    }

    @Test fun brutalShapeHoldsFractionsAndWholeNumbers() {
        val soft = BrutalShape(10f, 1.5f, 3f)
        assertEquals(1.5f, soft.outline, 0f)
        val whole = BrutalShape(6, 2, 4)
        assertEquals(Triple(6f, 2f, 4f), Triple(whole.radius, whole.outline, whole.shadow))
    }
}
