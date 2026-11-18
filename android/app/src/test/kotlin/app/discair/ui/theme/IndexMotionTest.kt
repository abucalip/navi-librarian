package app.discair.ui.theme

import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.double
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** docs/plans/INDEX_THEME.md section 8: Index's motion values match tokens.json, every duration is 0 when the phone removes animations, and the bar's order decides the slide. */
class IndexMotionTest {
    private val motion: JsonObject by lazy {
        val file = listOf("../../docs/design/index/tokens.json", "docs/design/index/tokens.json").map(::File).first { it.exists() }
        Json.parseToJsonElement(file.readText()).jsonObject.getValue("motion").jsonObject
    }

    private fun ms(name: String) = motion.getValue(name).jsonObject.getValue("ms").jsonPrimitive.int
    private fun curve(v: kotlinx.serialization.json.JsonElement) = v.jsonArray.map { it.jsonPrimitive.double.toFloat() }

    private fun same(want: List<Float>, got: androidx.compose.animation.core.CubicBezierEasing, label: String) {
        // CubicBezierEasing exposes no fields: equal curves give equal outputs, and the inputs are spread over the whole range.
        val ref = androidx.compose.animation.core.CubicBezierEasing(want[0], want[1], want[2], want[3])
        for (i in 0..20) assertEquals("$label at ${i / 20f}", ref.transform(i / 20f), got.transform(i / 20f), 0.0f)
    }

    @Test fun everyValueMatchesTokensJson() {
        assertEquals(ms("tabSlide"), IndexMotion.TAB_SLIDE_MS)
        assertEquals(ms("pushSlide"), IndexMotion.PUSH_MS)
        assertEquals(ms("rowCascade"), IndexMotion.ROW_MS)
        assertEquals(motion.getValue("rowCascade").jsonObject.getValue("staggerMs").jsonPrimitive.int, IndexMotion.ROW_STAGGER_MS)
        assertEquals(motion.getValue("rowCascade").jsonObject.getValue("maxStaggered").jsonPrimitive.int, IndexMotion.ROW_MAX)
        assertEquals(motion.getValue("rowCascade").jsonObject.getValue("fromDpX").jsonPrimitive.int, IndexMotion.ROW_FROM_DP)
        assertEquals(ms("signalBlock"), IndexMotion.SIGNAL_MS)
        assertEquals(ms("sourceBar"), IndexMotion.SOURCE_BAR_MS)
        assertEquals(ms("playerRise"), IndexMotion.PLAYER_RISE_MS)
        assertEquals(ms("playerFall"), IndexMotion.PLAYER_FALL_MS)
        assertEquals(ms("sheetIn"), IndexMotion.SHEET_IN_MS)
        assertEquals(ms("sheetOut"), IndexMotion.SHEET_OUT_MS)
        assertEquals(ms("numeralRoll"), IndexMotion.NUMERAL_MS)
        assertEquals(motion.getValue("numeralRoll").jsonObject.getValue("perDigitDelayMs").jsonPrimitive.int, IndexMotion.NUMERAL_DIGIT_DELAY_MS)
        assertEquals(ms("ruleDraw"), IndexMotion.RULE_MS)
        assertEquals(ms("snackIn"), IndexMotion.SNACK_MS)
        assertEquals(motion.getValue("snackIn").jsonObject.getValue("fromDp").jsonPrimitive.int, IndexMotion.SNACK_FROM_DP)
        assertEquals(motion.getValue("snackIn").jsonObject.getValue("holdMs").jsonPrimitive.int.toLong(), IndexMotion.SNACK_HOLD_MS)
        val bars = motion.getValue("playingBars").jsonObject
        assertEquals(bars.getValue("ms").jsonPrimitive.int, IndexMotion.BARS_MS)
        assertEquals(bars.getValue("minDp").jsonPrimitive.int, IndexMotion.BARS_MIN_DP)
        assertEquals(bars.getValue("maxDp").jsonPrimitive.int, IndexMotion.BARS_MAX_DP)
        assertEquals(bars.getValue("phaseMs").jsonArray.map { it.jsonPrimitive.int }, IndexMotion.BARS_PHASE_MS)
        same(curve(motion.getValue("firm")), IndexMotion.Firm, "firm")
        same(curve(motion.getValue("rowCascade").jsonObject.getValue("curve")), IndexMotion.Settle, "settle")
        same(curve(motion.getValue("sheetIn").jsonObject.getValue("curve")), IndexMotion.Settle, "sheetIn")
        same(curve(motion.getValue("sheetOut").jsonObject.getValue("curve")), IndexMotion.Exit, "sheetOut")
    }

