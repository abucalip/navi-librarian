package app.discair.ui.player

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import app.discair.player.PlayActions
import app.discair.ui.common.Target

val LocalPlayActions = compositionLocalOf<PlayActions> { error("No play actions") }

/** Play, Shuffle and (optionally) a menu with Play next and Add to queue. Shown only for owned albums and artists. */
@Composable
fun PlayRow(
    onPlay: () -> Unit,
    onShuffle: () -> Unit,
    modifier: Modifier = Modifier,
    onPlayNext: (() -> Unit)? = null,
    onAddToQueue: (() -> Unit)? = null,
) {
    Row(modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.CenterVertically) {
        Button(onClick = onPlay, Modifier.heightIn(min = Target)) {
            Icon(PlayerIcons.Play, contentDescription = null, Modifier.size(20.dp)); Text(" Play")
        }
        OutlinedButton(onClick = onShuffle, Modifier.heightIn(min = Target)) {
            Icon(PlayerIcons.Shuffle, contentDescription = null, Modifier.size(20.dp)); Text(" Shuffle")
        }
        if (onPlayNext != null && onAddToQueue != null) {
            var menu by remember { mutableStateOf(false) }
            Box {
                IconButton(onClick = { menu = true }, Modifier.size(Target)) { Icon(Icons.Default.MoreVert, contentDescription = "More ways to play") }
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    DropdownMenuItem(text = { Text("Play next") }, onClick = { menu = false; onPlayNext() })
                    DropdownMenuItem(text = { Text("Add to queue") }, onClick = { menu = false; onAddToQueue() })
                }
            }
        }
    }
}

/** A 48dp play button for a list row. [label] names what will play, for TalkBack. */
@Composable
fun RowPlayButton(label: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    IconButton(onClick = onClick, modifier.size(Target)) { Icon(PlayerIcons.Play, contentDescription = "Play $label") }
}

/** A 48dp "more" button for a list row with a short menu of ways to play (Shuffle, Play next, Add to queue). */
@Composable
fun RowMoreMenu(label: String, actions: List<Pair<String, () -> Unit>>, modifier: Modifier = Modifier) {
    var menu by remember { mutableStateOf(false) }
    Box(modifier) {
        IconButton(onClick = { menu = true }, Modifier.size(Target)) { Icon(Icons.Default.MoreVert, contentDescription = "More ways to play $label") }
        DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
            actions.forEach { (text, run) -> DropdownMenuItem(text = { Text(text) }, onClick = { menu = false; run() }) }
        }
    }
}
