package app.discair.ui.common

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.ui.theme.LocalPalette

/*
 * Index's sheets (I6). Spec: docs/INDEX_THEME.md section 7 (Sheet) and 8.2 #9; mockup: docs/design/index/pages/sheets.html, frames 1 to 3.
 * The pick, song and row menus are one lettered sheet: an optional header (cover, mono eyebrow, the Lead title at 30, the heavy rule), then 62dp options
 * lettered A, B, C in mono `accent`, each with an optional line under it and a trailing glyph. The sheet keeps Material's timing (decision I4); the options
 * cascade in once it is up (motion #5). Choosing an option closes the sheet and runs it; a swipe, the scrim and Back close it and run nothing.
 */

/** The pure words and glyph choices of Index's sheets. */
object IndexSheetRules {
    const val OPTION_MIN = 62f
    const val HEADER_ART = 72f

    /** "A", "B" … "Z", then "AA" for a 27th option (no menu is that long; the rule never fails). */
    fun letter(index: Int): String {
        require(index >= 0)
        var n = index
        val out = StringBuilder()
        do { out.insert(0, 'A' + n % 26); n = n / 26 - 1 } while (n >= 0)
        return out.toString()
    }

    /** The glyph at the end of an option, from its words, so callers keep passing plain label and action pairs. Null draws none. */
    fun glyphFor(label: String): ImageVector? {
        val l = label.lowercase()
        return when {
            l.startsWith("play next") -> IndexIcons.QueueAdd
            l.startsWith("add to queue") -> IndexIcons.Queue
            l == "play" -> IndexIcons.Play
            l == "shuffle" -> IndexIcons.Shuffle
            l.startsWith("go to album") || l.startsWith("open album") -> IndexIcons.Album
            l.startsWith("go to artist") || l.startsWith("open artist") -> IndexIcons.Place
            l.startsWith("paths") -> IndexIcons.Paths
            l.startsWith("why") -> IndexIcons.Chevron
            l.startsWith("not this") -> IndexIcons.Close
            l.startsWith("never suggest") || l.startsWith("block genre") -> IndexIcons.Ban
            l.startsWith("download") -> IndexIcons.Download
            l.startsWith("remove") || l == "dismiss" -> IndexIcons.Delete
            l.startsWith("move up") -> IndexIcons.Up
            l.startsWith("move down") -> IndexIcons.Down
            l.contains("sound like") || l.startsWith("sonic") -> IndexIcons.Wave
            l.contains("favourite") -> IndexIcons.Heart
            l.startsWith("more like") -> IndexIcons.Plus
            l.startsWith("less like") -> IndexIcons.Minus
            l.startsWith("reverse") -> IndexIcons.Sort
            l.startsWith("choose cover") -> IndexIcons.Photos
            else -> null
        }
    }

    /** An option that removes an artist from every list is drawn in `chartRedText` (mockup frame 1, "Never suggest this artist"). */
    fun isDanger(label: String): Boolean = label.lowercase().let { it.startsWith("never suggest") || it == "not this artist" }

    /** "PICK 01 / 12 · BARK PSYCHOSIS", "SONG 05 / 10 · KHRUANGBIN": the eyebrow over a menu header. Callers upper-case it through [IndexLabel]. */
    fun eyebrow(kind: String, position: Int?, total: Int?, maker: String?): String {
        val place = if (position != null && total != null && position > 0 && total > 0) "$kind ${pad(position)} / ${pad(total)}" else kind
        return listOfNotNull(place, maker?.takeIf { it.isNotBlank() }).joinToString(" · ")
    }

    private fun pad(n: Int) = n.toString().padStart(2, '0')
}

/** One option of an Index sheet. [detail] is the line under it; [icon] the trailing glyph; [danger] draws the words in `chartRedText`. */
data class IndexMenuItem(
    val label: String, val detail: String? = null, val icon: ImageVector? = IndexSheetRules.glyphFor(label),
    val danger: Boolean = IndexSheetRules.isDanger(label), val enabled: Boolean = true, val run: () -> Unit,
)

/** A sheet's header: the eyebrow line, the title and the 72dp art beside them. */
class IndexMenuHeader(val title: String, val eyebrow: String?, val art: @Composable () -> Unit)

