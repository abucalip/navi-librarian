package app.discair.ui.discover

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import app.discair.model.TasteCard
import app.discair.model.TasteCardState
import app.discair.model.TasteProfiles
import app.discair.model.TasteShift
import app.discair.model.TasteWindow
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.ModalBottomSheet
import app.discair.ui.common.Target
import app.discair.ui.theme.Ink
import app.discair.ui.theme.themeShape

/**
 * The compact "Your taste" card at the top of Insights (mockup: docs/design/android-taste/mockups.html). It draws the
 * server's headline, the biggest listed movers as chips and a Recent / All time toggle; a tap opens [TasteSheet].
 * [loaded] is false until the saved profiles have been read, so a slow read is not shown as an empty state.
 */
@Composable
fun TasteCardView(profiles: TasteProfiles?, loaded: Boolean) {
    var sheet by remember { mutableStateOf(false) }
    var window by remember { mutableStateOf("recent") }
    val state = TasteCard.state(profiles)
    val cs = app.discair.ui.common.isCoverStack()
    val fl = app.discair.ui.common.isFlow()
    CardBox {
        Eyebrow(if ((cs || fl) && state is TasteCardState.Ready) "Your taste · " + TasteCard.windowLabel(state.headline.window, profiles?.recentDays ?: 90) else "Your taste")
        when (state) {
            TasteCardState.Empty -> {
                Text(
                    if (loaded) "Taste needs listening history." else "Reading your saved profile.",
                    style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() },
                )
                if (loaded) Text(
                    "Connect ListenBrainz or keep playing. Once a window has enough listens I will start describing it.",
                    color = Ink.TextMuted, style = MaterialTheme.typography.bodyMedium,
                )
            }
            is TasteCardState.Thin -> {
                Text("Still getting to know you.", style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
                Text(
                    "Only ${state.have} listens in the recent window. I won't call a shift until there are ${state.need}.",
                    color = Ink.TextMuted, style = MaterialTheme.typography.bodyMedium,
                )
                if (cs) CoverStackProgress(TasteCard.progress(state.have, state.need), "${state.have} of ${state.need} listens needed")
                else ProgressBar(TasteCard.progress(state.have, state.need), "${state.have} of ${state.need} listens needed")
                WindowToggle(window) { window = it }
                if (window == "all_time") AllTimeChips(profiles)
            }
            is TasteCardState.Ready -> {
                Text(state.headline.text, style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
                val label = TasteCard.windowLabel(state.headline.window, profiles?.recentDays ?: 90)
                if (cs || fl) {
                    // Soft Brut and Flow (mockup frame 2): the window's top four genres as ranked bars, then the listen counts and Details.
                    val w = profiles?.window(state.headline.window)
                    val top = if (w == null || w.isLowSample("genre")) emptyList() else w.entries("genre").take(4)
                    if (top.isNotEmpty()) { if (fl) FlowBars(top) else CoverStackBars(top) }
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            "${state.windowListens} listens against ${state.allTimeListens} overall", Modifier.weight(1f),
                            color = Ink.TextMuted, style = MaterialTheme.typography.bodySmall,
                        )
                        if (fl) FlowLink("Details") { sheet = true } else CoverStackLink("Details") { sheet = true }
                    }
                } else {
                Text(
                    "${state.windowListens} listens, $label, against ${state.allTimeListens} overall",
                    color = Ink.TextMuted, style = MaterialTheme.typography.bodySmall,
                )
                if (window == "recent") {
                    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        for (s in state.movers.take(TasteCard.ChipCount)) MoverChip(s)
                    }
                } else AllTimeChips(profiles)
                WindowToggle(window, recentLabel = label) { window = it }
                }
            }
        }
        if (cs && state is TasteCardState.Thin) CoverStackLink("Details") { sheet = true }
        else if (fl && state is TasteCardState.Thin) FlowLink("Details") { sheet = true }
        else if (state !is TasteCardState.Empty && !((cs || fl) && state is TasteCardState.Ready)) {
            Row(
                Modifier.fillMaxWidth().heightIn(min = Target).clickable(role = Role.Button) { sheet = true },
                horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("See the full picture", color = Ink.Accent, style = MaterialTheme.typography.labelLarge)
                Text("›", color = Ink.Accent)
            }
        }
    }
    if (sheet && profiles != null) TasteSheet(profiles) { sheet = false }
}

