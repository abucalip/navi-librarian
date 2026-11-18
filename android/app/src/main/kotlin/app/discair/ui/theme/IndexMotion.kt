package app.discair.ui.theme

import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.TweenSpec
import androidx.compose.animation.core.tween

/*
 * Index's motion values (docs/INDEX_THEME.md section 8, docs/design/index/tokens.json → motion). Firm and directional: things slide along the axis they
 * belong to and stop without overshoot; no springs, no scale, no fades on navigation. Pure, so IndexMotionTest pins every value to the tokens.
 * Every duration goes through [MotionRules.duration], so it is 0 when the phone removes animations; Index code never calls Compose's own `tween`.
 */
object IndexMotion {
    val Firm = CubicBezierEasing(0.77f, 0f, 0.18f, 1f)

    /** rowCascade and sheetIn. */
    val Settle = CubicBezierEasing(0.2f, 0f, 0f, 1f)

    /** sheetOut. */
    val Exit = CubicBezierEasing(0.4f, 0f, 1f, 1f)

    const val TAB_SLIDE_MS = 380
    const val PUSH_MS = 340
    const val ROW_MS = 300
    const val ROW_STAGGER_MS = 20
    const val ROW_MAX = 12
    const val ROW_FROM_DP = -12
    const val SIGNAL_MS = 380
    const val SOURCE_BAR_MS = 260
    const val PLAYER_RISE_MS = 420
    const val PLAYER_FALL_MS = 320
    const val SHEET_IN_MS = 260
    const val SHEET_OUT_MS = 200
    const val NUMERAL_MS = 420
    const val NUMERAL_DIGIT_DELAY_MS = 40
    const val RULE_MS = 360
    const val SNACK_MS = 220

    /** Section 8.2 #10: the snackbar leaves in 180ms, 56dp down, and holds 4s ([SNACK_HOLD_MS], tokens.json `snackIn.holdMs`). */
    const val SNACK_OUT_MS = 180
    const val SNACK_FROM_DP = 56
    const val SNACK_HOLD_MS = 4000L

    /** Section 8.2 #2: a pushed page enters from +[PUSH_ENTER_FRACTION] of the width with a [PUSH_FADE_MS] fade, and the page under it leaves to -[PUSH_EXIT_FRACTION] and dims to [PUSH_DIM]. */
    const val PUSH_FADE_MS = 200
    const val PUSH_ENTER_FRACTION = 0.3f
    const val PUSH_EXIT_FRACTION = 0.12f
    const val PUSH_DIM = 0.85f

    /** The signal block is 14% of the bar's width and 3dp high (section 7, Dock). */
    const val SIGNAL_WIDTH_FRACTION = 0.14f
    const val SIGNAL_HEIGHT_DP = 3

    /** Generic, so the same call serves Float, Dp and IntOffset (slides) animations. */
    fun <T> firm(ms: Int, reduced: Boolean, delayMs: Int = 0): TweenSpec<T> =
        tween(MotionRules.duration(ms, MotionFamily.Standard, reduced), if (reduced) 0 else delayMs, Firm)

    /** The same, on the [Settle] curve (sheets in, the row cascade). */
    fun <T> settle(ms: Int, reduced: Boolean, delayMs: Int = 0): TweenSpec<T> =
        tween(MotionRules.duration(ms, MotionFamily.Standard, reduced), if (reduced) 0 else delayMs, Settle)

    /** The same, on the [Exit] curve (sheets out). */
    fun <T> exit(ms: Int, reduced: Boolean, delayMs: Int = 0): TweenSpec<T> =
        tween(MotionRules.duration(ms, MotionFamily.Standard, reduced), if (reduced) 0 else delayMs, Exit)

    /** A plain linear fade of [ms] (the push's 200ms fade): the duration still goes through [MotionRules.duration]. */
    fun <T> fade(ms: Int, reduced: Boolean): TweenSpec<T> =
        tween(MotionRules.duration(ms, MotionFamily.Standard, reduced), 0, androidx.compose.animation.core.LinearEasing)

    /** Section 8.2 #5: the delay of row [index] in the cascade, or null for a row past [ROW_MAX], which simply appears. */
    fun rowDelayMs(index: Int): Int? = if (index in 0 until ROW_MAX) index * ROW_STAGGER_MS else null

    /** Section 8.2 #7: digit [index] of a rolling numeral starts this late. */
    fun digitDelayMs(index: Int): Int = index * NUMERAL_DIGIT_DELAY_MS

    /** The bar's order, which decides the tab slide's direction (decision I3). Search is an overlay and has no slide. */
    val barOrder: List<String> = listOf("Home", "Discover", "Library", "Search")

    /** +1 when the target is to the right of the start in the bar, else -1. */
    fun tabDirection(from: Int, to: Int): Int = if (to > from) 1 else -1

    /** The signal block's left edge for the selected cell: the cell's centre less half the block, in the same unit as [barWidth]. */
    fun signalX(selected: Int, barWidth: Float, cells: Int = barOrder.size): Float {
        val cell = barWidth / cells
        return cell * selected.coerceAtLeast(0) + cell / 2f - barWidth * SIGNAL_WIDTH_FRACTION / 2f
    }
}
