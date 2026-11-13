package app.discair.ui.settings

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.ui.common.RowDivider
import app.discair.ui.player.PlayerIcons

/**
 * One Settings row as `downloads-settings-server` frame 2 draws it: a leading icon, the name, a state line in words under it,
 * and a chevron (or [trailing], the Scrobble switch) at the end, with a hairline above. The state is words, not colour alone.
 */
@Composable
fun SettingsRow(
    icon: ImageVector,
    title: String,
    state: String,
    modifier: Modifier = Modifier,
    stateColor: Color = MaterialTheme.colorScheme.onSurfaceVariant,
    onClick: (() -> Unit)? = null,
    trailing: (@Composable () -> Unit)? = null,
    divider: Boolean = true,
) {
    // Soft Brut: an icon tile, no hairline above the first row of a card (CoverStackSettings.kt). Every other theme is unchanged.
    if (app.discair.ui.common.isCoverStack()) { CoverStackSettingsRow(icon, title, state, modifier, stateColor, onClick, trailing, divider); return }
    // Flow: a 32dp icon tile in a white grouped card (FlowSettings.kt).
    if (app.discair.ui.common.isFlow()) { FlowSettingsRow(icon, title, state, modifier, stateColor, onClick, trailing, divider); return }
    Column(modifier) {
        RowDivider()
        Row(
            Modifier.fillMaxWidth().heightIn(min = 72.dp)
                .then(if (onClick != null) Modifier.clickable(role = Role.Button, onClick = onClick) else Modifier)
                .semantics(mergeDescendants = true) { contentDescription = "$title, $state" }
                .padding(vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(24.dp))
            Column(Modifier.weight(1f).padding(start = 16.dp, end = 16.dp)) {
                Text(title, style = MaterialTheme.typography.titleMedium)
                Text(state, style = MaterialTheme.typography.bodySmall, color = stateColor)
            }
            if (trailing != null) trailing() else Icon(PlayerIcons.Right, contentDescription = null)
        }
    }
}
