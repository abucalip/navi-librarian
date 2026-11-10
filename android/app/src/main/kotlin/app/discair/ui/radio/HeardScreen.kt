package app.discair.ui.radio

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.model.RadioPlay
import app.discair.player.RadioPlayback
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.PageHeading
import app.discair.ui.common.RowDivider
import app.discair.ui.common.rememberLoad
import app.discair.ui.home.Inline
import app.discair.ui.home.Muted
import app.discair.ui.theme.Ink

/**
 * Songs heard on the radio (docs/RADIO_PLAYBACK_CONTRACT.md section 4), newest first from `GET /api/radio/plays`, each with the
 * same Download states as Now Playing: Download, Downloading, Downloaded, Owned, Try again. The list is read each time the page
 * opens; the Download request is the existing `POST /api/radio/plays/{id}/get`.
 */
@Composable
fun HeardScreen(radio: RadioPlayback, onBack: () -> Unit) {
    val repo = LocalRepository.current
    val plays = rememberLoad("radio_plays") { repo.radioPlays() }
    val live by radio.state.collectAsState()
    Column(Modifier.fillMaxSize()) {
        app.discair.ui.common.BackBar(onBack)
        LazyColumn(Modifier.fillMaxWidth(), contentPadding = PaddingValues(bottom = 24.dp + app.discair.ui.LocalBottomClearance.current)) {
            item { PageHeading("Heard on radio", Modifier.padding(start = 16.dp, end = 16.dp, bottom = 8.dp)) }
            live.message?.let { text ->
                item(key = "message") { Text(text, Modifier.padding(horizontal = 16.dp, vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Polite }, style = MaterialTheme.typography.bodyMedium) }
            }
            when (val state = plays.state) {
                Load.Loading -> item { Muted("Loading…") }
                is Load.Failed -> item { Inline(state.failure.message, plays.reload) }
                is Load.Ready -> {
                    if (state.value.isEmpty()) item { Muted("Nothing heard yet. A song is logged once you have listened to it for about 30 seconds.") }
                    items(state.value, key = { it.id }) { play ->
                        PlayRow(play, live.downloadFor(play.id, play.grabbed, play.inLibrary), onDownload = { radio.download(play.id) }, failure = live.failed[play.id])
                        RowDivider()
                    }
                }
            }
        }
    }
}

@Composable
private fun PlayRow(play: RadioPlay, download: app.discair.model.RadioDownload, onDownload: () -> Unit, failure: String?) {
    Row(Modifier.fillMaxWidth().heightIn(min = 72.dp).padding(horizontal = 16.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(Modifier.weight(1f)) {
            Text(play.title, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis)
            Text(
                listOfNotNull(play.artist, play.stationName.takeIf { it.isNotBlank() }).joinToString(" · ").ifBlank { "Artist not named" },
                style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis,
            )
            failure?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = Ink.ChartRedText) }
        }
        // A song with no named artist cannot be looked up (RADIO-01), so it has no button rather than a dead one.
        if (play.hasArtist) DownloadControl(download, onDownload, noun = play.title)
    }
}
