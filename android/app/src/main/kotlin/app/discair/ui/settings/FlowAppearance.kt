package app.discair.ui.settings

import app.discair.ui.common.ArtIcons
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.ui.common.FilterChip
import app.discair.ui.common.FlowDivider
import app.discair.ui.common.FlowGroup
import app.discair.ui.common.FlowHeading
import app.discair.ui.common.FlowTabs
import app.discair.ui.common.Target
import app.discair.ui.theme.Appearance
import app.discair.ui.theme.AppearanceRules
import app.discair.ui.theme.FontPairs
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.Palette
import app.discair.ui.theme.Palettes
import app.discair.ui.theme.THEME_SYSTEM

/*
 * Flow's (Layout.Flow) Appearance. Mockup: flow/settings, frame 2. AppearanceScreen reaches this behind isFlow(). The choices (follow the
 * phone or one theme, day, night, font) and where they are kept are Appearance's, unchanged; which themes a chip shows is
 * [CoverStackAppearanceRules]'.
 */

private const val SLOT_THEME = "theme"
private const val SLOT_DAY = "day"
private const val SLOT_NIGHT = "night"

@Composable
internal fun FlowAppearance(appearance: Appearance, onBack: () -> Unit) {
    var picking by rememberSaveable { mutableStateOf<String?>(null) }
    var filter by rememberSaveable { mutableStateOf(ThemeGroups.of(Palettes.byId(appearance.themeChoice))) }
    BackHandler(enabled = picking != null) { picking = null }
    FlowSettingsColumn {
        FlowSettingsHead(
            CoverStackAppearanceRules.slotTitle(picking), { if (picking != null) picking = null else onBack() },
            barTitle = CoverStackAppearanceRules.slotTitle(picking).takeIf { picking != null } ?: "Appearance",
        )
        val slot = picking
        if (slot == null) Home(appearance, filter, { filter = it }) { picking = it; filter = ThemeGroups.of(Palettes.byId(when (it) { SLOT_DAY -> appearance.dayTheme; SLOT_NIGHT -> appearance.nightTheme; else -> appearance.themeChoice })) }
        else Picker(appearance, slot, filter) { filter = it }
    }
}

@Composable
private fun Home(appearance: Appearance, filter: String, onFilter: (String) -> Unit, open: (String) -> Unit) {
    val p = LocalPalette.current
    val following = appearance.themeChoice == THEME_SYSTEM
    val systemDark = isSystemInDarkTheme()
    FlowTabs(
        listOf("Follow the phone", "One theme"), if (following) 0 else 1,
        { appearance.chooseTheme(if (it == 0) THEME_SYSTEM else appearance.palette(systemDark).id) },
        Modifier.padding(horizontal = 16.dp).fillMaxWidth(),
    )
    Text(
        if (following) "Uses your day theme in light mode and your night theme in dark mode." else "One fixed theme, whatever the phone's setting is.",
        color = p.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 12.dp),
    )
    if (following) {
        Spacer(Modifier.size(16.dp))
        FlowGroup {
            Palettes.byId(appearance.dayTheme)?.let { SlotRow("Day theme", it, false) { open(SLOT_DAY) } }
            Palettes.byId(appearance.nightTheme)?.let { SlotRow("Night theme", it, true) { open(SLOT_NIGHT) } }
        }
    } else {
        Spacer(Modifier.size(20.dp))
        FlowHeading("Theme")
        Spacer(Modifier.size(8.dp))
        Picker(appearance, SLOT_THEME, filter, onFilter)
    }
    Spacer(Modifier.size(20.dp))
    FlowHeading("Font")
    Spacer(Modifier.size(8.dp))
    FlowGroup {
        FontPairs.All.forEachIndexed { i, pair ->
            val on = pair.id == appearance.fontPairId
            if (i > 0) FlowDivider()
            Row(
                Modifier.fillMaxWidth().heightIn(min = 64.dp).selectable(selected = on, role = Role.RadioButton) { appearance.chooseFont(pair.id) }
                    .semantics(mergeDescendants = true) { contentDescription = "${pair.label}, ${pair.titleName} and ${pair.bodyName}${if (on) ", selected" else ""}" }
                    .padding(vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(pair.label, color = p.text, fontFamily = pair.title, fontWeight = pair.titleWeight, style = MaterialTheme.typography.bodyLarge.copy(fontSize = 15.sp))
                    Text("${pair.titleName} and ${pair.bodyName}", color = p.textMuted, style = MaterialTheme.typography.bodySmall.copy(fontSize = 12.sp))
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
    app.discair.ui.common.FlowListRow(
        theme.label, state = title, onClick = onClick, divider = divider,
        leading = { Swatch(theme, Modifier.size(width = 56.dp, height = 32.dp), selected = false) },
    )
}

/** The filter chips (for the one theme) and the three-column grid of swatches, the chosen one ringed in the accent. */
@Composable
private fun Picker(appearance: Appearance, slot: String, filter: String, onFilter: (String) -> Unit) {
    val p = LocalPalette.current
    val selectedId = when (slot) { SLOT_DAY -> appearance.dayTheme; SLOT_NIGHT -> appearance.nightTheme; else -> appearance.themeChoice }
    val light = ThemeGroups.slotLight(slot)
    val chips = ThemeGroups.chips(Palettes.All, light)
    val group = if (filter in chips) filter else chips.firstOrNull() ?: ThemeGroups.DEFAULT
    val shown = ThemeGroups.shown(Palettes.All, group, light)
    run {
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            chips.forEach { f -> FilterChip(selected = f == group, onClick = { onFilter(f) }, label = { Text(f) }) }
        }
    }
    if (slot != SLOT_THEME) Text(if (slot == SLOT_DAY) "Light themes only." else "Dark themes only.", color = p.textMuted, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(horizontal = 16.dp))
    Text("${shown.size} themes", color = p.textMuted, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 8.dp))
    Column(Modifier.padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
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

/** A theme's own page colour with its accent as a corner wedge (flow.css `.sw`), radius 12; the chosen one has a 2dp ring in this theme's accent. */
@Composable
private fun Swatch(theme: Palette, modifier: Modifier, selected: Boolean) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(12.dp)
    Box(
        modifier.clip(shape).background(theme.ink)
            .drawBehind {
                val wedge = Path().apply { moveTo(size.width, 0f); lineTo(size.width, size.height); lineTo(size.width * 0.35f, size.height); close() }
                drawPath(wedge, theme.accent)
            }
            .then(if (selected) Modifier.border(2.dp, p.accent, shape) else Modifier.border(0.5.dp, p.edge, shape)),
    )
}
