package app.discair.ui.settings

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import app.discair.ui.common.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import app.discair.ui.common.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import app.discair.ui.common.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.drawscope.translate
import androidx.compose.ui.graphics.drawOutline
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import app.discair.ui.LocalBottomClearance
import app.discair.ui.common.DiscairSwitch
import app.discair.ui.common.Target
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.Appearance
import app.discair.ui.theme.Family
import app.discair.ui.theme.FontPair
import app.discair.ui.theme.FontPairs
import app.discair.ui.theme.Ink
import app.discair.ui.theme.Palette
import app.discair.ui.theme.Palettes
import app.discair.ui.theme.THEME_SYSTEM

/** What the Appearance row in Settings says under its name. */
private fun Appearance.summary(): String {
    val theme = if (themeChoice == THEME_SYSTEM) "${Palettes.byId(dayTheme)?.label} / ${Palettes.byId(nightTheme)?.label}"
    else Palettes.byId(themeChoice)?.label ?: ""
    return "$theme · ${fonts.label}"
}

/** Settings shows only this row: the name, what is chosen now, and a chevron to the Appearance screen. */
@Composable
fun AppearanceRow(appearance: Appearance, onClick: () -> Unit) {
    val summary = appearance.summary()
    Row(
        Modifier.fillMaxWidth().heightIn(min = Target).clickable(role = Role.Button, onClick = onClick)
            .semantics(mergeDescendants = true) { contentDescription = "Appearance, $summary" }
            .padding(top = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text("Appearance", style = MaterialTheme.typography.titleLarge.copy(
                fontFamily = MaterialTheme.typography.bodyLarge.fontFamily, fontWeight = androidx.compose.ui.text.font.FontWeight.Bold,
                letterSpacing = androidx.compose.ui.unit.TextUnit.Unspecified,
            ))
            Text(summary, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Icon(PlayerIcons.Right, contentDescription = null)
    }
}

/** Which list the picker is showing: the one fixed theme, or the day or night slot. Saved so a rotation keeps it. */
private const val SLOT_THEME = "theme"
private const val SLOT_DAY = "day"
private const val SLOT_NIGHT = "night"

private val Filters = listOf("All", "Light", "Dark", "Brutal")

/**
 * Appearance: "Follow phone light/dark" with Day and Night slots, or one fixed Theme slot, and the Font. A slot
 * opens a grid of tiles, each drawn in that theme's own colours and shape. Choices apply at once and are kept on this device.
 */
@Composable
fun AppearanceScreen(appearance: Appearance, onBack: () -> Unit) {
    var picking by rememberSaveable { mutableStateOf<String?>(null) }
    var filter by rememberSaveable { mutableStateOf("All") }
    BackHandler(enabled = picking != null) { picking = null }
    Box(Modifier.fillMaxSize().safeDrawingPadding(), contentAlignment = Alignment.TopCenter) {
        Column(
            Modifier.widthIn(max = 560.dp).fillMaxSize().verticalScroll(rememberScrollState())
                .padding(start = 16.dp, top = 24.dp, end = 16.dp, bottom = 24.dp + LocalBottomClearance.current),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            val slot = picking
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = { if (slot != null) picking = null else onBack() }, Modifier.size(Target)) {
                    Icon(PlayerIcons.Left, contentDescription = "Back")
                }
                Text(
                    when (slot) { SLOT_DAY -> "Day theme"; SLOT_NIGHT -> "Night theme"; SLOT_THEME -> "Theme"; else -> "Appearance" },
                    style = MaterialTheme.typography.headlineMedium, modifier = Modifier.semantics { heading() },
                )
            }
            if (slot == null) AppearanceHome(appearance) { picking = it; filter = when (it) { SLOT_DAY -> "Light"; SLOT_NIGHT -> "Dark"; else -> "All" } }
            else ThemeGrid(appearance, slot, filter, onFilter = { filter = it }, onPicked = { })
        }
    }
}

