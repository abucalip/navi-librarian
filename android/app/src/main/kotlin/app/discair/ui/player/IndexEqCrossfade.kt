package app.discair.ui.player

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
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
import app.discair.ui.common.IndexButton
import app.discair.ui.common.IndexButtonKind
import app.discair.ui.common.IndexIcons
import app.discair.ui.common.IndexLabel
import app.discair.ui.common.IndexMuted
import app.discair.ui.common.IndexNumeral
import app.discair.ui.common.IndexProgress
import app.discair.ui.common.IndexRules
import app.discair.ui.common.IndexSectionHead
import app.discair.ui.common.IndexTabs
import app.discair.ui.common.IndexType
import app.discair.ui.settings.IndexSettingsColumn
import app.discair.ui.settings.IndexSettingsHead
import app.discair.ui.settings.IndexSwitchRow
import app.discair.ui.theme.LocalPalette

/*
 * Index's Equalizer and Crossfade pages (I6). Spec: docs/INDEX_THEME.md sections 7 and 10; mockup: docs/design/index/pages/settings.html, frames 3 and 4.
 * EqualizerScreen and CrossfadeScreen reach these behind isIndex(); saving at once, hearing at once and the contracts' words are theirs, unchanged. The Now
 * Playing sheet shows the same pages with no bar ([onBack] null). The mockup draws five bands; the app has [EQ_BAND_COUNT], all drawn. The band and length
 * arithmetic is [CoverStackEqRules]'.
 */

private val Gutter = IndexRules.GUTTER.dp

/** The pure words of these pages. */
object IndexEqRules {
    /** A band's short frequency under its column: "60", "230", "3.6K", "14K". */
    fun bandShort(hz: Int): String = bandLabel(hz).replace(" kHz", "k").replace(" Hz", "").uppercase()

    /** A band's gain under its frequency: "+2", "0", "-1.5" (no unit; the column says dB in words to a screen reader). */
    fun gainShort(db: Double): String = formatDb(db).replace(" dB", "").replace("−", "-")
}

/** A 44dp square step button with a 1.5dp `edge` outline and a minus or a plus, inside a 48dp touch area (the ghost button's frame). */
@Composable
private fun Step(label: String, glyph: ImageVector, enabled: Boolean, onClick: () -> Unit) {
    val p = LocalPalette.current
    Box(Modifier.size(48.dp).alpha(if (enabled) 1f else 0.4f).clickable(enabled = enabled, role = Role.Button, onClick = onClick).semantics { contentDescription = label }, contentAlignment = Alignment.Center) {
        Box(Modifier.size(44.dp).border(1.5.dp, p.edge, RoundedCornerShape(IndexRules.BUTTON_RADIUS.dp)), contentAlignment = Alignment.Center) {
            Icon(glyph, null, tint = p.text, modifier = Modifier.size(IndexRules.ICON.dp))
        }
    }
}

// ----- Equalizer --------------------------------------------------------------------------------------------------

