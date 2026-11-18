package app.discair.ui.settings

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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.AppContainer
import app.discair.AppViewModel
import app.discair.Check
import app.discair.UiState
import app.discair.model.ServerReads
import app.discair.model.ServiceId
import app.discair.ui.LocalBottomClearance
import app.discair.ui.common.IndexButton
import app.discair.ui.common.IndexButtonKind
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexMuted
import app.discair.ui.common.IndexPageBar
import app.discair.ui.common.IndexPageHead
import app.discair.ui.common.IndexRow
import app.discair.ui.common.IndexRule
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexSectionHead
import app.discair.ui.common.IndexState
import app.discair.ui.common.IndexSwitch
import app.discair.ui.common.IndexTabs
import app.discair.ui.common.IndexType
import app.discair.ui.common.Load
import app.discair.ui.common.indexArrive
import app.discair.ui.downloads.SettingsRules
import app.discair.ui.home.Inline
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
 * Index's Settings, Server and Appearance (I6). Spec: docs/INDEX_THEME.md sections 7 and 10; mockups: docs/design/index/pages/settings.html (frames 1 and 2)
 * and downloads-stats-server.html (frame 3). Every row, switch, menu and button is the Standard page's, set out in ruled groups under a page head. The building
 * blocks here are also the Equalizer and Crossfade pages' (player/IndexEqCrossfade.kt).
 */

/** The pure words of these pages. */
object IndexSettingsRules {
    /** The longest state that stays a mono capital line under a row; a longer one (a sentence) is set in Inter so it can be read. */
    const val MONO_STATE_MAX = 44

    fun monoState(state: String): Boolean = state.length <= MONO_STATE_MAX

    /** "Discair 1.8.1": the page bar's catalogue line on Settings. */
    fun versionLine(version: String?): String = if (version.isNullOrBlank()) "Discair" else "Discair $version"

    /** "Checked 14:32": the page bar's catalogue line on Server. */
    fun checkedLine(clock: String): String = "Checked $clock"

    /**
     * A service row's mono line: its role, then what a newer server adds (Index I0): the Librarian's build label, and the Librarian's ping of Navidrome in
     * whole milliseconds on the Navidrome row. An older server adds nothing and the line is the role alone.
     */
    fun serviceMeta(id: ServiceId, role: String, version: String?, latencyMs: Int?): String = listOfNotNull(
        role.takeIf { it.isNotBlank() },
        version?.takeIf { id == ServiceId.Librarian && it.isNotBlank() }?.let { if (it.first().isDigit()) "v$it" else it },
        latencyMs?.takeIf { id == ServiceId.Navidrome && it >= 0 }?.let { "$it ms" },
    ).joinToString(" · ")

    /** The groups the Appearance swatches offer: day and night when following the phone, else every palette of the group. */
    fun slots(following: Boolean): List<Pair<String, Boolean?>> =
        if (following) listOf("Day" to true, "Night" to false) else listOf("Theme" to null)

    /** "DAY", "NIGHT · CHOSEN": the mono line under a swatch. */
    fun swatchLine(light: Boolean, chosen: Boolean): String = (if (light) "Day" else "Night") + if (chosen) " · chosen" else ""
}

