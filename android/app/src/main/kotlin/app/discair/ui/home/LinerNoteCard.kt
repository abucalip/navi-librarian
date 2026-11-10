package app.discair.ui.home

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.data.LibraryRepository
import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndexResult
import app.discair.model.ArtworkSize
import app.discair.model.LinerNoteChoice
import app.discair.model.Pick
import app.discair.model.linerNoteDay
import app.discair.model.linerNoteOrder
import app.discair.model.linerNotePicture
import app.discair.ui.common.LocalImageLoader
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.Target
import coil3.compose.AsyncImage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.time.LocalDate

/** The note as drawn: the picture and the album it is from. */
private data class LinerNote(val picture: ArtworkImage, val choice: LinerNoteChoice)

private const val PREFS = "discair_liner_note"

/**
 * Home's liner note of the day (docs/artwork.md, idea 12): one picture from an album in the Home picks, cropped to a square by a fixed
 * centre rule, with "Which album?" revealing the album on tap. Read-only. Nothing shows while loading, when no pick has a picture for
 * the day, or when the lookup fails.
 */
@Composable
fun LinerNoteCard(picks: List<Pick>) {
    val repo = LocalRepository.current
    val context = LocalContext.current
    val groups = remember(picks) {
        picks.mapNotNull { p -> p.releaseGroupMbid?.trim()?.lowercase()?.takeIf { it.isNotEmpty() }?.let { it to p } }.toMap()
    }
    val day = linerNoteDay(LocalDate.now())
    val note by produceState<LinerNote?>(null, day, groups.keys.sorted().joinToString(",")) {
        value = withContext(Dispatchers.IO) {
            try {
                findLinerNote(repo, context, day, groups)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                null
            }
        }
    }
    // Every remembered value is read before the early return, so the call order never changes between compositions.
    var revealed by rememberSaveable(day) { mutableStateOf(false) }
    val current = note
    val url = remember(current?.picture?.imageId) { current?.let { repo.artworkImageUrl(it.picture, ArtworkSize.Display) } }
    if (current == null) return
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp)
            .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f), RoundedCornerShape(14.dp))
            .padding(14.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier.size(120.dp).clip(RoundedCornerShape(8.dp)).background(MaterialTheme.colorScheme.surfaceVariant)
                .semantics { contentDescription = current.picture.label() },
        ) {
            if (url != null) {
                AsyncImage(
                    model = url, contentDescription = null, imageLoader = LocalImageLoader.current,
                    contentScale = ContentScale.Crop, modifier = Modifier.size(120.dp),
                )
            }
        }
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(
                "LINER NOTE OF THE DAY",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (revealed) {
                Text(current.choice.title, style = MaterialTheme.typography.titleMedium, maxLines = 2)
                Text(
                    current.choice.artist, style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1,
                )
            }
            OutlinedButton(onClick = { revealed = !revealed }, modifier = Modifier.heightIn(min = Target)) {
                Text(if (revealed) "Hide album" else "Which album?")
            }
        }
    }
}

/**
 * Today's note. A saved choice for today is tried first and kept; otherwise the picks are tried in the day's order, at most three,
 * and the first with a picture is saved. An index that is still building shows nothing now and is asked again on the next open.
 */
private fun findLinerNote(repo: LibraryRepository, context: Context, day: String, groups: Map<String, Pick>): LinerNote? {
    val prefs = try { context.getSharedPreferences(PREFS, Context.MODE_PRIVATE) } catch (e: Exception) { null }
    val saved = readChoice(prefs)?.takeIf { it.day == day }
    if (saved != null) {
        val result = repo.artworkIndex(saved.rgid, null)
        if (result !is ArtworkIndexResult.Ready) return null
        linerNotePicture(result.index, day)?.let { return LinerNote(it, saved) }
    }
    for (rgid in linerNoteOrder(groups.keys.toList(), day).take(3)) {
        val pick = groups[rgid] ?: continue
        val result = repo.artworkIndex(rgid, null) as? ArtworkIndexResult.Ready ?: continue
        val picture = linerNotePicture(result.index, day) ?: continue
        val choice = LinerNoteChoice(day, rgid, pick.album, pick.artist)
        writeChoice(prefs, choice)
        return LinerNote(picture, choice)
    }
    return null
}

/** Reads the saved choice; a missing or damaged value is "none", never a crash. */
private fun readChoice(prefs: android.content.SharedPreferences?): LinerNoteChoice? = try {
    prefs?.let {
        val day = it.getString("day", null)
        val rgid = it.getString("rgid", null)
        val title = it.getString("title", null)
        val artist = it.getString("artist", null)
        if (day != null && rgid != null && title != null && artist != null) LinerNoteChoice(day, rgid, title, artist) else null
    }
} catch (e: Exception) {
    null
}

private fun writeChoice(prefs: android.content.SharedPreferences?, choice: LinerNoteChoice) {
    try {
        prefs?.edit()?.putString("day", choice.day)?.putString("rgid", choice.rgid)
            ?.putString("title", choice.title)?.putString("artist", choice.artist)?.apply()
    } catch (e: Exception) {
        // Storage refused: the note still shows today; it may change on the next open.
    }
}
