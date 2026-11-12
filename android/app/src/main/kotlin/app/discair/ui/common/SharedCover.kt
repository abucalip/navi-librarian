package app.discair.ui.common

import androidx.compose.animation.AnimatedVisibilityScope
import androidx.compose.animation.ExperimentalSharedTransitionApi
import androidx.compose.animation.SharedTransitionScope
import androidx.compose.runtime.Composable
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.ui.Modifier
import app.discair.ui.theme.MotionPlans
import app.discair.ui.theme.currentMotionFamily
import app.discair.ui.theme.rememberReducedMotion
import app.discair.ui.theme.toTween

/*
 * Cover to Album page (docs/redesign.md 7.4): the cover on a shelf or grid grows into the album header. The shell provides the
 * two scopes; a screen outside it (a preview, a test) finds none and draws its cover as before. When the cover is not on
 * screen, nothing matches, and the page's own shared-axis push runs instead.
 */
@OptIn(ExperimentalSharedTransitionApi::class)
val LocalSharedTransitionScope = compositionLocalOf<SharedTransitionScope?> { null }

val LocalNavVisibilityScope = compositionLocalOf<AnimatedVisibilityScope?> { null }

/** The shared-element key of an album's cover: the album route key, so a shelf cover and its page header agree. */
fun coverElementKey(routeKey: String): String = "cover/$routeKey"

/**
 * Marks this cover as the shared element for the album [routeKey]. Use it on one cover per album per screen: two on one
 * screen with the same key would fight over the transition. Does nothing when the phone reduces motion.
 */
@OptIn(ExperimentalSharedTransitionApi::class)
@Composable
fun Modifier.sharedCover(routeKey: String): Modifier {
    val scope = LocalSharedTransitionScope.current ?: return this
    val visibility = LocalNavVisibilityScope.current ?: return this
    val plan = MotionPlans.sharedCover(currentMotionFamily(), rememberReducedMotion()) ?: return this
    return with(scope) {
        this@sharedCover.sharedElement(
            rememberSharedContentState(coverElementKey(routeKey)), visibility,
            boundsTransform = { _, _ -> plan.bounds.toTween() },
        )
    }
}
