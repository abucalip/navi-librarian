package app.discair.ui.player

import app.discair.ui.common.ArtIcons
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Icon
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
import app.discair.player.eq.EQ_STEP_DB
import app.discair.player.eq.EqEditor
import app.discair.player.eq.EqRuntimeStatus
import app.discair.player.eq.EqSettings
import app.discair.player.eq.bandLabel
import app.discair.player.eq.bandSpoken
import app.discair.player.eq.eqStatusLine
import app.discair.player.eq.formatDb
import app.discair.player.eq.presetLabel
import app.discair.ui.LocalBottomClearance
import app.discair.ui.common.CoverStackHeading
import app.discair.ui.common.CoverStackRules
import app.discair.ui.common.CoverStackTitle
import app.discair.ui.common.CoverStackTopBar
import app.discair.ui.common.Target
import app.discair.ui.common.coverStackFrame
import app.discair.ui.discover.CoverStackChip
import app.discair.ui.discover.SmallButton
import app.discair.ui.settings.CsGroup
import app.discair.ui.settings.CsSwitchRow
import app.discair.ui.theme.LocalPalette
import kotlin.math.roundToInt

/*
 * Soft Brut's (Layout.CoverStack) Equalizer and Crossfade pages. Mockup: soft-brut/settings, frames 3 and 4. EqualizerScreen and
 * CrossfadeScreen reach these behind isCoverStack(); saving at once, hearing at once and the contracts' words are theirs, unchanged.
 * The Now Playing sheet shows the same pages with no back arrow ([onBack] null).
 */

/** The arithmetic of the band columns and the length bar, kept pure. */
object CoverStackEqRules {
    /** A column's fill, 0 (bottom, -max) to 1 (top, +max), for a gain. */
    fun fill(gainDb: Double, maxDb: Double = EQ_MAX_GAIN_DB): Float = (((gainDb + maxDb) / (2 * maxDb)).toFloat()).coerceIn(0f, 1f)

    /** The gain a touch at [fraction] of the column's height, 0 at the top and 1 at the bottom, means, snapped to the 0.5 dB step. */
    fun gainAt(fraction: Float, maxDb: Double = EQ_MAX_GAIN_DB, step: Double = EQ_STEP_DB): Double {
        val raw = maxDb - fraction.coerceIn(0f, 1f) * 2 * maxDb
        return (Math.round(raw / step) * step) + 0.0
    }

    /** The label under a column: every other band is named so the labels do not touch. */
    fun showLabel(index: Int): Boolean = index % 2 == 0 || index == EQ_BAND_COUNT - 1

    /** The length bar's fill, 0 at the shortest and 1 at the longest. */
    fun lengthFill(seconds: Int): Float {
        val lo = CrossfadeSettings.MIN_SECONDS; val hi = CrossfadeSettings.MAX_SECONDS
        return ((CrossfadeSettings.sanitizeSeconds(seconds) - lo).toFloat() / (hi - lo)).coerceIn(0f, 1f)
    }

    /** The whole seconds a touch at [fraction] of the bar's width means. */
    fun lengthAt(fraction: Float): Int {
        val lo = CrossfadeSettings.MIN_SECONDS; val hi = CrossfadeSettings.MAX_SECONDS
        return CrossfadeText.fromSlider(lo + fraction.coerceIn(0f, 1f) * (hi - lo))
    }
}

@Composable
private fun Page(onBack: (() -> Unit)?, title: String, content: @Composable () -> Unit) {
    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(bottom = 24.dp + LocalBottomClearance.current)) {
        if (onBack != null) CoverStackTopBar(onBack, emptyList(), title = title)
        CoverStackTitle(title, Modifier.padding(start = 16.dp, end = 16.dp, top = if (onBack != null) 8.dp else 16.dp, bottom = 12.dp), maxLines = 1)
        content()
    }
}

/** A 48dp outlined button for the stepper: a minus or a plus. */
@Composable
private fun StepButton(label: String, glyph: androidx.compose.ui.graphics.vector.ImageVector, enabled: Boolean, onClick: () -> Unit) {
    CsButton(label, 48, onClick, enabled = enabled) { ink -> Icon(glyph, contentDescription = null, tint = ink, modifier = Modifier.size(24.dp)) }
}

// ----- Equalizer --------------------------------------------------------------------------------------------------

