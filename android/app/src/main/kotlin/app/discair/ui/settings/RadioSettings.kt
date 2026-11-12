package app.discair.ui.settings

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.selection.toggleable
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.data.RADIO_LOGO_MAX_BYTES
import app.discair.model.RadioScrobbling
import app.discair.model.RadioStation
import app.discair.model.RadioLogoVersion
import app.discair.model.radioLogoRequest
import app.discair.ui.common.Cover
import app.discair.ui.common.DiscairSwitch
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.Target
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** The words under the scrobbling switch (contract section 3.7): off by default, and honest when Last.fm is not set up on the server. */
internal fun scrobblingText(s: RadioScrobbling?, failed: String?): String = when {
    failed != null -> failed
    s == null -> "Checking the server."
    !s.configured && !s.enabled -> "Off. Last.fm is not set up on the server, so this cannot be switched on yet."
    s.enabled -> "On. The server sends each radio song to Last.fm once you have heard it for 30 seconds."
    else -> "Off. Radio songs are not sent to Last.fm."
}

/** Reads at most [RADIO_LOGO_MAX_BYTES] + 1 bytes, so an oversized picture is refused without loading all of it. Null when unreadable. */
internal fun readLogo(open: () -> java.io.InputStream?): ByteArray? = try {
    open()?.use { it.readNBytes(RADIO_LOGO_MAX_BYTES + 1) }
} catch (e: java.io.IOException) {
    null
}

/**
 * Radio settings (docs/RADIO_PLAYBACK_CONTRACT.md section 4): the scrobbling switch, the app address the phone reaches the relay at
 * (read only here: changing it rewrites the stations in Navidrome, which stays on the web Radio page), and a logo picker per station.
 * Everything lives on the server, so it is read live and written back.
 */
