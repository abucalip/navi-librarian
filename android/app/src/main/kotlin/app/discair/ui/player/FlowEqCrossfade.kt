package app.discair.ui.player

import app.discair.ui.common.FlowIcons
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.player.crossfade.CrossfadeSettings
import app.discair.player.crossfade.CrossfadeText
import app.discair.player.eq.EQ_BAND_COUNT
import app.discair.player.eq.EQ_BAND_HZ
import app.discair.player.eq.EQ_MAX_GAIN_DB
import app.discair.player.eq.EQ_PRESETS
import app.discair.player.eq.EqEditor
import app.discair.player.eq.EqRuntimeStatus
import app.discair.player.eq.EqSettings
import app.discair.player.eq.bandLabel
import app.discair.player.eq.bandSpoken
import app.discair.player.eq.eqStatusLine
import app.discair.player.eq.formatDb
import app.discair.ui.common.FilterChip
import app.discair.ui.common.FlowCircleButton
import app.discair.ui.common.FlowGroup
import app.discair.ui.common.FlowHeading
import app.discair.ui.common.FlowSmallButton
import app.discair.ui.common.Target
import app.discair.ui.settings.FlowSettingsColumn
import app.discair.ui.settings.FlowSettingsHead
import app.discair.ui.settings.FlowSwitchRow
import app.discair.ui.theme.LocalPalette

/*
 * Flow's (Layout.Flow) Equalizer and Crossfade pages. Mockup: flow/settings, frames 3 and 4. EqualizerScreen and CrossfadeScreen reach these
 * behind isFlow(); saving at once, hearing at once and the contracts' words are theirs, unchanged. The Now Playing sheet shows the same pages
 * with no back arrow ([onBack] null). The mockup's Fade row (Smooth, Even, Quick) is not drawn: the app has one equal-power curve and no setting for it.
 * The band columns and the length bar use the arithmetic of [CoverStackEqRules].
 */

private val SideGutter = 16.dp

/** The step buttons of the mockup: a round `raised` button with a minus or a plus, 44dp, inside a 48dp touch target. */
@Composable
private fun Step(label: String, glyph: androidx.compose.ui.graphics.vector.ImageVector, enabled: Boolean, onClick: () -> Unit) {
    FlowCircleButton(glyph, label, { if (enabled) onClick() }, Modifier.alpha(if (enabled) 1f else 0.4f), size = 44)
}

// ----- Equalizer --------------------------------------------------------------------------------------------------

