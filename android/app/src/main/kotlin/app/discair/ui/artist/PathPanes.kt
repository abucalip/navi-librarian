package app.discair.ui.artist

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Place
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.model.PathCredit
import app.discair.model.PathKind
import app.discair.model.PathLink
import app.discair.model.PathPane
import app.discair.model.PathStop
import app.discair.ui.common.AlbumCover
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.BrutalTag
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.Panel
import app.discair.ui.common.Target
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.Ink

/**
 * One pane per path. Each shows only what the server sends for that path: a song with its credits, a leader with the records that
 * link you, an album with its label, a recording beside the work it shares, an artist with a place. A fact the server did not send
 * is left out, never filled in.
 */
@Composable
internal fun ColumnScope.PaneBody(
    pane: PathPane, stop: PathStop, kind: PathKind, startName: String, startType: String, go: (PathLink) -> Unit,
) {
    when (pane) {
        is PathPane.Song -> SongPane(pane, stop, go)
        is PathPane.Leader -> LeaderPane(pane, stop, startName, startType, go)
        is PathPane.LabelAlbum -> LabelPane(pane, stop)
        is PathPane.Recording -> RecordingPane(pane, stop)
        is PathPane.Place -> PlacePane(pane, stop)
    }
    pane.secondary.forEach { link ->
        OutlinedButton(onClick = { go(link) }, Modifier.fillMaxWidth().heightIn(min = Target)) {
            Icon(if (link.album) PlayerIcons.Album else PlayerIcons.Person, contentDescription = null, modifier = Modifier.size(24.dp))
            Spacer(Modifier.width(8.dp))
            Text("${if (link.album) "Album" else "Artist"}: ${link.name}", maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f, fill = false))
        }
    }
    if (pane.moreReasons > 0) {
        Text(
            if (pane.moreReasons == 1) "1 more reason on the server." else "${pane.moreReasons} more reasons on the server.",
            style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted,
        )
    }
}

// ---------------------------------------------------------------- Follow the musician: a song

@Composable
private fun SongPane(pane: PathPane.Song, stop: PathStop, go: (PathLink) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.Top) {
        PathThumb(PathKind.FollowTheMusician, stop, 96)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(pane.title, style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
            Column {
                pane.album?.let { Text("on $it", style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted) }
                pane.artist?.let { Text("by $it", style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted) }
            }
            LibraryTag(stop.owned)
        }
    }
    SectionTitle("Why it's here")
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        pane.credits.forEach { CreditCard(it, go) }
    }
}

/** One reason as a card. When it names a musician the whole card opens their page, and the name is underlined to say so. */
@Composable
private fun CreditCard(credit: PathCredit, go: (PathLink) -> Unit) {
    val who = credit.who
    val text = buildAnnotatedString {
        if (who != null && credit.text.startsWith(who.name)) {
            withStyle(SpanStyle(textDecoration = TextDecoration.Underline, fontWeight = FontWeight.Bold)) { append(who.name) }
            append(credit.text.removePrefix(who.name))
        } else append(credit.text)
    }
    InfoCard(onClick = who?.let { { go(it) } }, onClickLabel = who?.let { "Open ${it.name}" }) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.Top) {
            Icon(PlayerIcons.Person, contentDescription = null, modifier = Modifier.size(24.dp))
            Text(text, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
        }
    }
}

// ---------------------------------------------------------------- Sideman: a leader and the records

@Composable
private fun LeaderPane(pane: PathPane.Leader, stop: PathStop, startName: String, startType: String, go: (PathLink) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) {
        PathThumb(PathKind.SidemanToLeader, stop, 72)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(pane.name, style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
            Text(pane.typeLabel, style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted)
            LibraryTag(stop.owned)
        }
    }
    val verb = if (startType == "group") "appeared on" else "played on"
    if (pane.records.isNotEmpty()) {
        SectionTitle("Records ${pane.name} led that $startName $verb")
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            pane.records.forEach { record ->
                OutlinedButton(
                    onClick = { go(PathLink(true, record.release, pane.name)) },
                    Modifier.fillMaxWidth().heightIn(min = 64.dp),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                ) {
                    // The release is the leader's own, so its cover is looked up under the leader's name.
                    AlbumCover(pane.name, record.release, null, Modifier.size(40.dp))
                    Column(Modifier.weight(1f).padding(horizontal = 16.dp)) {
                        Text(record.release, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis)
                        record.carries?.let {
                            Text("carries $it, a recording $startName $verb", style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted)
                        }
                    }
                    Icon(PlayerIcons.Right, contentDescription = null, modifier = Modifier.size(24.dp))
                }
            }
        }
    } else {
        // The server named no record for these reasons: say them as it did.
        pane.otherReasons.forEach { InfoCard { Text(it, style = MaterialTheme.typography.bodyMedium) } }
    }
}

// ---------------------------------------------------------------- Label: an album and its label

