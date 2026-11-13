package app.discair.ui.settings

import app.discair.ui.common.ArtIcons
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.horizontalScroll
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.ui.LocalBottomClearance
import app.discair.ui.common.CoverStackDivider
import app.discair.ui.common.CoverStackHeading
import app.discair.ui.common.CoverStackRules
import app.discair.ui.common.CoverStackTabs
import app.discair.ui.common.CoverStackTitle
import app.discair.ui.common.CoverStackTopBar
import app.discair.ui.common.Target
import app.discair.ui.common.coverStackShadow
import app.discair.ui.discover.CoverStackChip
import app.discair.ui.player.PlayerIcons
import app.discair.ui.theme.Appearance
import app.discair.ui.theme.AppearanceRules
import app.discair.ui.theme.Family
import app.discair.ui.theme.FontPairs
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.Palette
import app.discair.ui.theme.Palettes
import app.discair.ui.theme.THEME_SYSTEM

/*
 * Soft Brut's (Layout.CoverStack) Appearance. Mockup: soft-brut/settings, frame 2. AppearanceScreen reaches this behind isCoverStack().
 * The choices (follow the phone or one theme, day, night, font) and where they are kept are Appearance's, unchanged.
 */

private const val SLOT_THEME = "theme"
private const val SLOT_DAY = "day"
private const val SLOT_NIGHT = "night"
private val Filters = listOf("All", "Light", "Dark", "Brutal")

/** Which themes a filter chip shows. */
object CoverStackAppearanceRules {
    fun shown(all: List<Palette>, filter: String): List<Palette> = all.filter {
        when (filter) { "Light" -> it.light; "Dark" -> !it.light; "Brutal" -> it.family == Family.Brutal; else -> true }
    }

    /** The filter a slot opens with: day shows light themes, night dark ones, the one theme all of them. */
    fun slotFilter(slot: String): String = when (slot) { SLOT_DAY -> "Light"; SLOT_NIGHT -> "Dark"; else -> "All" }

    /** The slot's page title. */
    fun slotTitle(slot: String?): String = when (slot) { SLOT_DAY -> "Day theme"; SLOT_NIGHT -> "Night theme"; SLOT_THEME -> "Theme"; else -> "Appearance" }
}

@Composable
internal fun CoverStackAppearance(appearance: Appearance, onBack: () -> Unit) {
    var picking by rememberSaveable { mutableStateOf<String?>(null) }
    var filter by rememberSaveable { mutableStateOf("All") }
    BackHandler(enabled = picking != null) { picking = null }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(bottom = 24.dp + LocalBottomClearance.current)) {
        CoverStackTopBar({ if (picking != null) picking = null else onBack() }, emptyList(), title = CoverStackAppearanceRules.slotTitle(picking).takeIf { picking != null } ?: "Appearance")
        CoverStackTitle(CoverStackAppearanceRules.slotTitle(picking), Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 12.dp), maxLines = 1)
        val slot = picking
        if (slot == null) Home(appearance, filter, { filter = it }) { picking = it; filter = CoverStackAppearanceRules.slotFilter(it) }
        else Picker(appearance, slot, filter) { filter = it }
    }
}

@Composable
private fun Home(appearance: Appearance, filter: String, onFilter: (String) -> Unit, open: (String) -> Unit) {
    val p = LocalPalette.current
    val following = appearance.themeChoice == THEME_SYSTEM
    val systemDark = isSystemInDarkTheme()
    CoverStackTabs(
        listOf("Follow the phone", "One theme"), if (following) 0 else 1,
        { appearance.chooseTheme(if (it == 0) THEME_SYSTEM else appearance.palette(systemDark).id) },
        Modifier.padding(start = 16.dp, end = 19.dp).fillMaxWidth(),
    )
    Text(
        if (following) "Uses your day theme in light mode and your night theme in dark mode." else "One fixed theme, whatever the phone's setting is.",
        color = p.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 12.dp),
    )
    if (following) {
        CsGroup(Modifier.padding(top = 16.dp)) {
            Palettes.byId(appearance.dayTheme)?.let { SlotRow("Day theme", it, false) { open(SLOT_DAY) } }
            Palettes.byId(appearance.nightTheme)?.let { SlotRow("Night theme", it, true) { open(SLOT_NIGHT) } }
        }
    } else {
        Spacer(Modifier.size(16.dp))
        CoverStackHeading("Theme")
        Picker(appearance, SLOT_THEME, filter, onFilter)
    }
    Spacer(Modifier.size(16.dp))
    CoverStackHeading("Font")
    CsGroup(Modifier.padding(top = 8.dp)) {
        FontPairs.All.forEachIndexed { i, pair ->
            val on = pair.id == appearance.fontPairId
            if (i > 0) CoverStackDivider()
            Row(
                Modifier.fillMaxWidth().heightIn(min = 64.dp).selectable(selected = on, role = Role.RadioButton) { appearance.chooseFont(pair.id) }
                    .semantics(mergeDescendants = true) { contentDescription = "${pair.label}, ${pair.titleName} and ${pair.bodyName}${if (on) ", selected" else ""}" }
                    .padding(vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(pair.label, color = p.text, fontFamily = pair.title, fontWeight = pair.titleWeight, style = MaterialTheme.typography.bodyLarge.copy(fontSize = 14.sp))
                    Text("${pair.titleName} and ${pair.bodyName}", color = p.textMuted, style = MaterialTheme.typography.bodySmall)
                }
                if (on) Icon(ArtIcons.Check, contentDescription = null, tint = p.text, modifier = Modifier.size(24.dp))
            }
        }
    }
    Text(
        "Titles use ${appearance.fonts.titleName}; everything else uses ${appearance.fonts.bodyName}. Numbers use ${appearance.fonts.monoName}. All text still follows the phone's font size.",
        color = p.textMuted, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 12.dp),
    )
    val chosen = Palettes.byId(if (following) appearance.dayTheme else appearance.themeChoice)
    chosen?.let { c ->
        AppearanceRules.suggestedFont(c, appearance.fontPairId)?.let { f ->
            Text("${c.label} is drawn with ${f.label} (${f.titleName} and ${f.bodyName}). Your font is unchanged.", color = p.textMuted, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp))
        }
    }
}