@Composable
private fun CardBox(content: @Composable () -> Unit) {
    if (app.discair.ui.common.isCoverStack()) { CoverStackCardBox { content() }; return }
    if (app.discair.ui.common.isFlow()) { FlowCardBox { content() }; return }
    Column(
        Modifier.fillMaxWidth().clip(themeShape(16.dp)).background(MaterialTheme.colorScheme.surface).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) { content() }
}

@Composable
private fun Eyebrow(text: String) {
    if (app.discair.ui.common.isFlow()) { app.discair.ui.common.FlowEyebrow(text); return }
    // Soft Brut never sets the accent as text: its eyebrow is the muted mono label.
    if (app.discair.ui.common.isCoverStack()) Text(
        text.uppercase(), color = app.discair.ui.theme.LocalPalette.current.textMuted,
        style = MaterialTheme.typography.labelSmall.copy(fontFamily = app.discair.ui.theme.LocalFontPair.current.mono, fontWeight = androidx.compose.ui.text.font.FontWeight.Medium, fontSize = 11.sp, lineHeight = 16.sp, letterSpacing = 0.88.sp),
    ) else Text(text.uppercase(), color = Ink.Accent, style = MaterialTheme.typography.labelSmall)
}

/** One mover: the value and its change in points. Colour is never the only signal: the sign and the arrow word are read out too. */
@Composable
private fun MoverChip(s: TasteShift) {
    val points = TasteCard.percent(s.toShare) - TasteCard.percent(s.fromShare)
    val sign = if (points >= 0) "+$points" else "−${-points}"
    Row(
        Modifier.clip(RoundedCornerShape(99.dp)).background(Ink.Raised).padding(horizontal = 10.dp, vertical = 4.dp)
            .semantics(mergeDescendants = true) {
                contentDescription = "${s.value}, ${s.dimension}, ${if (s.isUp) "up" else "down"} ${kotlin.math.abs(points)} points"
            },
        horizontalArrangement = Arrangement.spacedBy(5.dp),
    ) {
        Text(s.value, style = MaterialTheme.typography.labelLarge)
        Text(sign, color = if (s.isUp) Ink.Ok else Ink.Caution, style = MaterialTheme.typography.labelLarge)
    }
}

/** The all-time view of the card: the biggest genres by share, only when the server calls that dimension sound. */
@Composable
private fun AllTimeChips(profiles: TasteProfiles?) {
    val all = profiles?.window("all_time")
    val top = if (all == null || all.isLowSample("genre")) emptyList() else all.entries("genre").take(TasteCard.ChipCount)
    if (top.isEmpty()) {
        Text("Not enough tagged listens for an all-time view yet.", color = Ink.TextMuted, style = MaterialTheme.typography.bodySmall)
        return
    }
    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        for (e in top) Row(
            Modifier.clip(RoundedCornerShape(99.dp)).background(Ink.Raised).padding(horizontal = 10.dp, vertical = 4.dp)
                .semantics(mergeDescendants = true) { contentDescription = "${e.value}, ${TasteCard.percent(e.share)} percent" },
            horizontalArrangement = Arrangement.spacedBy(5.dp),
        ) {
            Text(e.value, style = MaterialTheme.typography.labelLarge)
            Text("${TasteCard.percent(e.share)}%", color = Ink.TextMuted, style = MaterialTheme.typography.labelLarge)
        }
    }
}

/** The mockup's two-way toggle. Each segment keeps the 48dp touch height even though the pill looks smaller. */
@Composable
private fun WindowToggle(selected: String, recentLabel: String = "Recent", onSelect: (String) -> Unit) {
    if (app.discair.ui.common.isFlow()) {
        app.discair.ui.common.FlowTabs(listOf(recentLabel, "All time"), if (selected == "recent") 0 else 1, { onSelect(if (it == 0) "recent" else "all_time") })
        return
    }
    if (app.discair.ui.common.isCoverStack()) {
        app.discair.ui.common.CoverStackTabs(listOf(recentLabel, "All time"), if (selected == "recent") 0 else 1, { onSelect(if (it == 0) "recent" else "all_time") }, Modifier.padding(end = 3.dp))
        return
    }
    Row(
        Modifier.clip(RoundedCornerShape(99.dp)).background(Ink.Raised).padding(3.dp).semantics { contentDescription = "Window" },
        horizontalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        for ((key, name) in listOf("recent" to recentLabel, "all_time" to "All time")) {
            val on = selected == key
            Box(
                Modifier.heightIn(min = Target).clip(RoundedCornerShape(99.dp))
                    .background(if (on) Ink.Surface else Ink.Raised)
                    .clickable(role = Role.RadioButton) { onSelect(key) }
                    .semantics { this.selected = on }
                    .padding(horizontal = 14.dp),
                contentAlignment = Alignment.Center,
            ) { Text(name, color = if (on) Ink.Text else Ink.TextMuted, style = MaterialTheme.typography.labelLarge) }
        }
    }
}

