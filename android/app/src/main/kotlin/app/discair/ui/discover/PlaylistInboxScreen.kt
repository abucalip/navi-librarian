package app.discair.ui.discover

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.model.InboxEdition
import app.discair.model.InboxTrack
import app.discair.player.QueueItem
import app.discair.ui.LocalBottomClearance
import app.discair.ui.common.BackBar
import app.discair.ui.common.Button
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.PageHeading
import app.discair.ui.common.rememberLoad
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle

@Composable
internal fun PlaylistInboxShelf(onOpen: (Long) -> Unit) {
    val repo = LocalRepository.current
    val inbox = rememberLoad(repo) { repo.playlistInbox() }
    Column(Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
        PageHeading("Playlist Inbox", Modifier.padding(horizontal = 16.dp))
        when (val state = inbox.state) {
            Load.Loading -> InboxStatus("Loading playlists…")
            is Load.Failed -> InboxStatus(state.failure.message, inbox.reload)
            is Load.Ready -> {
                val playlists = state.value
                if (playlists.items.isEmpty()) {
                    InboxStatus(
                        if (playlists.state == "unconfigured") "Connect ListenBrainz in Settings to receive playlists."
                        else "No playlists have arrived yet.",
                    )
                } else {
                    LazyRow(
                        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 6.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        items(playlists.items, key = { it.id }) { edition ->
                            Surface(color = MaterialTheme.colorScheme.surfaceVariant, shape = MaterialTheme.shapes.medium) {
                                Column(
                                    Modifier.width(238.dp).clickable(role = androidx.compose.ui.semantics.Role.Button) {
                                        onOpen(edition.id)
                                    }.padding(12.dp),
                                    verticalArrangement = Arrangement.spacedBy(2.dp),
                                ) {
                                    Text(edition.displayTitle, style = MaterialTheme.typography.titleMedium,
                                        maxLines = 2, overflow = TextOverflow.Ellipsis)
                                    EditionMetadata(edition)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
internal fun InboxEditionScreen(id: Long, onBack: () -> Unit, onPlay: (List<QueueItem>) -> Unit) {
    val repo = LocalRepository.current
    val loaded = rememberLoad(repo, id) { repo.inboxEdition(id) }
    Column(Modifier.fillMaxSize().statusBarsPadding()) {
        BackBar(onBack, "Playlist Inbox")
        when (val state = loaded.state) {
            Load.Loading -> InboxStatus("Loading playlist…")
            is Load.Failed -> InboxStatus(state.failure.message, loaded.reload)
            is Load.Ready -> {
                val edition = state.value
                val playback = remember(edition) { edition.playbackItems() }
                LazyColumn(
                    Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(start = 16.dp, end = 16.dp, bottom = 24.dp + LocalBottomClearance.current),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item {
                        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            PageHeading(edition.displayTitle, large = true)
                            EditionMetadata(edition)
                            Button(onClick = { onPlay(playback) }, enabled = playback.isNotEmpty()) { Text("Play owned tracks") }
                            if (edition.tracks.isEmpty()) Text("This playlist has no tracks.")
                        }
                    }
                    items(edition.tracks, key = { it.position }) { track -> TrackRow(track) }
                }
            }
        }
    }
}

@Composable
private fun EditionMetadata(edition: InboxEdition) {
    val source = when (edition.source) {
        "hosted" -> "ListenBrainz · Created for Me"
        "cf" -> "ListenBrainz · Recommendations"
        "local" -> "Discair"
        else -> "Playlist"
    }
    val date = remember(edition.generatedAt) {
        edition.generatedAt?.let {
            try {
                OffsetDateTime.parse(it).atZoneSameInstant(ZoneId.systemDefault())
                    .format(DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM))
            } catch (_: java.time.format.DateTimeParseException) {
                null
            }
        }
    }
    val count = edition.ownedCount?.let { "$it of ${edition.totalCount} owned" }
        ?: "${edition.totalCount} tracks · Ownership unavailable"
    Text(source, style = MaterialTheme.typography.bodySmall)
    Text(date ?: "Generation date unavailable", style = MaterialTheme.typography.bodySmall)
    Text(count, style = MaterialTheme.typography.bodySmall)
}

@Composable
private fun TrackRow(track: InboxTrack) {
    Column(Modifier.fillMaxWidth()) {
        Text("${track.position + 1}. ${track.displayTitle}", style = MaterialTheme.typography.titleSmall)
        val metadata = listOfNotNull(track.artist, track.album).filter(String::isNotBlank).joinToString(" · ")
        if (metadata.isNotEmpty()) Text(metadata, style = MaterialTheme.typography.bodyMedium)
        val ownership = when (track.matchState) {
            "owned" -> "Owned"
            "missing" -> "Missing"
            "ambiguous" -> "Ambiguous match"
            else -> "Ownership unavailable"
        }
        Text(ownership, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun InboxStatus(message: String, retry: (() -> Unit)? = null) {
    Column(Modifier.padding(horizontal = 16.dp, vertical = 4.dp)) {
        Text(message, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
        if (retry != null) OutlinedButton(onClick = retry) { Text("Try again") }
    }
}