/** A row that opens a slot's theme grid: the theme's swatch, the slot's name, the theme in it and a chevron. */
@Composable
private fun SlotRow(title: String, theme: Palette, divider: Boolean, onClick: () -> Unit) {
    val p = LocalPalette.current
    if (divider) CoverStackDivider()
    Row(
        Modifier.fillMaxWidth().heightIn(min = 64.dp).clickable(role = Role.Button, onClick = onClick).semantics(mergeDescendants = true) { contentDescription = "$title, ${theme.label}" }.padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        Swatch(theme, Modifier.size(width = 56.dp, height = 32.dp), selected = false)
        Column(Modifier.weight(1f)) {
            Text(title, color = p.textMuted, style = MaterialTheme.typography.bodySmall)
            Text(theme.label, color = p.text, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
        }
        Icon(ArtIcons.Chevron, contentDescription = null, tint = p.text)
    }
}

/** The filter chips (for the one theme) and the three-column grid of swatches, the chosen one lifted on its hard shadow. */
@Composable
private fun Picker(appearance: Appearance, slot: String, filter: String, onFilter: (String) -> Unit) {
    val p = LocalPalette.current
    val selectedId = when (slot) { SLOT_DAY -> appearance.dayTheme; SLOT_NIGHT -> appearance.nightTheme; else -> appearance.themeChoice }
    val shown = CoverStackAppearanceRules.shown(Palettes.All.sortedBy { it.family }, filter)
    if (slot == SLOT_THEME) {
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(start = 16.dp, end = 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Filters.forEach { f -> CoverStackChip(f, f == filter) { onFilter(f) } }
        }
    } else Text(if (slot == SLOT_DAY) "Light themes only." else "Dark themes only.", color = p.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(horizontal = 16.dp))
    Text("${shown.size} themes", color = p.textMuted, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 4.dp, bottom = 8.dp))
    Column(Modifier.padding(start = 16.dp, end = 22.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        shown.chunked(3).forEach { row ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                row.forEach { theme ->
                    val on = theme.id == selectedId
                    Column(
                        Modifier.weight(1f).selectable(selected = on, role = Role.RadioButton) {
                            when (slot) { SLOT_DAY -> appearance.chooseDay(theme.id); SLOT_NIGHT -> appearance.chooseNight(theme.id); else -> appearance.chooseTheme(theme.id) }
                        }.heightIn(min = Target).semantics(mergeDescendants = true) { contentDescription = "${theme.label}, ${if (theme.light) "light" else "dark"}${if (on) ", selected" else ""}" },
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Swatch(theme, Modifier.fillMaxWidth().aspectRatio(1.75f), selected = on)
                        Text(theme.label, color = p.text, maxLines = 2, style = MaterialTheme.typography.bodySmall.copy(fontWeight = if (on) FontWeight.Bold else FontWeight.Normal))
                    }
                }
                repeat(3 - row.size) { Spacer(Modifier.weight(1f)) }
            }
        }
    }
}

/** A theme's own page colour with its accent as a corner wedge (mockup `.sw`), outlined in this theme's ink; the chosen one has the hard shadow. */
@Composable
private fun Swatch(theme: Palette, modifier: Modifier, selected: Boolean) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(8.dp)
    Box(
        modifier.then(if (selected) Modifier.coverStackShadow(shape, p) else Modifier).clip(shape).background(theme.ink)
            .drawBehind {
                val wedge = Path().apply { moveTo(size.width, 0f); lineTo(size.width, size.height); lineTo(size.width * 0.35f, size.height); close() }
                drawPath(wedge, theme.accent)
            }
            .border(CoverStackRules.outline(p).dp, p.edgeStrong, shape),
    )
}
