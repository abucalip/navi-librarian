package app.discair.ui.common

import androidx.compose.animation.animateColorAsState
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
import androidx.compose.ui.graphics.Color
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
import app.discair.ui.theme.Mono

// Dark themes keep the original dark pill; light themes get an inset pill with a pale knob.
private val SwitchOffRing = Color(0xFFEF565F)

/**
 * The app's switch (Uiverse, Admin12121): a dark inset pill with a raised round knob and a ring on the
 * other side. The ring is red while the switch is off and the app's yellow when it is on. It only draws the
 * state; the row that holds it is the toggle, so a tap anywhere on the row works and TalkBack reads one control.
 */
@Composable
fun DiscairSwitch(checked: Boolean, modifier: Modifier = Modifier, enabled: Boolean = true) {
    val knobX by animateDpAsState(if (checked) 32.dp else 0.dp, tween(300), label = "knob")
    val ringX by animateDpAsState(if (checked) 5.dp else 37.dp, tween(300), label = "ringX")
    val ring by animateColorAsState(if (checked) Ink.Accent else SwitchOffRing, tween(300), label = "ring")
    val shape = RoundedCornerShape(50)
    val light = LocalPalette.current.light
    val track = if (light) Ink.Edge else Color(0xFF252220)
    val trackEdge = if (light) Ink.EdgeStrong else Color(0xFF34302C)
    val knob = if (light) listOf(Ink.Surface, Ink.Raised) else listOf(Color(0xFF3A3632), Color(0xFF292624))
    val knobEdge = if (light) Ink.EdgeStrong else Color(0xFF4A4540)
    val inset = if (light) Color(0x33000000) else Color(0x80121110)
    Box(
        modifier.alpha(if (enabled) 1f else 0.45f).size(width = 66.dp, height = 32.dp)
            .clip(shape).background(track).border(BorderStroke(1.dp, trackEdge), shape)
            .padding(4.dp),
    ) {
        // The inset shadow along the top edge.
        Box(Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(inset, Color.Transparent))))
        // Off: a red ring. On: the wordmark's filled yellow square.
        if (checked) Box(Modifier.align(Alignment.CenterStart).offset(x = ringX + 2.dp).size(10.dp).background(Ink.Accent))
        else Box(
            Modifier.align(Alignment.CenterStart).offset(x = ringX).size(14.dp)
                .border(BorderStroke(2.dp, ring), CircleShape),
        )
        Box(
            Modifier.align(Alignment.CenterStart).offset(x = knobX).size(24.dp)
                .shadow(4.dp, CircleShape)
                .background(Brush.verticalGradient(knob), CircleShape)
                .border(BorderStroke(0.5.dp, knobEdge), CircleShape),
        )
    }
}

private val GroupShape = RoundedCornerShape(10.dp)

/**
 * The web's action group: buttons joined in one rounded frame on the surface colour, with a hairline between
 * them (static/app.css .action-group). Put [ActionGroupButton]s and [GroupDivider]s inside.
 */
@Composable
fun ActionGroup(modifier: Modifier = Modifier, content: @Composable RowScope.() -> Unit) {
    Row(
        modifier.height(Target).clip(GroupShape).background(Ink.Surface).border(BorderStroke(1.dp, Ink.EdgeStrong), GroupShape),
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
            .padding(horizontal = 12.dp),
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

private val GlassFill = Color(0xBF242424)
private val GlassTrack = Color(0xFF1A1A1A)

/** The glass card behind a set of bands (Uiverse, byllzz), in the app's palette. */
@Composable
fun GlassCard(modifier: Modifier = Modifier, content: @Composable androidx.compose.foundation.layout.ColumnScope.() -> Unit) {
    val shape = RoundedCornerShape(14.dp)
    androidx.compose.foundation.layout.Column(
        modifier.clip(shape).background(Ink.Surface).border(BorderStroke(1.dp, Color(0x14FFFFFF)), shape).padding(8.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
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
        Modifier.fillMaxWidth().heightIn(min = 44.dp).clip(RoundedCornerShape(8.dp)).background(GlassFill).padding(horizontal = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        BandNudge(app.discair.ui.player.PlayerIcons.Remove, lowerLabel, enabled && canLower) { onNudge(-1) }
        Text(
            label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1, modifier = Modifier.widthIn(min = labelWidth).padding(horizontal = 2.dp),
        )
        Slider(
            value = sliderValue, onValueChange = onSlide, valueRange = min..max, steps = steps, enabled = enabled,
            modifier = Modifier.weight(1f).heightIn(min = 32.dp).semantics {
                contentDescription = spokenName
                stateDescription = spokenValue
            },
            thumb = {
                Box(
                    Modifier.size(20.dp).shadow(2.dp, CircleShape).background(Color.White, CircleShape)
                        .border(BorderStroke(1.dp, Color(0x1A000000)), CircleShape),
                )
            },
            track = { state: SliderState ->
                val frac = ((state.value - state.valueRange.start) / (state.valueRange.endInclusive - state.valueRange.start)).coerceIn(0f, 1f)
                Box(Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(3.dp)).background(GlassTrack)) {
                    Box(Modifier.fillMaxWidth(frac).fillMaxHeight().background(if (enabled) Ink.Accent else Ink.AccentDim))
                }
            },
        )
        Box(Modifier.padding(horizontal = 6.dp).width(1.dp).height(16.dp).background(Color(0x77CCCCCC)))
        Text(
            value, style = MaterialTheme.typography.labelMedium.copy(fontFamily = Mono, fontWeight = FontWeight.SemiBold),
            color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, textAlign = TextAlign.End,
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
