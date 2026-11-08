package app.discair.ui.common

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.SliderState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.discair.ui.theme.Ink
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.brutalShadow
import app.discair.ui.theme.pillShape
import app.discair.ui.theme.themeBorder
import app.discair.ui.theme.themeShape

// Dark themes keep the original dark pill; light themes get an inset pill with a pale knob.

/**
 * The app's switch (Uiverse, Admin12121): a dark inset pill with a raised round knob and a filled square on the
 * other side, shown only while the switch is on, with a faint glow of the same colour around it. It only draws the
 * state; the row that holds it is the toggle, so a tap anywhere on the row works and TalkBack reads one control.
 */
@Composable
fun DiscairSwitch(checked: Boolean, modifier: Modifier = Modifier, enabled: Boolean = true) {
    val knobX by animateDpAsState(if (checked) 32.dp else 0.dp, tween(300), label = "knob")
    val glow by animateFloatAsState(if (checked) 1f else 0f, tween(300), label = "glow")
    val shape = pillShape()
    if (LocalPalette.current.brutal) {
        BrutalSwitch(checked, shape, modifier)
        return
    }
    val light = LocalPalette.current.light
    // Light themes: a well pressed into the page, a little darker at the top, with the page's own cream at the bottom.
    // Dark themes keep the original dark pill. When on, the accent lights the well from the square's side.
    // Off is the lighter shade, the same whether or not the row is enabled; only the on state is deeper.
    val trackTop = if (light) lerp(Ink.Raised, Ink.EdgeStrong, if (checked) 0.38f else 0.14f) else Color(0xFF1E1C1A)
    val trackBottom = if (light) lerp(Ink.Raised, Ink.Surface, if (checked) 0.35f else 0.6f) else Color(0xFF2A2725)
    val trackEdge = if (light) (if (checked) Ink.EdgeStrong else lerp(Ink.Edge, Ink.EdgeStrong, 0.4f)) else Color(0xFF34302C)
    val knob = if (light) listOf(Ink.Surface, lerp(Ink.Surface, Ink.Edge, 0.6f)) else listOf(Color(0xFF3A3632), Color(0xFF292624))
    val knobEdge = if (light) Ink.EdgeStrong else Color(0xFF4A4540)
    val inset = if (light) Color(0x40000000) else Color(0x80121110)
    Box(
        modifier.size(width = 66.dp, height = 32.dp)
            .clip(shape).background(Brush.verticalGradient(listOf(trackTop, trackBottom)))
            .border(BorderStroke(1.dp, trackEdge), shape),
    ) {
        // The glow lights the inside of the well, strongest at the square and fading across the pill.
        if (glow > 0f) {
            Box(
                Modifier.fillMaxSize().alpha(glow).background(
                    Brush.radialGradient(
                        0f to Ink.Accent.copy(alpha = if (light) 0.55f else 0.42f),
                        0.55f to Ink.Accent.copy(alpha = if (light) 0.22f else 0.14f),
                        1f to Color.Transparent,
                        center = Offset(with(LocalDensity.current) { 16.dp.toPx() }, with(LocalDensity.current) { 16.dp.toPx() }),
                        radius = with(LocalDensity.current) { 44.dp.toPx() },
                    ),
                ),
            )
        }
        // The inset shadow along the top edge, over the glow so the well keeps its depth.
        Box(Modifier.fillMaxWidth().height(12.dp).background(Brush.verticalGradient(listOf(inset, Color.Transparent))))
        Box(Modifier.fillMaxWidth().height(6.dp).align(Alignment.BottomCenter).background(Brush.verticalGradient(listOf(Color.Transparent, if (light) Color(0x22FFFFFF) else Color(0x14FFFFFF)))))
        if (glow > 0f) {
            Box(Modifier.align(Alignment.CenterStart).offset(x = 11.dp).size(10.dp).alpha(glow).background(Ink.Accent))
        }
        Box(
            Modifier.padding(4.dp).align(Alignment.CenterStart).offset(x = knobX).size(24.dp)
                .shadow(4.dp, CircleShape)
                .background(Brush.verticalGradient(knob), CircleShape)
                .border(BorderStroke(0.5.dp, knobEdge), CircleShape),
        )
    }
}


