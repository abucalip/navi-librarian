package app.discair.ui.discover

import android.widget.Toast
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import app.discair.model.DiscoveryEntry
import app.discair.model.Lean
import app.discair.model.blockableGenres
import app.discair.ui.common.LocalRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Star Operation S2c: the extra entries of an album's three-dot menu, after "Not this artist". More like this and Less like
 * this lean on the artist (neither hides anything); Block genre offers only the genres the album itself carries, because the
 * server matches on those. A block hides picks only, never the library. The answer comes as a short toast; the blocklist
 * (Settings) lifts any of these. One helper for all three Discover themes, so the menus cannot drift apart.
 */
@Composable
fun PickFeedbackItems(entry: DiscoveryEntry, close: () -> Unit) {
    val repo = LocalRepository.current
    val context = LocalContext.current
    val artist = entry.item.artistName
    val genres = blockableGenres(entry.item.genres)

    fun run(done: String, call: () -> Unit) {
        close()
        // Not the menu's own scope: closing the menu leaves composition and would cancel the request with it.
        CoroutineScope(Dispatchers.IO).launch {
            val message = try {
                call()
                done
            } catch (e: Exception) {
                "Could not save that: " + (e.message ?: "the server did not answer.")
            }
            withContext(Dispatchers.Main) { Toast.makeText(context, message, Toast.LENGTH_SHORT).show() }
        }
    }

    DropdownMenuItem(
        text = { Text("More like this artist") },
        onClick = { run("More like $artist next time.") { repo.setArtistLean(artist, Lean.More, genres, null) } },
    )
    DropdownMenuItem(
        text = { Text("Less like this artist") },
        onClick = { run("Fewer picks like $artist. Nothing is hidden.") { repo.setArtistLean(artist, Lean.Less, genres, null) } },
    )
    for (genre in genres) DropdownMenuItem(
        text = { Text("Block genre: $genre") },
        onClick = { run("Blocked $genre. Your library is not affected.") { repo.blockGenre(genre) } },
    )
}