@Composable
internal fun IndexEqualizer(editor: EqEditor, settings: EqSettings, status: EqRuntimeStatus, onBack: (() -> Unit)?, onReset: () -> Unit) {
    val p = LocalPalette.current
    val on = settings.config.enabled
    var selected by remember { mutableIntStateOf(0) }
    IndexSettingsColumn {
        IndexSettingsHead("Equalizer", onBack, action = { app.discair.ui.common.IndexIconButton(IndexIcons.Refresh, "Reset to flat", onReset) })
        IndexSwitchRow(
            "Equalizer on", if (on) "On. The curve below shapes everything you play here." else "Off. Songs play as they are. Turn it on to use the controls below.",
            on, onChange = editor::setEnabled,
        )
        eqStatusLine(on, status)?.let {
            Text(it, color = p.text, style = IndexType.body(), modifier = Modifier.padding(start = Gutter, end = Gutter, top = 8.dp).semantics { liveRegion = LiveRegionMode.Polite })
        }
        val presets = listOf(EqSettings.PRESET_CUSTOM to "Custom") + EQ_PRESETS.map { it.id to it.label }
        Box(Modifier.padding(top = 12.dp).alpha(if (on) 1f else 0.5f)) {
            IndexTabs(presets.map { it.second }, presets.indexOfFirst { it.first == settings.presetId }.coerceAtLeast(0), { if (on) editor.selectPreset(presets[it].first) })
        }
        Bands(settings, on, selected, { selected = it }, editor)
        // The selected band's value and the two 48dp buttons: the columns are the quick way, never the only way.
        val gain = settings.config.bandGainsDb[selected]
        Row(Modifier.padding(start = Gutter, end = Gutter, top = 14.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Step("Lower ${bandSpoken(EQ_BAND_HZ[selected])} by half a decibel", IndexIcons.Minus, on && gain > -EQ_MAX_GAIN_DB) { editor.nudgeBand(selected, -1) }
            Text(
                "${bandLabel(EQ_BAND_HZ[selected])} · ${formatDb(gain)}".uppercase(),
                Modifier.weight(1f).semantics { liveRegion = LiveRegionMode.Polite; contentDescription = "${bandSpoken(EQ_BAND_HZ[selected])}, ${formatDb(gain, spoken = true)}" },
                color = p.text, textAlign = TextAlign.Center, style = IndexType.label().copy(fontSize = 13.sp),
            )
            Step("Raise ${bandSpoken(EQ_BAND_HZ[selected])} by half a decibel", IndexIcons.Plus, on && gain < EQ_MAX_GAIN_DB) { editor.nudgeBand(selected, 1) }
        }
        IndexSectionHead("Headroom")
        val auto = settings.config.preGainAuto
        IndexSwitchRow(
            "Automatic headroom",
            if (auto) "Automatic · ${formatDb(settings.config.effectivePreGainDb())}. The volume is lowered when you boost a band, so loud songs do not distort."
            else "Manual. You set the volume change yourself. A strong boost can distort.",
            auto, on, editor::setPreGainAuto,
        )
        if (!auto) Row(Modifier.padding(start = Gutter, end = Gutter, top = 8.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            val pre = settings.config.preGainDb
            Step("Lower the volume change by half a decibel", IndexIcons.Minus, on && pre > -EQ_MAX_GAIN_DB) { editor.nudgePreGain(-1) }
            Text("Volume change · ${formatDb(pre)}".uppercase(), Modifier.weight(1f), color = p.text, textAlign = TextAlign.Center, style = IndexType.label().copy(fontSize = 13.sp))
            Step("Raise the volume change by half a decibel", IndexIcons.Plus, on && pre < 0.0) { editor.nudgePreGain(1) }
        }
        Row(Modifier.padding(start = Gutter, end = Gutter, top = 24.dp)) {
            IndexButton("Reset to flat", onReset, kind = IndexButtonKind.Ghost, icon = IndexIcons.Refresh, enabled = on)
        }
    }
}

/**
 * The bands as the mockup's columns: a 6dp `edge` track, the part below the gain in `accent` and a 22 by 10dp `text` block at the gain; the frequency and
 * the gain in mono under each. Touch or drag sets a gain; the chosen band's words are in `text`, the others in `textMuted`.
 */
@Composable
private fun Bands(settings: EqSettings, on: Boolean, selected: Int, onSelect: (Int) -> Unit, editor: EqEditor) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxWidth().padding(start = Gutter, end = Gutter, top = 20.dp).alpha(if (on) 1f else 0.5f)) {
        Row(Modifier.fillMaxWidth().height(200.dp)) {
            for (i in 0 until EQ_BAND_COUNT) {
                val gain = settings.config.bandGainsDb[i]
                Canvas(
                    Modifier.weight(1f).fillMaxHeight()
                        .pointerInput(on, i) { detectTapGestures { at -> onSelect(i); if (on) editor.setBand(i, CoverStackEqRules.gainAt(at.y / size.height)) } }
                        .pointerInput(on, i) { detectDragGestures(onDragStart = { onSelect(i) }) { change, _ -> change.consume(); if (on) editor.setBand(i, CoverStackEqRules.gainAt(change.position.y / size.height)) } }
                        .semantics { contentDescription = "${bandSpoken(EQ_BAND_HZ[i])}, ${formatDb(gain, spoken = true)}"; stateDescription = if (i == selected) "Selected" else "" },
                ) {
                    val track = 6.dp.toPx()
                    val x = size.width / 2f
                    val thumbH = 10.dp.toPx()
                    val y = ((1f - CoverStackEqRules.fill(gain)) * size.height).coerceIn(thumbH / 2, size.height - thumbH / 2)
                    drawRect(p.edge, Offset(x - track / 2, 0f), Size(track, size.height))
                    drawRect(p.accent, Offset(x - track / 2, y), Size(track, size.height - y))
                    val thumbW = (if (i == selected) 24.dp else 20.dp).toPx()
                    drawRect(p.text, Offset(x - thumbW / 2, y - thumbH / 2), Size(thumbW, thumbH))
                }
            }
        }
        Row(Modifier.fillMaxWidth().padding(top = 10.dp)) {
            for (i in 0 until EQ_BAND_COUNT) {
                val ink = if (i == selected) p.text else p.textMuted
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(IndexEqRules.bandShort(EQ_BAND_HZ[i]), color = ink, maxLines = 1, style = IndexType.label().copy(fontSize = 9.5.sp, letterSpacing = 0.sp))
                    Text(IndexEqRules.gainShort(settings.config.bandGainsDb[i]), color = ink, maxLines = 1, style = IndexType.label().copy(fontSize = 9.5.sp, letterSpacing = 0.sp))
                }
            }
        }
    }
}