/** One row of an Index group: the name (Inter 600 15), its state under it (mono capitals, or Inter when it is a sentence), a chevron or [trailing], a rule above when [divider]. */
@Composable
internal fun IndexSettingsRow(
    icon: ImageVector, title: String, state: String, modifier: Modifier, stateColor: Color, onClick: (() -> Unit)?, trailing: (@Composable () -> Unit)?, divider: Boolean,
) {
    val p = LocalPalette.current
    // A caller that passes no colour gets Material's muted default, which is not Index's; only a tone (green, amber, red) is carried over.
    val tone = if (stateColor == androidx.compose.material3.MaterialTheme.colorScheme.onSurfaceVariant) p.textMuted else stateColor
    Column(modifier) {
        if (divider) IndexRule()
        Row(
            Modifier.fillMaxWidth().heightIn(min = IndexRules.ROW_MIN.dp)
                .then(if (onClick != null) Modifier.clickable(role = Role.Button, onClick = onClick) else Modifier)
                .semantics(mergeDescendants = true) { contentDescription = if (state.isEmpty()) title else "$title, $state" }
                .padding(vertical = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(title, color = p.text, style = IndexType.rowTitle())
                if (state.isNotEmpty()) {
                    if (IndexSettingsRules.monoState(state)) IndexLabel(state, color = tone, maxLines = 2)
                    else Text(state, color = tone, style = IndexType.body().copy(fontSize = 13.sp, lineHeight = 18.sp))
                }
            }
            if (trailing != null) trailing() else if (onClick != null) Icon(IndexIcons.Chevron, null, tint = p.text, modifier = Modifier.size(IndexRules.ICON_INLINE.dp))
        }
    }
}

/** A title, a line of help and the square Index switch, the whole row toggling (the Equalizer on, Crossfade and Not inside an album rows). */
@Composable
internal fun IndexSwitchRow(title: String, help: String, checked: Boolean, enabled: Boolean = true, onChange: (Boolean) -> Unit) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxWidth().padding(horizontal = IndexRules.GUTTER.dp)) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = IndexRules.ROW_MIN.dp)
                .toggleable(value = checked, enabled = enabled, role = Role.Switch, onValueChange = onChange).padding(vertical = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(title, color = if (enabled) p.text else p.textMuted, style = IndexType.rowTitle())
                if (IndexSettingsRules.monoState(help)) IndexLabel(help, maxLines = 2)
                else Text(help, color = p.textMuted, style = IndexType.body().copy(fontSize = 13.sp, lineHeight = 18.sp))
            }
            IndexSwitch(checked)
        }
        IndexRule()
    }
}

/** A section head (its heavy rule draws on arrival) and the gutter column of rows under it. */
@Composable
internal fun IndexSettingsGroup(title: String, first: Boolean = false, meta: String? = null, content: @Composable ColumnScope.() -> Unit) {
    IndexSectionHead(title, meta = meta, first = first)
    Column(Modifier.fillMaxWidth().padding(horizontal = IndexRules.GUTTER.dp), content = content)
}

/** The page bar (mono [catalogue]) and the page head every one of these pages starts with; [onBack] null (the Now Playing sheet) draws only the head. */
@Composable
internal fun IndexSettingsHead(title: String, onBack: (() -> Unit)?, catalogue: String = title, count: String? = null, action: (@Composable () -> Unit)? = null) {
    if (onBack != null) IndexPageBar(catalogue, onBack, action = action)
    IndexPageHead(title, Modifier.padding(top = if (onBack != null) 0.dp else 8.dp, bottom = 4.dp), count = count)
}

/** The page's scroll column, clear of the strip and the bar. */
@Composable
internal fun IndexSettingsColumn(content: @Composable ColumnScope.() -> Unit) {
    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(bottom = 24.dp + LocalBottomClearance.current), content = content)
}

// ----- Settings ---------------------------------------------------------------------------------------------------

