package app.discair.ui.artist

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Place
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
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
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.model.PathAlbum
import app.discair.model.Span
import app.discair.model.creditPhrase
import app.discair.model.PathKind
import app.discair.model.PathLink
import app.discair.model.PathPane
import app.discair.model.PathStop
import app.discair.ui.common.PathAlbumCover
import app.discair.ui.common.ArtistPhoto
import app.discair.ui.common.Cover
import app.discair.ui.common.LocalRepository
import app.discair.ui.common.LookupDispatcher
import app.discair.ui.common.OutlinedButton
import kotlinx.coroutines.withContext
import app.discair.ui.common.Panel
import app.discair.ui.common.Target
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.Ink

/**
 * The body of an opened step, one per path; its header row (picture, name, lines) is the step's, in the trail, and the cards sit
 * on the sheet's ground so they read against the opened step's raised panel. Each shows only what the server sends for that path: a song with its credit, a leader with the records
 * that link you, an album with its label, a recording with its work, an artist with a place and an era. A fact the server did
 * not send is left out, never filled in. The server's extra reasons are not counted aloud: a pane picks among them at random.
 */
@Composable
internal fun ColumnScope.PaneBody(pane: PathPane, stop: PathStop, startName: String, go: (PathLink) -> Unit) {
    when (pane) {
        is PathPane.Song -> SongPane(pane, stop, go)
        is PathPane.Leader -> LeaderPane(pane, stop, startName, go)
        is PathPane.LabelAlbum -> LabelPane(pane, stop, go)
        is PathPane.Recording -> RecordingPane(pane, stop, startName, go)
        is PathPane.Place -> PlacePane(pane, stop, go)
    }
}

// ---------------------------------------------------------------- Follow the musician: a song

@Composable
private fun SongPane(pane: PathPane.Song, stop: PathStop, go: (PathLink) -> Unit) {
    Text(story(pane.story), style = MaterialTheme.typography.bodyLarge)
    FindRow(
        person = pane.musician?.let { it.name to it },
        album = pane.album?.let { a -> pane.artist?.let { by -> Triple(a, PathLink(true, a, by), pane.covers) } },
        go = go,
    )
}

// ---------------------------------------------------------------- Sideman: a leader and the records

@Composable
private fun LeaderPane(pane: PathPane.Leader, stop: PathStop, startName: String, go: (PathLink) -> Unit) {
    if (pane.records.isNotEmpty()) {
        SectionTitle("Records ${pane.name} led")
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            pane.records.forEach { record ->
                OutlinedButton(
                    onClick = { go(PathLink(true, record.release, pane.name)) },
                    Modifier.fillMaxWidth().heightIn(min = 64.dp),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                ) {
                    // The release is the leader's own, so its cover is looked up under the leader's name.
                    PathAlbumCover(pane.name, record.release, Modifier.size(40.dp))
                    Column(Modifier.weight(1f).padding(horizontal = 16.dp)) {
                        Text(record.release, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis)
                        record.carries?.let {
                            Text(
                                story(listOf(Span("carries "), Span(it, true), Span(", a recording $startName ${creditPhrase(record.credit, past = true)}."))),
                                style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted,
                            )
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
private fun LabelPane(pane: PathPane.LabelAlbum, stop: PathStop, go: (PathLink) -> Unit) {
    val reason = pane.reason
    if (reason == null || reason.label.isBlank()) {
        InfoCard { Text(pane.sentence, style = MaterialTheme.typography.bodyMedium) }
    } else {
        InfoCard() {
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) {
                Row(Modifier.weight(1f), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(PlayerIcons.Album, contentDescription = null, modifier = Modifier.size(32.dp))
                    Text(reason.label, style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
                }
                reason.anchor?.let { anchor ->
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(
                            if (reason.related) "Related label of:" else "Same label as:",
                            style = MaterialTheme.typography.bodySmall, color = Ink.TextMuted,
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                            if (reason.anchorArtist != null) PathAlbumCover(reason.anchorArtist, anchor, Modifier.size(40.dp)) else PathTile(PlayerIcons.Album, 40)
                            Text(anchor, style = MaterialTheme.typography.titleMedium, maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                        }
                    }
                }
            }
        }
    }
    FindRow(
        person = pane.artist?.let { it to PathLink(false, it) },
        album = pane.artist?.let { by -> Triple(pane.album, PathLink(true, pane.album, by), pane.covers) },
        go = go,
    )
}

// ---------------------------------------------------------------- Composition: a recording and the work

@Composable
private fun RecordingPane(pane: PathPane.Recording, stop: PathStop, startName: String, go: (PathLink) -> Unit) {
    val work = pane.work
    if (work == null) {
        InfoCard { Text(pane.sentence, style = MaterialTheme.typography.bodyMedium) }
    } else {
        InfoCard() {
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.Top) {
                if (pane.yoursAlbum != null && pane.yoursArtist != null) PathAlbumCover(pane.yoursArtist, pane.yoursAlbum, Modifier.size(64.dp))
                else PathTile(PlayerIcons.MusicNote, 64)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(work, style = MaterialTheme.typography.titleLarge, modifier = Modifier.semantics { heading() })
                    Text(
                        if (pane.related) "related to a work by $startName" else "composed by $startName",
                        style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted,
                    )
                    // The library recording this work was found from is always one the owner has.
                    LibraryLine(true)
                }
            }
        }
    }
    val who = pane.performer
    val on = pane.album?.let { " on $it" }.orEmpty()
    val library = if (stop.owned) "In your library" else "Not in your library"
    Text(
        story(
            if (who != null) listOf(Span(who), Span(" also recorded "), Span(pane.track, true), Span("$on. $library"))
            else listOf(Span("Also recorded as "), Span(pane.track, true), Span("$on. $library")),
        ),
        style = MaterialTheme.typography.bodyLarge,
    )
    FindRow(
        person = who?.let { it to PathLink(false, it) },
        album = pane.album?.let { a -> (pane.albumArtist ?: who)?.let { by -> Triple(a, PathLink(true, a, by), pane.covers) } },
        go = go,
    )
}

// ---------------------------------------------------------------- Scene: an artist, a place and an era

@Composable
private fun PlacePane(pane: PathPane.Place, stop: PathStop, go: (PathLink) -> Unit) {
    val open = PathLink(false, pane.name, null, pane.mbid)
    val place = pane.place
    val anchor = pane.anchor
    // The place comes out of the server's fixed wording; if it is missing the sentence is shown as the server wrote it.
    val era = pane.era ?: pane.years?.let { "Within $it years" }
    if (place == null || anchor == null || era == null) {
        InfoCard { Text(pane.sentence, style = MaterialTheme.typography.bodyMedium) }
        return
    }
    Row(Modifier.fillMaxWidth().height(IntrinsicSize.Max), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        InfoCard(Modifier.weight(1f).fillMaxHeight(), fill = true) {
            Column(Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterVertically)) {
                Eyebrow("Same place")
                Icon(Icons.Default.Place, contentDescription = null, modifier = Modifier.size(32.dp))
                Text(place, style = MaterialTheme.typography.titleLarge, textAlign = TextAlign.Center)
            }
        }
        InfoCard(Modifier.weight(1f).fillMaxHeight(), fill = true) {
            Column(Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterVertically)) {
                Eyebrow("Same era")
                Text(era, style = MaterialTheme.typography.titleLarge, textAlign = TextAlign.Center)
            }
        }
    }
    Text(
        "${pane.name} is from $place, just like $anchor. They both started their careers in the same era.",
        style = MaterialTheme.typography.bodyLarge,
    )
    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        LinkTile(pane.name, open, go) { ArtistPhoto(pane.name, null, Modifier.size(80.dp), circle = true) }
    }
}

// ---------------------------------------------------------------- shared pieces

/** A sentence made of plain pieces and italic titles. */
internal fun story(spans: List<Span>) = buildAnnotatedString {
    spans.forEach { span ->
        if (span.title) withStyle(SpanStyle(fontStyle = FontStyle.Italic, fontWeight = FontWeight.Medium)) { append(span.text) } else append(span.text)
    }
}

/** The musician as a circle on the left and the album as a square on the right, each with its name below and each opening its page. */
@Composable
internal fun FindRow(person: Pair<String, PathLink>?, album: Triple<String, PathLink, List<PathAlbum>>?, go: (PathLink) -> Unit) {
    if (person == null && album == null) return
    // Close together and centred; a lone circle (or square) sits in the middle.
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.Top) {
        if (person != null) {
            LinkTile(person.first, person.second, go) { ArtistPhoto(person.first, null, Modifier.size(96.dp), circle = true) }
        }
        if (album != null) {
            LinkTile(album.first, album.second, go) { CandidateCover(album.third, Modifier.size(96.dp)) { PathTile(PlayerIcons.Album, 96) } }
        }
    }
}

