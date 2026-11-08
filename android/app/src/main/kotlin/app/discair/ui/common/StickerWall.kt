package app.discair.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.discair.ui.theme.LocalFontPair
import app.discair.ui.theme.Palette
import app.discair.ui.theme.brutalShadow
import app.discair.ui.theme.themeShape

/** The words on the Sticker Wall's stickers. Always text: the tilt and colour only decorate them. */
enum class Sticker(val word: String) { New("New"), Missing("Missing") }

/** Pure rules for the Sticker Wall layout (docs/BRUT_LAYOUTS_PLAN.md section 7), apart from the drawing so they are unit-tested. */
object StickerWallRules {
    /** How many tiles each Home wall shows. */
    const val WALL_TILES = 6

    /** A tile's static tilt in degrees, alternating so neighbours lean apart; never animated. */
    fun tiltFor(index: Int): Float = floatArrayOf(-2f, 1.5f, 1.5f, -2f)[Math.floorMod(index, 4)]

    /** The spoken name of a tile: the album, the artist and the sticker's word, so the sticker is never lost to a screen reader. */
    fun tileDescription(album: String, artist: String, sticker: Sticker): String =
        listOf(album.ifBlank { "Unknown album" }, artist.ifBlank { "unknown artist" }.let { "by $it" }, sticker.word).joinToString(", ")

    /**
     * Breaks a title into at most [maxLines] stacked lines of whole words, as even as it can: a long title becomes a stack, a short
     * one stays on one or two lines. The words are never cut or reordered.
     */
    fun stackTitle(title: String, maxLines: Int = 3): List<String> {
        val words = title.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        if (words.isEmpty()) return emptyList()
        val lines = minOf(maxLines, words.size)
        val total = words.sumOf { it.length } + (words.size - 1)
        val target = total.toDouble() / lines
        val out = mutableListOf<String>()
        var current = StringBuilder()
        for ((i, word) in words.withIndex()) {
            val wordsLeft = words.size - i
            val linesLeft = lines - out.size
            val mustBreak = current.isNotEmpty() && (current.length + 1 + word.length > target * 1.15 || wordsLeft < linesLeft) && out.size < lines - 1
            if (mustBreak) { out.add(current.toString()); current = StringBuilder() }
            if (current.isNotEmpty()) current.append(' ')
            current.append(word)
        }
        if (current.isNotEmpty()) out.add(current.toString())
        return out
    }

    /** One of the three bars: bass (the lowest three of ten bands), mid (the next four) or treble (the top three). */
    enum class EqBar(val label: String, val bands: IntRange) { Bass("Bass", 0..2), Mid("Mid", 3..6), Treble("Treble", 7..9) }

    /** The bar's average gain in dB over its bands; a missing band counts as 0. */
    fun barGainDb(bands: List<Double>, bar: EqBar): Double = bar.bands.map { bands.getOrNull(it) ?: 0.0 }.average()

    /** Where the pill's fill reaches, 0 to 1: the centre is flat, full is the largest boost, empty the deepest cut. */
    fun barFraction(gainDb: Double, maxDb: Double): Float = (((gainDb + maxDb) / (2 * maxDb)).coerceIn(0.0, 1.0)).toFloat()

    /** Spoken value of a bar, in words: "Bass plus 2.5 decibels", "Mid flat". */
    fun barSpoken(bar: EqBar, gainDb: Double): String {
        val rounded = Math.round(gainDb * 10) / 10.0
        val value = when {
            rounded == 0.0 -> "flat"
            rounded > 0 -> "plus ${trim(rounded)} decibels"
            else -> "minus ${trim(-rounded)} decibels"
        }
        return "${bar.label} $value"
    }

    private fun trim(v: Double): String = if (v == Math.floor(v)) v.toInt().toString() else v.toString()
}

/**
 * The Sticker Wall's navigation: a floating pill (Search, Home, Player) with a hard shadow, each cell an icon over a word. The
 * current page is a filled round chip. Replaces the island, in the owner's chosen theme rather than the artwork tint.
 */
