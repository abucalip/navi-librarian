package app.discair.ui.theme

import android.provider.Settings
import androidx.compose.animation.ContentTransform
import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.Easing
import androidx.compose.animation.core.FiniteAnimationSpec
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.snap
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import kotlin.math.roundToInt

/*
 * The motion kit (docs/redesign.md section 7.4, step A2). Pure rules first, so they are unit-tested without a device:
 * [MotionRules] turns a token, a layout family and the reduced-motion flag into a duration, a curve, a spring or a
 * stagger. The composables at the bottom only apply those values to Compose.
 */

/** A cubic-bezier curve as its four control values, in the order CSS writes them. */
data class Bezier(val x1: Float, val y1: Float, val x2: Float, val y2: Float)

/** The curve of a transition: a bezier, or straight across (Tape, which is mechanical). */
sealed interface Curve {
    data class Curved(val bezier: Bezier) : Curve
    data object Linear : Curve
}

/** A tween: how long it runs and how it eases. */
data class Timing(val durationMs: Int, val curve: Curve)

/** A spring with a damping ratio; 1.0 is critically damped, so it never overshoots. */
data class SpringSpec(val damping: Float, val stiffness: Float)

/** Which motion family a theme's layout uses (7.4: Day and Night are the standard, Tape is mechanical, Sheet is springy). */
enum class MotionFamily { Standard, Tape, Sheet }

/** What a transition does, which picks its curve (7.4: "anything arriving", "anything leaving", "moves within the screen"). */
enum class MotionRole { Arrive, Leave, Move }

/** The tokens of 7.4. Durations are in milliseconds. */
object MotionTokens {
    const val FAST_MS = 100
    const val BASE_MS = 200
    const val ENTER_MS = 300
    const val EMPHASIS_MS = 400
    const val SHEET_MS = 350

    val EASE_ENTER = Bezier(0.05f, 0.7f, 0.1f, 1f)
    val EASE_EXIT = Bezier(0.3f, 0f, 0.8f, 0.15f)
    val EASE_STANDARD = Bezier(0.2f, 0f, 0f, 1f)

    const val SPRING_DAMPING = 0.8f
    const val SPRING_STIFFNESS = 380f

    /** Sheet's springier damping on entering cards and sheets (7.4). */
    const val SHEET_SPRING_DAMPING = 0.7f

    /** Tape runs every duration at this share of the table (7.4). */
    const val TAPE_SCALE = 0.6f

    /** Cards rise and fade in with a 50 ms step, for the first four only (7.2, Screen load). */
    const val STAGGER_MS = 50
    const val STAGGER_MAX_ITEMS = 4

    /** Rise of entering content, in dp. */
    const val RISE_DP = 16

    /** Horizontal slide of a shared-axis push, in dp. */
    const val SLIDE_DP = 30
}

object MotionRules {
    /** The family a theme's layout uses. The Sticker Wall has no motion of its own in 7.4, so it takes the standard family. */
    fun familyFor(layout: Layout): MotionFamily = when (layout) {
        Layout.Standard, Layout.StickerWall, Layout.CoverStack -> MotionFamily.Standard
        Layout.TapeDeck -> MotionFamily.Tape
        Layout.SheetStack -> MotionFamily.Sheet
    }

    /** A token's duration for a family: the table value, Tape at 60%, and 0 when the phone reduces motion. */
    fun duration(baseMs: Int, family: MotionFamily, reduced: Boolean): Int = when {
        reduced -> 0
        family == MotionFamily.Tape -> (baseMs * MotionTokens.TAPE_SCALE).roundToInt()
        else -> baseMs
    }

    /** easeExit runs for two thirds of the time the matching enter takes (7.4). */
    fun exitDuration(enterMs: Int): Int = (enterMs * 2f / 3f).roundToInt()

