package app.discair.ui.player

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import app.discair.ui.common.AlertDialog
import app.discair.ui.common.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import app.discair.ui.common.OutlinedButton
import app.discair.ui.common.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.dp
import app.discair.AppContainer
import app.discair.DiscairApplication
import app.discair.player.eq.EQ_BAND_COUNT
import app.discair.player.eq.EQ_BAND_HZ
import app.discair.player.eq.EQ_MAX_GAIN_DB
import app.discair.player.eq.EQ_PRESETS
import app.discair.player.eq.EQ_STEP_DB
import app.discair.player.eq.EqEditor
import app.discair.player.eq.EqSettings
import app.discair.player.eq.bandLabel
import app.discair.player.eq.bandSpoken
import app.discair.player.eq.eqStatusLine
import app.discair.player.eq.eqSummary
import app.discair.player.eq.formatDb
import app.discair.player.eq.presetLabel
import app.discair.ui.common.Target

/**
 * The Equalizer page (ANDROID_EQ_CONTRACT.md 7). Every change is saved at once and heard at once.
 * Every value can be changed with 48dp minus and plus buttons; the slider is the quick way, never the only way.
 * Off is shown in words and the controls stay on screen, marked unavailable.
 */
@Composable
fun EqualizerScreen(container: AppContainer, onBack: (() -> Unit)?) {
    val editor = remember { EqEditor(container.eqSettings) }
    val settings by editor.state.collectAsState()
    val status by container.eqStatus.collectAsState()
    val on = settings.config.enabled
    var confirmReset by remember { mutableStateOf(false) }
    // Soft Brut draws its own page (CoverStackEqCrossfade.kt); the editor, the reset sheet below and the sheet's no-back case are shared.
    // Flow draws its own page (FlowEqCrossfade.kt).
    if (app.discair.ui.common.isFlow()) FlowEqualizer(editor, settings, status, onBack, onReset = { confirmReset = true })
    else if (app.discair.ui.common.isCoverStack()) CoverStackEqualizer(editor, settings, status, onBack, onReset = { confirmReset = true }) else Column(
        Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(start = 16.dp, top = 8.dp, end = 16.dp, bottom = 8.dp + app.discair.ui.LocalBottomClearance.current),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            // Inside the Now Playing sheet there is no back arrow: the sheet closes by swipe, scrim tap or back.
            if (onBack != null) IconButton(onClick = onBack, Modifier.size(Target)) { Icon(app.discair.ui.player.PlayerIcons.Left, contentDescription = "Back") }
            Text("Equalizer", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.semantics { heading() })
        }
        Row(
            Modifier.fillMaxWidth().heightIn(min = Target)
                .toggleable(value = on, role = Role.Switch, onValueChange = editor::setEnabled),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f).padding(end = 16.dp)) {
                Text("Equalizer", style = MaterialTheme.typography.titleMedium)
                Text(
                    if (on) "On. The curve below shapes everything you play here."
                    else "Off. Songs play as they are. Turn it on to use the controls below.",
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            app.discair.ui.common.DiscairSwitch(checked = on)
        }
        eqStatusLine(on, status)?.let {
            Text(
                it, style = MaterialTheme.typography.bodyMedium, color = app.discair.ui.theme.Ink.AccentText,
                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
            )
        }

        PresetPicker(settings, enabled = on, onPick = editor::selectPreset)

        Text("Bands", style = MaterialTheme.typography.titleLarge, modifier = Modifier.padding(top = 8.dp).semantics { heading() })
        app.discair.ui.common.GlassCard(Modifier.fillMaxWidth()) {
            for (i in 0 until EQ_BAND_COUNT) {
                GainRow(
                    label = bandLabel(EQ_BAND_HZ[i]), spokenName = bandSpoken(EQ_BAND_HZ[i]),
                    db = settings.config.bandGainsDb[i], min = -EQ_MAX_GAIN_DB, max = EQ_MAX_GAIN_DB, enabled = on,
                    onChange = { editor.setBand(i, it) }, onNudge = { editor.nudgeBand(i, it) },
                )
            }
        }

        Text("Headroom", style = MaterialTheme.typography.titleLarge, modifier = Modifier.padding(top = 8.dp).semantics { heading() })
        val auto = settings.config.preGainAuto
        Row(
            Modifier.fillMaxWidth().heightIn(min = Target)
                .toggleable(value = auto, enabled = on, role = Role.Switch, onValueChange = editor::setPreGainAuto),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f).padding(end = 16.dp)) {
                Text("Automatic", style = MaterialTheme.typography.titleMedium)
                Text(
                    if (auto) "On. The volume is lowered by ${formatDb(-settings.config.effectivePreGainDb()).removePrefix("+")} when you boost a band, so loud songs do not distort."
                    else "Off. You set the volume change yourself. A strong boost can distort.",
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            app.discair.ui.common.DiscairSwitch(checked = auto, enabled = on)
        }
        if (!auto) {
            GainRow(
                label = "Volume change", spokenName = "Volume change",
                db = settings.config.preGainDb, min = -EQ_MAX_GAIN_DB, max = 0.0, enabled = on,
                onChange = editor::setPreGain, onNudge = editor::nudgePreGain,
            )
        }

        OutlinedButton(
            onClick = { confirmReset = true }, enabled = on,
            modifier = Modifier.fillMaxWidth().heightIn(min = Target).padding(top = 16.dp),
        ) { Text("Reset to flat") }
        Spacer(Modifier.size(24.dp))
    }
    if (confirmReset) {
        app.discair.ui.common.ConfirmSheet(
            app.discair.ui.common.ConfirmSpecs.resetEqualizer(),
            onKeep = { confirmReset = false },
            onConfirm = { confirmReset = false; editor.reset() },
        )
    }
}