@Composable
private fun ProgressBar(fraction: Double, description: String) {
    Column(Modifier.semantics(mergeDescendants = true) { contentDescription = description }, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Box(Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)).background(Ink.Raised)) {
            Box(Modifier.fillMaxWidth(fraction.toFloat()).height(8.dp).background(Ink.Accent))
        }
        Text(description, color = Ink.TextMuted, style = MaterialTheme.typography.bodySmall, modifier = Modifier.clearAndSetSemantics { })
    }
}

/**
 * The full picture: every listed mover (from, to, in percent), then one window's ranked bars for one dimension, with the
 * all-time share as a tick. A low-sample window or dimension is shown as a sketch, never as a finding.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun TasteSheet(profiles: TasteProfiles, onDismiss: () -> Unit) {
    var window by remember { mutableStateOf("recent") }
    var dimension by remember { mutableStateOf("genre") }
    val headline = profiles.headline
    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = 18.dp).padding(bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            val cs = app.discair.ui.common.isCoverStack()
            val fl = app.discair.ui.common.isFlow()
            if (cs || fl) Text("Your taste", style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() }) else Eyebrow("Your taste")
            Text(headline?.text ?: "No clear shift yet.", style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
            if (headline != null) {
                for (s in profiles.shifts(headline.window)) MoverRow(s)
            } else {
                Text(
                    "I only call a change when both the recent window and your history are solid.",
                    color = Ink.TextMuted, style = MaterialTheme.typography.bodyMedium,
                )
            }
            val dimensionRow: @Composable () -> Unit = {
                Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    for (d in TasteProfiles.Dimensions) Pick(d.replaceFirstChar { it.uppercase() }, dimension == d) { dimension = d }
                }
            }
            val windows = TasteProfiles.WindowNames
            // Soft Brut draws the windows first, then the dimension chips (mockup frame 3).
            if (!cs && !fl) dimensionRow()
            app.discair.ui.common.SegmentedTabs(
                windows.map { TasteCard.windowLabel(it, profiles.recentDays) }, windows.indexOf(window).coerceAtLeast(0),
                onSelect = { window = windows[it] }, modifier = Modifier.fillMaxWidth().then(if (cs) Modifier.padding(end = 3.dp) else Modifier),
            )
            if (cs || fl) dimensionRow()
            val w = profiles.window(window)
            if (w == null) {
                Text("No ${TasteCard.windowLabel(window, profiles.recentDays).lowercase()} window yet.", color = Ink.TextMuted, style = MaterialTheme.typography.bodyMedium)
            } else {
                Bars(w, profiles.window("all_time"), dimension, showTick = window != "all_time")
            }
            // The mockup's one filled action: the server builds a Navidrome playlist from the genre.
            TasteCard.playlistTarget(profiles)?.let { target ->
                val repo = LocalRepository.current
                val scope = rememberCoroutineScope()
                var made by remember(target) { mutableStateOf<PlaylistState>(PlaylistState.Idle) }
                app.discair.ui.common.Button(
                    onClick = {
                        made = PlaylistState.Working
                        scope.launch {
                            made = try {
                                PlaylistState.Done(withContext(Dispatchers.IO) { repo.makeTastePlaylist(target) }.name)
                            } catch (e: Exception) {
                                PlaylistState.Failed
                            }
                        }
                    },
                    enabled = made != PlaylistState.Working,
                    modifier = Modifier.fillMaxWidth().heightIn(min = Target).padding(top = 8.dp),
                ) { Text(
                    if (made == PlaylistState.Working) "Making the playlist…"
                    else if (app.discair.ui.common.isFlow()) "Make a playlist from $target" // the mockup's words (flow/discover frame 3)
                    else "Make ${if (target.firstOrNull()?.lowercaseChar()?.let { it in "aeiou" } == true) "an" else "a"} $target playlist",
                ) }
                when (val m = made) {
                    is PlaylistState.Done -> Text("Made \"${m.name}\" in Navidrome.", color = Ink.TextMuted, style = MaterialTheme.typography.bodySmall)
                    PlaylistState.Failed -> Text("Could not make the playlist. Try again.", color = app.discair.ui.theme.LocalPalette.current.chartRedText, style = MaterialTheme.typography.bodySmall)
                    else -> {}
                }
            }
        }
    }
}

private sealed interface PlaylistState {
    data object Idle : PlaylistState
    data object Working : PlaylistState
    data class Done(val name: String) : PlaylistState
    data object Failed : PlaylistState
}

@Composable
private fun Pick(label: String, on: Boolean, onClick: () -> Unit) {
    if (app.discair.ui.common.isCoverStack()) { CoverStackChip(label, on, onClick); return }
    if (app.discair.ui.common.isFlow()) { app.discair.ui.common.FilterChip(on, onClick, { Text(label) }, Modifier.heightIn(min = Target)); return }
    Box(
        Modifier.heightIn(min = Target).clip(RoundedCornerShape(99.dp))
            .background(if (on) Ink.Text else Ink.Raised)
            .clickable(role = Role.RadioButton, onClick = onClick).semantics { selected = on }
            .padding(horizontal = 14.dp),
        contentAlignment = Alignment.Center,
    ) { Text(label, color = if (on) Ink.Ink else Ink.TextMuted, style = MaterialTheme.typography.labelLarge) }
}

/** A listed shift as "Jazz  13% → 7%". The wording of the change is the numbers; the direction word is read out. */
@Composable
private fun MoverRow(s: TasteShift) {
    Row(
        Modifier.fillMaxWidth().semantics(mergeDescendants = true) {
            contentDescription = "${s.value}, ${s.dimension}, ${if (s.isUp) "up" else "down"} from ${TasteCard.percent(s.fromShare)} to ${TasteCard.percent(s.toShare)} percent"
        },
        horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(s.value, Modifier.weight(1f), maxLines = 1, style = MaterialTheme.typography.bodyMedium)
        Text(
            "${TasteCard.percent(s.fromShare)}% → ${TasteCard.percent(s.toShare)}%",
            color = if (s.isUp) Ink.Ok else Ink.Caution, style = MaterialTheme.typography.labelLarge,
        )
    }
}