@Composable
fun StickerPill(
    palette: Palette, homeSelected: Boolean, playerLabel: String,
    onSearch: () -> Unit, onHome: () -> Unit, onPlayer: () -> Unit, modifier: Modifier = Modifier,
    searchIcon: @Composable (Color) -> Unit, homeIcon: @Composable (Color) -> Unit, player: @Composable (Color) -> Unit,
) {
    val pill = CircleShape
    val outline = (palette.shape?.outline ?: 3).dp
    Box(modifier.fillMaxWidth().navigationBarsPadding().padding(bottom = 16.dp), contentAlignment = Alignment.BottomCenter) {
        Row(
            Modifier.brutalShadow(pill).clip(pill).background(palette.surface).border(outline, palette.edgeStrong, pill).padding(horizontal = 8.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            PillCell(palette, "Search", "Search", false, onSearch) { searchIcon(it) }
            PillCell(palette, "Home", "Home", homeSelected, onHome) { homeIcon(it) }
            PillCell(palette, "Player", playerLabel, false, onPlayer) { player(it) }
        }
    }
}

@Composable
private fun PillCell(palette: Palette, word: String, spoken: String, selected: Boolean, onClick: () -> Unit, icon: @Composable (Color) -> Unit) {
    val fill = if (selected) palette.accent else palette.surface
    val ink = if (selected) palette.onAccent else palette.text
    Column(
        Modifier.heightIn(min = 52.dp).clip(CircleShape).background(fill).then(if (selected) Modifier.border((palette.shape?.outline ?: 3).dp, palette.edgeStrong, CircleShape) else Modifier)
            .clickable(role = Role.Button, onClick = onClick).padding(horizontal = 16.dp, vertical = 4.dp)
            .semantics { contentDescription = spoken; this.selected = selected },
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
    ) {
        Box(Modifier.size(24.dp), contentAlignment = Alignment.Center) { icon(ink) }
        Text(word, style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), color = ink, maxLines = 1, modifier = Modifier.clearAndSetSemantics { })
    }
}

/** A text sticker: a bordered, rounded label, tilted a little. Its word is part of the tile's spoken name, so this node is silent. */
@Composable
fun StickerBadge(sticker: Sticker, palette: Palette, tilt: Float, modifier: Modifier = Modifier) {
    val fill = if (sticker == Sticker.New) palette.accent4 else palette.accent3
    Text(
        sticker.word, style = MaterialTheme.typography.labelMedium.copy(fontFamily = LocalFontPair.current.mono, fontWeight = FontWeight.ExtraBold),
        color = palette.text, maxLines = 1,
        modifier = modifier.graphicsLayer { rotationZ = tilt }.clip(themeShape(8.dp)).background(fill)
            .border((palette.shape?.outline ?: 3).dp, palette.edgeStrong, themeShape(8.dp)).padding(horizontal = 8.dp, vertical = 4.dp)
            .clearAndSetSemantics { },
    )
}

/**
 * One tile of the wall: the cover in a round, hard-shadowed frame, the album and artist under it, a sticker on its corner, the whole
 * tile leaning a little. The tilt is static. The tile is one button named "album, by artist, sticker word"; [action] (a Get button) sits
 * over the cover outside that name, so it keeps its own.
 */
@Composable
fun StickerTile(
    album: String, artist: String, sticker: Sticker, index: Int, palette: Palette, onClick: () -> Unit,
    modifier: Modifier = Modifier, action: (@Composable BoxScope.() -> Unit)? = null, cover: @Composable () -> Unit,
) {
    val shape = themeShape(18.dp)
    val tilt = StickerWallRules.tiltFor(index)
    Box(modifier.graphicsLayer { rotationZ = tilt }.padding(end = 8.dp, bottom = 8.dp)) {
        Column(
            Modifier.fillMaxWidth().brutalShadow(shape).clip(shape).background(palette.surface).border((palette.shape?.outline ?: 3).dp, palette.edgeStrong, shape)
                .clickable(role = Role.Button, onClick = onClick)
                .semantics(mergeDescendants = true) { contentDescription = StickerWallRules.tileDescription(album, artist, sticker) },
        ) {
            Box(Modifier.fillMaxWidth()) {
                Box(Modifier.fillMaxWidth().clearAndSetSemantics { }) { cover() }
                StickerBadge(sticker, palette, -tilt * 2 - 4f, Modifier.align(Alignment.TopStart).padding(8.dp))
            }
            Column(Modifier.padding(horizontal = 8.dp, vertical = 8.dp)) {
                Text(album, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold), maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(artist, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
        }
        action?.let { Box(Modifier.matchParentSize().padding(end = 8.dp, bottom = 8.dp)) { it() } }
    }
}

/** Two columns of tiles, the right column dropped a little so the wall looks stuck up by hand. Not lazy: a Home wall is short. */
@Composable
fun <T> StickerWall(items: List<T>, modifier: Modifier = Modifier, tile: @Composable (item: T, index: Int) -> Unit) {
    Row(modifier.fillMaxWidth().padding(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        for (column in 0..1) {
            Column(Modifier.weight(1f).padding(top = if (column == 1) 16.dp else 0.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items.forEachIndexed { index, item -> if (index % 2 == column) tile(item, index) }
            }
        }
    }
}