@Composable
private fun PresetPicker(settings: EqSettings, enabled: Boolean, onPick: (String) -> Unit) {
    var open by remember { mutableStateOf(false) }
    val name = presetLabel(settings.presetId)
    Column {
        Text("Preset", style = MaterialTheme.typography.titleMedium)
        OutlinedButton(
            onClick = { open = true }, enabled = enabled,
            modifier = Modifier.fillMaxWidth().heightIn(min = Target)
                .semantics { contentDescription = "Preset, $name"; role = Role.DropdownList },
        ) {
            Text(name, Modifier.weight(1f))
            Icon(app.discair.ui.player.PlayerIcons.Down, contentDescription = null)
        }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            (EQ_PRESETS.map { it.id to it.label } + (EqSettings.PRESET_CUSTOM to "Custom")).forEach { (id, label) ->
                DropdownMenuItem(
                    text = { Text(if (id == settings.presetId) "$label (selected)" else label) },
                    onClick = { open = false; onPick(id) },
                    modifier = Modifier.heightIn(min = Target),
                )
            }
        }
    }
}

/** One line: minus, the frequency, the slider, the dB value and plus, in the glass band style. */
@Composable
private fun GainRow(
    label: String, spokenName: String, db: Double, min: Double, max: Double, enabled: Boolean,
    onChange: (Double) -> Unit, onNudge: (Int) -> Unit,
) {
    app.discair.ui.common.GlassBand(
        label = label, value = formatDb(db), spokenName = spokenName, spokenValue = formatDb(db, spoken = true),
        min = min.toFloat(), max = max.toFloat(), steps = ((max - min) / EQ_STEP_DB).toInt() - 1,
        sliderValue = db.toFloat(), enabled = enabled, canLower = db > min, canRaise = db < max,
        lowerLabel = "Lower $spokenName by half a decibel", raiseLabel = "Raise $spokenName by half a decibel",
        onSlide = { onChange(it.toDouble()) }, onNudge = onNudge,
    )
}

/** The sheet's entry to the page: the state is in the words, so it can be read without opening the page. */
@Composable
fun EqualizerLink(onOpen: () -> Unit) {
    val store = (LocalContext.current.applicationContext as DiscairApplication).container.eqSettings
    var summary by remember { mutableStateOf(eqSummary(store.load())) }
    DisposableEffect(Unit) {
        val remove = store.addListener { summary = eqSummary(store.load()) }
        onDispose { remove() }
    }
    // The state stays in words for TalkBack; sighted users read it from the icon's brightness.
    val on = !summary.endsWith(": off")
    val brut = app.discair.ui.theme.LocalPalette.current.brutal
    app.discair.ui.common.PlayerIconButton(onClick = onOpen, Modifier.size(if (brut) 48.dp else Target), selected = on) {
        Icon(PlayerIcons.Wave, contentDescription = summary, tint = if (brut) androidx.compose.material3.LocalContentColor.current else if (on) Color.White else Color.White.copy(alpha = 0.4f), modifier = Modifier.size(24.dp))
    }
}
