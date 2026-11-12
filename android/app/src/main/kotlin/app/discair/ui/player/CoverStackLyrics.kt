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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.lyrics.LyricsTimeline
import app.discair.lyrics.LyricsUiState
import app.discair.lyrics.lyricsFailureText
import app.discair.ui.common.FilledTonalButton
import app.discair.ui.common.Target
import app.discair.ui.theme.LocalPalette

/**
 * Soft Brut's lyrics (mockup: soft-brut/player, frame 3): Space Grotesk 700, 20/28, muted; the line being sung is ink on a lavender
 * highlight, which is also announced as "Current line". Messages, notes, "Try again" and "Back to the current line" are the Standard ones.
 * Over the photos (the Photos switch) the lines are white, as on every theme's photo backdrop.
 */
@Composable
fun CoverStackLyricsPanel(state: LyricsUiState, currentLine: Int, songId: String, onTryAgain: () -> Unit, modifier: Modifier = Modifier, overPhotos: Boolean = false) {
    val p = LocalPalette.current
    val quiet = if (overPhotos) androidx.compose.ui.graphics.Color.White else p.textMuted
    Column(modifier.fillMaxWidth()) {
        when (state) {
            LyricsUiState.Idle, is LyricsUiState.Loading -> Message("Loading lyrics…", quiet, progress = true)
            is LyricsUiState.None -> Message("No lyrics for this song.", quiet)
            is LyricsUiState.Unsupported -> Message("Your Navidrome doesn't provide lyrics.", quiet)
            is LyricsUiState.Failed -> {
                Message(lyricsFailureText(state.problem), quiet)
                TextButton(onClick = onTryAgain, Modifier.heightIn(min = Target).align(Alignment.CenterHorizontally)) { Text("Try again", color = quiet, textDecoration = TextDecoration.Underline) }
            }
            is LyricsUiState.Ready -> {
                if (state.savedCopy) Note("Saved copy", quiet)
                if (!state.lyrics.timed) Note("These lyrics are not timed.", quiet)
                Lines(state, currentLine, songId, quiet, Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun Message(text: String, color: androidx.compose.ui.graphics.Color, progress: Boolean = false) {
    Column(Modifier.fillMaxWidth().padding(vertical = 32.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        if (progress) CircularProgressIndicator(Modifier.padding(bottom = 16.dp).semantics { heading() }, color = LocalPalette.current.text)
        Text(text, style = MaterialTheme.typography.bodyLarge, color = color)
    }
}

@Composable
private fun Note(text: String, color: androidx.compose.ui.graphics.Color) = Text(text, style = MaterialTheme.typography.bodySmall, color = color, modifier = Modifier.padding(bottom = 8.dp))

@Composable
private fun Lines(state: LyricsUiState.Ready, currentLine: Int, songId: String, quiet: androidx.compose.ui.graphics.Color, modifier: Modifier = Modifier) {
    val p = LocalPalette.current
    val list = rememberLazyListState()
    // Following resumes when the song changes (lyrics contract 6); a hand scroll stops it.
    var following by remember(songId) { mutableStateOf(true) }
    var scrolling by remember(songId) { mutableStateOf(false) }
    val context = LocalContext.current
    val reduceMotion = remember { Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f }
    val timed = state.lyrics.timed
    LaunchedEffect(songId) { snapshotFlow { list.isScrollInProgress }.collect { moving -> if (moving && !scrolling) following = false } }
    LaunchedEffect(currentLine, following, songId) {
        if (!timed || !following || currentLine < 0) return@LaunchedEffect
        scrolling = true
        try {
            val offset = -(list.layoutInfo.viewportSize.height / 3)
            if (reduceMotion) list.scrollToItem(currentLine, offset) else list.animateScrollToItem(currentLine, offset)
        } finally { scrolling = false }
    }
    val style = MaterialTheme.typography.titleLarge.copy(fontSize = 20.sp, lineHeight = 28.sp, fontWeight = FontWeight.Bold)
    Box(modifier.fillMaxWidth()) {
        LazyColumn(Modifier.fillMaxSize(), state = list, verticalArrangement = Arrangement.spacedBy(14.dp)) {
            itemsIndexed(state.lyrics.lines) { index, line ->
                if (line.text.isBlank()) Spacer(Modifier.height(14.dp).fillMaxWidth().clearAndSetSemantics { })
                else if (timed && index == currentLine) Text(
                    buildAnnotatedString { withStyle(SpanStyle(background = p.accent, color = p.onAccent)) { append(" ${line.text} ") } },
                    style = style, modifier = Modifier.fillMaxWidth().semantics { stateDescription = "Current line" },
                ) else Text(line.text, style = style, color = quiet, modifier = Modifier.fillMaxWidth())
            }
        }
        if (timed && !following && currentLine != LyricsTimeline.NONE) {
            FilledTonalButton(onClick = { following = true }, Modifier.align(Alignment.BottomCenter).padding(bottom = 8.dp).heightIn(min = Target)) { Text("Back to the current line") }
        }
    }
}
