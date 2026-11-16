package app.discair.ui.settings

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.AppContainer
import app.discair.AppViewModel
import app.discair.Check
import app.discair.UiState
import app.discair.model.ServerReads
import app.discair.ui.LocalBottomClearance
import app.discair.ui.common.GalleryBanner
import app.discair.ui.common.GalleryButton
import app.discair.ui.common.GalleryButtonKind
import app.discair.ui.common.GalleryIcons
import app.discair.ui.common.GalleryPageBar
import app.discair.ui.common.GalleryPageHead
import app.discair.ui.common.GalleryRow
import app.discair.ui.common.GalleryRule
import app.discair.ui.common.GalleryRules
import app.discair.ui.common.GallerySectionHead
import app.discair.ui.common.GallerySourceSwitch
import app.discair.ui.common.GallerySwitch
import app.discair.ui.common.GalleryTabs
import app.discair.ui.common.GalleryType
import app.discair.ui.common.Load
import app.discair.ui.common.galleryShadow
import app.discair.ui.downloads.SettingsRules
import app.discair.ui.home.Inline
import app.discair.ui.home.Muted
import app.discair.ui.theme.Appearance
import app.discair.ui.theme.AppearanceRules
import app.discair.ui.theme.FontPairs
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.Palette
import app.discair.ui.theme.Palettes
import app.discair.ui.theme.THEME_SYSTEM
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/*
 * Gallery's Settings, Appearance and Server (G6). Spec: docs/GALLERY_THEME.md sections 7 and 10; mockups: docs/design/gallery/pages/settings.html
 * (frames 1 and 2) and downloads-stats-server.html (frame 3). Every row, switch, menu and button is the Standard page's, set out in hairline groups.
 * The building blocks here are also the Equalizer and Crossfade pages' (player/GalleryEqCrossfade.kt).
 */

/** The pure words of these pages. */
object GallerySettingsRules {
    /** "Checked at 14:32": the catalogue line over the Server title. */
    fun checkedLine(clock: String): String = "Checked at $clock"

    /** "Discair 1.3": the catalogue line over the Settings title. */
    fun versionLine(version: String?): String = if (version.isNullOrBlank()) "Discair" else "Discair $version"

    /** The icon a Settings row draws in Gallery: its own line icon for the rows the mockup names, the row's given icon otherwise. */
    fun iconFor(title: String, given: ImageVector): ImageVector = when (title) {
        "Server and services" -> GalleryIcons.Server
        "Appearance" -> GalleryIcons.Sun
        "Equalizer" -> GalleryIcons.Tune
        "Crossfade" -> GalleryIcons.Swap
        "Radio" -> GalleryIcons.Radio
        "Streaming quality" -> GalleryIcons.Wave
        else -> given
    }

    /** The groups the Appearance picker offers: day palettes and night palettes when following the phone, else every palette of the group. */
    fun slots(following: Boolean): List<Pair<String, Boolean?>> =
        if (following) listOf("Day" to true, "Night" to false) else listOf("Theme" to null)
}

/** One row of a Gallery group: a 22dp line icon in `control`, the name, its state in words under it, a chevron or [trailing], a hairline above when [divider]. */
@Composable
internal fun GallerySettingsRow(
    icon: ImageVector, title: String, state: String, modifier: Modifier, stateColor: Color, onClick: (() -> Unit)?, trailing: (@Composable () -> Unit)?, divider: Boolean,
) {
    val p = LocalPalette.current
    // A caller that passes no colour gets Material's muted default, which is not Gallery's; only a tone (green, amber, red) is carried over.
    val tone = if (stateColor == androidx.compose.material3.MaterialTheme.colorScheme.onSurfaceVariant) p.textMuted else stateColor
    Column(modifier) {
        if (divider) GalleryRule()
        Row(
            Modifier.fillMaxWidth().heightIn(min = 64.dp)
                .then(if (onClick != null) Modifier.clickable(role = Role.Button, onClick = onClick) else Modifier)
                .semantics(mergeDescendants = true) { contentDescription = "$title, $state" }
                .padding(vertical = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.size(36.dp), contentAlignment = Alignment.CenterStart) {
                Icon(GallerySettingsRules.iconFor(title, icon), null, tint = p.control, modifier = Modifier.size(GalleryRules.ICON.dp))
            }
            Column(Modifier.weight(1f)) {
                Text(title, color = p.text, style = GalleryType.rowTitle())
                if (state.isNotEmpty()) Text(state, color = tone, style = GalleryType.small())
            }
            if (trailing != null) trailing() else if (onClick != null) Icon(GalleryIcons.Chevron, null, tint = p.textMuted, modifier = Modifier.size(GalleryRules.ICON_INLINE.dp))
        }
    }
}