/** The Settings page (frame 1): Sound and look; Listening; Library; Playback; Account (Check connection, Edit servers, Sign out). */
@Composable
internal fun IndexSettingsPage(
    state: UiState, model: AppViewModel, container: AppContainer, onBack: () -> Unit,
    onEqualizer: () -> Unit, onCrossfade: () -> Unit, onAppearance: () -> Unit, onServer: () -> Unit, onSignOut: () -> Unit,
) {
    val p = LocalPalette.current
    val context = LocalContext.current
    val version = remember { try { context.packageManager.getPackageInfo(context.packageName, 0).versionName } catch (e: Exception) { null } }
    IndexSettingsColumn {
        IndexSettingsHead("Settings", onBack, catalogue = IndexSettingsRules.versionLine(version))
        // A failed check says why; the Server row below carries the calm states.
        if (state.librarian is Check.Failed || state.navidrome is Check.Failed) Column(Modifier.padding(horizontal = IndexRules.GUTTER.dp, vertical = 8.dp)) { app.discair.ui.CheckLines(state) }
        IndexSettingsGroup("Sound and look") {
            AppearanceRow(container.appearance, onAppearance, divider = false)
            app.discair.ui.PlaybackSettings(container, onEqualizer, onCrossfade, app.discair.ui.PlaybackShow.LookAndSound)
        }
        IndexSettingsGroup("Library") {
            val serverLine = SettingsRules.serverLine(state.librarian, state.navidrome)
            SettingsRow(
                IndexIcons.Server, "Server", serverLine.text, onClick = onServer, divider = false,
                stateColor = when (serverLine.tone) {
                    SettingsRules.Tone.Success -> p.ok
                    SettingsRules.Tone.Danger -> p.chartRedText
                    else -> p.textMuted
                },
            )
            app.discair.ui.LibrarySettings()
        }
        IndexSettingsGroup("Listening") {
            RadioSettings(divider = false)
            ListenBrainzSettings()
            BlocklistSettings()
        }
        IndexSettingsGroup("Playback") { app.discair.ui.PlaybackSettings(container, onEqualizer, onCrossfade, app.discair.ui.PlaybackShow.Rest) }
        IndexSettingsGroup("Account") {
            SettingsRow(IndexIcons.Refresh, "Check connection", "Ask both servers again", onClick = { model.recheck() }, divider = false)
            SettingsRow(IndexIcons.Server, "Edit servers", "Addresses and sign-in", onClick = { model.editServers() })
            // Destructive and rare: last, in red words, and always confirmed (the sheet is the page's).
            Column {
                IndexRule()
                Row(
                    Modifier.fillMaxWidth().heightIn(min = IndexRules.ROW_MIN.dp).clickable(role = Role.Button, onClickLabel = "Sign out", onClick = onSignOut),
                    horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text("Sign out", color = p.chartRedText, style = IndexType.rowTitle())
                        IndexLabel("Removes both servers from this phone")
                    }
                    Icon(IndexIcons.SignOut, null, tint = p.chartRedText, modifier = Modifier.size(IndexRules.ICON_INLINE.dp))
                }
                IndexRule()
            }
        }
    }
}

// ----- Server -----------------------------------------------------------------------------------------------------