@Composable
internal fun CoverStackEqualizer(editor: EqEditor, settings: EqSettings, status: EqRuntimeStatus, onBack: (() -> Unit)?, onReset: () -> Unit) {
    val p = LocalPalette.current
    val on = settings.config.enabled
    var selected by remember { mutableIntStateOf(0) }
    Page(onBack, "Equalizer") {
        CsGroup {
            CsSwitchRow(
                "Equalizer", if (on) "On. The curve below shapes everything you play here." else "Off. Songs play as they are. Turn it on to use the controls below.",
                on, onChange = editor::setEnabled,
            )
        }
        eqStatusLine(on, status)?.let {
            Text(it, color = p.text, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp).semantics { liveRegion = LiveRegionMode.Polite })
        }
        Spacer(Modifier.height(16.dp))
        CoverStackHeading("Preset")
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(start = 16.dp, end = 16.dp).alpha(if (on) 1f else 0.5f), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            (listOf(EqSettings.PRESET_CUSTOM to "Custom") + EQ_PRESETS.map { it.id to it.label }).forEach { (id, label) ->
                CoverStackChip(label, id == settings.presetId) { if (on) editor.selectPreset(id) }
            }
        }
        Spacer(Modifier.height(16.dp))
        CoverStackHeading("Bands")
        Bands(settings, on, selected, { selected = it }, editor)
        // The selected band's value and the two 48dp buttons: the columns are the quick way, never the only way.
        val gain = settings.config.bandGainsDb[selected]
        Row(Modifier.padding(start = 16.dp, end = 19.dp, top = 12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            StepButton("Lower ${bandSpoken(EQ_BAND_HZ[selected])} by half a decibel", ArtIcons.Minus, on && gain > -EQ_MAX_GAIN_DB) { editor.nudgeBand(selected, -1) }
            Text(
                "${bandLabel(EQ_BAND_HZ[selected])} · ${formatDb(gain)}", Modifier.weight(1f).semantics { liveRegion = LiveRegionMode.Polite; contentDescription = "${bandSpoken(EQ_BAND_HZ[selected])}, ${formatDb(gain, spoken = true)}" },
                color = p.text, textAlign = TextAlign.Center, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp),
            )
            StepButton("Raise ${bandSpoken(EQ_BAND_HZ[selected])} by half a decibel", ArtIcons.Plus, on && gain < EQ_MAX_GAIN_DB) { editor.nudgeBand(selected, 1) }
        }
        Spacer(Modifier.height(16.dp))
        CoverStackHeading("Headroom")
        val auto = settings.config.preGainAuto
        CsGroup(Modifier.padding(top = 8.dp)) {
            CsSwitchRow(
                "Automatic",
                if (auto) "On. The volume is lowered by ${formatDb(-settings.config.effectivePreGainDb()).removePrefix("+")} when you boost a band, so loud songs do not distort."
                else "Off. You set the volume change yourself. A strong boost can distort.",
                auto, on, editor::setPreGainAuto,
            )
        }
        if (!auto) Row(Modifier.padding(start = 16.dp, end = 19.dp, top = 12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            val pre = settings.config.preGainDb
            StepButton("Lower the volume change by half a decibel", ArtIcons.Minus, on && pre > -EQ_MAX_GAIN_DB) { editor.nudgePreGain(-1) }
            Text("Volume change · ${formatDb(pre)}", Modifier.weight(1f), color = p.text, textAlign = TextAlign.Center, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 14.sp))
            StepButton("Raise the volume change by half a decibel", ArtIcons.Plus, on && pre < 0.0) { editor.nudgePreGain(1) }
        }
        Row(Modifier.padding(start = 16.dp, end = 19.dp, top = 20.dp)) {
            SmallButton("Reset to flat", null, false, "Reset to flat", Modifier.fillMaxWidth(), enabled = on, onClick = onReset)
        }
    }
}

