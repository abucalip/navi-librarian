package app.discair.ui.player

import android.provider.Settings
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
import app.discair.lyrics.LyricsTimeline
import app.discair.lyrics.LyricsUiState
import app.discair.lyrics.lyricsFailureText
import app.discair.ui.common.Target

/** The Lyrics view of the Now Playing sheet (lyrics contract 7). Lines are not tappable (owner decision). */
@Composable
fun LyricsPanel(state: LyricsUiState, currentLine: Int, songId: String, onTryAgain: () -> Unit) {
    Column(Modifier.fillMaxWidth().heightIn(min = 240.dp)) {
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
                Lines(state, currentLine, songId)
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

@Composable
private fun Lines(state: LyricsUiState.Ready, currentLine: Int, songId: String) {
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

    // Half the screen height: fits portrait, landscape and large text, and the list scrolls inside it.
    val maxHeight = (LocalConfiguration.current.screenHeightDp * 0.5f).dp.coerceAtLeast(160.dp)
    Box(Modifier.fillMaxWidth().heightIn(max = maxHeight)) {
        LazyColumn(Modifier.fillMaxWidth().heightIn(max = maxHeight), state = list, verticalArrangement = Arrangement.spacedBy(10.dp)) {
            itemsIndexed(state.lyrics.lines) { index, line ->
                val current = timed && index == currentLine
                if (line.text.isBlank()) {
                    Spacer(Modifier.height(14.dp).fillMaxWidth().clearAndSetSemantics { })
                } else {
                    Text(
                        line.text,
                        style = if (current) MaterialTheme.typography.titleLarge else MaterialTheme.typography.bodyLarge,
                        fontWeight = if (current) FontWeight.Bold else FontWeight.Normal,
                        color = if (current) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.fillMaxWidth().then(if (current) Modifier.semantics { stateDescription = "Current line" } else Modifier),
                    )
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