/** Server (frame 3): the summary with Check now, the numbered services with their state words, and the activity. [reload] is "Check now". */
@Composable
internal fun IndexServer(state: Load<ServerReads>, reload: () -> Unit, onBack: () -> Unit) {
    val p = LocalPalette.current
    IndexSettingsColumn {
        when (state) {
            Load.Loading -> { IndexSettingsHead("Server", onBack); IndexMuted("Checking the services…", Modifier.padding(IndexRules.GUTTER.dp)) }
            is Load.Failed -> { IndexSettingsHead("Server", onBack); Inline(state.failure.message, reload) }
            is Load.Ready -> {
                val zone = remember { ZoneId.systemDefault() }
                val clock = DateTimeFormatter.ofPattern("HH:mm").format(Instant.ofEpochMilli(state.value.checkedAtMillis).atZone(zone))
                val view = remember(state.value) { ServerRules.build(state.value, clock) }
                IndexSettingsHead("Server", onBack, catalogue = IndexSettingsRules.checkedLine(clock))
                Row(
                    Modifier.fillMaxWidth().padding(start = IndexRules.GUTTER.dp, end = IndexRules.GUTTER.dp, top = 12.dp).semantics { liveRegion = LiveRegionMode.Polite },
                    horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(view.summary.title, color = toneColor(view.summary.tone), style = IndexType.rowTitle())
                        if (view.summary.detail.isNotBlank()) Text(view.summary.detail, color = p.textMuted, style = IndexType.body().copy(fontSize = 13.sp, lineHeight = 18.sp))
                    }
                    IndexButton("Check now", reload, kind = IndexButtonKind.Ghost, small = true)
                }
                IndexSectionHead("Services", meta = null, link = null)
                Column(Modifier.padding(horizontal = IndexRules.GUTTER.dp)) {
                    view.services.forEachIndexed { i, row ->
                        IndexRow(
                            row.name, Modifier.indexArrive(i, "services"),
                            meta = IndexSettingsRules.serviceMeta(row.id, row.role, state.value.librarianVersion, state.value.navidromeLatencyMs),
                            number = "%02d".format(i + 1), divider = i < view.services.lastIndex,
                            trail = { IndexState(row.status.word, color = toneColor(row.status.tone)) },
                        )
                    }
                }
                if (view.activity.isNotEmpty()) {
                    IndexSectionHead("Activity")
                    Column(Modifier.padding(horizontal = IndexRules.GUTTER.dp)) {
                        view.activity.forEachIndexed { i, row ->
                            // A warning or a failure says its word first; a finished job shows only its line (mockup).
                            val calm = row.status.tone == ServerTone.Success || row.status.tone == ServerTone.Neutral
                            IndexRow(
                                row.name, Modifier.indexArrive(view.services.size + i, "services"), meta = if (calm) row.line else "${row.status.word} · ${row.line}",
                                divider = i < view.activity.lastIndex,
                                trail = if (calm) null else ({ IndexState(row.status.word, color = toneColor(row.status.tone)) }),
                            )
                        }
                    }
                }
            }
        }
    }
}

// ----- Appearance -------------------------------------------------------------------------------------------------

/**
 * Appearance (frame 2): Follow the phone or One theme as tabs, the theme groups as tabs (Index first when it is the theme in use), then two-column swatches
 * for day and night, and the font pairs. The choices and where they are kept are Appearance's, unchanged; another group's palette leaves Index.
 */