/** Ten outlined columns filled from the bottom with lavender; touch or drag sets a gain, the chosen band has the heavier outline. */
@Composable
private fun Bands(settings: EqSettings, on: Boolean, selected: Int, onSelect: (Int) -> Unit, editor: EqEditor) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(4.dp)
    Column(Modifier.fillMaxWidth().padding(start = 16.dp, end = 19.dp).alpha(if (on) 1f else 0.5f)) {
        Row(Modifier.fillMaxWidth().height(150.dp), horizontalArrangement = Arrangement.spacedBy(3.dp)) {
            for (i in 0 until EQ_BAND_COUNT) {
                val gain = settings.config.bandGainsDb[i]
                Box(
                    Modifier.weight(1f).fillMaxHeight().clip(shape).background(p.surface)
                        .border(if (i == selected) (CoverStackRules.outline(p) + 1f).dp else CoverStackRules.outline(p).dp, p.edgeStrong, shape)
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
                Text(
                    if (CoverStackEqRules.showLabel(i)) bandLabel(EQ_BAND_HZ[i]).replace(" kHz", "k").replace(" Hz", "") else "", Modifier.weight(1f),
                    color = p.textMuted, textAlign = TextAlign.Center, maxLines = 1, style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
                )
            }
        }
    }
}

// ----- Crossfade --------------------------------------------------------------------------------------------------

@Composable
internal fun CoverStackCrossfade(settings: app.discair.player.PlayerSettings, xf: CrossfadeSettings, rate: Int?, onBack: (() -> Unit)?) {
    val p = LocalPalette.current
    val on = xf.enabled
    val seconds = CrossfadeSettings.sanitizeSeconds(xf.seconds)
    Page(onBack, "Crossfade") {
        CsGroup { CsSwitchRow("Crossfade", CrossfadeText.switchHelp(on), on) { settings.crossfadeEnabled = it } }
        Spacer(Modifier.height(16.dp))
        CoverStackHeading("Length")
        Column(Modifier.padding(start = 16.dp, end = 19.dp, top = 12.dp).alpha(if (on) 1f else 0.5f), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.CenterVertically) {
                StepButton("Shorten the crossfade by one second", ArtIcons.Minus, on && CrossfadeText.canLower(seconds)) { settings.crossfadeSeconds = CrossfadeText.nudge(seconds, -1) }
                Text(
                    CrossfadeText.length(seconds), color = p.text, style = MaterialTheme.typography.headlineLarge.copy(fontSize = 28.sp, lineHeight = 32.sp, fontWeight = FontWeight.Bold),
                    modifier = Modifier.semantics { contentDescription = CrossfadeText.lengthSpoken(seconds); liveRegion = LiveRegionMode.Polite },
                )
                StepButton("Lengthen the crossfade by one second", ArtIcons.Plus, on && CrossfadeText.canRaise(seconds)) { settings.crossfadeSeconds = CrossfadeText.nudge(seconds, 1) }
            }
            LengthBar(seconds, on) { settings.crossfadeSeconds = it }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("${CrossfadeSettings.MIN_SECONDS} s", color = p.textMuted, style = MaterialTheme.typography.bodySmall)
                Text("${CrossfadeSettings.MAX_SECONDS} s", color = p.textMuted, style = MaterialTheme.typography.bodySmall)
            }
        }
        Spacer(Modifier.height(16.dp))
        CoverStackHeading("Albums")
        val keep = xf.skipSameAlbum
        CsGroup(Modifier.padding(top = 8.dp)) { CsSwitchRow("Keep albums gapless", CrossfadeText.keepAlbumsHelp(keep), keep, on) { settings.crossfadeSkipSameAlbum = it } }
        CrossfadeText.qualityLine(rate)?.let {
            Text(it, color = p.textMuted, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 12.dp))
        }
        Text("A change applies at the next song change, never to the song that is playing.", color = p.textMuted, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 8.dp))
    }
}

/** The 10dp outlined bar with a lavender fill (components: Progress); touch or drag sets the length. */
@Composable
private fun LengthBar(seconds: Int, on: Boolean, onSet: (Int) -> Unit) {
    val p = LocalPalette.current
    val shape = RoundedCornerShape(5.dp)
    Box(
        Modifier.fillMaxWidth().heightIn(min = Target).pointerInput(on) {
            detectTapGestures { at -> if (on) onSet(CoverStackEqRules.lengthAt(at.x / size.width)) }
        }.pointerInput(on) {
            detectDragGestures { change, _ -> change.consume(); if (on) onSet(CoverStackEqRules.lengthAt(change.position.x / size.width)) }
        },
        contentAlignment = Alignment.Center,
    ) {
        Box(Modifier.fillMaxWidth().height(10.dp).background(p.surface, shape).border(CoverStackRules.outline(p).dp, p.edgeStrong, shape)) {
            Box(Modifier.fillMaxWidth(CoverStackEqRules.lengthFill(seconds)).height(10.dp).background(p.accent, shape))
        }
    }
}