/** A title, a line of help and a Gallery switch, the whole row toggling (the mockup's Equalizer, Crossfade and Keep albums gapless rows). */
@Composable
internal fun GallerySwitchRow(title: String, help: String, checked: Boolean, enabled: Boolean = true, onChange: (Boolean) -> Unit) {
    val p = LocalPalette.current
    Row(
        Modifier.fillMaxWidth().heightIn(min = 64.dp).padding(horizontal = GalleryRules.GUTTER.dp)
            .toggleable(value = checked, enabled = enabled, role = Role.Switch, onValueChange = onChange).padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, color = p.text, style = GalleryType.rowTitle())
            Text(help, color = p.textMuted, style = GalleryType.small())
        }
        GallerySwitch(checked)
    }
}

/** A section head and the 20dp-inset column of rows under it. */
@Composable
internal fun GalleryGroup(title: String, first: Boolean = false, content: @Composable ColumnScope.() -> Unit) {
    GallerySectionHead(title, first = first)
    Column(Modifier.fillMaxWidth().padding(horizontal = GalleryRules.GUTTER.dp), content = content)
}

/** The bar and the head every one of these pages starts with; [onBack] null (the Now Playing sheet) draws only the title. */
@Composable
internal fun GallerySettingsHead(title: String, onBack: (() -> Unit)?, eyebrow: String? = null, barTitle: String = title) {
    if (onBack != null) GalleryPageBar(barTitle, onBack)
    GalleryPageHead(title, Modifier.padding(top = if (onBack != null) 0.dp else 16.dp, bottom = 18.dp), eyebrow = eyebrow)
}

/** The page's scroll column, clear of the dock. */
@Composable
internal fun GallerySettingsColumn(content: @Composable ColumnScope.() -> Unit) {
    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(bottom = 24.dp + LocalBottomClearance.current), content = content)
}

// ----- Settings ---------------------------------------------------------------------------------------------------