// ----- Crossfade --------------------------------------------------------------------------------------------------

@Composable
internal fun IndexCrossfade(settings: app.discair.player.PlayerSettings, xf: CrossfadeSettings, rate: Int?, onBack: (() -> Unit)?) {
    val p = LocalPalette.current
    val on = xf.enabled
    val seconds = CrossfadeSettings.sanitizeSeconds(xf.seconds)
    IndexSettingsColumn {
        IndexSettingsHead("Crossfade", onBack)
        IndexSwitchRow("Crossfade", CrossfadeText.switchHelp(on), on) { settings.crossfadeEnabled = it }
        Column(Modifier.padding(start = Gutter, end = Gutter, top = 16.dp).alpha(if (on) 1f else 0.5f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            // The length as the page's numeral (motion #7) with SECONDS beside it, and the two step buttons.
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Bottom) {
                Row(Modifier.weight(1f).semantics(mergeDescendants = true) { contentDescription = CrossfadeText.lengthSpoken(seconds); liveRegion = LiveRegionMode.Polite }, verticalAlignment = Alignment.Bottom) {
                    IndexNumeral(seconds.toString(), IndexType.numeral(), p.text)
                    IndexLabel(if (seconds == 1) "Second" else "Seconds", Modifier.padding(start = 8.dp, bottom = 10.dp))
                }
                Step("Shorten the crossfade by one second", IndexIcons.Minus, on && CrossfadeText.canLower(seconds)) { settings.crossfadeSeconds = CrossfadeText.nudge(seconds, -1) }
                Step("Lengthen the crossfade by one second", IndexIcons.Plus, on && CrossfadeText.canRaise(seconds)) { settings.crossfadeSeconds = CrossfadeText.nudge(seconds, 1) }
            }
            LengthBar(seconds, on) { settings.crossfadeSeconds = it }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                IndexLabel("${CrossfadeSettings.MIN_SECONDS} s")
                IndexLabel("${CrossfadeSettings.MAX_SECONDS} s")
            }
        }
        IndexSectionHead("Albums")
        val keep = xf.skipSameAlbum
        IndexSwitchRow("Keep albums gapless", CrossfadeText.keepAlbumsHelp(keep), keep, on) { settings.crossfadeSkipSameAlbum = it }
        CrossfadeText.qualityLine(rate)?.let { IndexMuted(it, Modifier.padding(start = Gutter, end = Gutter, top = 12.dp)) }
        IndexMuted("A change applies at the next song change, never to the song that is playing.", Modifier.padding(start = Gutter, end = Gutter, top = 8.dp))
    }
}

/** The 6dp progress line with the length in `accent`; touch or drag sets the length, in a 48dp-high touch area. */
@Composable
private fun LengthBar(seconds: Int, on: Boolean, onSet: (Int) -> Unit) {
    Box(
        Modifier.fillMaxWidth().heightIn(min = 48.dp).pointerInput(on) {
            detectTapGestures { at -> if (on) onSet(CoverStackEqRules.lengthAt(at.x / size.width)) }
        }.pointerInput(on) {
            detectDragGestures { change, _ -> change.consume(); if (on) onSet(CoverStackEqRules.lengthAt(change.position.x / size.width)) }
        },
        contentAlignment = Alignment.Center,
    ) { IndexProgress(CoverStackEqRules.lengthFill(seconds)) }
}
