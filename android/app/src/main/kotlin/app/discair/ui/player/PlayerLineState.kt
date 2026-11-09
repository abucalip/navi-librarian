package app.discair.ui.player

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import app.discair.lyrics.LyricsUiState
import app.discair.model.PeaksResult
import app.discair.model.PlayerFact
import app.discair.model.loadPeaks
import app.discair.model.mixFacts
import app.discair.player.LibraryFacts
import app.discair.player.PlayerLine
import app.discair.player.PlayerLineRules
import app.discair.player.QueueItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import java.util.Calendar

/** What the player's reads of the server look like to a screen: two lambdas, so screens stay free of the repository. */
class PlayerExtras(
    val peaks: suspend (songId: String) -> PeaksResult,
    val facts: suspend (songId: String) -> List<PlayerFact>,
)

/** The bars for the song that is playing: null until the server has them, and for good when it has none. */
@Composable
fun rememberPeaks(extras: PlayerExtras?, songId: String?, enabled: Boolean): FloatArray? {
    val bars by produceState<FloatArray?>(null, extras, songId, enabled) {
        value = null
        if (extras == null || songId == null || !enabled) return@produceState
        value = loadPeaks { withContext(Dispatchers.IO) { extras.peaks(songId) } }
    }
    return bars
}

/**
 * The one line under the title: the synced lyric, or a rotating fact. The facts are the phone's own lines at once, then the
 * server's added; they rotate every 14 s while the song plays and only while a fact is what is showing.
 */
@Composable
fun rememberPlayerLine(
    extras: PlayerExtras?, item: QueueItem?, lyrics: LyricsUiState, currentLine: Int, playing: Boolean,
    showLyrics: Boolean, showFacts: Boolean,
): PlayerLine {
    val songId = item?.songId
    val facts by produceState(emptyList<PlayerFact>(), songId) {
        value = emptyList()
        if (item == null || !showFacts) return@produceState
        val own = LibraryFacts.make(item, Calendar.getInstance().get(Calendar.YEAR))
        value = mixFacts(emptyList(), own)
        if (extras != null) {
            val server = try { withContext(Dispatchers.IO) { extras.facts(item.songId) } } catch (e: kotlinx.coroutines.CancellationException) { throw e } catch (e: Exception) { emptyList() }
            value = mixFacts(server, own)
        }
    }
    var index by remember(songId) { mutableStateOf(0) }
    LaunchedEffect(songId, facts.size, playing) {
        while (playing && facts.size > 1) {
            delay(PlayerLineSeconds * 1000)
            index = (index + 1) % facts.size
        }
    }
    val ready = lyrics as? LyricsUiState.Ready
    val lyric = ready?.lyrics?.lines?.getOrNull(currentLine)?.text
    return PlayerLineRules.choose(showLyrics, showFacts, ready?.lyrics?.timed == true, lyric, facts.takeIf { it.isNotEmpty() }?.get(index % facts.size))
}

private const val PlayerLineSeconds = app.discair.player.PlayerLineRules.FACT_SECONDS