    /** The curve for a role: Tape is linear everywhere, the others use their bezier. */
    fun curve(role: MotionRole, family: MotionFamily): Curve = when {
        family == MotionFamily.Tape -> Curve.Linear
        role == MotionRole.Arrive -> Curve.Curved(MotionTokens.EASE_ENTER)
        role == MotionRole.Leave -> Curve.Curved(MotionTokens.EASE_EXIT)
        else -> Curve.Curved(MotionTokens.EASE_STANDARD)
    }

    /** A tween for a token and a role. The role picks the curve; the duration is the token's own (pass [exitDuration] for a leave that follows an enter). */
    fun timing(baseMs: Int, role: MotionRole, family: MotionFamily, reduced: Boolean): Timing =
        Timing(duration(baseMs, family, reduced), curve(role, family))

    /**
     * The spring for a gesture or an entering card. Null when the phone reduces motion: the caller then snaps to the end.
     * Tape has no overshoot (damping 1.0). Sheet's entering cards and sheets use 0.7; everything else uses 0.8.
     */
    fun spring(family: MotionFamily, entering: Boolean, reduced: Boolean): SpringSpec? {
        if (reduced) return null
        val damping = when {
            family == MotionFamily.Tape -> 1f
            family == MotionFamily.Sheet && entering -> MotionTokens.SHEET_SPRING_DAMPING
            else -> MotionTokens.SPRING_DAMPING
        }
        return SpringSpec(damping, MotionTokens.SPRING_STIFFNESS)
    }

    /** Delay before the [index]th item of a staggered entrance. Only the first [MotionTokens.STAGGER_MAX_ITEMS] wait; the rest arrive together. */
    fun staggerDelayMs(index: Int, family: MotionFamily, reduced: Boolean): Int {
        if (reduced || index < 0 || index >= MotionTokens.STAGGER_MAX_ITEMS) return 0
        return duration(MotionTokens.STAGGER_MS, family, reduced) * index
    }

    /** Rise of entering content in dp; 0 when reduced. */
    fun riseDp(reduced: Boolean): Int = if (reduced) 0 else MotionTokens.RISE_DP

    /** Slide of a shared-axis push in dp; 0 when reduced. */
    fun slideDp(reduced: Boolean): Int = if (reduced) 0 else MotionTokens.SLIDE_DP
}

/** Tab change (7.4): the old content fades out, then the new one fades in while it rises. */
data class FadeThroughPlan(val leave: Timing, val arrive: Timing, val arriveDelayMs: Int, val riseDp: Int)

/** Push to a stack page (7.4): the new page slides in over a 30 dp shared axis while it fades; the old one moves the other way. */
data class SharedAxisPlan(val arrive: Timing, val leave: Timing, val slideDp: Int)

/** Cover to Album page (7.4): the cover grows into the album header over `enter` on `easeStandard`. */
data class SharedCoverPlan(val bounds: Timing)

object MotionPlans {
    /** Null when the phone reduces motion: the cover is then not shared and the page uses the plain transition. */
    fun sharedCover(family: MotionFamily, reduced: Boolean): SharedCoverPlan? =
        if (reduced) null else SharedCoverPlan(MotionRules.timing(MotionTokens.ENTER_MS, MotionRole.Move, family, reduced))

    fun fadeThrough(family: MotionFamily, reduced: Boolean): FadeThroughPlan {
        val leave = MotionRules.timing(MotionTokens.FAST_MS, MotionRole.Leave, family, reduced)
        val arrive = MotionRules.timing(MotionTokens.BASE_MS, MotionRole.Arrive, family, reduced)
        return FadeThroughPlan(leave, arrive, arriveDelayMs = leave.durationMs, riseDp = MotionRules.riseDp(reduced))
    }

    fun sharedAxisX(family: MotionFamily, reduced: Boolean): SharedAxisPlan = SharedAxisPlan(
        arrive = MotionRules.timing(MotionTokens.ENTER_MS, MotionRole.Arrive, family, reduced),
        leave = MotionRules.timing(MotionRules.exitDuration(MotionTokens.ENTER_MS), MotionRole.Leave, family, reduced),
        slideDp = MotionRules.slideDp(reduced),
    )
}