    @Test fun theSpecNumbersThatTokensJsonDoesNotCarryAreSection8() {
        // Section 8.2 #2 (push): +30% in with a 200ms fade; -12% out, dimmed to 85%. #10: the snackbar leaves in 180ms. Section 7 (Dock): 3dp by 14%.
        assertEquals(0.3f, IndexMotion.PUSH_ENTER_FRACTION); assertEquals(0.12f, IndexMotion.PUSH_EXIT_FRACTION); assertEquals(0.85f, IndexMotion.PUSH_DIM)
        assertEquals(200, IndexMotion.PUSH_FADE_MS); assertEquals(180, IndexMotion.SNACK_OUT_MS)
        assertEquals(0.14f, IndexMotion.SIGNAL_WIDTH_FRACTION); assertEquals(3, IndexMotion.SIGNAL_HEIGHT_DP)
    }

    @Test fun everyDurationIsZeroWhenTheDeviceRemovesAnimations() {
        for (ms in listOf(IndexMotion.TAB_SLIDE_MS, IndexMotion.PUSH_MS, IndexMotion.SIGNAL_MS, IndexMotion.SOURCE_BAR_MS, IndexMotion.SHEET_IN_MS, IndexMotion.SHEET_OUT_MS, IndexMotion.SNACK_MS, IndexMotion.SNACK_OUT_MS, IndexMotion.PUSH_FADE_MS)) {
            assertEquals(0, IndexMotion.firm<Float>(ms, reduced = true, delayMs = 40).durationMillis)
            assertEquals(0, IndexMotion.firm<Float>(ms, reduced = true, delayMs = 40).delay)
            assertEquals(0, IndexMotion.settle<Float>(ms, reduced = true).durationMillis)
            assertEquals(0, IndexMotion.exit<Float>(ms, reduced = true).durationMillis)
            assertEquals(0, IndexMotion.fade<Float>(ms, reduced = true).durationMillis)
            assertEquals(ms, IndexMotion.firm<Float>(ms, reduced = false).durationMillis)
        }
        assertEquals(40, IndexMotion.firm<Float>(100, reduced = false, delayMs = 40).delay)
    }

    @Test fun thePlayingBarsSwingFromThreeToTwelveAndBackWithEachBarOffset() {
        // #13: 3dp at the start, 12dp after 800ms, 3dp again after 1600ms; a bar 300ms early is already on its way up; still bars stand at 7dp.
        assertEquals(3f, IndexMotion.barHeightDp(0, 0), 0.01f)
        assertEquals(12f, IndexMotion.barHeightDp(800, 0), 0.01f)
        assertEquals(3f, IndexMotion.barHeightDp(1600, 0), 0.01f)
        assertEquals(IndexMotion.barHeightDp(300, 0), IndexMotion.barHeightDp(0, -300), 0.01f)
        assertTrue(IndexMotion.barHeightDp(0, -300) > 3f)
        assertEquals(7, IndexMotion.BARS_REST_DP)
    }

    @Test fun theBarOrderDecidesTheDirection() {
        assertEquals(listOf("Home", "Discover", "Library", "Search"), IndexMotion.barOrder)
        assertEquals(1, IndexMotion.tabDirection(0, 1)); assertEquals(1, IndexMotion.tabDirection(0, 2)); assertEquals(1, IndexMotion.tabDirection(1, 2))
        assertEquals(-1, IndexMotion.tabDirection(2, 0)); assertEquals(-1, IndexMotion.tabDirection(1, 0)); assertEquals(-1, IndexMotion.tabDirection(2, 1))
    }

    @Test fun theSignalBlockSitsOverTheSelectedCell() {
        val width = 400f
        for (cell in 0..3) {
            val x = IndexMotion.signalX(cell, width)
            assertEquals("cell $cell centre", width / 4 * cell + width / 8, x + width * 0.14f / 2, 0.001f)
        }
        // Nothing selected (a page that is not a bar destination): the block rests over the first cell.
        assertEquals(IndexMotion.signalX(0, width), IndexMotion.signalX(-1, width), 0f)
        assertTrue(IndexMotion.signalX(0, width) >= 0f)
    }

    @Test fun theRowCascadeStaggersTwelveRowsAndTheRestAppearAtOnce() {
        val c = motion.getValue("rowCascade").jsonObject
        val stagger = c.getValue("staggerMs").jsonPrimitive.int
        val max = c.getValue("maxStaggered").jsonPrimitive.int
        assertEquals(0, IndexMotion.rowDelayMs(0))
        assertEquals(stagger * (max - 1), IndexMotion.rowDelayMs(max - 1))
        assertNull(IndexMotion.rowDelayMs(max))
        assertNull(IndexMotion.rowDelayMs(-1))
    }

    @Test fun eachDigitOfTheNumeralRollStartsLaterThanTheOneBefore() {
        val perDigit = motion.getValue("numeralRoll").jsonObject.getValue("perDigitDelayMs").jsonPrimitive.int
        assertEquals(0, IndexMotion.digitDelayMs(0))
        assertEquals(perDigit * 2, IndexMotion.digitDelayMs(2))
    }
}
