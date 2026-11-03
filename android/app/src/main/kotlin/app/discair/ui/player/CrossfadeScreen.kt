package app.discair.ui.player

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import app.discair.ui.common.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.dp
import app.discair.AppContainer
import app.discair.DiscairApplication
import app.discair.player.PlayerSettings
import app.discair.player.crossfade
import app.discair.player.crossfade.CrossfadeSettings
import app.discair.player.crossfade.CrossfadeText
import app.discair.ui.common.Target

/** The settings as the page shows them; refreshed whenever any player setting is saved. */
@Composable
internal fun rememberCrossfade(settings: PlayerSettings): Pair<CrossfadeSettings, Int?> {
    var now by remember { mutableStateOf(settings.crossfade to settings.maxBitRate) }
    DisposableEffect(settings) {
        val handle = settings.onChange { now = settings.crossfade to settings.maxBitRate }
        onDispose { handle.close() }
    }
    return now
}

/**
 * The Crossfade page (ANDROID_CROSSFADE_CONTRACT.md 7). Every change is saved at once and applies at the next join.
 * The length changes with 48dp minus and plus buttons; the slider is the quick way, never the only way.
 * Off is shown in words and the controls stay on screen, marked unavailable.
 */
@Composable
fun CrossfadeScreen(container: AppContainer, onBack: (() -> Unit)?) {
    val settings = container.playerSettings
    val (xf, rate) = rememberCrossfade(settings)
    val on = xf.enabled
    val seconds = CrossfadeSettings.sanitizeSeconds(xf.seconds)
    Column(
        Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(start = 16.dp, top = 8.dp, end = 16.dp, bottom = 8.dp + app.discair.ui.LocalBottomClearance.current),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            // Inside the Now Playing sheet there is no back arrow: the sheet closes by swipe, scrim tap or back.
            if (onBack != null) IconButton(onClick = onBack, Modifier.size(Target)) { Icon(app.discair.ui.player.PlayerIcons.Left, contentDescription = "Back") }
            Text("Crossfade", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.semantics { heading() })
        }
        Row(
            Modifier.fillMaxWidth().heightIn(min = Target)
                .toggleable(value = on, role = Role.Switch, onValueChange = { settings.crossfadeEnabled = it }),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f).padding(end = 12.dp)) {
                Text("Crossfade", style = MaterialTheme.typography.titleMedium)
                Text(
                    CrossfadeText.switchHelp(on),
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            app.discair.ui.common.DiscairSwitch(checked = on)
        }

        Text("Length", style = MaterialTheme.typography.titleLarge, modifier = Modifier.padding(top = 8.dp).semantics { heading() })
        app.discair.ui.common.GlassCard(Modifier.fillMaxWidth()) {
            app.discair.ui.common.GlassBand(
                label = "Fade", value = CrossfadeText.length(seconds), spokenName = CrossfadeText.lengthSpoken(seconds),
                spokenValue = CrossfadeText.length(seconds),
                min = CrossfadeSettings.MIN_SECONDS.toFloat(), max = CrossfadeSettings.MAX_SECONDS.toFloat(),
                steps = CrossfadeSettings.MAX_SECONDS - CrossfadeSettings.MIN_SECONDS - 1,
                sliderValue = seconds.toFloat(), enabled = on,
                canLower = CrossfadeText.canLower(seconds), canRaise = CrossfadeText.canRaise(seconds),
                lowerLabel = "Shorten the crossfade by one second", raiseLabel = "Lengthen the crossfade by one second",
                onSlide = { settings.crossfadeSeconds = CrossfadeText.fromSlider(it) },
                onNudge = { settings.crossfadeSeconds = CrossfadeText.nudge(seconds, it) },
                valueWidth = 76.dp, labelWidth = 36.dp,
            )
        }

        Text("Albums", style = MaterialTheme.typography.titleLarge, modifier = Modifier.padding(top = 8.dp).semantics { heading() })
        val keep = xf.skipSameAlbum
        Row(
            Modifier.fillMaxWidth().heightIn(min = Target)
                .toggleable(value = keep, enabled = on, role = Role.Switch, onValueChange = { settings.crossfadeSkipSameAlbum = it }),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f).padding(end = 12.dp)) {
                Text("Keep albums gapless", style = MaterialTheme.typography.titleMedium)
                Text(
                    CrossfadeText.keepAlbumsHelp(keep),
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            app.discair.ui.common.DiscairSwitch(checked = keep, enabled = on)
        }

        CrossfadeText.qualityLine(rate)?.let {
            Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(top = 8.dp))
        }
        Text(
            "A change applies at the next song change, never to the song that is playing.",
            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.size(24.dp))
    }
}

/** The sheet's entry to the page: shown only while crossfade is on, in words, so the state is readable at a glance. */
@Composable
fun CrossfadeLink(onOpen: () -> Unit) {
    val settings = (LocalContext.current.applicationContext as DiscairApplication).container.playerSettings
    val (xf, _) = rememberCrossfade(settings)
    // Always shown so the page stays reachable; white when on, dim when off, and the state is spoken too.
    val label = CrossfadeText.nowPlayingLink(xf) ?: "Crossfade: off"
    val brut = app.discair.ui.theme.LocalPalette.current.brutal
    app.discair.ui.common.PlayerIconButton(onClick = onOpen, Modifier.size(if (brut) 48.dp else Target), selected = xf.enabled) {
        Icon(PlayerIcons.Swap, contentDescription = label, tint = if (brut) androidx.compose.material3.LocalContentColor.current else if (xf.enabled) Color.White else Color.White.copy(alpha = 0.4f), modifier = Modifier.size(24.dp))
    }
}
