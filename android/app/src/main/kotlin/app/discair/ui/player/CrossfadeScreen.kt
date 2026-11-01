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
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
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
private fun rememberCrossfade(settings: PlayerSettings): Pair<CrossfadeSettings, Int?> {
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
fun CrossfadeScreen(container: AppContainer, onBack: () -> Unit) {
    val settings = container.playerSettings
    val (xf, rate) = rememberCrossfade(settings)
    val on = xf.enabled
    val seconds = CrossfadeSettings.sanitizeSeconds(xf.seconds)
    Column(
        Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack, Modifier.size(Target)) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back") }
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
            Switch(checked = on, onCheckedChange = null)
        }

        Text("Length", style = MaterialTheme.typography.titleLarge, modifier = Modifier.padding(top = 8.dp).semantics { heading() })
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Fade length", style = MaterialTheme.typography.bodyLarge)
            Text(CrossfadeText.length(seconds), style = MaterialTheme.typography.bodyLarge)
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(
                onClick = { settings.crossfadeSeconds = CrossfadeText.nudge(seconds, -1) },
                enabled = on && CrossfadeText.canLower(seconds), modifier = Modifier.size(Target),
            ) { Icon(PlayerIcons.Remove, contentDescription = "Shorten the crossfade by one second") }
            Slider(
                value = seconds.toFloat(), onValueChange = { settings.crossfadeSeconds = CrossfadeText.fromSlider(it) },
                valueRange = CrossfadeSettings.MIN_SECONDS.toFloat()..CrossfadeSettings.MAX_SECONDS.toFloat(),
                steps = CrossfadeSettings.MAX_SECONDS - CrossfadeSettings.MIN_SECONDS - 1,
                enabled = on,
                colors = SliderDefaults.colors(
                    activeTickColor = Color.Transparent, inactiveTickColor = Color.Transparent,
                    disabledActiveTickColor = Color.Transparent, disabledInactiveTickColor = Color.Transparent,
                ),
                modifier = Modifier.weight(1f).semantics {
                    contentDescription = CrossfadeText.lengthSpoken(seconds)
                    stateDescription = CrossfadeText.length(seconds)
                },
            )
            IconButton(
                onClick = { settings.crossfadeSeconds = CrossfadeText.nudge(seconds, +1) },
                enabled = on && CrossfadeText.canRaise(seconds), modifier = Modifier.size(Target),
            ) { Icon(PlayerIcons.Add, contentDescription = "Lengthen the crossfade by one second") }
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
            Switch(checked = keep, onCheckedChange = null, enabled = on)
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
    CrossfadeText.nowPlayingLink(xf)?.let { label ->
        TextButton(onClick = onOpen, Modifier.heightIn(min = Target)) { Text(label) }
    }
}