@Composable
internal fun FlowEqualizer(editor: EqEditor, settings: EqSettings, status: EqRuntimeStatus, onBack: (() -> Unit)?, onReset: () -> Unit) {
    val p = LocalPalette.current
    val on = settings.config.enabled
    var selected by remember { mutableIntStateOf(0) }
    FlowSettingsColumn {
        FlowSettingsHead("Equalizer", onBack)
        FlowGroup {
            FlowSwitchRow(
                "Equalizer", if (on) "On. The curve below shapes everything you play here." else "Off. Songs play as they are. Turn it on to use the controls below.",
                on, onChange = editor::setEnabled,
            )
        }
        eqStatusLine(on, status)?.let {
            Text(it, color = p.text, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(start = SideGutter, end = SideGutter, top = 8.dp).semantics { liveRegion = LiveRegionMode.Polite })
        }
        Spacer(Modifier.height(20.dp))
        FlowHeading("Preset")
        Row(
            Modifier.fillMaxWidth().padding(top = 8.dp).horizontalScroll(rememberScrollState()).padding(horizontal = SideGutter).alpha(if (on) 1f else 0.5f),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            (listOf(EqSettings.PRESET_CUSTOM to "Custom") + EQ_PRESETS.map { it.id to it.label }).forEach { (id, label) ->
                FilterChip(selected = id == settings.presetId, onClick = { if (on) editor.selectPreset(id) }, label = { Text(label) })
            }
        }
        Spacer(Modifier.height(20.dp))
        FlowHeading("Bands")
        Spacer(Modifier.height(8.dp))
        Bands(settings, on, selected, { selected = it }, editor)
        // The selected band's value and the two 48dp buttons: the columns are the quick way, never the only way.
        val gain = settings.config.bandGainsDb[selected]
        Row(Modifier.padding(start = SideGutter, end = SideGutter, top = 12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Step("Lower ${bandSpoken(EQ_BAND_HZ[selected])} by half a decibel", FlowIcons.Minus, on && gain > -EQ_MAX_GAIN_DB) { editor.nudgeBand(selected, -1) }
            Text(
                "${bandLabel(EQ_BAND_HZ[selected])} · ${formatDb(gain)}", Modifier.weight(1f).semantics { liveRegion = LiveRegionMode.Polite; contentDescription = "${bandSpoken(EQ_BAND_HZ[selected])}, ${formatDb(gain, spoken = true)}" },
                color = p.text, textAlign = TextAlign.Center, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp),
            )
            Step("Raise ${bandSpoken(EQ_BAND_HZ[selected])} by half a decibel", FlowIcons.Plus, on && gain < EQ_MAX_GAIN_DB) { editor.nudgeBand(selected, 1) }
        }
        Spacer(Modifier.height(20.dp))
        val auto = settings.config.preGainAuto
        FlowGroup {
            // The mockup's Headroom card: the name over its state in words; the switch is how it is changed.
            FlowSwitchRow(
                "Headroom",
                if (auto) "Automatic · ${formatDb(settings.config.effectivePreGainDb())}. The volume is lowered when you boost a band, so loud songs do not distort."
                else "Manual. You set the volume change yourself. A strong boost can distort.",
                auto, on, editor::setPreGainAuto,
            )
        }
        if (!auto) Row(Modifier.padding(start = SideGutter, end = SideGutter, top = 12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            val pre = settings.config.preGainDb
            Step("Lower the volume change by half a decibel", FlowIcons.Minus, on && pre > -EQ_MAX_GAIN_DB) { editor.nudgePreGain(-1) }
            Text("Volume change · ${formatDb(pre)}", Modifier.weight(1f), color = p.text, textAlign = TextAlign.Center, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp))
            Step("Raise the volume change by half a decibel", FlowIcons.Plus, on && pre < 0.0) { editor.nudgePreGain(1) }
        }
        Row(Modifier.padding(start = SideGutter, end = SideGutter, top = 20.dp)) {
            FlowSmallButton("Reset to flat", null, false, "Reset to flat", Modifier.fillMaxWidth(), enabled = on, onClick = onReset)
        }
    }
}

/** Ten tall rounded columns on a `raised` track filled from the bottom with the accent; touch or drag sets a gain. The chosen band's label is bold. */
@Composable
private fun Bands(settings: EqSettings, on: Boolean, selected: Int, onSelect: (Int) -> Unit, editor: EqEditor) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(6.dp)
    Column(Modifier.fillMaxWidth().padding(horizontal = SideGutter).alpha(if (on) 1f else 0.5f)) {
        Row(Modifier.fillMaxWidth().height(150.dp), horizontalArrangement = Arrangement.spacedBy(3.dp)) {
            for (i in 0 until EQ_BAND_COUNT) {
                val gain = settings.config.bandGainsDb[i]
                Box(
                    Modifier.weight(1f).fillMaxHeight().clip(shape).background(p.raised)
                        .pointerInput(on, i) {
                            detectTapGestures { at -> onSelect(i); if (on) editor.setBand(i, CoverStackEqRules.gainAt(at.y / size.height)) }
                        }
                        .pointerInput(on, i) {
                            detectDragGestures(onDragStart = { onSelect(i) }) { change, _ -> change.consume(); if (on) editor.setBand(i, CoverStackEqRules.gainAt(change.position.y / size.height)) }
                        }
                        .semantics { contentDescription = "${bandSpoken(EQ_BAND_HZ[i])}, ${formatDb(gain, spoken = true)}"; stateDescription = if (i == selected) "Selected" else "" },
                    contentAlignment = Alignment.BottomCenter,
                ) { Box(Modifier.fillMaxWidth().fillMaxHeight(CoverStackEqRules.fill(gain)).background(p.accent)) }
            }
        }
        Row(Modifier.fillMaxWidth().padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(3.dp)) {
            for (i in 0 until EQ_BAND_COUNT) {
                val shown = CoverStackEqRules.showLabel(i) || i == selected
                Text(
                    if (shown) bandLabel(EQ_BAND_HZ[i]).replace(" kHz", "k").replace(" Hz", "") else "", Modifier.weight(1f),
                    color = if (i == selected) p.text else p.textMuted, textAlign = TextAlign.Center, maxLines = 1,
                    style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp, fontWeight = if (i == selected) FontWeight.Bold else FontWeight.Normal),
                )
            }
        }
    }
}