/** The Settings page: Server; Look and sound; Listening; Playback; then the connection buttons and Sign out. */
@Composable
internal fun GallerySettingsPage(
    state: UiState, model: AppViewModel, container: AppContainer, onBack: () -> Unit,
    onEqualizer: () -> Unit, onCrossfade: () -> Unit, onAppearance: () -> Unit, onServer: () -> Unit, onSignOut: () -> Unit,
) {
    val p = LocalPalette.current
    val context = LocalContext.current
    val version = remember { try { context.packageManager.getPackageInfo(context.packageName, 0).versionName } catch (e: Exception) { null } }
    GallerySettingsColumn {
        GallerySettingsHead("Settings", onBack, eyebrow = GallerySettingsRules.versionLine(version))
        // A failed check says why; the Server row below carries the calm states.
        if (state.librarian is Check.Failed || state.navidrome is Check.Failed) Column(Modifier.padding(horizontal = GalleryRules.GUTTER.dp)) { app.discair.ui.CheckLines(state) }
        val serverLine = SettingsRules.serverLine(state.librarian, state.navidrome)
        GalleryGroup("Server", first = true) {
            SettingsRow(
                GalleryIcons.Server, "Server and services", serverLine.text, onClick = onServer, divider = false,
                stateColor = when (serverLine.tone) {
                    SettingsRules.Tone.Success -> p.ok
                    SettingsRules.Tone.Danger -> p.chartRedText
                    else -> p.textMuted
                },
            )
        }
        GalleryGroup("Look and sound") {
            AppearanceRow(container.appearance, onAppearance, divider = false)
            app.discair.ui.PlaybackSettings(container, onEqualizer, onCrossfade, app.discair.ui.PlaybackShow.LookAndSound)
        }
        GalleryGroup("Listening") {
            RadioSettings(divider = false)
            ListenBrainzSettings()
            BlocklistSettings()
            app.discair.ui.LibrarySettings()
        }
        GalleryGroup("Playback") { app.discair.ui.PlaybackSettings(container, onEqualizer, onCrossfade, app.discair.ui.PlaybackShow.Rest) }
        Row(Modifier.padding(start = GalleryRules.GUTTER.dp, end = GalleryRules.GUTTER.dp, top = 28.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            GalleryButton("Check connection", { model.recheck() }, Modifier.weight(1f), kind = GalleryButtonKind.Outlined)
            GalleryButton("Edit servers", { model.editServers() }, Modifier.weight(1f), kind = GalleryButtonKind.Outlined)
        }
        // Destructive and rare: set apart and always confirmed (the sheet is the page's).
        Box(Modifier.fillMaxWidth().padding(top = 8.dp), contentAlignment = Alignment.Center) {
            GalleryButton("Sign out…", onSignOut, kind = GalleryButtonKind.Danger, icon = GalleryIcons.SignOut)
        }
    }
}

// ----- Server -----------------------------------------------------------------------------------------------------

/** The summary line with Check now, the services in words, and the activity, under a bar and a large title. [reload] is "Check now". */
@Composable
internal fun GalleryServer(state: Load<ServerReads>, reload: () -> Unit, onBack: () -> Unit) {
    val p = LocalPalette.current
    GallerySettingsColumn {
        when (state) {
            Load.Loading -> { GallerySettingsHead("Server", onBack); Muted("Checking the services…") }
            is Load.Failed -> { GallerySettingsHead("Server", onBack); Inline(state.failure.message, reload) }
            is Load.Ready -> {
                val zone = remember { ZoneId.systemDefault() }
                val clock = DateTimeFormatter.ofPattern("HH:mm").format(Instant.ofEpochMilli(state.value.checkedAtMillis).atZone(zone))
                val view = remember(state.value) { ServerRules.build(state.value, clock) }
                GallerySettingsHead("Server", onBack, eyebrow = GallerySettingsRules.checkedLine(clock))
                Summary(view.summary, reload)
                GalleryGroup("Services") {
                    view.services.forEachIndexed { i, row ->
                        GalleryRow(
                            row.name, divider = i < view.services.lastIndex,
                            lead = { Icon(GalleryIcons.Server, null, tint = p.control, modifier = Modifier.size(GalleryRules.ICON.dp)) },
                            trail = null,
                            sub = row.status.word, subColor = toneColor(row.status.tone),
                        )
                    }
                }
                if (view.activity.isNotEmpty()) GalleryGroup("Server activity") {
                    view.activity.forEachIndexed { i, row ->
                        // A warning or a failure says its word first; a finished job shows only its line (mockup).
                        val calm = row.status.tone == ServerTone.Success || row.status.tone == ServerTone.Neutral
                        GalleryRow(
                            row.name, divider = i < view.activity.lastIndex,
                            lead = { Icon(GalleryIcons.Wave, null, tint = p.control, modifier = Modifier.size(GalleryRules.ICON.dp)) },
                            sub = if (calm) row.line else "${row.status.word}. ${row.line}", subColor = if (calm) p.textMuted else toneColor(row.status.tone),
                        )
                    }
                }
            }
        }
    }
}

/** "One service needs attention" with its icon and a Check now button, between two hairlines (mockup frame 3). A calm result takes a check mark and the `ok` ink. */
@Composable
private fun Summary(summary: ServerSummary, reload: () -> Unit) {
    val p = LocalPalette.current
    val ink = toneColor(summary.tone)
    if (summary.tone == ServerTone.Success) {
        Column(Modifier.fillMaxWidth().padding(horizontal = GalleryRules.GUTTER.dp)) {
            GalleryRule()
            Row(
                Modifier.padding(vertical = 8.dp).semantics { liveRegion = LiveRegionMode.Polite },
                horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(GalleryIcons.Check, null, tint = ink, modifier = Modifier.size(GalleryRules.ICON_INLINE.dp))
                Text(summary.title, Modifier.weight(1f), color = p.text, style = GalleryType.small().copy(fontSize = 13.sp, lineHeight = 19.sp))
                GalleryButton("Check now", reload, kind = GalleryButtonKind.Outlined, small = true)
            }
            GalleryRule()
        }
        return
    }
    Column(Modifier.semantics { liveRegion = LiveRegionMode.Polite }) {
        GalleryBanner(summary.title, link = null)
        Row(Modifier.fillMaxWidth().padding(horizontal = GalleryRules.GUTTER.dp, vertical = 8.dp), horizontalArrangement = Arrangement.End) {
            GalleryButton("Check now", reload, kind = GalleryButtonKind.Outlined, small = true)
        }
    }
}

// ----- Appearance -------------------------------------------------------------------------------------------------

/**
 * Appearance (mockup settings, frame 2): Follow the phone or One theme as tabs, then Day and Night swatch grids of small prints. A word switch picks which of the
 * eight themes' palettes the grids show. The choices (follow the phone or one theme, day, night, font) and where they are kept are Appearance's, unchanged.
 */
@Composable
internal fun GalleryAppearance(appearance: Appearance, onBack: () -> Unit) {
    val p = LocalPalette.current
    val following = appearance.themeChoice == THEME_SYSTEM
    val systemDark = isSystemInDarkTheme()
    var filter by rememberSaveable { mutableStateOf(ThemeGroups.of(Palettes.byId(if (following) appearance.dayTheme else appearance.themeChoice))) }
    GallerySettingsColumn {
        GallerySettingsHead("Appearance", onBack, eyebrow = "Theme and type")
        GalleryTabs(
            listOf("Follow the phone", "One theme"), if (following) 0 else 1,
            { appearance.chooseTheme(if (it == 0) THEME_SYSTEM else appearance.palette(systemDark).id) },
        )
        Text(
            if (following) "Day theme when the phone is light, night theme when it is dark." else "One fixed theme, whatever the phone's setting is.",
            color = p.textMuted, style = GalleryType.small().copy(fontSize = 13.sp, lineHeight = 19.sp), modifier = Modifier.padding(horizontal = GalleryRules.GUTTER.dp, vertical = 14.dp),
        )
        val chips = ThemeGroups.chips(Palettes.All, null)
        val group = if (filter in chips) filter else chips.firstOrNull() ?: ThemeGroups.DEFAULT
        if (chips.size > 1) GallerySourceSwitch(chips, chips.indexOf(group), { filter = chips[it] })
        GallerySettingsRules.slots(following).forEach { (name, light) ->
            val shown = ThemeGroups.shown(Palettes.All, group, light)
            if (shown.isEmpty()) return@forEach
            val selectedId = when (light) { true -> appearance.dayTheme; false -> appearance.nightTheme; null -> appearance.themeChoice }
            GallerySectionHead(name)
            Column(Modifier.padding(horizontal = GalleryRules.GUTTER.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                shown.chunked(3).forEach { row ->
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                        row.forEach { theme ->
                            Swatch(theme, theme.id == selectedId, Modifier.weight(1f)) {
                                when (light) { true -> appearance.chooseDay(theme.id); false -> appearance.chooseNight(theme.id); null -> appearance.chooseTheme(theme.id) }
                            }
                        }
                        repeat(3 - row.size) { Spacer(Modifier.weight(1f)) }
                    }
                }
            }
        }
        GallerySectionHead("Type")
        Column(Modifier.padding(horizontal = GalleryRules.GUTTER.dp)) {
            FontPairs.All.forEachIndexed { i, pair ->
                val on = pair.id == appearance.fontPairId
                Column(
                    Modifier.selectable(selected = on, role = Role.RadioButton) { appearance.chooseFont(pair.id) }
                        .semantics(mergeDescendants = true) { contentDescription = "${pair.label}, ${pair.titleName} and ${pair.bodyName}${if (on) ", selected" else ""}" },
                ) {
                    if (i > 0) GalleryRule()
                    Row(Modifier.fillMaxWidth().heightIn(min = 64.dp).padding(vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(pair.label, color = p.text, fontFamily = pair.title, fontWeight = pair.titleWeight, style = GalleryType.rowTitle().copy(fontSize = 17.sp))
                            Text("${pair.titleName} and ${pair.bodyName}", color = p.textMuted, style = GalleryType.small())
                        }
                        if (on) Icon(GalleryIcons.Check, null, tint = p.control, modifier = Modifier.size(GalleryRules.ICON.dp))
                    }
                }
            }
        }
        Text(
            "Titles use ${appearance.fonts.titleName}; everything else uses ${appearance.fonts.bodyName}. Numbers use ${appearance.fonts.monoName}. All text still follows the phone's font size.",
            color = p.textMuted, style = GalleryType.small(), modifier = Modifier.padding(start = GalleryRules.GUTTER.dp, end = GalleryRules.GUTTER.dp, top = 12.dp),
        )
        Palettes.byId(if (following) appearance.dayTheme else appearance.themeChoice)?.let { c ->
            AppearanceRules.suggestedFont(c, appearance.fontPairId)?.let { f ->
                Text(
                    "${c.label} is drawn with ${f.label} (${f.titleName} and ${f.bodyName}). Your font is unchanged.",
                    color = p.textMuted, style = GalleryType.small(), modifier = Modifier.padding(start = GalleryRules.GUTTER.dp, end = GalleryRules.GUTTER.dp, top = 8.dp),
                )
            }
        }
    }
}

/**
 * A theme as a small print: a 5dp `mat` round its page colour, split by a diagonal of its text colour with its accent in the corner (the mockup's swatches),
 * its name under it. The chosen one has a 1.5dp `control` outline 3dp outside the mat.
 */
@Composable
private fun Swatch(theme: Palette, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    val p = LocalPalette.current
    Column(
        modifier.selectable(selected = selected, role = Role.RadioButton, onClick = onClick).heightIn(min = 48.dp)
            .semantics(mergeDescendants = true) { contentDescription = "${theme.label}, ${if (theme.light) "light" else "dark"}${if (selected) ", selected" else ""}" },
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Box(Modifier.fillMaxWidth().border(1.5.dp, if (selected) p.control else Color.Transparent).padding(3.dp)) {
            Box(Modifier.fillMaxWidth().galleryShadow(false, p).background(p.mat).padding(5.dp)) {
                Canvas(Modifier.fillMaxWidth().aspectRatio(1f)) {
                    drawRect(theme.ink)
                    val w = size.width; val h = size.height
                    drawPath(Path().apply { moveTo(w * 0.25f, h); lineTo(w, h * 0.2f); lineTo(w, h); close() }, theme.text)
                    drawPath(Path().apply { moveTo(w * 0.62f, h); lineTo(w, h * 0.57f); lineTo(w, h); close() }, theme.accent)
                    drawRect(theme.edge, Offset.Zero, size, style = androidx.compose.ui.graphics.drawscope.Stroke(0.5.dp.toPx()))
                }
            }
        }
        Text(theme.label, color = p.text, maxLines = 2, style = GalleryType.small().copy(fontSize = 12.sp, lineHeight = 15.sp), modifier = Modifier.padding(horizontal = 3.dp))
    }
}
