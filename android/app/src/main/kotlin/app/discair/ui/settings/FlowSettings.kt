package app.discair.ui.settings

import app.discair.ui.common.ArtIcons
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.AppContainer
import app.discair.AppViewModel
import app.discair.UiState
import app.discair.ui.LocalBottomClearance
import app.discair.ui.common.DiscairSwitch
import app.discair.ui.common.FlowEyebrow
import app.discair.ui.common.FlowGroup
import app.discair.ui.common.FlowIconTile
import app.discair.ui.common.FlowLargeTitle
import app.discair.ui.common.FlowListRow
import app.discair.ui.common.FlowPageBar
import app.discair.ui.common.FlowRules
import app.discair.ui.common.FlowSmallButton
import app.discair.ui.downloads.SettingsRules
import app.discair.ui.theme.LocalPalette

/*
 * Flow's (Layout.Flow) Settings. Mockup: flow/settings, frame 1. SettingsScreen reaches FlowSettingsPage behind isFlow(); every row, switch,
 * menu and button is the Standard page's, grouped into white cards with a 32dp icon tile each. The group, row and switch row here are also the
 * Server, Appearance, Equalizer and Crossfade pages' building blocks.
 */

/** One row of a Flow group: a 32dp icon tile, the name, its state in words, a chevron or [trailing] (flow.css `.li`). */
@Composable
internal fun FlowSettingsRow(
    icon: ImageVector, title: String, state: String, modifier: Modifier, stateColor: Color, onClick: (() -> Unit)?, trailing: (@Composable () -> Unit)?, divider: Boolean,
) {
    // A caller that passes no colour gets Material's muted default, which is not Flow's; only a tone (green, amber, red) is carried over.
    val tone = if (stateColor == MaterialTheme.colorScheme.onSurfaceVariant) Color.Unspecified else stateColor
    FlowListRow(
        title, modifier, state, onClick, divider, leading = { FlowIconTile(icon) },
        trailing = trailing ?: if (onClick != null) null else ({}), stateColor = tone,
    )
}

/** A row with a title, a line of help and a Flow switch, the whole row toggling (mockup: the cards over Equalizer, Crossfade and Albums). */
@Composable
internal fun FlowSwitchRow(title: String, help: String, checked: Boolean, enabled: Boolean = true, onChange: (Boolean) -> Unit) {
    val p = LocalPalette.current
    Row(
        Modifier.fillMaxWidth().heightIn(min = FlowRules.ROW_MIN.dp).toggleable(value = checked, enabled = enabled, role = Role.Switch, onValueChange = onChange).padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, color = p.text, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp, lineHeight = 20.sp))
            Text(help, color = p.textMuted, style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.sp, lineHeight = 18.sp))
        }
        DiscairSwitch(checked = checked, enabled = enabled)
    }
}

/** A caption in capitals over a group (flow.css `.h .eb`). */
@Composable
internal fun FlowGroupEyebrow(text: String) {
    Box(Modifier.padding(start = 16.dp, end = 16.dp, top = 20.dp, bottom = 8.dp)) { FlowEyebrow(text) }
}

/** The bar and the large title every one of these pages starts with; [onBack] null (the Now Playing sheet) draws only the title. */
@Composable
internal fun FlowSettingsHead(title: String, onBack: (() -> Unit)?, barTitle: String = title) {
    if (onBack != null) FlowPageBar(onBack, emptyList(), title = barTitle)
    FlowLargeTitle(title, Modifier.padding(start = 16.dp, end = 16.dp, top = if (onBack != null) 8.dp else 16.dp, bottom = 12.dp))
}

/** The page's scroll column, clear of the floating navigation and the mini player. */
@Composable
internal fun FlowSettingsColumn(content: @Composable ColumnScope.() -> Unit) {
    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(bottom = 24.dp + LocalBottomClearance.current), content = content)
}

/** The Settings page: Server and services; Look and sound; Listening; Playback; then the connection buttons and Sign out. */
@Composable
internal fun FlowSettingsPage(
    state: UiState, model: AppViewModel, container: AppContainer, onBack: () -> Unit,
    onEqualizer: () -> Unit, onCrossfade: () -> Unit, onAppearance: () -> Unit, onServer: () -> Unit, onSignOut: () -> Unit,
) {
    val p = LocalPalette.current
    FlowSettingsColumn {
        FlowSettingsHead("Settings", onBack)
        Column(Modifier.padding(horizontal = 16.dp)) { app.discair.ui.CheckLines(state) }
        val serverLine = SettingsRules.serverLine(state.librarian, state.navidrome)
        FlowGroup {
            SettingsRow(
                ArtIcons.Server, "Server and services", serverLine.text, onClick = onServer, divider = false,
                stateColor = when (serverLine.tone) {
                    SettingsRules.Tone.Success -> p.ok
                    SettingsRules.Tone.Danger -> p.chartRedText
                    else -> p.textMuted
                },
            )
        }
        FlowGroupEyebrow("Look and sound")
        FlowGroup {
            AppearanceRow(container.appearance, onAppearance, divider = false)
            app.discair.ui.PlaybackSettings(container, onEqualizer, onCrossfade, app.discair.ui.PlaybackShow.LookAndSound)
        }
        FlowGroupEyebrow("Listening")
        FlowGroup {
            RadioSettings(divider = false)
            ListenBrainzSettings()
            app.discair.ui.LibrarySettings()
        }
        FlowGroupEyebrow("Playback")
        FlowGroup { app.discair.ui.PlaybackSettings(container, onEqualizer, onCrossfade, app.discair.ui.PlaybackShow.Rest) }
        Row(Modifier.padding(start = 16.dp, end = 16.dp, top = 20.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FlowSmallButton("Check connection", null, false, "Check connection", Modifier.weight(1f)) { model.recheck() }
            FlowSmallButton("Edit servers", null, false, "Edit servers", Modifier.weight(1f)) { model.editServers() }
        }
        // Destructive and rare: set apart and always confirmed (the sheet is the page's).
        Row(Modifier.padding(start = 16.dp, end = 16.dp, top = 4.dp).fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
            FlowDangerButton("Sign out…", onSignOut)
        }
    }
}

/** A capsule with a danger label on `raised`, for the rare destructive action (flow.css `.btn.d`). */
@Composable
internal fun FlowDangerButton(label: String, onClick: () -> Unit) {
    val p = LocalPalette.current
    Box(Modifier.fillMaxWidth().heightIn(min = 48.dp).clickable(role = Role.Button, onClick = onClick), contentAlignment = Alignment.Center) {
        Box(Modifier.heightIn(min = 34.dp).clip(RoundedCornerShape(17.dp)).background(p.raised).padding(horizontal = 18.dp), contentAlignment = Alignment.Center) {
            Text(label, color = p.chartRedText, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.SemiBold))
        }
    }
}