@Composable
private fun Bars(w: TasteWindow, allTime: TasteWindow?, dimension: String, showTick: Boolean) {
    val sketch = w.lowSample || w.isLowSample(dimension)
    Text(
        if (sketch) "Only ${w.listens} listens here, so this is a sketch, not a verdict."
        else "${w.listens} listens" + if (showTick) ". Tick = your all-time share." else ".",
        color = Ink.TextMuted, style = MaterialTheme.typography.bodySmall,
    )
    val entries = w.entries(dimension).take(8)
    if (entries.isEmpty()) {
        Text("Nothing tagged for this yet.", color = Ink.TextMuted, style = MaterialTheme.typography.bodyMedium)
        return
    }
    if (app.discair.ui.common.isCoverStack()) { CoverStackBars(entries, sketch); return }
    if (app.discair.ui.common.isFlow()) { FlowBars(entries, sketch); return }
    for ((index, e) in entries.withIndex()) {
        val tick = if (showTick) allTime?.entries(dimension)?.firstOrNull { it.value == e.value }?.share else null
        Row(
            Modifier.fillMaxWidth().semantics(mergeDescendants = true) {
                contentDescription = "${e.value}, ${TasteCard.percent(e.share)} percent" + (tick?.let { ", all time ${TasteCard.percent(it)} percent" } ?: "")
            },
            horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(e.value, Modifier.width(96.dp), maxLines = 1, style = MaterialTheme.typography.bodySmall)
            Box(Modifier.weight(1f).height(10.dp).clip(RoundedCornerShape(5.dp)).background(Ink.Raised)) {
                Box(Modifier.fillMaxWidth(e.share.coerceIn(0.0, 1.0).toFloat()).height(10.dp).background(if (sketch || index > 0) Ink.TextMuted else Ink.Accent))
                if (tick != null) BoxWithFraction(tick)
            }
            Text("${TasteCard.percent(e.share)}%", Modifier.width(40.dp), color = Ink.TextMuted, style = MaterialTheme.typography.bodySmall)
        }
    }
}

/** The all-time tick: a thin mark placed at [fraction] of the track's width. */
@Composable
private fun BoxWithFraction(fraction: Double) {
    androidx.compose.foundation.layout.BoxWithConstraints(Modifier.fillMaxWidth().height(10.dp)) {
        Box(Modifier.offset(x = maxWidth * fraction.coerceIn(0.0, 1.0).toFloat()).width(2.dp).height(10.dp).background(Ink.Text))
    }
}
