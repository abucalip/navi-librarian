package app.discair.ui.radio

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import app.discair.model.RadioNow
import app.discair.model.RadioStation
import app.discair.model.radioNowText
import app.discair.ui.common.Cover
import app.discair.ui.home.Inline
import app.discair.ui.common.Load
import app.discair.ui.common.LocalRepository
import app.discair.ui.home.Muted
import app.discair.ui.common.PageHeading
import app.discair.ui.common.RowDivider
import app.discair.ui.common.Target
import app.discair.ui.common.rememberLoad
import app.discair.ui.theme.Ink
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** The radio session for the signed-in shell (built in MainShell). */
val LocalRadio = androidx.compose.runtime.compositionLocalOf<app.discair.player.RadioPlayback> { error("No radio playback") }

/** How often the live titles are asked for while the page is on screen (the route is one cheap read, no provider call). */
internal const val LIVE_REFRESH_MS = 15_000L

/**
 * The Radio page (docs/RADIO_PLAYBACK_CONTRACT.md section 4, slice 4): the owner's Navidrome stations with their
 * logos, favourites first as the server orders them, a live title strip per station from `GET /api/radio/now`, and a
 * favourite toggle. Playing a station comes in slice 5. The strip is refreshed only while the page is visible.
 */
@Composable
fun RadioScreen(onBack: () -> Unit, onOpenHeard: () -> Unit, onOpenPlayer: () -> Unit) {
    val repo = LocalRepository.current
    val radio = LocalRadio.current
    val onAir by radio.state.collectAsState()
    val stations = rememberLoad("radio_stations") { repo.radioStations() }
    val live = remember { mutableStateMapOf<String, RadioNow>() }
    val favourites = remember { mutableStateMapOf<String, Boolean>() }
    var message by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    val lifecycle = LocalLifecycleOwner.current.lifecycle

    LaunchedEffect(lifecycle, stations.state) {
        if (stations.state !is Load.Ready) return@LaunchedEffect
        lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (true) {
                try {
                    val items = withContext(Dispatchers.IO) { repo.radioNow() }
                    live.clear()
                    items.forEach { live[it.stationId] = it.now }
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    // The strip keeps its last words; the list itself is not an error.
                }
                delay(LIVE_REFRESH_MS)
            }
        }
    }

    Column(Modifier.fillMaxSize()) {
        app.discair.ui.common.BackBar(onBack)
        LazyColumn(Modifier.fillMaxWidth(), contentPadding = androidx.compose.foundation.layout.PaddingValues(bottom = 24.dp + app.discair.ui.LocalBottomClearance.current)) {
            item { PageHeading("Radio", Modifier.padding(start = 16.dp, end = 16.dp, bottom = 8.dp)) }
            item(key = "heard") {
                androidx.compose.material3.TextButton(onClick = onOpenHeard, Modifier.padding(horizontal = 8.dp).heightIn(min = Target)) { Text("Heard on radio") }
            }
            message?.let { text ->
                item(key = "message") {
                    Text(text, Modifier.padding(horizontal = 16.dp, vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Polite }, color = Ink.ChartRedText, style = MaterialTheme.typography.bodyMedium)
                }
            }
            when (val state = stations.state) {
                Load.Loading -> item { Muted("Loading…") }
                is Load.Failed -> item { Inline(state.failure.message, stations.reload) }
                is Load.Ready -> {
                    if (state.value.isEmpty()) item { Muted("No radio stations. Add them in Navidrome and they appear here.") }
                    items(state.value, key = { it.id }) { station ->
                        val favourite = favourites[station.id] ?: station.favourite
                        StationRow(
                            station = station,
                            favourite = favourite,
                            now = live[station.id],
                            onAir = onAir.stationId == station.id,
                            onPlay = { if (onAir.stationId == station.id) onOpenPlayer() else radio.play(station).also { onOpenPlayer() } },
                            onFavourite = {
                                val wanted = !favourite
                                favourites[station.id] = wanted
                                message = null
                                scope.launch {
                                    try {
                                        val saved = withContext(Dispatchers.IO) { repo.setRadioFavourite(station.id, wanted) }
                                        favourites[station.id] = saved
                                    } catch (e: CancellationException) {
                                        throw e
                                    } catch (e: Exception) {
                                        favourites.remove(station.id)
                                        message = "Could not save the favourite for ${station.name}. Try again."
                                    }
                                }
                            },
                        )
                        RowDivider()
                    }
                }
            }
        }
    }
}

@Composable
private fun StationRow(station: RadioStation, favourite: Boolean, now: RadioNow?, onAir: Boolean, onPlay: () -> Unit, onFavourite: () -> Unit) {
    val repo = LocalRepository.current
    Row(
        Modifier.fillMaxWidth().heightIn(min = 72.dp).clickable(onClickLabel = "Play ${station.name}", role = androidx.compose.ui.semantics.Role.Button, onClick = onPlay)
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Cover(repo.absolute(station.logoUrl) + "?size=128", Modifier.size(56.dp), rect = false)
        Column(Modifier.weight(1f)) {
            Text(if (onAir) "${station.name} · On air" else station.name, style = MaterialTheme.typography.titleMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(
                stripText(station, now),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
        IconButton(
            onClick = onFavourite,
            Modifier.size(Target).semantics { contentDescription = if (favourite) "Remove ${station.name} from favourites" else "Add ${station.name} to favourites" },
        ) {
            if (favourite) Icon(Icons.Default.Favorite, contentDescription = null, tint = Ink.Accent)
            else Icon(Icons.Default.FavoriteBorder, contentDescription = null)
        }
    }
}

/** The line under a station name: the live song, or the honest reason there is none (contract section 6). */
internal fun stripText(station: RadioStation, now: RadioNow?): String = when {
    !station.proxied -> radioNowText(RadioNow.Unknown.copy(state = app.discair.model.RadioNowState.NotProxied), false)
    now == null -> radioNowText(RadioNow.Unknown.copy(state = app.discair.model.RadioNowState.Idle), true)
    else -> radioNowText(now, true)
}