@Composable
internal fun IndexAppearance(appearance: Appearance, onBack: () -> Unit) {
    val p = LocalPalette.current
    val following = appearance.themeChoice == THEME_SYSTEM
    val systemDark = isSystemInDarkTheme()
    var filter by rememberSaveable { mutableStateOf(ThemeGroups.of(Palettes.byId(if (following) appearance.dayTheme else appearance.themeChoice))) }
    val chips = ThemeGroups.chips(Palettes.All, null)
    val group = if (filter in chips) filter else chips.firstOrNull() ?: ThemeGroups.DEFAULT
    val inGroup = ThemeGroups.shown(Palettes.All, group, null)
    IndexSettingsColumn {
        IndexSettingsHead("Appearance", onBack, count = inGroup.size.toString())
        IndexTabs(
            listOf("Follow the phone", "One theme"), if (following) 0 else 1,
            { appearance.chooseTheme(if (it == 0) THEME_SYSTEM else appearance.palette(systemDark).id) },
            Modifier.padding(top = 8.dp),
        )
        IndexMuted(
            if (following) "Day theme when the phone is light, night theme when it is dark." else "One fixed theme, whatever the phone's setting is.",
            Modifier.padding(horizontal = IndexRules.GUTTER.dp, vertical = 12.dp),
        )
        if (chips.size > 1) {
            IndexLabel("Layout", Modifier.padding(start = IndexRules.GUTTER.dp, top = 4.dp))
            IndexTabs(chips, chips.indexOf(group), { filter = chips[it] })
        }
        IndexSettingsRules.slots(following).forEach { (name, light) ->
            val shown = ThemeGroups.shown(Palettes.All, group, light)
            if (shown.isEmpty()) return@forEach
            val selectedId = when (light) { true -> appearance.dayTheme; false -> appearance.nightTheme; null -> appearance.themeChoice }
            IndexSectionHead(name)
            Column(Modifier.padding(horizontal = IndexRules.GUTTER.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                shown.chunked(2).forEach { row ->
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        row.forEach { theme ->
                            Swatch(theme, theme.id == selectedId, Modifier.weight(1f)) {
                                when (light) { true -> appearance.chooseDay(theme.id); false -> appearance.chooseNight(theme.id); null -> appearance.chooseTheme(theme.id) }
                            }
                        }
                        repeat(2 - row.size) { Spacer(Modifier.weight(1f)) }
                    }
                }
            }
        }
        IndexSectionHead("Type")
        Column(Modifier.padding(horizontal = IndexRules.GUTTER.dp)) {
            FontPairs.All.forEachIndexed { i, pair ->
                val on = pair.id == appearance.fontPairId
                Column(
                    Modifier.selectable(selected = on, role = Role.RadioButton) { appearance.chooseFont(pair.id) }
                        .semantics(mergeDescendants = true) { contentDescription = "${pair.label}, ${pair.titleName} and ${pair.bodyName}${if (on) ", selected" else ""}" },
                ) {
                    if (i > 0) IndexRule()
                    Row(Modifier.fillMaxWidth().heightIn(min = IndexRules.ROW_MIN.dp).padding(vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(pair.label, color = p.text, fontFamily = pair.title, fontWeight = pair.titleWeight, style = IndexType.rowTitle().copy(fontSize = 17.sp))
                            IndexLabel("${pair.titleName}, ${pair.bodyName}, ${pair.monoName}", maxLines = 2)
                        }
                        if (on) Icon(IndexIcons.Check, null, tint = p.text, modifier = Modifier.size(IndexRules.ICON.dp))
                    }
                }
            }
        }
        Palettes.byId(if (following) appearance.dayTheme else appearance.themeChoice)?.let { c ->
            AppearanceRules.suggestedFont(c, appearance.fontPairId)?.let { f ->
                IndexMuted(
                    "${c.label} is drawn with ${f.label} (${f.titleName} and ${f.bodyName}). Your font is unchanged.",
                    Modifier.padding(start = IndexRules.GUTTER.dp, end = IndexRules.GUTTER.dp, top = 12.dp),
                )
            }
        }
    }
}

/**
 * A palette as the mockup draws it: its page colour with a 1dp `edge` outline, a square of its accent and "Aa" in its text colour across the top, a bar of its
 * control colour along the bottom; then its name and a mono line. The chosen one has a 2dp outline in the page's `text`.
 */
@Composable
private fun Swatch(theme: Palette, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    val p = LocalPalette.current
    Column(
        modifier.selectable(selected = selected, role = Role.RadioButton, onClick = onClick).heightIn(min = 48.dp)
            .semantics(mergeDescendants = true) { contentDescription = "${theme.label}, ${if (theme.light) "light" else "dark"}${if (selected) ", selected" else ""}" },
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Box(Modifier.fillMaxWidth().border(if (selected) 2.dp else 1.dp, if (selected) p.text else p.edge).padding(if (selected) 3.dp else 0.dp)) {
            Column(Modifier.fillMaxWidth().background(theme.ink).border(1.dp, theme.edge).padding(8.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(18.dp).background(theme.accent))
                    Spacer(Modifier.weight(1f))
                    Text("Aa", color = theme.text, style = IndexType.section().copy(fontSize = 20.sp, lineHeight = 22.sp))
                }
                Box(Modifier.fillMaxWidth().height(12.dp).background(theme.control))
            }
        }
        Text(theme.label, color = p.text, maxLines = 2, overflow = TextOverflow.Ellipsis, style = IndexType.rowTitle().copy(fontSize = 14.sp, fontWeight = FontWeight.SemiBold))
        IndexLabel(IndexSettingsRules.swatchLine(theme.light, selected))
    }
}
