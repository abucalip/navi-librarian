package app.discair.ui

import app.discair.ui.common.ArtIcons
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.LocalThemePalette

/**
 * The navigation rail of wide screens (600 dp and over; docs/design/redesign section 7.1). It replaces the bottom navigation: Home,
 * Discover, Library and Search as labelled cells, and the player at the foot when the layout has a player button. The current page is
 * filled with the accent. It takes the owner's chosen theme.
 */
@Composable
fun NavRail(
    homeSelected: Boolean,
    discoverSelected: Boolean,
    librarySelected: Boolean,
    playing: Boolean,
    playerLabel: String,
    showPlayer: Boolean,
    onHome: () -> Unit,
    onDiscover: () -> Unit,
    onLibrary: () -> Unit,
    onSearch: () -> Unit,
    onPlayer: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val palette = LocalThemePalette.current ?: LocalPalette.current
    val reduced = app.discair.ui.theme.rememberReducedMotion()
    Column(
        modifier.width(80.dp).fillMaxHeight().background(palette.rail).statusBarsPadding().navigationBarsPadding().padding(vertical = 16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        RailCell(palette, "Home", homeSelected, onHome, ArtIcons.Home)
        RailCell(palette, "Discover", discoverSelected, onDiscover, ArtIcons.Disc)
        RailCell(palette, "Library", librarySelected, onLibrary, ArtIcons.Lib)
        RailCell(palette, "Search", false, onSearch, ArtIcons.Search)
        Spacer(Modifier.weight(1f))
        if (showPlayer) {
            Column(
                Modifier.width(64.dp).height(56.dp).clip(RoundedCornerShape(28.dp))
                    .clickable(role = Role.Button, onClickLabel = playerLabel, onClick = onPlayer)
                    .semantics { contentDescription = playerLabel },
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                app.discair.ui.common.TapeMeter(4, app.discair.ui.common.TapeDeckRules.meterMoves(playing, false, reduced), palette.text, size = 22.dp)
            }
        }
    }
}

@Composable
private fun RailCell(palette: app.discair.ui.theme.Palette, label: String, selected: Boolean, onClick: () -> Unit, icon: ImageVector) {
    val ink = if (selected) palette.onAccent else palette.text
    Column(
        Modifier.width(64.dp).height(56.dp).clip(RoundedCornerShape(28.dp))
            .background(if (selected) palette.accent else Color.Transparent)
            .clickable(role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label; this.selected = selected },
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Icon(icon, contentDescription = null, tint = ink, modifier = Modifier.size(24.dp))
    }
}
