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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleStartEffect
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import app.discair.model.AcquisitionJob
import app.discair.model.InboxDownload
import app.discair.model.InboxEdition
import app.discair.model.InboxTrack
import app.discair.model.inboxDownloadActive
import app.discair.model.inboxDownloadRetryable
import app.discair.model.statusInfo
import app.discair.net.ConnectionFailure
import app.discair.net.classifyException
import app.discair.player.QueueItem
import app.discair.ui.LocalBottomClearance
import app.discair.ui.common.BackBar
import app.discair.ui.common.Button
import app.discair.ui.common.Load
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.PageHeading
import app.discair.ui.common.rememberLoad
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

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
    val hub = LocalAcquisitions.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val scope = rememberCoroutineScope()
    var edition by remember(repo, id) { mutableStateOf<InboxEdition?>(null) }
    var refreshProblem by remember(repo, id) { mutableStateOf<String?>(null) }
    var refresh by remember(repo, id) { mutableIntStateOf(0) }
    val actions = remember(repo, id) { mutableStateMapOf<Int, InboxAction>() }

    LaunchedEffect(repo, id, lifecycle, refresh) {
        lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            var ownershipChecks = 0
            while (true) {
                try {
                    val fresh = withContext(Dispatchers.IO) { repo.inboxEdition(id) }
                    for (track in fresh.tracks) {
                        val action = actions[track.position] as? InboxAction.Result ?: continue
                        val attached = action.reply.acquisitionKey != null && track.acquisitionKey != null
                        val keepRetryMessage = inboxDownloadRetryable(action.reply.status) &&
                            action.reply.status == track.acquisitionStatus
                        if (track.matchState == "owned" || (attached && track.acquisitionStatus != null && !keepRetryMessage)) {
                            actions.remove(track.position)
                        }
                    }
                    edition = fresh
                    refreshProblem = null
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    refreshProblem = classifyException(e, networkAvailable = true).message
                }

                val statuses = edition?.tracks.orEmpty().mapNotNull { track ->
                    track.downloadStatus(actions[track.position])
                }
                if (statuses.any(::inboxDownloadActive)) {
                    delay(5_000)
                } else if (statuses.any { it == "imported" || it == "owned" } && ownershipChecks++ < 8) {
                    delay(15_000)
                } else {
                    break
                }
            }
        }
    }

    val currentEdition = edition
    val tracking = currentEdition?.tracks.orEmpty().any { track ->
        inboxDownloadActive(track.downloadStatus(actions[track.position]))
    }
    if (tracking) {
        LifecycleStartEffect(hub) {
            hub.watch()
            onStopOrDispose { hub.unwatch() }
        }
    }

    Column(Modifier.fillMaxSize().statusBarsPadding()) {
        BackBar(onBack, "Playlist Inbox")
        if (currentEdition == null) {
            val problem = refreshProblem
            if (problem == null) InboxStatus("Loading playlist…")
            else InboxStatus(problem) { refresh++ }
        } else {
            val playback = remember(currentEdition) { currentEdition.playbackItems() }
            LazyColumn(
                Modifier.fillMaxSize(),
                contentPadding = PaddingValues(start = 16.dp, end = 16.dp, bottom = 24.dp + LocalBottomClearance.current),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                item {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        PageHeading(currentEdition.displayTitle, large = true)
                        EditionMetadata(currentEdition)
                        Button(onClick = { onPlay(playback) }, enabled = playback.isNotEmpty()) { Text("Play owned tracks") }
                        OutlinedButton(onClick = { refresh++ }) { Text("Refresh status") }
                        refreshProblem?.let { InboxStatus(it) }
                        if (currentEdition.tracks.isEmpty()) Text("This playlist has no tracks.")
                    }
                }
                items(currentEdition.tracks, key = { it.position }) { track ->
                    val action = actions[track.position]
                    val key = track.acquisitionKey ?: (action as? InboxAction.Result)?.reply?.acquisitionKey
                    val job = hub.jobs?.firstOrNull { key?.matches(it) == true }
                    TrackRow(track, action, job) {
                        if (actions[track.position] != action) return@TrackRow
                        actions[track.position] = InboxAction.Pending
                        scope.launch {
                            actions[track.position] = try {
                                InboxAction.Result(withContext(Dispatchers.IO) { repo.downloadInboxTrack(id, track.position) })
                            } catch (e: CancellationException) {
                                throw e
                            } catch (e: Exception) {
                                val failure = classifyException(e, networkAvailable = true)
                                InboxAction.Failed(failure.message, (failure as? ConnectionFailure.Server)?.code != 409)
                            }
                            refresh++
                        }
                    }
                }
            }
        }
    }
}

private sealed interface InboxAction {
    data object Pending : InboxAction
    data class Result(val reply: InboxDownload) : InboxAction
    data class Failed(val message: String, val retryable: Boolean) : InboxAction
}

private fun InboxTrack.downloadStatus(action: InboxAction?): String? =
    if (matchState == "owned") null else (action as? InboxAction.Result)?.reply?.status ?: acquisitionStatus

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
private fun TrackRow(track: InboxTrack, action: InboxAction?, job: AcquisitionJob?, onDownload: () -> Unit) {
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
        if (track.matchState != "owned") {
            val status = track.downloadStatus(action)
            val result = (action as? InboxAction.Result)?.reply
            val failure = action as? InboxAction.Failed
            val liveJob = job?.takeIf { it.status == status }
            val percent = liveJob?.progress?.percent?.toInt()
            val message = when {
                action == InboxAction.Pending -> "Requesting download…"
                failure != null -> failure.message
                status == "imported" || status == "owned" -> "Waiting for library ownership to refresh"
                percent != null -> "${statusInfo(status.orEmpty()).label} · $percent%"
                else -> result?.message ?: liveJob?.error ?: liveJob?.message ?: status?.let { statusInfo(it).label }
            }
            if (message != null) {
                Text(message, style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
            }
            val retry = failure?.retryable ?: (inboxDownloadRetryable(status) ||
                (result?.ok == false && status != "identity_conflict" && !inboxDownloadActive(status)))
            val canDownload = action == null && status == null && track.matchState == "missing"
            if (action != InboxAction.Pending && (canDownload || retry)) {
                OutlinedButton(onClick = onDownload) { Text(if (retry && status != "dismissed") "Try again" else "Download") }
            }
        }
    }
}

@Composable
private fun InboxStatus(message: String, retry: (() -> Unit)? = null) {
    Column(Modifier.padding(horizontal = 16.dp, vertical = 4.dp)) {
        Text(message, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
        if (retry != null) OutlinedButton(onClick = retry) { Text("Try again") }
    }
}
