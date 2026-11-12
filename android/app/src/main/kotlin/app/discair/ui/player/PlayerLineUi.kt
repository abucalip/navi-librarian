package app.discair.ui.player

import android.os.Build
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.BlurredEdgeTreatment
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.player.PlayerLine
import app.discair.ui.common.Target
import app.discair.ui.theme.rememberReducedMotion
import app.discair.ui.theme.Ink
import coil3.compose.AsyncImage

/** Everything the three player layouts need to show the line, the two switches and the sound graph. */
class LineUi(
    val line: PlayerLine,
    val peaks: FloatArray?,
    val showLyrics: Boolean,
    val showFacts: Boolean,
    val onLyrics: () -> Unit,
    val onFacts: () -> Unit,
)

/** True where the phone can blur an image (Android 12 and up); older phones keep the artwork tint. */
val canBlur: Boolean get() = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S

/** The cover, enlarged and blurred, behind the sheet, with a dark layer so light text keeps its contrast. Call inside a Box. */
@Composable
fun androidx.compose.foundation.layout.BoxScope.ArtworkBackdrop(coverUrl: String?) {
    if (!canBlur || coverUrl.isNullOrBlank()) return
    AsyncImage(
        model = coverUrl, contentDescription = null, contentScale = ContentScale.Crop,
        modifier = Modifier.matchParentSize().graphicsLayer { scaleX = 1.3f; scaleY = 1.3f }.blur(28.dp, BlurredEdgeTreatment.Unbounded),
    )
    Box(Modifier.matchParentSize().background(Color.Black.copy(alpha = 0.42f)))
}

/**
 * The one line: the synced lyric, or a fact with its source. It always keeps one line of height so nothing jumps between
 * lines. The line slides up and the old one leaves; under Reduce Motion it only fades. It is announced politely when a
 * lyric changes only if TalkBack asks for it, so a fact every 14 s does not interrupt.
 */
@Composable
fun PlayerLineText(line: PlayerLine, modifier: Modifier = Modifier, align: TextAlign = TextAlign.Center) {
    val reduced = rememberReducedMotion()
    val muted = MaterialTheme.colorScheme.onSurfaceVariant
    Box(modifier.fillMaxWidth().heightIn(min = 24.dp), contentAlignment = if (align == TextAlign.Start) Alignment.CenterStart else Alignment.Center) {
        AnimatedContent(
            targetState = line,
            transitionSpec = {
                if (reduced) fadeIn() togetherWith fadeOut()
                else (slideInVertically { it / 2 } + fadeIn()) togetherWith (slideOutVertically { -it / 2 } + fadeOut())
            },
            label = "playerLine",
        ) { l ->
            when (l) {
                is PlayerLine.Lyric -> Text(l.text, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold), maxLines = 1, overflow = TextOverflow.Ellipsis, textAlign = align)
                is PlayerLine.Fact -> Text(
                    l.fact.text + "  ·  " + l.fact.source, style = MaterialTheme.typography.bodySmall, color = muted,
                    maxLines = 2, overflow = TextOverflow.Ellipsis, textAlign = align,
                )
                PlayerLine.Empty -> Text("", style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

/** A round on/off switch, 48 dp to touch and 32 dp to see; its state is said in words, not colour alone. */
@Composable
fun LineSwitch(on: Boolean, label: String, onClick: () -> Unit, icon: @Composable () -> Unit) {
    Box(
        Modifier.size(Target).clickable(role = Role.Switch, onClickLabel = label, onClick = onClick)
            .semantics { contentDescription = label; stateDescription = if (on) "On" else "Off" },
        contentAlignment = Alignment.Center,
    ) {
        val fill = if (on) Ink.Accent else Color.Transparent
        Box(
            Modifier.size(32.dp).clip(CircleShape).background(fill).border(1.5.dp, if (on) Ink.Accent else MaterialTheme.colorScheme.onSurfaceVariant, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            androidx.compose.runtime.CompositionLocalProvider(androidx.compose.material3.LocalContentColor provides if (on) Ink.Ink else MaterialTheme.colorScheme.onSurfaceVariant) { icon() }
        }
    }
}

/** The quote (lyric line) and i (facts) switches. */
@Composable
fun LineSwitches(ui: LineUi) {
    Row(horizontalArrangement = Arrangement.spacedBy(0.dp), verticalAlignment = Alignment.CenterVertically) {
        LineSwitch(ui.showLyrics, "Show the lyric line", ui.onLyrics) { Icon(PlayerIcons.Quote, null, Modifier.size(16.dp)) }
        LineSwitch(ui.showFacts, "Show facts", ui.onFacts) { Icon(PlayerIcons.Info, null, Modifier.size(16.dp)) }
    }
}
