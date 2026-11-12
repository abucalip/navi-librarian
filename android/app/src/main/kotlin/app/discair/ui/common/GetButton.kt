package app.discair.ui.common

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.togetherWith
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.keyframes
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.material3.ProgressIndicatorDefaults
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.vector.ImageVector
import app.discair.ui.theme.MotionRole
import app.discair.ui.theme.MotionRules
import app.discair.ui.theme.MotionTokens
import app.discair.ui.theme.Timing
import app.discair.ui.theme.currentMotionFamily
import app.discair.ui.theme.rememberReducedMotion
import app.discair.ui.theme.toTween
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.dp
import app.discair.R
import app.discair.data.AcquisitionHub
import app.discair.model.GetState
import app.discair.ui.theme.Ink
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

val LocalAcquisitions = compositionLocalOf<AcquisitionHub> { error("No acquisition hub") }

/** Metadata for a Get that starts from a page rather than a list row (the web sends the same fields). */
fun pageMetadata(artist: String, album: String, year: Int?, releaseGroupMbid: String? = null): JsonObject = buildJsonObject {
    put("artist", artist)
    put("album", album)
    if (year != null) put("year", year)
    if (releaseGroupMbid != null) put("release_group_mbid", releaseGroupMbid)
}

/**
 * The cloud Get control (ACQ-02). Idle offers the request; pending shows a spinner and ignores taps;
 * requested shows a check and ignores taps, so a request is never sent twice; failed shows a warning
 * and a tap tries again. The four states differ by icon and spoken state, never by colour alone, and
 * Requested appears only after the server accepted the request.
 */
@Composable
fun GetButton(noun: String, name: String, state: GetState, onClick: () -> Unit, modifier: Modifier = Modifier, overlay: Boolean = false) {
    val family = currentMotionFamily()
    val reduced = rememberReducedMotion()
    // A failed request shakes once it appears (docs/redesign.md 7.4). The first composition never shakes, so a
    // row that scrolls back into view does not repeat a failure it already showed.
    val failed = state is GetState.Failed
    val shake = remember { Animatable(0f) }
    var seenFirst by remember { mutableStateOf(false) }
    LaunchedEffect(failed) {
        if (failed && seenFirst && !reduced) shake.animateTo(0f, shakeSpec())
        seenFirst = true
    }
    IconButton(
        onClick = { if (state is GetState.Idle || state is GetState.Failed) onClick() },
        modifier.size(Target).semantics {
            contentDescription = "Get $noun $name"
            stateDescription = when (state) {
                GetState.Idle -> "Not requested"
                GetState.Pending -> "Requesting"
                is GetState.Requested -> "Requested. Follow it under Downloads"
                is GetState.Failed -> "Could not request. ${state.message} Select to try again"
            }
        },
    ) {
        // The icon swaps with a 200 ms cross-fade and a scale from 0.8 to 1 (the base token); reduced motion swaps at once.
        val enter = MotionRules.timing(MotionTokens.BASE_MS, MotionRole.Arrive, family, reduced)
        val leave = Timing(MotionRules.duration(MotionRules.exitDuration(MotionTokens.BASE_MS), family, reduced), MotionRules.curve(MotionRole.Leave, family))
        AnimatedContent(
            targetState = state,
            contentKey = { it::class },
            modifier = Modifier.graphicsLayer { translationX = shake.value.dp.toPx() },
            transitionSpec = {
                if (reduced) EnterTransition.None togetherWith ExitTransition.None
                else (fadeIn(enter.toTween()) + scaleIn(initialScale = 0.8f, animationSpec = enter.toTween())) togetherWith fadeOut(leave.toTween())
            },
            label = "get-state",
        ) { s ->
            when (s) {
                GetState.Idle -> GetIcon(app.discair.ui.player.PlayerIcons.Cloud, null, overlay)
                GetState.Pending -> CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp, color = if (overlay) Color.White else ProgressIndicatorDefaults.circularColor)
                is GetState.Requested -> GetIcon(Icons.Default.Check, Ink.Ok, overlay)
                is GetState.Failed -> GetIcon(Icons.Default.Warning, Ink.ChartRedText, overlay)
            }
        }
    }
}

/** Two full cycles of 4 dp, 300 ms in total (the enter token's length; the table gives no shake token). */
private fun shakeSpec() = keyframes<Float> {
    durationMillis = 300
    0f at 0
    4f at 60
    -4f at 120
    4f at 180
    -4f at 240
    0f at 300
}

/**
 * A state icon. On artwork ([overlay]) it has no backing circle: it is white (or its state colour) over a soft
 * dark shadow, so it stays visible on light covers.
 */
@Composable
private fun GetIcon(icon: ImageVector, tint: Color?, overlay: Boolean) {
    if (!overlay) {
        if (tint == null) Icon(icon, contentDescription = null) else Icon(icon, contentDescription = null, tint = tint)
        return
    }
    Box(contentAlignment = Alignment.Center) {
        Icon(icon, contentDescription = null, tint = Color.Black.copy(alpha = 0.6f), modifier = Modifier.offset(y = 1.dp).blur(2.dp))
        Icon(icon, contentDescription = null, tint = tint ?: Color.White)
    }
}

/** Get for a whole album. */
@Composable
fun GetAlbumButton(artist: String, album: String, metadata: JsonObject, modifier: Modifier = Modifier, overlay: Boolean = false) {
    val hub = LocalAcquisitions.current
    GetButton("album", album, hub.getState(artist, album), { hub.getAlbum(artist, album, metadata) }, modifier, overlay)
}

/** Get for one song, filed with [album] by the server. */
@Composable
fun GetSongButton(
    artist: String, album: String, title: String, trackNumber: Int?, year: Int?, modifier: Modifier = Modifier,
) {
    val hub = LocalAcquisitions.current
    GetButton(
        "song", title, hub.getState(artist, album, title),
        { hub.getTrack(artist, album, title, trackNumber, year) }, modifier,
    )
}
