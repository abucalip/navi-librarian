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
import app.discair.ui.common.GalleryButton
import app.discair.ui.common.GalleryButtonKind
import app.discair.ui.common.GalleryIcons
import app.discair.ui.common.GalleryProgress
import app.discair.ui.common.GalleryRule
import app.discair.ui.common.GalleryRules
import app.discair.ui.common.GallerySectionHead
import app.discair.ui.common.GallerySourceSwitch
import app.discair.ui.common.GalleryType
import app.discair.ui.settings.GallerySettingsColumn
import app.discair.ui.settings.GallerySettingsHead
import app.discair.ui.settings.GallerySwitchRow
import app.discair.ui.theme.LocalPalette

/*
 * Gallery's Equalizer and Crossfade pages (G6). Spec: docs/GALLERY_THEME.md sections 7 and 10; mockup: docs/design/gallery/pages/settings.html, frames 3 and 4.
 * EqualizerScreen and CrossfadeScreen reach these behind isGallery(); saving at once, hearing at once and the contracts' words are theirs, unchanged. The Now Playing
 * sheet shows the same pages with no back arrow ([onBack] null). The mockup's Fade row (Smooth, Even, Quick) is not drawn: the app has one equal-power curve and no
 * setting for it. The band and length arithmetic is [CoverStackEqRules]'.
 */

private val Gutter = GalleryRules.GUTTER.dp

/** The square step button of the mockup: a 44dp box with a 1dp `control` outline, radius 2, a minus or a plus, inside a 48dp touch target. */
@Composable
private fun Step(label: String, glyph: ImageVector, enabled: Boolean, onClick: () -> Unit) {
    val p = LocalPalette.current
    Box(Modifier.size(48.dp).alpha(if (enabled) 1f else 0.4f).clickable(enabled = enabled, role = Role.Button, onClick = onClick).semantics { contentDescription = label }, contentAlignment = Alignment.Center) {
        Box(Modifier.size(44.dp).border(1.dp, p.control, RoundedCornerShape(GalleryRules.BUTTON_RADIUS.dp)), contentAlignment = Alignment.Center) {
            Icon(glyph, null, tint = p.control, modifier = Modifier.size(GalleryRules.ICON.dp))
        }
    }
}

// ----- Equalizer --------------------------------------------------------------------------------------------------

