package app.discair.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Spacer
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.model.AcquisitionJob
import app.discair.model.Tone
import app.discair.ui.Opener
import app.discair.ui.common.LocalAcquisitions
import app.discair.ui.common.PageHeading
import app.discair.ui.common.SheetStackRules
import app.discair.ui.common.routeKey
import app.discair.ui.theme.LocalFontPair
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.brutalShadow
import app.discair.ui.theme.themeShape

/**
 * Sheet Stack only: "Requests", the newest acquisition requests as rows with a status badge. The badge is always a word (Fetching,
 * Queued, Done, or the app's own label for anything else); the fill only adds emphasis. The list is the one the Downloads page
 * shows (the same hub), so the two never disagree. Tapping a row opens the album.
 */
@Composable
fun SheetRequestsSection(open: Opener) {
    val hub = LocalAcquisitions.current
    val jobs = hub.jobs
    val p = LocalPalette.current
    val rule = (p.shape?.outline ?: 2).dp
    val shape = themeShape(14.dp)
    PageHeading("Requests", Modifier.padding(start = 16.dp, end = 16.dp, top = 24.dp, bottom = 8.dp))
    val shown = jobs?.filter { it.status.lowercase() != "dismissed" }?.take(SheetStackRules.HOME_REQUESTS).orEmpty()
    when {
        jobs == null -> Muted("Connecting to acquisition status…")
        shown.isEmpty() -> Muted("No requests yet. Albums you get appear here.")
        else -> Column(
            Modifier.padding(start = 16.dp, end = 24.dp, bottom = 4.dp).fillMaxWidth().brutalShadow(shape).clip(shape)
                .background(p.surface).border(rule, p.edgeStrong, shape),
        ) {
            shown.forEachIndexed { index, job ->
                RequestRow(job, open)
                if (index < shown.lastIndex) Box(Modifier.fillMaxWidth().height(rule).background(p.edgeStrong))
            }
        }
    }
}

@Composable
private fun RequestRow(job: AcquisitionJob, open: Opener) {
    val p = LocalPalette.current
    val word = SheetStackRules.requestWord(job.status, job.info.label)
    Row(
        Modifier.fillMaxWidth().heightIn(min = 64.dp)
            .clickable(role = Role.Button) { open.album(routeKey(job.artist, job.albumName), job.artist, job.albumName, null, job.year) }
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f).padding(end = 16.dp)) {
            Text(job.title, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(
                job.artistName, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1, overflow = TextOverflow.Ellipsis,
            )
        }
        // The status badge: a bordered word. Active is the accent, Queued the soft accent, Done the second tone; failures stay outlined.
        val (fill, ink) = when {
            word == "Fetching" -> p.accent to p.onAccent
            word == "Queued" -> p.accentDim to p.text
            word == "Done" -> p.accent2 to p.onAccent
            job.info.tone == Tone.Error -> p.surface to p.chartRedText
            else -> p.surface to p.text
        }
        Text(
            word, style = MaterialTheme.typography.labelMedium.copy(fontFamily = LocalFontPair.current.mono, fontWeight = androidx.compose.ui.text.font.FontWeight.Bold),
            color = ink, maxLines = 1,
            modifier = Modifier.clip(themeShape(6.dp)).background(fill).border((p.shape?.outline ?: 2).dp, p.edgeStrong, themeShape(6.dp))
                .padding(horizontal = 8.dp, vertical = 4.dp),
        )
    }
}
