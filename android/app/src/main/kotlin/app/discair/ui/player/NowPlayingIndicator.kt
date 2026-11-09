package app.discair.ui.player

import android.provider.Settings
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.StartOffset
import androidx.compose.animation.core.StartOffsetType
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/** The song that is playing now, for lists that mark it (the album page). Null when nothing is queued. */
data class PlayingNow(val albumId: String, val title: String, val isPlaying: Boolean, val track: Int? = null, val disc: Int? = null) {
    /**
     * True for the track of an album page: same album, same title (case aside), and, when both sides know them, the same track
     * and disc. An album can hold several versions of one title (takes of the same song); only the one playing is marked.
     */
    fun matches(albumId: String?, title: String, number: Int? = null, disc: Int? = null) =
        albumId != null && this.albumId == albumId && this.title.trim().equals(title.trim(), ignoreCase = true) &&
            (track == null || number == null || track == number) &&
            (this.disc == null || disc == null || (this.disc ?: 1) == disc)
}

val LocalPlayingNow = compositionLocalOf<PlayingNow?> { null }

/**
 * Five solid bars that grow and shrink from the centre line while the song plays, and stand still while it
 * is paused (or when the phone is set to reduce motion). Spoken as "Now playing" or "Paused here".
 */
@Composable
fun NowPlayingIndicator(playing: Boolean, modifier: Modifier = Modifier, size: Dp = 16.dp) {
    val context = LocalContext.current
    val still = !playing || remember { Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f }
    val color = MaterialTheme.colorScheme.primary
    val transition = rememberInfiniteTransition(label = "nowPlaying")
    // Each bar has its own speed and phase so they never move together.
    val durations = listOf(800, 650, 900, 720, 840)
    val offsets = listOf(120, 420, 240, 520, 330)
    val moving = durations.mapIndexed { i, ms ->
        val scale by transition.animateFloat(
            0.3f, 1f, infiniteRepeatable(tween(ms, easing = FastOutSlowInEasing), RepeatMode.Reverse, StartOffset(offsets[i], StartOffsetType.FastForward)), label = "bar$i",
        )
        scale
    }
    // Resting shape: tallest in the middle, as in the proposal.
    val resting = listOf(0.4f, 0.75f, 1f, 0.65f, 0.4f)
    val fractions = if (still) resting else moving.mapIndexed { i, m -> resting[i].coerceAtLeast(0.55f) * m }
    Canvas(modifier.size(size).semantics { contentDescription = if (playing) "Now playing" else "Paused here" }) {
        val barW = this.size.width * 3f / 24f
        val gap = (this.size.width - 5 * barW) / 4f
        fractions.forEachIndexed { i, f ->
            val barH = this.size.height * f
            drawRoundRect(
                color, Offset(i * (barW + gap), (this.size.height - barH) / 2f), Size(barW, barH), CornerRadius(barW / 2f),
            )
        }
    }
}