@Composable
internal fun GalleryEqualizer(editor: EqEditor, settings: EqSettings, status: EqRuntimeStatus, onBack: (() -> Unit)?, onReset: () -> Unit) {
    val p = LocalPalette.current
    val on = settings.config.enabled
    var selected by remember { mutableIntStateOf(0) }
    GallerySettingsColumn {
        GallerySettingsHead("Equalizer", onBack, eyebrow = "Shapes everything you play here")
        GallerySwitchRow(
            "Equalizer", if (on) "On. The curve below shapes everything you play here." else "Off. Songs play as they are. Turn it on to use the controls below.",
            on, onChange = editor::setEnabled,
        )
        eqStatusLine(on, status)?.let {
            Text(it, color = p.text, style = GalleryType.body(), modifier = Modifier.padding(start = Gutter, end = Gutter, top = 4.dp).semantics { liveRegion = LiveRegionMode.Polite })
        }
        GallerySectionHead("Preset")
        val presets = listOf(EqSettings.PRESET_CUSTOM to "Custom") + EQ_PRESETS.map { it.id to it.label }
        Box(Modifier.alpha(if (on) 1f else 0.5f)) {
            GallerySourceSwitch(presets.map { it.second }, presets.indexOfFirst { it.first == settings.presetId }.coerceAtLeast(0), { if (on) editor.selectPreset(presets[it].first) })
        }
        GallerySectionHead("Bands")
        Bands(settings, on, selected, { selected = it }, editor)
        // The selected band's value and the two 48dp buttons: the plot is the quick way, never the only way.
        val gain = settings.config.bandGainsDb[selected]
        Row(Modifier.padding(start = Gutter, end = Gutter, top = 14.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Step("Lower ${bandSpoken(EQ_BAND_HZ[selected])} by half a decibel", GalleryIcons.Minus, on && gain > -EQ_MAX_GAIN_DB) { editor.nudgeBand(selected, -1) }
            Text(
                "${bandLabel(EQ_BAND_HZ[selected])} · ${formatDb(gain)}", Modifier.weight(1f).semantics { liveRegion = LiveRegionMode.Polite; contentDescription = "${bandSpoken(EQ_BAND_HZ[selected])}, ${formatDb(gain, spoken = true)}" },
                color = p.text, textAlign = TextAlign.Center, style = GalleryType.time.copy(fontSize = 13.sp),
            )
            Step("Raise ${bandSpoken(EQ_BAND_HZ[selected])} by half a decibel", GalleryIcons.Plus, on && gain < EQ_MAX_GAIN_DB) { editor.nudgeBand(selected, 1) }
        }
        Column(Modifier.padding(top = 20.dp)) {
            GalleryRule(Modifier.padding(horizontal = Gutter))
            val auto = settings.config.preGainAuto
            // The mockup's Headroom row: the name over its state in words; the switch is how it is changed.
            GallerySwitchRow(
                "Headroom",
                if (auto) "Automatic · ${formatDb(settings.config.effectivePreGainDb())}. The volume is lowered when you boost a band, so loud songs do not distort."
                else "Manual. You set the volume change yourself. A strong boost can distort.",
                auto, on, editor::setPreGainAuto,
            )
            if (!auto) Row(Modifier.padding(start = Gutter, end = Gutter, top = 8.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                val pre = settings.config.preGainDb
                Step("Lower the volume change by half a decibel", GalleryIcons.Minus, on && pre > -EQ_MAX_GAIN_DB) { editor.nudgePreGain(-1) }
                Text("Volume change · ${formatDb(pre)}", Modifier.weight(1f), color = p.text, textAlign = TextAlign.Center, style = GalleryType.time.copy(fontSize = 13.sp))
                Step("Raise the volume change by half a decibel", GalleryIcons.Plus, on && pre < 0.0) { editor.nudgePreGain(1) }
            }
        }
        Row(Modifier.padding(start = Gutter, end = Gutter, top = 24.dp)) {
            GalleryButton("Reset to flat", onReset, kind = GalleryButtonKind.Outlined, enabled = on)
        }
    }
}

/** Ten hairline columns with a dot at each band's gain; touch or drag sets a gain. The chosen band's label is in `text`, the others in `textMuted`. */
@Composable
private fun Bands(settings: EqSettings, on: Boolean, selected: Int, onSelect: (Int) -> Unit, editor: EqEditor) {
    val p = LocalPalette.current
    Column(Modifier.fillMaxWidth().padding(horizontal = Gutter).alpha(if (on) 1f else 0.5f)) {
        Row(Modifier.fillMaxWidth().height(160.dp)) {
            for (i in 0 until EQ_BAND_COUNT) {
                val gain = settings.config.bandGainsDb[i]
                Canvas(
                    Modifier.weight(1f).fillMaxHeight()
                        .pointerInput(on, i) { detectTapGestures { at -> onSelect(i); if (on) editor.setBand(i, CoverStackEqRules.gainAt(at.y / size.height)) } }
                        .pointerInput(on, i) { detectDragGestures(onDragStart = { onSelect(i) }) { change, _ -> change.consume(); if (on) editor.setBand(i, CoverStackEqRules.gainAt(change.position.y / size.height)) } }
                        .semantics { contentDescription = "${bandSpoken(EQ_BAND_HZ[i])}, ${formatDb(gain, spoken = true)}"; stateDescription = if (i == selected) "Selected" else "" },
                ) {
                    val x = size.width / 2f
                    drawLine(p.edge, Offset(x, 0f), Offset(x, size.height), strokeWidth = 1.dp.toPx())
                    val y = (1f - CoverStackEqRules.fill(gain)) * size.height
                    drawCircle(p.text, radius = (if (i == selected) 6.5.dp else 5.dp).toPx(), center = Offset(x, y.coerceIn(6.dp.toPx(), size.height - 6.dp.toPx())))
                }
            }
        }
        Row(Modifier.fillMaxWidth().padding(top = 8.dp)) {
            for (i in 0 until EQ_BAND_COUNT) {
                val shown = CoverStackEqRules.showLabel(i) || i == selected
                Text(
                    if (shown) bandLabel(EQ_BAND_HZ[i]).replace(" kHz", "k").replace(" Hz", "") else "", Modifier.weight(1f),
                    color = if (i == selected) p.text else p.textMuted, textAlign = TextAlign.Center, maxLines = 1, style = GalleryType.time.copy(fontSize = 10.5.sp),
                )
            }
        }
    }
}

// ----- Crossfade --------------------------------------------------------------------------------------------------

@Composable
internal fun GalleryCrossfade(settings: app.discair.player.PlayerSettings, xf: CrossfadeSettings, rate: Int?, onBack: (() -> Unit)?) {
    val p = LocalPalette.current
    val on = xf.enabled
    val seconds = CrossfadeSettings.sanitizeSeconds(xf.seconds)
    GallerySettingsColumn {
        GallerySettingsHead("Crossfade", onBack, eyebrow = "Songs blend into each other")
        GallerySwitchRow("Crossfade", CrossfadeText.switchHelp(on), on) { settings.crossfadeEnabled = it }
        GallerySectionHead("Length")
        Column(Modifier.padding(horizontal = Gutter).alpha(if (on) 1f else 0.5f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(20.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.CenterVertically) {
                Step("Shorten the crossfade by one second", GalleryIcons.Minus, on && CrossfadeText.canLower(seconds)) { settings.crossfadeSeconds = CrossfadeText.nudge(seconds, -1) }
                Text(
                    CrossfadeText.length(seconds), color = p.text, style = GalleryType.numeral,
                    modifier = Modifier.semantics { contentDescription = CrossfadeText.lengthSpoken(seconds); liveRegion = LiveRegionMode.Polite },
                )
                Step("Lengthen the crossfade by one second", GalleryIcons.Plus, on && CrossfadeText.canRaise(seconds)) { settings.crossfadeSeconds = CrossfadeText.nudge(seconds, 1) }
            }
            LengthBar(seconds, on) { settings.crossfadeSeconds = it }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("${CrossfadeSettings.MIN_SECONDS} s", color = p.textMuted, style = GalleryType.time.copy(fontSize = 11.sp))
                Text("${CrossfadeSettings.MAX_SECONDS} s", color = p.textMuted, style = GalleryType.time.copy(fontSize = 11.sp))
            }
        }
        GallerySectionHead("Albums")
        val keep = xf.skipSameAlbum
        GallerySwitchRow("Keep albums gapless", CrossfadeText.keepAlbumsHelp(keep), keep, on) { settings.crossfadeSkipSameAlbum = it }
        CrossfadeText.qualityLine(rate)?.let {
            Text(it, color = p.textMuted, style = GalleryType.small(), modifier = Modifier.padding(start = Gutter, end = Gutter, top = 12.dp))
        }
        Text("A change applies at the next song change, never to the song that is playing.", color = p.textMuted, style = GalleryType.small(), modifier = Modifier.padding(start = Gutter, end = Gutter, top = 8.dp))
    }
}

/** The 1.5dp line with the length in `text` (Gallery's progress line); touch or drag sets the length, in a 48dp-high touch area. */
@Composable
private fun LengthBar(seconds: Int, on: Boolean, onSet: (Int) -> Unit) {
    Box(
        Modifier.fillMaxWidth().heightIn(min = 48.dp).pointerInput(on) {
            detectTapGestures { at -> if (on) onSet(CoverStackEqRules.lengthAt(at.x / size.width)) }
        }.pointerInput(on) {
            detectDragGestures { change, _ -> change.consume(); if (on) onSet(CoverStackEqRules.lengthAt(change.position.x / size.width)) }
        },
        contentAlignment = Alignment.Center,
    ) { GalleryProgress(CoverStackEqRules.lengthFill(seconds)) }
}