/** True when the phone's animations are turned off (Settings, Developer options or Accessibility, "Remove animations"). */
@Composable
fun rememberReducedMotion(): Boolean {
    val context = LocalContext.current
    return remember { Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f }
}

/** The motion family of the theme the owner chose. */
@Composable
@ReadOnlyComposable
fun currentMotionFamily(): MotionFamily = MotionRules.familyFor(currentLayout())

private fun Curve.easing(): Easing = when (this) {
    is Curve.Curved -> CubicBezierEasing(bezier.x1, bezier.y1, bezier.x2, bezier.y2)
    Curve.Linear -> LinearEasing
}

/** A Compose tween for [this] timing, starting after [delayMs]. */
fun <T> Timing.toTween(delayMs: Int = 0): FiniteAnimationSpec<T> = tween(durationMillis = durationMs, delayMillis = delayMs, easing = curve.easing())

/** A Compose spring for [spec], or an instant snap when [spec] is null (reduced motion). */
fun <T> SpringSpec?.toSpring(): FiniteAnimationSpec<T> = if (this == null) snap() else spring(dampingRatio = damping, stiffness = stiffness)

/** Tab change: the old content fades out, then the new one fades in and rises. Nothing moves when reduced. */
@Composable
fun fadeThrough(): ContentTransform {
    val family = currentMotionFamily()
    val reduced = rememberReducedMotion()
    val plan = MotionPlans.fadeThrough(family, reduced)
    if (reduced) return EnterTransition.None togetherWith ExitTransition.None
    val density = LocalDensity.current
    val risePx = with(density) { plan.riseDp.dp.roundToPx() }
    return (
        fadeIn(plan.arrive.toTween(plan.arriveDelayMs)) +
            slideInVertically(plan.arrive.toTween(plan.arriveDelayMs)) { risePx }
        ) togetherWith fadeOut(plan.leave.toTween())
}

/**
 * Push to a stack page along a horizontal shared axis. [forward] is true for a push and false for a pop, which runs the
 * other way. Nothing moves when reduced.
 */
@Composable
fun sharedAxisX(forward: Boolean = true): ContentTransform {
    val family = currentMotionFamily()
    val reduced = rememberReducedMotion()
    val plan = MotionPlans.sharedAxisX(family, reduced)
    if (reduced) return EnterTransition.None togetherWith ExitTransition.None
    val density = LocalDensity.current
    val slidePx = with(density) { plan.slideDp.dp.roundToPx() }
    val sign = if (forward) 1 else -1
    return (
        slideInHorizontally(plan.arrive.toTween()) { sign * slidePx } + fadeIn(plan.arrive.toTween())
        ) togetherWith (
        slideOutHorizontally(plan.leave.toTween()) { -sign * slidePx } + fadeOut(plan.leave.toTween())
        )
}

/**
 * A card that rises 16 dp and fades in. The first four items of a list wait 50 ms more than the one before them; the
 * rest arrive together. Shows at once, without motion, when reduced.
 */
@Composable
fun Modifier.enterStagger(index: Int): Modifier {
    val family = currentMotionFamily()
    val reduced = rememberReducedMotion()
    val timing = MotionRules.timing(MotionTokens.ENTER_MS, MotionRole.Arrive, family, reduced)
    val delay = MotionRules.staggerDelayMs(index, family, reduced)
    val progress = remember { Animatable(if (reduced) 1f else 0f) }
    LaunchedEffect(reduced) {
        if (reduced) progress.snapTo(1f) else progress.animateTo(1f, timing.toTween(delay))
    }
    return this.graphicsLayer {
        alpha = progress.value
        translationY = (1f - progress.value) * MotionRules.riseDp(reduced).dp.toPx()
    }
}