/**
 * The web's action group: buttons joined in one rounded frame on the surface colour, with a hairline between
 * them (static/app.css .action-group). Put [ActionGroupButton]s and [GroupDivider]s inside.
 */
@Composable
fun ActionGroup(modifier: Modifier = Modifier, content: @Composable RowScope.() -> Unit) {
    val shape = themeShape(10.dp)
    Row(
        modifier.brutalShadow(shape).height(Target).clip(shape).background(Ink.Surface).border(themeBorder(BorderStroke(1.dp, Ink.EdgeStrong)), shape),
        verticalAlignment = Alignment.CenterVertically,
        content = content,
    )
}

@Composable
fun GroupDivider() {
    Box(Modifier.width(1.dp).fillMaxHeight().background(Ink.EdgeStrong))
}

/** A cell of an [ActionGroup]. [selected] marks the chosen one of a set, in the icon colour and for TalkBack. */
@Composable
fun ActionGroupButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    description: String? = null,
    selected: Boolean? = null,
    enabled: Boolean = true,
    content: @Composable () -> Unit,
) {
    Box(
        modifier.fillMaxHeight().widthIn(min = 44.dp)
            .background(if (selected == true) Ink.Raised else Color.Transparent)
            .clickable(enabled = enabled, role = if (selected != null) Role.Tab else Role.Button, onClick = onClick)
            .semantics {
                if (description != null) contentDescription = description
                if (selected != null) this.selected = selected
            }
            .padding(horizontal = 16.dp),
        contentAlignment = Alignment.Center,
    ) { content() }
}

/** An icon cell: white, or the accent when it is the selected one. */
@Composable
fun GroupIcon(icon: ImageVector, selected: Boolean = false) {
    Icon(icon, contentDescription = null, tint = if (selected) Ink.Accent else Ink.Text, modifier = Modifier.size(22.dp))
}

/** A text cell: white, as the web's group buttons. */
@Composable
fun GroupLabel(text: String) {
    Text(
        text, color = Ink.Text, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, textAlign = TextAlign.Center,
        maxLines = 2, overflow = TextOverflow.Ellipsis,
    )
}

private val GlassFillDark = Color(0xBF242424)
private val GlassTrackDark = Color(0xFF1A1A1A)
private val GlassFill: Color @Composable get() = if (LocalPalette.current.light) Ink.Raised else GlassFillDark
private val GlassTrack: Color @Composable get() = if (LocalPalette.current.light) Ink.Edge else GlassTrackDark