/** A picture with its name below, as one button. The name is not underlined: the picture says it opens. */
@Composable
internal fun LinkTile(label: String, link: PathLink, go: (PathLink) -> Unit, picture: @Composable () -> Unit) {
    Column(
        Modifier.width(128.dp).heightIn(min = Target).clickable(onClickLabel = "Open $label", role = Role.Button) { go(link) },
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        picture()
        Text(label, style = MaterialTheme.typography.bodyMedium, textAlign = TextAlign.Center, maxLines = 2, overflow = TextOverflow.Ellipsis)
    }
}

/**
 * A cover for one of several releases: each is asked for in turn until one has a picture, so a release the cover lookup does
 * not know does not leave the square empty. Nothing to try gives [none].
 */
@Composable
internal fun CandidateCover(candidates: List<PathAlbum>, modifier: Modifier, none: @Composable () -> Unit) {
    if (candidates.isEmpty()) return none()
    val repo = LocalRepository.current
    val url by produceState<String?>(null, candidates) {
        value = withContext(LookupDispatcher) { candidates.firstNotNullOfOrNull { repo.ownedAlbumArtwork(it.artist, it.album) ?: repo.albumImage(it.artist, it.album) } }
    }
    Cover(url, modifier)
}

@Composable
internal fun SectionTitle(text: String) {
    Text(text, style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() })
}

/** A short label above a card's content. Small capitals are kept for labels like this one. */
@Composable
internal fun Eyebrow(text: String) {
    Text(text.uppercase(), style = MaterialTheme.typography.labelMedium.copy(letterSpacing = 0.08.em), color = Ink.TextMuted)
}

/** Library state as a plain line of words. */
@Composable
internal fun LibraryLine(owned: Boolean) {
    Text(if (owned) "In your library" else "Not in your library", style = MaterialTheme.typography.bodyMedium, color = Ink.TextMuted)
}

/** A card: padded 16, the app's panel. [raised] sets it on the raised ground. */
@Composable
internal fun InfoCard(modifier: Modifier = Modifier, raised: Boolean = false, fill: Boolean = false, content: @Composable ColumnScope.() -> Unit) {
    Panel(modifier.fillMaxWidth()) {
        Column(
            Modifier.fillMaxWidth().then(if (fill) Modifier.fillMaxHeight() else Modifier).then(if (raised) Modifier.background(Ink.Raised) else Modifier).padding(16.dp),
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