/** Plain label and action pairs as sheet options. */
fun indexMenuItems(items: List<Pair<String, () -> Unit>>): List<IndexMenuItem> = items.map { (label, run) -> IndexMenuItem(label, run = run) }

/**
 * The lettered sheet. Each option is at least 62dp: its letter in mono `accent` in a 26dp column, the label (Inter 600 15) over an optional line, and the
 * trailing glyph; a 1dp `edge` rule under each. Disabled options are muted and do nothing.
 */
@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun IndexMenuSheet(items: List<IndexMenuItem>, onDismiss: () -> Unit, header: IndexMenuHeader? = null) {
    val p = LocalPalette.current
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = androidx.compose.material3.rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        Column(Modifier.fillMaxWidth().padding(bottom = 16.dp)) {
            if (header != null) IndexSheetHeader(header.title, eyebrow = header.eyebrow, art = { Box(Modifier.size(IndexSheetRules.HEADER_ART.dp)) { header.art() } })
            items.forEachIndexed { i, item ->
                val ink = when {
                    !item.enabled -> p.textMuted
                    item.danger -> p.chartRedText
                    else -> p.text
                }
                Column(Modifier.indexArrive(i, "sheet")) {
                    Row(
                        Modifier.fillMaxWidth().heightIn(min = IndexSheetRules.OPTION_MIN.dp)
                            .clickable(enabled = item.enabled, role = Role.Button, onClick = { onDismiss(); item.run() })
                            .semantics(mergeDescendants = true) { contentDescription = listOfNotNull(item.label, item.detail).joinToString(". ") }
                            .padding(horizontal = IndexRules.GUTTER.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(IndexSheetRules.letter(i), style = IndexType.label(), color = if (item.enabled) p.accent else p.textMuted, maxLines = 1, modifier = Modifier.width(26.dp))
                        Column(Modifier.weight(1f).padding(vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(item.label, color = ink, style = IndexType.rowTitle(), maxLines = 2, overflow = TextOverflow.Ellipsis)
                            item.detail?.let { Text(it, color = p.textMuted, style = IndexType.body().copy(fontSize = 13.sp, lineHeight = 18.sp)) }
                        }
                        item.icon?.let { Icon(it, null, tint = ink, modifier = Modifier.size(IndexRules.ICON_INLINE.dp)) }
                    }
                    IndexRule()
                }
            }
        }
    }
}

/** The three dots that open a lettered sheet of [items] under an optional [header]. Draws nothing when there is nothing to offer. */
@Composable
fun IndexMenuButton(
    label: String, items: List<IndexMenuItem>, modifier: Modifier = Modifier, header: IndexMenuHeader? = null,
    tint: Color = LocalPalette.current.text, size: Dp = IndexRules.ICON.dp,
) {
    if (items.isEmpty()) return
    var open by remember { mutableStateOf(false) }
    Box(modifier) {
        IndexIconButton(IndexIcons.More, label, { open = true }, tint = tint, size = size)
        if (open) IndexMenuSheet(items, onDismiss = { open = false }, header = header)
    }
}

/**
 * The confirmation as Index draws it (mockup sheets, frame 3): a mono eyebrow, the question as a Lead title, the sentence, then Keep (ghost) and the
 * destructive button (`chartRedText` fill). The two stack, Keep first, because the destructive label names what goes and is too long to sit beside it.
 */
@Composable
internal fun IndexConfirmBody(spec: ConfirmSpec, onKeep: () -> Unit, onConfirm: () -> Unit) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxWidth().padding(start = IndexRules.GUTTER.dp, end = IndexRules.GUTTER.dp, bottom = 24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            spec.eyebrow?.let { IndexLabel(it) }
            Text(spec.title, color = p.text, style = IndexType.leadTitle().copy(fontSize = 30.sp, lineHeight = 30.sp))
        }
        Text(spec.message, color = p.text, style = IndexType.body().copy(fontSize = 15.sp, lineHeight = 22.sp))
        ConfirmRules.actions(spec).forEach { action ->
            when (action) {
                is ConfirmAction.Keep -> IndexButton(action.label, onKeep, Modifier.fillMaxWidth(), kind = IndexButtonKind.Ghost)
                is ConfirmAction.Delete -> IndexButton(action.label, onConfirm, Modifier.fillMaxWidth(), kind = IndexButtonKind.Danger)
            }
        }
    }
}