@Composable
private fun AppearanceHome(appearance: Appearance, open: (String) -> Unit) {
    val following = appearance.themeChoice == THEME_SYSTEM
    val systemDark = isSystemInDarkTheme()
    Row(
        Modifier.fillMaxWidth().heightIn(min = Target).toggleable(value = following, role = Role.Switch) { on ->
            appearance.chooseTheme(if (on) THEME_SYSTEM else appearance.palette(systemDark).id)
        },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f).padding(end = 16.dp)) {
            Text("Follow phone light/dark", style = MaterialTheme.typography.titleMedium)
            Text(
                if (following) "Uses your day theme in light mode and your night theme in dark mode."
                else "One fixed theme, whatever the phone's setting is.",
                style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        DiscairSwitch(following)
    }
    if (following) {
        Palettes.byId(appearance.dayTheme)?.let { ThemeSlot("Day theme", it) { open(SLOT_DAY) } }
        Palettes.byId(appearance.nightTheme)?.let { ThemeSlot("Night theme", it) { open(SLOT_NIGHT) } }
    } else {
        Palettes.byId(appearance.themeChoice)?.let { ThemeSlot("Theme", it) { open(SLOT_THEME) } }
    }

    Text("Font", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 16.dp))
    ChoiceDropdown(
        title = "Font",
        current = "${appearance.fonts.label} · ${appearance.fonts.titleName} and ${appearance.fonts.bodyName}",
        options = FontPairs.All.map { FontOption(it.id, it.label, "${it.titleName} and ${it.bodyName}", it) },
        selectedId = appearance.fontPairId,
        onPick = appearance::chooseFont,
    )
    Text(
        "Titles use ${appearance.fonts.titleName}; everything else uses ${appearance.fonts.bodyName}. Numbers use ${appearance.fonts.monoName}. All text still follows the phone's font size.",
        style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

/** A row that opens the grid: the slot's name, the theme in it, its three dots and a chevron. */
@Composable
private fun ThemeSlot(title: String, p: Palette, onClick: () -> Unit) {
    val shape = RoundedCornerShape(12.dp)
    Row(
        Modifier.fillMaxWidth().heightIn(min = Target + 8.dp).clip(shape).border(BorderStroke(1.dp, Ink.Edge), shape)
            .background(Ink.Surface).clickable(role = Role.Button, onClick = onClick)
            .semantics(mergeDescendants = true) { contentDescription = "$title, ${p.label}" }
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Swatch(p)
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(p.label, style = MaterialTheme.typography.titleMedium)
        }
        Icon(PlayerIcons.Right, contentDescription = null)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ThemeGrid(appearance: Appearance, slot: String, filter: String, onFilter: (String) -> Unit, onPicked: () -> Unit) {
    val fixed = slot == SLOT_THEME
    val selectedId = when (slot) { SLOT_DAY -> appearance.dayTheme; SLOT_NIGHT -> appearance.nightTheme; else -> appearance.themeChoice }
    val all = Palettes.All.sortedBy { it.family } // Classic first, each family keeps its light-then-dark order
    val shown = all.filter {
        when (filter) {
            "Light" -> it.light
            "Dark" -> !it.light
            "Brutal" -> it.family == Family.Brutal
            else -> true
        }
    }
    if (fixed) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Filters.forEach { f ->
                FilterChip(
                    selected = f == filter, onClick = { onFilter(f) }, label = { Text(f) },
                    modifier = Modifier.heightIn(min = Target),
                )
            }
        }
    } else {
        Text(if (slot == SLOT_DAY) "Light themes only." else "Dark themes only.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
    Text("${shown.size} themes", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    shown.chunked(2).forEach { pair ->
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            pair.forEach { p ->
                ThemeTile(p, p.id == selectedId, Modifier.weight(1f)) {
                    when (slot) { SLOT_DAY -> appearance.chooseDay(p.id); SLOT_NIGHT -> appearance.chooseNight(p.id); else -> appearance.chooseTheme(p.id) }
                    onPicked()
                }
            }
            if (pair.size == 1) Spacer(Modifier.weight(1f))
        }
    }
}

/** A small page drawn in the theme's own colours and shape, with its name and kind under it. Selected: a ring and a check. */
@Composable
private fun ThemeTile(p: Palette, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    val s = p.shape
    val radius = s?.radius ?: 10
    val shape: Shape = if (radius == 0) RectangleShape else RoundedCornerShape(radius.dp)
    val inner: Shape = if (radius == 0) RectangleShape else RoundedCornerShape((radius * 0.6f).coerceAtLeast(3f).dp)
    val outline = (s?.outline ?: 1).dp
    val edge = if (s != null) p.edgeStrong else p.edge
    val kind = (if (p.light) "Light" else "Dark") + (if (p.family == Family.Brutal) " · Brutal" else "") +
        (if (p.layout != app.discair.ui.theme.Layout.Standard) " · ${p.layout.label}" else "")
    val description = "${p.label}, ${kind.replace(" · ", ", ").lowercase()}${if (selected) ", selected" else ""}"
    Column(
        modifier.selectable(selected = selected, role = Role.RadioButton, onClick = onClick)
            .semantics(mergeDescendants = true) { contentDescription = description }
            .heightIn(min = Target),
    ) {
        Box(Modifier.padding(end = 8.dp, bottom = 8.dp)) {
            Column(
                Modifier.fillMaxWidth().heightIn(min = 84.dp)
                    .let { m ->
                        if (s == null || s.shadow == 0) m else m.drawBehind {
                            val o = shape.createOutline(size, layoutDirection, this)
                            translate(s.shadow.dp.toPx(), s.shadow.dp.toPx()) { drawOutline(o, p.shadowColor) }
                        }
                    }
                    .clip(shape).background(p.ink).border(BorderStroke(outline, edge), shape)
                    .let { if (selected) it.border(BorderStroke(3.dp, Ink.Text), shape) else it }
                    .padding(8.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                repeat(2) { Box(Modifier.fillMaxWidth().size(width = 0.dp, height = 18.dp).background(p.surface, inner).border(BorderStroke(outline, edge), inner)) }
                Box(Modifier.fillMaxWidth(0.55f).size(width = 0.dp, height = 16.dp).background(p.accent, inner).border(BorderStroke(outline, edge), inner))
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(p.label, style = MaterialTheme.typography.titleSmall)
                Text(kind, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            if (selected) Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(20.dp))
        }
    }
}

private class FontOption(val id: String, val label: String, val detail: String, val font: FontPair)

/** The same dropdown the Playback section uses: a full-width button, a menu of rows at least 48dp tall. */
@Composable
private fun ChoiceDropdown(title: String, current: String, options: List<FontOption>, selectedId: String, onPick: (String) -> Unit) {
    var open by remember { mutableStateOf(false) }
    Box {
        OutlinedButton(
            onClick = { open = true },
            modifier = Modifier.fillMaxWidth().heightIn(min = Target)
                .semantics { contentDescription = "$title, $current"; role = Role.DropdownList },
        ) {
            Text(current, Modifier.weight(1f))
            Icon(PlayerIcons.Down, contentDescription = null)
        }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            options.forEach { option ->
                val on = option.id == selectedId
                DropdownMenuItem(
                    text = {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                            Column {
                                Text(
                                    option.label, fontFamily = option.font.title, fontWeight = option.font.titleWeight,
                                    style = MaterialTheme.typography.titleMedium,
                                )
                                Text(option.detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Spacer(Modifier.width(4.dp))
                            if (on) Icon(Icons.Default.Check, contentDescription = "Selected", modifier = Modifier.size(18.dp))
                        }
                    },
                    onClick = { open = false; onPick(option.id) },
                    modifier = Modifier.heightIn(min = Target)
                        .semantics { contentDescription = "${option.label}, ${option.detail}${if (on) ", selected" else ""}" },
                )
            }
        }
    }
}

/** Three dots in the theme's own page, surface and accent colours, ringed so a pale one still shows. */
@Composable
private fun Swatch(p: Palette) {
    Row(
        Modifier.background(p.ink, RoundedCornerShape(50)).border(BorderStroke(1.dp, p.edgeStrong), RoundedCornerShape(50))
            .padding(horizontal = 8.dp, vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        listOf(p.surface, p.text, p.accent).forEach { Spacer(Modifier.size(16.dp).background(it, CircleShape).border(BorderStroke(0.5.dp, p.edge), CircleShape)) }
    }
}
