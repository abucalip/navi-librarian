package app.discair.ui.player

import android.provider.Settings
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.lyrics.LyricsTimeline
import app.discair.lyrics.LyricsUiState
import app.discair.lyrics.lyricsFailureText
import app.discair.ui.common.Target

/** The Lyrics view of the Now Playing sheet (lyrics contract 7). Lines are not tappable (owner decision). */
@Composable
fun LyricsPanel(state: LyricsUiState, currentLine: Int, songId: String, onTryAgain: () -> Unit, modifier: Modifier = Modifier) {
    Column(modifier.fillMaxWidth()) {
        when (state) {
            LyricsUiState.Idle, is LyricsUiState.Loading -> Message("Loading lyrics…", progress = true)
            is LyricsUiState.None -> Message("No lyrics for this song.")
            is LyricsUiState.Unsupported -> Message("Your Navidrome doesn't provide lyrics.")
            is LyricsUiState.Failed -> {
                Message(lyricsFailureText(state.problem))
                TextButton(onClick = onTryAgain, Modifier.heightIn(min = Target).align(Alignment.CenterHorizontally)) { Text("Try again") }
            }
            is LyricsUiState.Ready -> {
                // Both labels are words, not colour: saved copies and untimed lyrics say so.
                if (state.savedCopy) Note("Saved copy")
                if (!state.lyrics.timed) Note("These lyrics are not timed.")
                Lines(state, currentLine, songId, Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun Message(text: String, progress: Boolean = false) {
    Column(Modifier.fillMaxWidth().padding(vertical = 32.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        if (progress) { CircularProgressIndicator(Modifier.padding(bottom = 16.dp).semantics { heading() }) }
        Text(text, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun Note(text: String) =
    Text(text, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(bottom = 8.dp))

/** Timed lyrics are set larger, so about five or six lines fill the card. */
private const val TIMED_BASE_SP = 22f
/** The active line is a quarter bigger than the rest (owner decision). */
private const val ACTIVE_SCALE = 1.25f

/**
 * One line of timed lyrics. The body font stays; the active line is bold and 25% bigger, the others are
 * smaller and dimmed while a line is active. Moving to the next line animates both: the old one shrinks
 * and fades, the new one grows and brightens (instant when animations are off).
 */
@Composable
private fun TimedLine(text: String, active: Boolean, anyActive: Boolean, reduceMotion: Boolean) {
    val spec = if (reduceMotion) tween<Float>(0) else tween<Float>(300)
    val scale by animateFloatAsState(if (active) ACTIVE_SCALE else 1f, spec, label = "lineScale")
    // Before the first line starts nothing is dimmed; once a line is active the rest recede.
    val alpha by animateFloatAsState(if (!anyActive || active) 1f else 0.45f, spec, label = "lineAlpha")
    val size = (TIMED_BASE_SP * scale).sp
    Text(
        text,
        style = MaterialTheme.typography.bodyLarge.copy(fontSize = size, lineHeight = (TIMED_BASE_SP * scale * 1.3f).sp),
        fontWeight = if (active) FontWeight.Bold else FontWeight.Normal,
        color = (if (active) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant).copy(alpha = alpha),
        modifier = Modifier.fillMaxWidth().then(if (active) Modifier.semantics { stateDescription = "Current line" } else Modifier),
    )
}

@Composable
private fun Lines(state: LyricsUiState.Ready, currentLine: Int, songId: String, modifier: Modifier = Modifier) {
    val list = rememberLazyListState()
    // Following resumes when the song changes (contract 6).
    var following by remember(songId) { mutableStateOf(true) }
    var scrolling by remember(songId) { mutableStateOf(false) }
    val context = LocalContext.current
    val reduceMotion = remember { Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f }
    val timed = state.lyrics.timed

    // A hand scroll (the program's own scroll is flagged) stops following.
    LaunchedEffect(songId) {
        snapshotFlow { list.isScrollInProgress }.collect { moving -> if (moving && !scrolling) following = false }
    }
    LaunchedEffect(currentLine, following, songId) {
        if (!timed || !following || currentLine < 0) return@LaunchedEffect
        scrolling = true
        try {
            val offset = -(list.layoutInfo.viewportSize.height / 3)
            if (reduceMotion) list.scrollToItem(currentLine, offset) else list.animateScrollToItem(currentLine, offset)
        } finally { scrolling = false }
    }

    // The list fills the flip card it sits in and scrolls inside it.
    Box(modifier.fillMaxWidth()) {
        LazyColumn(Modifier.fillMaxSize(), state = list, verticalArrangement = Arrangement.spacedBy(10.dp)) {
            itemsIndexed(state.lyrics.lines) { index, line ->
                val current = timed && index == currentLine
                if (line.text.isBlank()) {
                    Spacer(Modifier.height(14.dp).fillMaxWidth().clearAndSetSemantics { })
                } else {
                    if (timed) TimedLine(line.text, current, anyActive = currentLine >= 0, reduceMotion = reduceMotion)
                    else Text(line.text, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.fillMaxWidth())
                }
            }
        }
        if (timed && !following && currentLine != LyricsTimeline.NONE) {
            FilledTonalButton(
                onClick = { following = true },
                Modifier.align(Alignment.BottomCenter).padding(bottom = 8.dp).heightIn(min = Target),
            ) { Text("Back to the current line") }
        }
    }
}