@Composable
private fun LabelPane(pane: PathPane.LabelAlbum, stop: PathStop) {
    Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.Bottom) {
        PathThumb(PathKind.LabelPath, stop, 144)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(pane.album, style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
            pane.artist?.let { Text(it, style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted) }
            LibraryTag(stop.owned)
        }
    }
    pane.reasons.forEach { reason ->
        if (reason.label.isBlank()) {
            InfoCard { Text(reason.text, style = MaterialTheme.typography.bodyMedium) }
            return@forEach
        }
        InfoCard(raised = true) {
            Eyebrow(if (reason.related) "Released on a related label" else "Released on")
            Row(Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(PlayerIcons.Album, contentDescription = null, modifier = Modifier.size(32.dp))
                Text(reason.label, style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
            }
        }
        reason.anchor?.let { anchor ->
            InfoCard {
                Eyebrow("Same label as your album")
                Row(Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) {
                    if (reason.anchorArtist != null) AlbumCover(reason.anchorArtist, anchor, null, Modifier.size(48.dp)) else PathTile(PlayerIcons.Album, 48)
                    Column(Modifier.weight(1f)) {
                        Text(anchor, style = MaterialTheme.typography.titleMedium)
                        Text("in your library", style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted)
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------- Composition: a recording and the work

@Composable
private fun RecordingPane(pane: PathPane.Recording, stop: PathStop) {
    val work = pane.work
    if (work == null) {
        InfoCard { Text(pane.sentence, style = MaterialTheme.typography.bodyMedium) }
    } else {
        InfoCard(raised = true) {
            Eyebrow("The work")
            Row(Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(PlayerIcons.MusicNote, contentDescription = null, modifier = Modifier.size(32.dp))
                Text(work, style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f).semantics { heading() })
            }
            Box(Modifier.padding(top = 8.dp)) { BrutalTag(primary = false) { Text(if (pane.related) "Related work" else "Same work", style = MaterialTheme.typography.labelMedium) } }
        }
    }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        pane.yours?.let { yours ->
            InfoCard {
                Eyebrow("Your recording")
                Row(Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) {
                    if (pane.yoursAlbum != null && pane.yoursArtist != null) AlbumCover(pane.yoursArtist, pane.yoursAlbum, null, Modifier.size(48.dp))
                    else PathTile(PlayerIcons.MusicNote, 48)
                    Column(Modifier.weight(1f)) {
                        Text(yours, style = MaterialTheme.typography.titleMedium)
                        Text("in your library", style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted)
                    }
                    Icon(Icons.Default.Check, contentDescription = "In your library", tint = Ink.Ok, modifier = Modifier.size(24.dp))
                }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                Icon(PlayerIcons.Swap, contentDescription = null, modifier = Modifier.size(24.dp))
                Text(
                    if (pane.related) "is a work related to" else "is the same work as",
                    style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted, modifier = Modifier.padding(start = 8.dp),
                )
            }
        }
        InfoCard {
            Eyebrow("This recording")
            Row(Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) {
                PathThumb(PathKind.CompositionPath, stop, 48)
                Column(Modifier.weight(1f)) {
                    Text(pane.track, style = MaterialTheme.typography.titleMedium)
                    Text(pane.performer ?: "Artist not listed", style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted)
                }
            }
            Box(Modifier.padding(top = 8.dp)) { LibraryTag(stop.owned) }
        }
    }
}

// ---------------------------------------------------------------- Scene: an artist, a place and an era

@Composable
private fun PlacePane(pane: PathPane.Place, stop: PathStop) {
    Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) {
        PathThumb(PathKind.ScenePath, stop, 72)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(pane.name, style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
            Text(pane.typeLabel, style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted)
            LibraryTag(stop.owned)
        }
    }
    val place = pane.place
    val anchor = pane.anchor
    // The place and the era come out of the server's fixed wording; if either is missing the sentence is shown as the server wrote it.
    if (place == null || anchor == null || pane.years == null) {
        InfoCard { Text(pane.sentence, style = MaterialTheme.typography.bodyMedium) }
        return
    }
    InfoCard(raised = true) {
        Eyebrow("Same place")
        Row(Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.Place, contentDescription = null, modifier = Modifier.size(32.dp))
            Text(place, style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
        }
        Text("$anchor is also from $place.", style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(top = 8.dp))
    }
    InfoCard {
        Eyebrow("Same era")
        Text("Started within ${pane.years} years of $anchor.", style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(top = 8.dp))
    }
}

// ---------------------------------------------------------------- shared pieces

@Composable
private fun SectionTitle(text: String) {
    Text(text, style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() })
}

/** A short label above a card's content. Small capitals are kept for labels like this one. */
@Composable
private fun Eyebrow(text: String) {
    Text(text.uppercase(), style = MaterialTheme.typography.labelMedium.copy(letterSpacing = 0.6.sp), color = Ink.TextMuted)
}

/** Library state in words and an icon, never colour alone. */
@Composable
private fun LibraryTag(owned: Boolean) {
    BrutalTag(primary = false) {
        Row(horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically) {
            if (owned) Icon(Icons.Default.Check, contentDescription = null, tint = Ink.Ok, modifier = Modifier.size(16.dp))
            Text(if (owned) "In your library" else "Not in your library", style = MaterialTheme.typography.labelMedium)
        }
    }
}

/** A card: padded 16, the app's panel. [raised] sets it on the raised ground; [onClick] makes the whole card one button. */
@Composable
private fun InfoCard(
    raised: Boolean = false, onClick: (() -> Unit)? = null, onClickLabel: String? = null, content: @Composable ColumnScope.() -> Unit,
) {
    Panel(Modifier.fillMaxWidth()) {
        Column(
            Modifier.fillMaxWidth()
                .then(if (raised) Modifier.background(Ink.Raised) else Modifier)
                .then(if (onClick != null) Modifier.heightIn(min = Target).clickable(onClickLabel = onClickLabel, role = Role.Button, onClick = onClick) else Modifier)
                .padding(16.dp),
            content = content,
        )
    }
}

/** A plain square with an icon, for a step that has no picture to look up. */
@Composable
internal fun PathTile(icon: ImageVector, size: Int) {
    Box(
        Modifier.size(size.dp).clip(RoundedCornerShape(4.dp)).background(Ink.Raised),
        contentAlignment = Alignment.Center,
    ) { Icon(icon, contentDescription = null, modifier = Modifier.size((size / 2).dp)) }
}