@Composable
fun RadioSettings() {
    val repo = LocalRepository.current
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    var scrobbling by remember { mutableStateOf<RadioScrobbling?>(null) }
    var scrobblingProblem by remember { mutableStateOf<String?>(null) }
    var appUrl by remember { mutableStateOf<String?>(null) }
    var stations by remember { mutableStateOf<List<RadioStation>?>(null) }
    var stationsProblem by remember { mutableStateOf(false) }
    var note by remember { mutableStateOf<String?>(null) }
    var logoEdits by remember { mutableIntStateOf(0) }
    var pickFor by remember { mutableStateOf<RadioStation?>(null) }

    LaunchedEffect(repo) {
        try { scrobbling = withContext(Dispatchers.IO) { repo.radioScrobbling() } } catch (e: CancellationException) { throw e } catch (e: Exception) { scrobblingProblem = "Could not read this from the server." }
        try { appUrl = withContext(Dispatchers.IO) { repo.radioAppUrl() } } catch (e: CancellationException) { throw e } catch (e: Exception) { appUrl = null }
        try { stations = withContext(Dispatchers.IO) { repo.radioStations() } } catch (e: CancellationException) { throw e } catch (e: Exception) { stationsProblem = true }
    }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        val station = pickFor ?: return@rememberLauncherForActivityResult
        pickFor = null
        if (uri == null) return@rememberLauncherForActivityResult
        scope.launch {
            note = null
            val bytes = withContext(Dispatchers.IO) { readLogo { context.contentResolver.openInputStream(uri) } }
            when {
                bytes == null || bytes.isEmpty() -> note = "That picture could not be read."
                bytes.size > RADIO_LOGO_MAX_BYTES -> note = "That picture is too large. Pick one under 2 MB."
                else -> try {
                    withContext(Dispatchers.IO) { repo.setRadioLogo(station.id, bytes) }
                    RadioLogoVersion.bump(); logoEdits++
                    note = "Logo saved for ${station.name}."
                } catch (e: CancellationException) { throw e } catch (e: Exception) { note = e.message ?: "The server did not save the logo. Try again." }
            }
        }
    }

    var expanded by androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf(false) }
    Column(Modifier.fillMaxWidth()) {
        val count = stations?.size
        SettingsRow(
            app.discair.ui.player.PlayerIcons.Radio, "Radio",
            when { stationsProblem -> "Could not read the stations"; count == null -> "Checking the server."; else -> app.discair.ui.common.plural(count, "station") },
            onClick = { expanded = !expanded },
            trailing = { androidx.compose.material3.Icon(if (expanded) app.discair.ui.player.PlayerIcons.Down else app.discair.ui.player.PlayerIcons.Right, contentDescription = if (expanded) "Collapse" else "Expand") },
        )
        if (expanded) Column(Modifier.fillMaxWidth()) {
        val current = scrobbling
        Row(
            Modifier.fillMaxWidth().heightIn(min = Target).then(
                if (current == null) Modifier else Modifier.toggleable(value = current.enabled, enabled = current.configured || current.enabled, role = Role.Switch) { on ->
                    scrobbling = current.copy(enabled = on); scrobblingProblem = null
                    scope.launch {
                        try {
                            scrobbling = withContext(Dispatchers.IO) { repo.setRadioScrobbling(on) }
                        } catch (e: CancellationException) { throw e } catch (e: Exception) {
                            scrobbling = current
                            scrobblingProblem = e.message ?: "The server did not save this. Try again."
                        }
                    }
                },
            ),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f).padding(end = 16.dp)) {
                Text("Scrobble radio songs", style = MaterialTheme.typography.titleMedium)
                Text(scrobblingText(current, scrobblingProblem), Modifier.semantics { liveRegion = LiveRegionMode.Polite }, style = MaterialTheme.typography.bodySmall, color = if (scrobblingProblem != null) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant)
            }
            if (current != null) DiscairSwitch(checked = current.enabled, enabled = current.configured || current.enabled)
        }
        Spacer(Modifier.size(8.dp))
        Text("App address", style = MaterialTheme.typography.titleMedium)
        Text(
            when {
                appUrl == null -> "Could not read the address from the server."
                appUrl!!.isBlank() -> "Not set. Set the address your phone reaches Discair at (for example the Tailscale address) on the web Radio page, so station streams can play here."
                else -> "${appUrl}\nThe relay address in Navidrome. It must be reachable from this phone. Change it on the web Radio page."
            },
            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.size(8.dp))
        Text("Station logos", style = MaterialTheme.typography.titleMedium)
        Text("Pick your own picture for a station (up to 2 MB). Without one, the server finds a logo itself.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        val list = stations
        when {
            stationsProblem -> Text("Could not read the stations from the server.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
            list == null -> Text("Checking the server.", style = MaterialTheme.typography.bodySmall)
            list.isEmpty() -> Text("No radio stations in Navidrome yet.", style = MaterialTheme.typography.bodySmall)
            else -> list.forEach { station ->
                Row(Modifier.fillMaxWidth().heightIn(min = 56.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    // `logoEdits` keys the picture so it reloads after a change.
                    androidx.compose.runtime.key(logoEdits) { Cover(radioLogoRequest(repo.absolute(station.logoUrl), 128), Modifier.size(40.dp), rect = false) }
                    Text(station.name, Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis)
                    TextButton(onClick = { pickFor = station; picker.launch("image/*") }, Modifier.heightIn(min = Target).semantics { contentDescription = "Change logo for ${station.name}" }) { Text("Change") }
                    TextButton(
                        onClick = {
                            scope.launch {
                                note = null
                                try {
                                    withContext(Dispatchers.IO) { repo.clearRadioLogo(station.id) }
                                    RadioLogoVersion.bump(); logoEdits++
                                    note = "${station.name} uses an automatic logo again."
                                } catch (e: CancellationException) { throw e } catch (e: Exception) { note = e.message ?: "The server did not clear the logo. Try again." }
                            }
                        },
                        Modifier.heightIn(min = Target).semantics { contentDescription = "Use the automatic logo for ${station.name}" },
                    ) { Text("Reset") }
                }
            }
        }
        note?.let { Text(it, Modifier.semantics { liveRegion = LiveRegionMode.Polite }, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
    }
    }
}