/** The glass card behind a set of bands (Uiverse, byllzz), in the app's palette. */
@Composable
fun GlassCard(modifier: Modifier = Modifier, content: @Composable androidx.compose.foundation.layout.ColumnScope.() -> Unit) {
    val shape = themeShape(14.dp)
    androidx.compose.foundation.layout.Column(
        modifier.brutalShadow(shape).clip(shape).background(Ink.Surface)
            .border(themeBorder(BorderStroke(1.dp, if (LocalPalette.current.light) Ink.Edge else Color(0x14FFFFFF))), shape).padding(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
        content = content,
    )
}

/**
 * One band, all on one line: a small minus, the name (the frequency), the slider, a hairline, the value and a
 * small plus. The slider is the quick way; the buttons make every value reachable by tap (and by TalkBack).
 */
@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun GlassBand(
    label: String,
    value: String,
    spokenName: String,
    spokenValue: String,
    min: Float,
    max: Float,
    steps: Int,
    sliderValue: Float,
    enabled: Boolean,
    canLower: Boolean,
    canRaise: Boolean,
    lowerLabel: String,
    raiseLabel: String,
    onSlide: (Float) -> Unit,
    onNudge: (Int) -> Unit,
    valueWidth: Dp = 56.dp,
    labelWidth: Dp = 48.dp,
) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 44.dp).clip(RoundedCornerShape(8.dp)).background(GlassFill).padding(horizontal = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        BandNudge(app.discair.ui.player.PlayerIcons.Remove, lowerLabel, enabled && canLower) { onNudge(-1) }
        Text(
            label, style = MaterialTheme.typography.labelMedium, color = Ink.TextMuted,
            maxLines = 1, modifier = Modifier.widthIn(min = labelWidth).padding(horizontal = 4.dp),
        )
        Slider(
            value = sliderValue, onValueChange = onSlide, valueRange = min..max, steps = steps, enabled = enabled,
            modifier = Modifier.weight(1f).heightIn(min = 32.dp).semantics {
                contentDescription = spokenName
                stateDescription = spokenValue
            },
            thumb = {
                if (LocalPalette.current.brutal) BrutalSliderThumb(enabled) else
                Box(
                    Modifier.size(20.dp).shadow(2.dp, CircleShape).background(Color.White, CircleShape)
                        .border(BorderStroke(1.dp, Color(0x1A000000)), CircleShape),
                )
            },
            track = { state: SliderState ->
                val frac = ((state.value - state.valueRange.start) / (state.valueRange.endInclusive - state.valueRange.start)).coerceIn(0f, 1f)
                if (LocalPalette.current.brutal) BrutalSliderTrack(frac, enabled) else
                Box(Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(3.dp)).background(GlassTrack)) {
                    Box(Modifier.fillMaxWidth(frac).fillMaxHeight().background(if (enabled) Ink.Accent else Ink.AccentDim))
                }
            },
        )
        Box(Modifier.padding(horizontal = 8.dp).width(1.dp).height(16.dp).background(if (LocalPalette.current.light) Ink.EdgeStrong else Color(0x77CCCCCC)))
        Text(
            value, style = MaterialTheme.typography.labelMedium.copy(fontFamily = app.discair.ui.theme.LocalFontPair.current.mono, fontWeight = FontWeight.SemiBold),
            color = Ink.TextMuted, maxLines = 1, textAlign = TextAlign.End,
            modifier = Modifier.widthIn(min = valueWidth),
        )
        BandNudge(app.discair.ui.player.PlayerIcons.Add, raiseLabel, enabled && canRaise) { onNudge(+1) }
    }
}

// Small signs: the glyphs are 14dp inside a 36dp button, so the Hz and dB fit beside them on one line.
@Composable
private fun BandNudge(icon: ImageVector, description: String, enabled: Boolean, onClick: () -> Unit) {
    IconButton(onClick = onClick, enabled = enabled, modifier = Modifier.size(36.dp)) {
        Icon(icon, contentDescription = description, modifier = Modifier.size(14.dp))
    }
}

/** The Brutal themes' switch: a flat track (accent when on), an outlined round knob that slides across, a hard shadow. */
@Composable
private fun BrutalSwitch(checked: Boolean, shape: androidx.compose.ui.graphics.Shape, modifier: Modifier) {
    val knobX by animateDpAsState(if (checked) 40.dp else 0.dp, tween(200), label = "knob")
    val line = themeBorder(BorderStroke(2.dp, Ink.EdgeStrong))
    val knobShape = if (LocalPalette.current.shape?.radius == 0) androidx.compose.ui.graphics.RectangleShape else CircleShape
    Box(
        modifier.size(width = 66.dp, height = 32.dp).brutalShadow(shape).clip(shape)
            .background(if (checked) Ink.Accent else Ink.Surface).border(line, shape),
    ) {
        Box(
            Modifier.padding(4.dp).align(Alignment.CenterStart).offset(x = knobX).size(24.dp)
                .background(if (checked) Color.White else Ink.Text, knobShape).border(line, knobShape),
        )
    }
}
