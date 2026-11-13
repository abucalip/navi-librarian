package app.discair.ui.settings

import app.discair.ui.common.ArtIcons
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.AppContainer
import app.discair.AppViewModel
import app.discair.UiState
import app.discair.ui.LocalBottomClearance
import app.discair.ui.common.CoverStackDivider
import app.discair.ui.common.CoverStackRules
import app.discair.ui.common.CoverStackTitle
import app.discair.ui.common.CoverStackTopBar
import app.discair.ui.common.DiscairSwitch
import app.discair.ui.common.Target
import app.discair.ui.common.coverStackFrame
import app.discair.ui.downloads.SettingsRules
import app.discair.ui.player.Eyebrow
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.LocalPalette

/*
 * Soft Brut's (Layout.CoverStack) Settings. Mockup: soft-brut/settings, frame 1. SettingsScreen reaches CoverStackSettingsPage behind
 * isCoverStack(); every row, switch, menu and button is the Standard page's, grouped into outlined cards with an icon tile each.
 * The pieces here (group, row, switch row) are also the Server, Equalizer and Crossfade pages' building blocks.
 */

/** An outlined card that holds a list of rows (mockup `.list.card`): the rows sit 12dp in from its edge, dashed rules between them. */
@Composable
internal fun CsGroup(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    val p = LocalPalette.current
    Column(
        modifier.padding(start = 16.dp, end = 16.dp + CoverStackRules.shadow(p).dp).fillMaxWidth()
            .coverStackFrame(RoundedCornerShape(CoverStackRules.radius(p).dp), p).padding(horizontal = 12.dp),
        content = content,
    )
}

/** One row of a group: a 36dp outlined icon tile on the pale accent, the name, its state in words, a chevron or [trailing] (mockup `.li`). */
@Composable
internal fun CoverStackSettingsRow(
    icon: ImageVector, title: String, state: String, modifier: Modifier, stateColor: Color, onClick: (() -> Unit)?, trailing: (@Composable () -> Unit)?, divider: Boolean,
) {
    val p = LocalPalette.current
    val tile = RoundedCornerShape(6.dp)
    Column(modifier) {
        if (divider) CoverStackDivider()
        Row(
            Modifier.fillMaxWidth().heightIn(min = 64.dp)
                .then(if (onClick != null) Modifier.clickable(role = Role.Button, onClick = onClick) else Modifier)
                .semantics(mergeDescendants = true) { contentDescription = "$title, $state" }
                .padding(vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.size(36.dp).clip(tile).background(p.accentDim).border(CoverStackRules.outline(p).dp, p.edgeStrong, tile), contentAlignment = Alignment.Center) {
                Icon(icon, contentDescription = null, tint = p.text, modifier = Modifier.size(20.dp))
            }
            Column(Modifier.weight(1f)) {
                Text(title, color = p.text, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
                Text(state, color = if (stateColor == Color.Unspecified) p.textMuted else stateColor, style = MaterialTheme.typography.bodySmall)
            }
            if (trailing != null) trailing() else Icon(ArtIcons.Chevron, contentDescription = null, tint = p.text)
        }
    }
}

/** A row with a title, a line of help and a switch, the whole row toggling (mockup: the cards over Equalizer, Crossfade and Albums). */
@Composable
internal fun CsSwitchRow(title: String, help: String, checked: Boolean, enabled: Boolean = true, onChange: (Boolean) -> Unit) {
    val p = LocalPalette.current
    Row(
        Modifier.fillMaxWidth().heightIn(min = 64.dp).toggleable(value = checked, enabled = enabled, role = Role.Switch, onValueChange = onChange).padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, color = p.text, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
            Text(help, color = p.textMuted, style = MaterialTheme.typography.bodySmall)
        }
        DiscairSwitch(checked = checked, enabled = enabled)
    }
}

/** A mono eyebrow over a group (mockup `.h .eb`). */
@Composable
internal fun CsEyebrow(text: String) {
    Box(Modifier.padding(start = 16.dp, end = 16.dp, top = 20.dp, bottom = 8.dp)) { Eyebrow(text, heading = true) }
}

/** The words on the Settings page that are not drawing. */
object CoverStackSettingsRules {
    /** The groups in the order the mockup draws them, by eyebrow. */
    val eyebrows = listOf("Look and sound", "Listening", "Playback")
}

/** The Settings page: Server and services; Look and sound; Listening; Playback; then the connection buttons and Sign out. */
@Composable
internal fun CoverStackSettingsPage(
    state: UiState, model: AppViewModel, container: AppContainer, onBack: () -> Unit,
    onEqualizer: () -> Unit, onCrossfade: () -> Unit, onAppearance: () -> Unit, onServer: () -> Unit, onSignOut: () -> Unit,
) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(bottom = 24.dp + LocalBottomClearance.current)) {
        CoverStackTopBar(onBack, emptyList(), title = "Settings")
        CoverStackTitle("Settings", Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 12.dp), maxLines = 1)
        Column(Modifier.padding(horizontal = 16.dp)) { app.discair.ui.CheckLines(state) }
        val serverLine = SettingsRules.serverLine(state.librarian, state.navidrome)
        CsGroup {
            SettingsRow(
                ArtIcons.Server, "Server and services", serverLine.text, onClick = onServer, divider = false,
                stateColor = when (serverLine.tone) {
                    SettingsRules.Tone.Success -> p.ok
                    SettingsRules.Tone.Danger -> p.chartRedText
                    else -> p.textMuted
                },
            )
        }
        CsEyebrow("Look and sound")
        CsGroup {
            AppearanceRow(container.appearance, onAppearance, divider = false)
            app.discair.ui.PlaybackSettings(container, onEqualizer, onCrossfade, app.discair.ui.PlaybackShow.LookAndSound)
        }
        CsEyebrow("Listening")
        CsGroup {
            RadioSettings(divider = false)
            ListenBrainzSettings()
            app.discair.ui.LibrarySettings()
        }
        CsEyebrow("Playback")
        CsGroup { app.discair.ui.PlaybackSettings(container, onEqualizer, onCrossfade, app.discair.ui.PlaybackShow.Rest) }
        Row(Modifier.padding(start = 16.dp, end = 19.dp, top = 20.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            app.discair.ui.discover.SmallButton("Check connection", null, false, "Check connection", Modifier.weight(1f)) { model.recheck() }
            app.discair.ui.discover.SmallButton("Edit servers", null, false, "Edit servers", Modifier.weight(1f)) { model.editServers() }
        }
        // Destructive and rare: set apart and always confirmed (the sheet is the page's).
        Box(Modifier.padding(start = 16.dp, end = 19.dp, top = 12.dp).fillMaxWidth()) {
            val shape = RoundedCornerShape(CoverStackRules.radius(p).dp)
            Row(
                Modifier.fillMaxWidth().height(48.dp).coverStackFrame(shape, p).clickable(role = Role.Button, onClick = onSignOut),
                horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically,
            ) { Text("Sign out…", color = p.chartRedText, style = MaterialTheme.typography.labelLarge.copy(fontSize = 14.sp, fontWeight = FontWeight.Bold)) }
        }
    }
}