// ----- Crossfade --------------------------------------------------------------------------------------------------

@Composable
internal fun FlowCrossfade(settings: app.discair.player.PlayerSettings, xf: CrossfadeSettings, rate: Int?, onBack: (() -> Unit)?) {
    val p = LocalPalette.current
    val on = xf.enabled
    val seconds = CrossfadeSettings.sanitizeSeconds(xf.seconds)
    FlowSettingsColumn {
        FlowSettingsHead("Crossfade", onBack)
        FlowGroup { FlowSwitchRow("Crossfade", CrossfadeText.switchHelp(on), on) { settings.crossfadeEnabled = it } }
        Spacer(Modifier.height(20.dp))
        FlowHeading("Length")
        Column(Modifier.padding(start = SideGutter, end = SideGutter, top = 12.dp).alpha(if (on) 1f else 0.5f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.CenterVertically) {
                Step("Shorten the crossfade by one second", FlowIcons.Minus, on && CrossfadeText.canLower(seconds)) { settings.crossfadeSeconds = CrossfadeText.nudge(seconds, -1) }
                Text(
                    CrossfadeText.length(seconds), color = p.text, style = MaterialTheme.typography.headlineLarge.copy(fontSize = 28.sp, lineHeight = 32.sp, fontWeight = FontWeight.ExtraBold),
                    modifier = Modifier.semantics { contentDescription = CrossfadeText.lengthSpoken(seconds); liveRegion = LiveRegionMode.Polite },
                )
                Step("Lengthen the crossfade by one second", FlowIcons.Plus, on && CrossfadeText.canRaise(seconds)) { settings.crossfadeSeconds = CrossfadeText.nudge(seconds, 1) }
            }
            LengthBar(seconds, on) { settings.crossfadeSeconds = it }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("${CrossfadeSettings.MIN_SECONDS} s", color = p.textMuted, style = MaterialTheme.typography.bodySmall)
                Text("${CrossfadeSettings.MAX_SECONDS} s", color = p.textMuted, style = MaterialTheme.typography.bodySmall)
            }
        }
        Spacer(Modifier.height(20.dp))
        FlowHeading("Albums")
        val keep = xf.skipSameAlbum
        Spacer(Modifier.height(8.dp))
        FlowGroup { FlowSwitchRow("Keep albums gapless", CrossfadeText.keepAlbumsHelp(keep), keep, on) { settings.crossfadeSkipSameAlbum = it } }
        CrossfadeText.qualityLine(rate)?.let {
            Text(it, color = p.textMuted, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = SideGutter, end = SideGutter, top = 12.dp))
        }
        Text("A change applies at the next song change, never to the song that is playing.", color = p.textMuted, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = SideGutter, end = SideGutter, top = 8.dp))
    }
}

/** The 4dp bar on a `raised` track with an accent fill (flow.css `.pb`); touch or drag sets the length, in a 48dp-high touch area. */
@Composable
private fun LengthBar(seconds: Int, on: Boolean, onSet: (Int) -> Unit) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(2.dp)
    Box(
        Modifier.fillMaxWidth().heightIn(min = Target).pointerInput(on) {
            detectTapGestures { at -> if (on) onSet(CoverStackEqRules.lengthAt(at.x / size.width)) }
        }.pointerInput(on) {
            detectDragGestures { change, _ -> change.consume(); if (on) onSet(CoverStackEqRules.lengthAt(change.position.x / size.width)) }
        },
        contentAlignment = Alignment.Center,
    ) {
        Box(Modifier.fillMaxWidth().height(4.dp).background(p.raised, shape)) {
            Box(Modifier.fillMaxWidth(CoverStackEqRules.lengthFill(seconds)).height(4.dp).background(p.accent, shape))
        }
    }
}
