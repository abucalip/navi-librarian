package app.discair.ui.home

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.R
import app.discair.data.releaseMonth
import app.discair.model.DiscoveryEntry
import app.discair.model.GetState
import app.discair.ui.Opener
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.Load
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.Target
import app.discair.ui.common.rememberLoad
import app.discair.ui.common.routeKey
import app.discair.ui.theme.Mono

private const val ROWS_PER_PAGE = 3

/** "New releases": albums from the discovery list, three tiles to a page, pages that slide sideways. */
@Composable
fun NewReleasesSection(open: Opener) {
    val repo = LocalRepository.current
    val loaded = rememberLoad("new_releases") { repo.discovery("new_releases", 20).entries.distinctBy { it.key } }
    Text(
        "New releases", style = MaterialTheme.typography.headlineMedium,
        modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 24.dp, bottom = 8.dp).semantics { heading() },
    )
    when (val state = loaded.state) {
        Load.Loading -> Muted("Loading…")
        is Load.Failed -> Inline(state.failure.message, loaded.reload)
        is Load.Ready -> {
            val pages = state.value.chunked(ROWS_PER_PAGE)
            if (pages.isEmpty()) Muted("Nothing here yet.")
            else HorizontalPager(
                rememberPagerState { pages.size }, Modifier.fillMaxWidth(),
                contentPadding = PaddingValues(start = 16.dp, end = 32.dp), pageSpacing = 16.dp,
                verticalAlignment = Alignment.Top,
            ) { page ->
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    pages[page].forEach { entry -> ReleaseTile(entry, open) }
                }
            }
        }
    }
}

@Composable
private fun ReleaseTile(entry: DiscoveryEntry, open: Opener) {
    val item = entry.item
    val artist = item.artistName
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp))
            .clickable(role = Role.Button) { open.album(routeKey(artist, item.album), artist, item.album, null, item.year) },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        AlbumCover(artist, item.album, null, Modifier.size(72.dp).clip(RoundedCornerShape(12.dp)), rect = true)
        Column(Modifier.weight(1f).padding(horizontal = 12.dp)) {
            Text(item.album, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis)
            Text(
                artist, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1, overflow = TextOverflow.Ellipsis,
            )
        }
        releaseMonth(item.firstReleaseDate, item.year)?.let {
            Text(it, style = MaterialTheme.typography.labelMedium.copy(fontFamily = Mono), color = MaterialTheme.colorScheme.onSurface, maxLines = 1)
        }
        ReleaseMenu(entry)
    }
}

/** The three dots: Download, as on the Discover cards. */
@Composable
private fun ReleaseMenu(entry: DiscoveryEntry) {
    val item = entry.item
    val hub = LocalAcquisitions.current
    val get = hub.getState(item.artistName, item.album)
    var open by remember { mutableStateOf(false) }
    Box {
        IconButton(onClick = { open = true }, Modifier.size(Target)) {
            Icon(Icons.Default.MoreVert, contentDescription = "Options for ${item.album}")
        }
        DropdownMenu(open, onDismissRequest = { open = false }) {
            val downloadable = !item.acquired && (get is GetState.Idle || get is GetState.Failed)
            DropdownMenuItem(
                text = { Text(if (item.acquired) "In your library" else if (get is GetState.Requested) "Requested" else "Download") },
                leadingIcon = { Icon(app.discair.ui.player.PlayerIcons.Cloud, contentDescription = null) },
                enabled = downloadable,
                onClick = { open = false; hub.getAlbum(item.artistName, item.album, entry.raw) },
            )
        }
    }
}
