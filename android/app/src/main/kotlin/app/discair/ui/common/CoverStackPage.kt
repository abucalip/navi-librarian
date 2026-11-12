package app.discair.ui.common

import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.LocalPalette

/*
 * Pieces the Soft Brut (Layout.CoverStack) Album and Artist pages share. Mockup: soft-brut/album-artist-genre.
 * Nothing here is reached by another theme: only CoverStackAlbum and CoverStackArtist call it.
 */

/** The page's top bar: Back at the left, an optional three-dot menu at the right (mockup `.bar`). Sits under the status bar. */
@Composable
fun CoverStackTopBar(onBack: () -> Unit, menu: List<Pair<String, () -> Unit>>, modifier: Modifier = Modifier, title: String? = null) {
    val p = LocalPalette.current
    Row(modifier.statusBarsPadding().fillMaxWidth().padding(start = 8.dp, end = 8.dp, top = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button, onClick = onBack), contentAlignment = Alignment.Center) {
            Icon(PlayerIcons.Left, contentDescription = "Back", tint = p.text)
        }
        if (title != null) Text(
            title, Modifier.weight(1f).padding(start = 4.dp), color = p.text, maxLines = 1, overflow = TextOverflow.Ellipsis,
            style = MaterialTheme.typography.titleMedium.copy(fontSize = 15.sp, fontWeight = FontWeight.SemiBold),
        ) else Box(Modifier.weight(1f))
        if (menu.isNotEmpty()) {
            var open by remember { mutableStateOf(false) }
            Box {
                Box(Modifier.size(Target).clip(CircleShape).clickable(role = Role.Button) { open = true }, contentAlignment = Alignment.Center) {
                    Icon(Icons.Default.MoreVert, contentDescription = "More", tint = p.text)
                }
                DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
                    menu.forEach { (label, run) -> DropdownMenuItem(text = { Text(label) }, onClick = { open = false; run() }) }
                }
            }
        }
    }
}

/** A section heading (Space Grotesk 700 18) with an optional underlined ink link at the right (mockup `.h`). */
@Composable
fun CoverStackHeading(title: String, modifier: Modifier = Modifier, link: String? = null, onLink: () -> Unit = {}) {
    val p = LocalPalette.current
    Row(modifier.fillMaxWidth().padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(
            title, Modifier.weight(1f).semantics { heading() }, color = p.text,
            style = MaterialTheme.typography.titleLarge.copy(fontSize = 18.sp, lineHeight = 24.sp, fontWeight = FontWeight.Bold),
        )
        if (link != null) Box(Modifier.heightIn(min = Target).clickable(role = Role.Button, onClick = onLink).padding(start = 8.dp), contentAlignment = Alignment.Center) {
            Text(link, color = p.text, textDecoration = TextDecoration.Underline, style = MaterialTheme.typography.labelLarge.copy(fontSize = 13.sp, fontWeight = FontWeight.SemiBold))
        }
    }
}

/** A cover with the 1.5dp ink outline, radius 6 unless [radius] says otherwise (mockup `.cv`). */
@Composable
fun CoverStackCover(artist: String, album: String, ownedPath: String?, modifier: Modifier = Modifier, radius: Int = 6) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(radius.dp)
    AlbumCover(artist, album, ownedPath, modifier.aspectSquare().clip(shape).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape), rect = true)
}

/** A round artist photo, 68dp, with its name under it, two lines at most (mockup `.who`). */
@Composable
fun CoverStackArtistChip(name: String, ownedPath: String?, onClick: () -> Unit, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    Column(
        modifier.width(72.dp).clip(RoundedCornerShape(8.dp)).clickable(role = Role.Button, onClick = onClick),
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        ArtistPhoto(name, ownedPath, Modifier.size(68.dp).clip(CircleShape).border(CoverStackRules.outline(p).dp, p.edgeStrong, CircleShape), circle = true)
        Text(
            name, color = p.text, textAlign = TextAlign.Center, maxLines = 2, overflow = TextOverflow.Ellipsis,
            style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.SemiBold, lineHeight = 16.sp),
        )
    }
}

/** The page title: Space Grotesk 700, 26/30. */
@Composable
fun CoverStackTitle(text: String, modifier: Modifier = Modifier, maxLines: Int = 3) {
    Text(
        text, modifier.semantics { heading() }, color = LocalPalette.current.text, maxLines = maxLines, overflow = TextOverflow.Ellipsis,
        style = MaterialTheme.typography.headlineLarge.copy(fontSize = 26.sp, lineHeight = 30.sp, fontWeight = FontWeight.Bold),
    )
}

/** A cover or photo for TalkBack when it carries no caption. */
fun Modifier.describedAs(text: String): Modifier = semantics { contentDescription = text }
