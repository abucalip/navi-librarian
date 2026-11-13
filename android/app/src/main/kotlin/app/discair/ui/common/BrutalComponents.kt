@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package app.discair.ui.common

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialogDefaults
import androidx.compose.material3.ButtonColors
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ButtonElevation
import androidx.compose.material3.SelectableChipColors
import androidx.compose.material3.SelectableChipElevation
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.IconButtonColors
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.SheetState
import androidx.compose.material3.SliderColors
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.SliderState
import androidx.compose.material3.SnackbarData
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextFieldColors
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.layout.heightIn
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.window.PopupProperties
import androidx.compose.ui.unit.DpOffset
import androidx.compose.foundation.ScrollState
import androidx.compose.foundation.rememberScrollState
import app.discair.ui.theme.Ink
import app.discair.ui.theme.LocalPalette
import app.discair.ui.theme.Palette
import app.discair.ui.theme.brutalOutline
import app.discair.ui.theme.brutalShadow
import app.discair.ui.theme.themeShape
import app.discair.ui.theme.accentText

/*
 * The Neobrut component layer of the app (neobrut.md, after neobrutalism.com): a thick outline, a small radius, a hard
 * shadow, and a press that drops the control into its shadow. These composables have the names and parameters of
 * Material's, so a call site only changes its import. On a Classic theme every one passes straight through to Material,
 * so Classic themes look exactly as before; on a Brutal theme they draw the Neobrut version.
 */

/** The small-shadow scale of buttons and icon buttons. Soft Brut draws its full 3dp shadow on every control (proposal section 3). */
private val Palette.sm: Float get() = if (layout == app.discair.ui.theme.Layout.CoverStack) 1f else 0.6f

// ---------------------------------------------------------------- buttons

private enum class BrutKind { Primary, Outlined, Tonal }

@Composable
private fun brutColors(kind: BrutKind): ButtonColors {
    val p = LocalPalette.current
    return when (kind) {
        BrutKind.Primary -> ButtonDefaults.buttonColors(containerColor = p.accent, contentColor = p.onAccent, disabledContainerColor = p.raised, disabledContentColor = p.textMuted)
        BrutKind.Outlined -> ButtonDefaults.buttonColors(containerColor = p.surface, contentColor = p.text, disabledContainerColor = p.raised, disabledContentColor = p.textMuted)
        BrutKind.Tonal -> ButtonDefaults.buttonColors(containerColor = p.accent2, contentColor = Color.Black, disabledContainerColor = p.raised, disabledContentColor = p.textMuted)
    }
}

/** The press state of a Neobrut control: it drops by the shadow offset and the shadow disappears. */
@Composable
private fun pressOffset(source: MutableInteractionSource, enabled: Boolean): Dp {
    val pressed by source.collectIsPressedAsState()
    val p = LocalPalette.current
    return if (pressed && enabled) ((p.shape?.shadow ?: 0f) * p.sm).dp else 0.dp
}

@Composable
private fun BrutalButtonBody(
    kind: BrutKind, onClick: () -> Unit, modifier: Modifier, enabled: Boolean, shape: Shape?, colors: ButtonColors?,
    contentPadding: PaddingValues, interactionSource: MutableInteractionSource?, content: @Composable RowScope.() -> Unit,
) {
    val source = interactionSource ?: remember { MutableInteractionSource() }
    val drop = pressOffset(source, enabled)
    val s = shape ?: themeShape(8.dp)
    val cs = isCoverStack()
    // Soft Brut: 44dp high, 16dp padding, label Inter 700 14.
    androidx.compose.material3.Button(
        onClick = onClick,
        modifier = modifier.offset { IntOffset(drop.roundToPx(), drop.roundToPx()) }
            .then(if (cs) Modifier.heightIn(min = 44.dp) else Modifier)
            .then(if (drop == 0.dp && enabled) Modifier.brutalShadow(s, LocalPalette.current.sm) else Modifier),
        enabled = enabled, shape = s, colors = colors ?: brutColors(kind), elevation = null, border = brutalOutline(),
        contentPadding = if (cs && contentPadding == ButtonDefaults.ContentPadding) PaddingValues(horizontal = 16.dp) else contentPadding,
        interactionSource = source,
        content = if (cs) ({ androidx.compose.material3.ProvideTextStyle(LocalTextStyle.current.copy(fontWeight = FontWeight.Bold, fontSize = 14.sp)) { content() } }) else content,
    )
}

@Composable
fun Button(
    onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true, shape: Shape? = null, colors: ButtonColors? = null,
    elevation: ButtonElevation? = ButtonDefaults.buttonElevation(), border: BorderStroke? = null,
    contentPadding: PaddingValues = ButtonDefaults.ContentPadding, interactionSource: MutableInteractionSource? = null,
    content: @Composable RowScope.() -> Unit,
) {
    if (isFlow()) { FlowButton(FlowKind.Primary, onClick, modifier, enabled, shape, colors, contentPadding, interactionSource, content); return }
    if (!LocalPalette.current.brutal) {
        androidx.compose.material3.Button(onClick, modifier, enabled, shape ?: ButtonDefaults.shape, colors ?: ButtonDefaults.buttonColors(), elevation, border, contentPadding, interactionSource, content)
        return
    }
    BrutalButtonBody(BrutKind.Primary, onClick, modifier, enabled, shape, colors, contentPadding, interactionSource, content)
}

@Composable
fun OutlinedButton(
    onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true, shape: Shape? = null, colors: ButtonColors? = null,
    elevation: ButtonElevation? = null, border: BorderStroke? = null,
    contentPadding: PaddingValues = ButtonDefaults.ContentPadding, interactionSource: MutableInteractionSource? = null,
    content: @Composable RowScope.() -> Unit,
) {
    if (isFlow()) { FlowButton(FlowKind.Tonal, onClick, modifier, enabled, shape, colors, contentPadding, interactionSource, content); return }
    if (!LocalPalette.current.brutal) {
        androidx.compose.material3.OutlinedButton(onClick, modifier, enabled, shape ?: ButtonDefaults.outlinedShape, colors ?: ButtonDefaults.outlinedButtonColors(), elevation, border ?: ButtonDefaults.outlinedButtonBorder(enabled), contentPadding, interactionSource, content)
        return
    }
    BrutalButtonBody(BrutKind.Outlined, onClick, modifier, enabled, shape, colors, contentPadding, interactionSource, content)
}

@Composable
fun FilledTonalButton(
    onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true, shape: Shape? = null, colors: ButtonColors? = null,
    elevation: ButtonElevation? = ButtonDefaults.filledTonalButtonElevation(), border: BorderStroke? = null,
    contentPadding: PaddingValues = ButtonDefaults.ContentPadding, interactionSource: MutableInteractionSource? = null,
    content: @Composable RowScope.() -> Unit,
) {
    if (isFlow()) { FlowButton(FlowKind.Tonal, onClick, modifier, enabled, shape, colors, contentPadding, interactionSource, content); return }
    if (!LocalPalette.current.brutal) {
        androidx.compose.material3.FilledTonalButton(onClick, modifier, enabled, shape ?: ButtonDefaults.filledTonalShape, colors ?: ButtonDefaults.filledTonalButtonColors(), elevation, border, contentPadding, interactionSource, content)
        return
    }
    BrutalButtonBody(BrutKind.Tonal, onClick, modifier, enabled, shape, colors, contentPadding, interactionSource, content)
}

@Composable
fun FilledIconButton(
    onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true, shape: Shape? = null, colors: IconButtonColors? = null,
    interactionSource: MutableInteractionSource? = null, content: @Composable () -> Unit,
) {
    val p = LocalPalette.current
    if (!p.brutal) {
        androidx.compose.material3.FilledIconButton(onClick, modifier, enabled, shape ?: IconButtonDefaults.filledShape, colors ?: IconButtonDefaults.filledIconButtonColors(), interactionSource, content)
        return
    }
    val source = interactionSource ?: remember { MutableInteractionSource() }
    val drop = pressOffset(source, enabled)
    val s = shape ?: themeShape(10.dp)
    androidx.compose.material3.FilledIconButton(
        onClick = onClick,
        modifier = modifier.offset { IntOffset(drop.roundToPx(), drop.roundToPx()) }
            .then(if (drop == 0.dp && enabled) Modifier.brutalShadow(s, p.sm) else Modifier)
            .border(brutalOutline(), s),
        enabled = enabled, shape = s,
        colors = colors ?: IconButtonDefaults.filledIconButtonColors(containerColor = p.accent, contentColor = p.onAccent),
        interactionSource = source, content = content,
    )
}

@Composable
fun OutlinedIconButton(
    onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true, shape: Shape? = null, colors: IconButtonColors? = null,
    border: BorderStroke? = null, interactionSource: MutableInteractionSource? = null, content: @Composable () -> Unit,
) {
    val p = LocalPalette.current
    if (!p.brutal) {
        androidx.compose.material3.OutlinedIconButton(onClick, modifier, enabled, shape ?: IconButtonDefaults.outlinedShape, colors ?: IconButtonDefaults.outlinedIconButtonColors(), border ?: IconButtonDefaults.outlinedIconButtonBorder(enabled), interactionSource, content)
        return
    }
    val source = interactionSource ?: remember { MutableInteractionSource() }
    val drop = pressOffset(source, enabled)
    val s = shape ?: themeShape(10.dp)
    androidx.compose.material3.OutlinedIconButton(
        onClick = onClick,
        modifier = modifier.offset { IntOffset(drop.roundToPx(), drop.roundToPx()) }
            .then(if (drop == 0.dp && enabled) Modifier.brutalShadow(s, p.sm) else Modifier),
        enabled = enabled, shape = s,
        colors = colors ?: IconButtonDefaults.outlinedIconButtonColors(containerColor = p.surface, contentColor = p.text),
        border = brutalOutline(), interactionSource = source, content = content,
    )
}

// ---------------------------------------------------------------- input field

/** A text field: a classic Material outlined field, or on a Brutal theme an outlined box with a shadow-sm whose outline thickens on focus. */
@Composable
fun OutlinedTextField(
    value: String, onValueChange: (String) -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true, readOnly: Boolean = false,
    textStyle: TextStyle = LocalTextStyle.current, label: @Composable (() -> Unit)? = null, placeholder: @Composable (() -> Unit)? = null,
    leadingIcon: @Composable (() -> Unit)? = null, trailingIcon: @Composable (() -> Unit)? = null,
    supportingText: @Composable (() -> Unit)? = null, isError: Boolean = false,
    visualTransformation: VisualTransformation = VisualTransformation.None, keyboardOptions: KeyboardOptions = KeyboardOptions.Default,
    keyboardActions: KeyboardActions = KeyboardActions.Default, singleLine: Boolean = false,
    maxLines: Int = if (singleLine) 1 else Int.MAX_VALUE, minLines: Int = 1, interactionSource: MutableInteractionSource? = null,
    shape: Shape? = null, colors: TextFieldColors? = null,
) {
    val p = LocalPalette.current
    if (isFlow()) {
        // Flow: a 44dp field of radius 12 filled with `raised`, no outline.
        val clear = Color.Transparent
        androidx.compose.material3.OutlinedTextField(
            value, onValueChange, modifier, enabled, readOnly, textStyle, label, placeholder, leadingIcon, trailingIcon, null, null,
            supportingText, isError, visualTransformation, keyboardOptions, keyboardActions, singleLine, maxLines, minLines,
            interactionSource, shape ?: RoundedCornerShape(12.dp),
            colors ?: androidx.compose.material3.OutlinedTextFieldDefaults.colors(
                focusedContainerColor = p.raised, unfocusedContainerColor = p.raised, disabledContainerColor = p.raised, errorContainerColor = p.raised,
                focusedBorderColor = if (isError) p.chartRedText else p.accent, unfocusedBorderColor = if (isError) p.chartRedText else clear, disabledBorderColor = clear, errorBorderColor = p.chartRedText,
            ),
        )
        return
    }
    if (!p.brutal) {
        androidx.compose.material3.OutlinedTextField(
            value, onValueChange, modifier, enabled, readOnly, textStyle, label, placeholder, leadingIcon, trailingIcon, null, null,
            supportingText, isError, visualTransformation, keyboardOptions, keyboardActions, singleLine, maxLines, minLines,
            interactionSource, shape ?: androidx.compose.material3.OutlinedTextFieldDefaults.shape,
            colors ?: androidx.compose.material3.OutlinedTextFieldDefaults.colors(),
        )
        return
    }
    val source = interactionSource ?: remember { MutableInteractionSource() }
    val focused by source.collectIsFocusedAsState()
    val s = shape ?: themeShape(8.dp)
    val outline = (p.shape?.outline ?: 2f).dp
    val edge = if (isError) Ink.ChartRedText else p.edgeStrong
    val clear = Color.Transparent
    // The label sits above the box: a floating label would land on the thick outline and vanish into it. The caller's
    // modifier (padding, focus requester) goes on the column; a focus request reaches the field inside it.
    Column(modifier) {
        if (label != null) Box(Modifier.padding(bottom = 8.dp)) {
            CompositionLocalProvider(LocalContentColor provides p.text) {
                androidx.compose.material3.ProvideTextStyle(MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold), label)
            }
        }
    androidx.compose.material3.OutlinedTextField(
        value, onValueChange,
        Modifier.fillMaxWidth().brutalShadow(s, if (isCoverStack()) 1f else 0.5f).border(BorderStroke(if (focused) outline + 1.dp else outline, edge), s),
        enabled, readOnly, textStyle, null, placeholder ?: label, leadingIcon, trailingIcon, null, null, supportingText, isError,
        visualTransformation, keyboardOptions, keyboardActions, singleLine, maxLines, minLines, source, s,
        colors ?: androidx.compose.material3.OutlinedTextFieldDefaults.colors(
            focusedBorderColor = clear, unfocusedBorderColor = clear, errorBorderColor = clear, disabledBorderColor = clear,
            focusedContainerColor = p.surface, unfocusedContainerColor = p.surface, errorContainerColor = p.surface, disabledContainerColor = p.raised,
            focusedTextColor = p.text, unfocusedTextColor = p.text, cursorColor = p.text,
            focusedLabelColor = p.text, unfocusedLabelColor = p.textMuted,
        ),
    )
    }
}

private val LocalTextStyle get() = androidx.compose.material3.LocalTextStyle

// ---------------------------------------------------------------- dropdown menu

/** A dropdown menu: an outlined panel with a hard shadow on a Brutal theme. */
@Composable
fun DropdownMenu(
    expanded: Boolean, onDismissRequest: () -> Unit, modifier: Modifier = Modifier, offset: DpOffset = DpOffset(0.dp, 0.dp),
    scrollState: ScrollState = rememberScrollState(), properties: PopupProperties = PopupProperties(focusable = true),
    content: @Composable ColumnScope.() -> Unit,
) {
    val p = LocalPalette.current
    if (!p.brutal) {
        androidx.compose.material3.DropdownMenu(expanded, onDismissRequest, modifier, offset, scrollState, properties, content = content)
        return
    }
    val s = themeShape(8.dp)
    val sh = ((p.shape?.shadow ?: 0f)).dp
    androidx.compose.material3.DropdownMenu(
        expanded, onDismissRequest, modifier, offset, scrollState, properties,
        shape = RectangleShape, containerColor = Color.Transparent, tonalElevation = 0.dp, shadowElevation = 0.dp, border = null,
    ) {
        // The panel (outline, background, shadow) is drawn here so the shadow sits inside the popup window.
        Box(Modifier.padding(end = sh, bottom = sh)) {
            Column(Modifier.brutalShadow(s).clip(s).background(p.surface).border(brutalOutline(), s).padding(vertical = 4.dp), content = content)
        }
    }
}

// ---------------------------------------------------------------- alert dialog

/** An alert dialog: on a Brutal theme an outlined card with a hard shadow, a bold title and a footer band holding the actions. */
@Composable
fun AlertDialog(
    onDismissRequest: () -> Unit, confirmButton: @Composable () -> Unit, modifier: Modifier = Modifier,
    dismissButton: @Composable (() -> Unit)? = null, icon: @Composable (() -> Unit)? = null,
    title: @Composable (() -> Unit)? = null, text: @Composable (() -> Unit)? = null, shape: Shape? = null,
    containerColor: Color? = null, properties: DialogProperties = DialogProperties(),
) {
    val p = LocalPalette.current
    if (!p.brutal) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest, confirmButton, modifier, dismissButton, icon, title, text, shape ?: AlertDialogDefaults.shape,
            containerColor ?: AlertDialogDefaults.containerColor, properties = properties,
        )
        return
    }
    val s = shape ?: themeShape(10.dp)
    val sh = ((p.shape?.shadow ?: 0f)).dp
    androidx.compose.ui.window.Dialog(onDismissRequest = onDismissRequest, properties = properties) {
        Box(modifier.padding(end = sh, bottom = sh)) {
            Column(Modifier.widthIn(max = 360.dp).brutalShadow(s).clip(s).background(containerColor ?: p.surface).border(brutalOutline(), s)) {
                Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    icon?.invoke()
                    title?.let { ProvideTextStyle(MaterialTheme.typography.titleLarge) { CompositionLocalProvider(LocalContentColor provides p.text) { it() } } }
                    text?.let { ProvideTextStyle(MaterialTheme.typography.bodyMedium) { CompositionLocalProvider(LocalContentColor provides p.textMuted) { it() } } }
                }
                // The footer band: a rule, then the actions on the raised ground (neobrutalism.com's border-t-2 bg-muted/50).
                Box(Modifier.fillMaxWidth().height((p.shape?.outline ?: 2f).dp).background(p.edgeStrong))
                Row(Modifier.fillMaxWidth().background(p.raised).padding(horizontal = 16.dp, vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.End), verticalAlignment = Alignment.CenterVertically) {
                    dismissButton?.invoke()
                    confirmButton()
                }
            }
        }
    }
}

@Composable
private fun ProvideTextStyle(style: TextStyle, content: @Composable () -> Unit) = androidx.compose.material3.ProvideTextStyle(style, content)

// ---------------------------------------------------------------- slider

/** A corner that never grows past [maxDp]: controls inside a rounded theme stay near-square (square on a theme with radius 0). */
@Composable
internal fun smallShape(maxDp: Int): Shape {
    val r = minOf(LocalPalette.current.shape?.radius ?: 0f, maxDp.toFloat())
    return if (r == 0f) RectangleShape else RoundedCornerShape(r.dp)
}

/** The Neobrut slider thumb: a square with an outline and a shadow-sm. */
@Composable
fun BrutalSliderThumb(enabled: Boolean = true) {
    val p = LocalPalette.current
    val s = smallShape(2)
    Box(Modifier.size(22.dp).brutalShadow(s, 0.5f).background(if (enabled) p.accent else p.raised, s).border(brutalOutline(), s))
}

/** The Neobrut slider track: an outlined bar with a solid fill. */
@Composable
fun BrutalSliderTrack(fraction: Float, enabled: Boolean = true) {
    val p = LocalPalette.current
    val s = smallShape(3)
    Box(Modifier.fillMaxWidth().height(14.dp).clip(s).background(p.surface).border(brutalOutline(), s)) {
        Box(Modifier.fillMaxWidth(fraction.coerceIn(0f, 1f)).fillMaxHeight().background(if (enabled) p.accent else p.raised))
    }
}

@Composable
fun Slider(
    value: Float, onValueChange: (Float) -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true,
    valueRange: ClosedFloatingPointRange<Float> = 0f..1f, steps: Int = 0, onValueChangeFinished: (() -> Unit)? = null,
    colors: SliderColors = SliderDefaults.colors(), interactionSource: MutableInteractionSource = remember { MutableInteractionSource() },
) {
    if (!LocalPalette.current.brutal) {
        androidx.compose.material3.Slider(value, onValueChange, modifier, enabled, valueRange, steps, onValueChangeFinished, colors, interactionSource)
        return
    }
    androidx.compose.material3.Slider(
        value = value, onValueChange = onValueChange, modifier = modifier, enabled = enabled, valueRange = valueRange,
        onValueChangeFinished = onValueChangeFinished, colors = colors, interactionSource = interactionSource, steps = steps,
        thumb = { BrutalSliderThumb(enabled) },
        track = { state: SliderState ->
            val frac = ((state.value - state.valueRange.start) / (state.valueRange.endInclusive - state.valueRange.start)).coerceIn(0f, 1f)
            BrutalSliderTrack(frac, enabled)
        },
    )
}

// ---------------------------------------------------------------- progress

/** A determinate progress bar: an outlined track and a solid fill on a Brutal theme. */
@Composable
fun LinearProgressIndicator(
    progress: () -> Float, modifier: Modifier = Modifier, color: Color = ProgressIndicatorDefaultsColor(), trackColor: Color = ProgressIndicatorDefaultsTrack(),
) {
    if (isFlow()) { FlowProgress(progress(), modifier); return }
    if (!LocalPalette.current.brutal) {
        androidx.compose.material3.LinearProgressIndicator(progress, modifier, color, trackColor)
        return
    }
    BrutalSliderTrackBar(progress(), modifier)
}

@Composable
fun LinearProgressIndicator(modifier: Modifier = Modifier, color: Color = ProgressIndicatorDefaultsColor(), trackColor: Color = ProgressIndicatorDefaultsTrack()) {
    if (isFlow()) { androidx.compose.material3.LinearProgressIndicator(modifier.height(4.dp).clip(RoundedCornerShape(2.dp)), LocalPalette.current.accent, LocalPalette.current.raised); return }
    if (!LocalPalette.current.brutal) {
        androidx.compose.material3.LinearProgressIndicator(modifier, color, trackColor)
        return
    }
    // Indeterminate: an outlined track with a half-width block (no motion, so nothing animates under reduced motion).
    BrutalSliderTrackBar(0.5f, modifier)
}

@Composable private fun ProgressIndicatorDefaultsColor() = MaterialTheme.colorScheme.primary
@Composable private fun ProgressIndicatorDefaultsTrack() = MaterialTheme.colorScheme.surfaceVariant

@Composable
private fun BrutalSliderTrackBar(fraction: Float, modifier: Modifier) {
    val p = LocalPalette.current
    val cs = isCoverStack()
    val s = if (cs) RoundedCornerShape(6.dp) else smallShape(3)
    Box(modifier.height(if (cs) 10.dp else 14.dp).clip(s).background(p.surface).border(brutalOutline(), s)) {
        val f = fraction.coerceIn(0f, 1f)
        Box(
            Modifier.fillMaxWidth(f).fillMaxHeight().background(p.accent).then(
                // Soft Brut closes the fill with a rule, so a part-full bar reads as a block.
                if (cs && f > 0f && f < 1f) Modifier.drawBehind { drawRect(p.edgeStrong, Offset(size.width - 1.5.dp.toPx(), 0f), Size(1.5.dp.toPx(), size.height)) } else Modifier,
            ),
        )
    }
}

// ---------------------------------------------------------------- toast

/** The snackbar host: on a Brutal theme each toast is an outlined card with a hard shadow and a pressable action. */
@Composable
fun SnackbarHost(hostState: SnackbarHostState, modifier: Modifier = Modifier) {
    if (isFlow()) { androidx.compose.material3.SnackbarHost(hostState, modifier) { data -> FlowSnackbar(data) }; return }
    if (!LocalPalette.current.brutal) {
        androidx.compose.material3.SnackbarHost(hostState, modifier)
        return
    }
    androidx.compose.material3.SnackbarHost(hostState, modifier) { data -> BrutalSnackbar(data) }
}

@Composable
private fun BrutalSnackbar(data: SnackbarData) {
    val p = LocalPalette.current
    val s = themeShape(8.dp)
    val sh = ((p.shape?.shadow ?: 0f)).dp
    if (isCoverStack()) {
        // Soft Brut: an ink toast with page-coloured text and an underlined Undo (mockup: soft-brut/sheets frame 3).
        Box(Modifier.padding(start = 12.dp, top = 8.dp, end = 12.dp + sh, bottom = 8.dp + sh)) {
            Row(
                Modifier.fillMaxWidth().brutalShadow(s).clip(s).background(p.text).border(brutalOutline(), s).padding(start = 14.dp, end = 4.dp),
                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text(data.visuals.message, Modifier.weight(1f).padding(vertical = 12.dp), color = p.ink, style = MaterialTheme.typography.bodyMedium)
                data.visuals.actionLabel?.let { label ->
                    Box(Modifier.heightIn(min = 48.dp).clickable(role = Role.Button, onClick = { data.performAction() }).padding(horizontal = 12.dp), contentAlignment = Alignment.Center) {
                        Text(label, color = p.ink, fontWeight = FontWeight.SemiBold, textDecoration = androidx.compose.ui.text.style.TextDecoration.Underline, style = MaterialTheme.typography.labelLarge)
                    }
                }
            }
        }
        return
    }
    Box(Modifier.padding(start = 16.dp, top = 16.dp, end = 16.dp + sh, bottom = 16.dp + sh)) {
        Row(
            Modifier.fillMaxWidth().brutalShadow(s).clip(s).background(p.surface).border(brutalOutline(), s).padding(start = 16.dp, top = 8.dp, bottom = 8.dp, end = 8.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text(data.visuals.message, Modifier.weight(1f), color = p.text, style = MaterialTheme.typography.bodyMedium)
            data.visuals.actionLabel?.let { label -> Button(onClick = { data.performAction() }) { Text(label, fontWeight = FontWeight.Bold) } }
        }
    }
}

// ---------------------------------------------------------------- bottom sheet

/** A modal bottom sheet: outlined (a rule along its edge) on a Brutal theme. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ModalBottomSheet(
    onDismissRequest: () -> Unit, modifier: Modifier = Modifier, sheetState: SheetState = rememberModalBottomSheetState(),
    shape: Shape? = null, containerColor: Color? = null, content: @Composable ColumnScope.() -> Unit,
) {
    val p = LocalPalette.current
    if (isFlow()) {
        // Flow: a white sheet with a 24dp top radius and a short grey handle (mockup: flow/sheets).
        androidx.compose.material3.ModalBottomSheet(
            onDismissRequest, modifier, sheetState, shape = shape ?: RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp),
            containerColor = containerColor ?: p.surface,
            dragHandle = { Box(Modifier.padding(vertical = 10.dp).size(width = 36.dp, height = 4.dp).clip(RoundedCornerShape(2.dp)).background(p.chartGrid)) },
            content = content,
        )
        return
    }
    if (!p.brutal) {
        androidx.compose.material3.ModalBottomSheet(
            onDismissRequest, modifier, sheetState, shape = shape ?: androidx.compose.material3.BottomSheetDefaults.ExpandedShape,
            containerColor = containerColor ?: androidx.compose.material3.BottomSheetDefaults.ContainerColor, content = content,
        )
        return
    }
    if (isCoverStack()) {
        // Soft Brut: an outlined surface with a 14dp top radius, no shadow, and a short grey handle (mockup: soft-brut/sheets).
        val top = shape ?: RoundedCornerShape(topStart = CoverStackRules.barRadius(p).dp, topEnd = CoverStackRules.barRadius(p).dp)
        androidx.compose.material3.ModalBottomSheet(
            onDismissRequest, modifier.border(BorderStroke(CoverStackRules.outline(p).dp, p.edgeStrong), top), sheetState, shape = top,
            containerColor = containerColor ?: p.surface,
            dragHandle = { Box(Modifier.padding(vertical = 10.dp).size(width = 36.dp, height = 4.dp).clip(RoundedCornerShape(2.dp)).background(p.chartGrid)) },
            content = content,
        )
        return
    }
    val top = shape ?: (p.shape?.radius ?: 0f).let { r -> if (r == 0f) RectangleShape else RoundedCornerShape(topStart = r.dp, topEnd = r.dp) }
    androidx.compose.material3.ModalBottomSheet(
        onDismissRequest, modifier, sheetState, shape = top,
        containerColor = containerColor ?: p.surface,
        // A full-width rule is the sheet's edge, with a short thick bar as the handle.
        dragHandle = {
            Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
                Box(Modifier.fillMaxWidth().height((p.shape?.outline ?: 2f).dp).background(p.edgeStrong))
                Box(Modifier.padding(vertical = 8.dp).size(width = 40.dp, height = 8.dp).clip(smallShape(2)).background(p.text))
            }
        },
        content = content,
    )
}

// ---------------------------------------------------------------- chip / tag

/** A filter chip: a tag (badge) on a Brutal theme: outlined, bold, shadow-sm, the chosen one filled with the accent. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FilterChip(
    selected: Boolean, onClick: () -> Unit, label: @Composable () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true,
    leadingIcon: @Composable (() -> Unit)? = null, trailingIcon: @Composable (() -> Unit)? = null, shape: Shape? = null,
    colors: SelectableChipColors? = null, elevation: SelectableChipElevation? = null, border: BorderStroke? = null, interactionSource: MutableInteractionSource? = null,
) {
    val p = LocalPalette.current
    if (isFlow()) {
        // Flow: a 34dp capsule on `raised`; the chosen one is filled with the text colour.
        val pill = RoundedCornerShape(17.dp)
        Row(
            modifier.heightIn(min = 34.dp).clip(pill).background(if (selected) p.text else p.raised)
                .clickable(enabled = enabled, role = Role.Checkbox, onClick = onClick).padding(horizontal = 14.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            leadingIcon?.invoke()
            CompositionLocalProvider(LocalContentColor provides if (selected) p.ink else p.text) {
                androidx.compose.material3.ProvideTextStyle(MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Medium, fontSize = 14.sp), label)
            }
            trailingIcon?.invoke()
        }
        return
    }
    if (!p.brutal) {
        androidx.compose.material3.FilterChip(
            selected, onClick, label, modifier, enabled, leadingIcon, trailingIcon, shape ?: FilterChipDefaults.shape,
            colors ?: FilterChipDefaults.filterChipColors(), elevation ?: FilterChipDefaults.filterChipElevation(), border ?: FilterChipDefaults.filterChipBorder(enabled, selected), interactionSource,
        )
        return
    }
    if (isCoverStack()) {
        // Soft Brut: a 36dp pill, outlined, no shadow; the chosen one is filled with the accent.
        val pill = RoundedCornerShape(50)
        Row(
            modifier.heightIn(min = 36.dp).clip(pill).background(if (selected) p.accent else p.surface).border(brutalOutline(), pill)
                .clickable(enabled = enabled, role = Role.Checkbox, onClick = onClick).padding(horizontal = 13.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            leadingIcon?.invoke()
            CompositionLocalProvider(LocalContentColor provides if (selected) p.onAccent else p.text) {
                androidx.compose.material3.ProvideTextStyle(MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.SemiBold, fontSize = 13.sp), label)
            }
            trailingIcon?.invoke()
        }
        return
    }
    val s = shape ?: themeShape(8.dp)
    val source = interactionSource ?: remember { MutableInteractionSource() }
    val drop = pressOffset(source, enabled)
    Row(
        modifier.offset { IntOffset(drop.roundToPx(), drop.roundToPx()) }
            .then(if (drop == 0.dp) Modifier.brutalShadow(s, 0.5f) else Modifier)
            .clip(s).background(if (selected) p.accent else p.surface).border(brutalOutline(), s)
            .clickable(enabled = enabled, interactionSource = source, indication = null, role = Role.Checkbox, onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        leadingIcon?.invoke()
        CompositionLocalProvider(LocalContentColor provides if (selected) p.onAccent else p.text) {
            androidx.compose.material3.ProvideTextStyle(MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold), label)
        }
        trailingIcon?.invoke()
    }
}

/** A small tag (a badge): outlined, bold, shadow-sm, on the accent (primary) or the raised ground (secondary). */
@Composable
fun BrutalTag(modifier: Modifier = Modifier, primary: Boolean = true, content: @Composable () -> Unit) {
    val p = LocalPalette.current
    val cs = isCoverStack()
    val s = if (cs) RoundedCornerShape(6.dp) else themeShape(4.dp)
    Box(
        modifier.then(if (cs) Modifier else Modifier.brutalShadow(s, 0.4f)).clip(s).background(if (primary) p.accent else p.raised).border(brutalOutline(), s)
            .padding(horizontal = 8.dp, vertical = 4.dp),
        contentAlignment = Alignment.Center,
    ) { CompositionLocalProvider(LocalContentColor provides if (primary) p.onAccent else p.text) { content() } }
}

// ---------------------------------------------------------------- square icon button (the player)

/**
 * The square icon button of the Neobrut player (after the owner's reference): a [surface] square with an outline and a hard
 * shadow; [selected] or [primary] fill it with the accent. It presses down into its shadow. The icon takes the content colour.
 */
@Composable
fun BrutalIconButton(
    onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true, selected: Boolean = false, primary: Boolean = false,
    content: @Composable () -> Unit,
) {
    val p = LocalPalette.current
    val s = smallShape(6)
    val source = remember { MutableInteractionSource() }
    val drop = pressOffset(source, enabled)
    val filled = selected || primary
    val shadowScale = if (primary) 1f else p.sm
    val fill = if (!enabled) p.raised else if (filled) p.accent else p.surface
    Box(
        modifier.offset { IntOffset(drop.roundToPx(), drop.roundToPx()) }
            .then(if (drop == 0.dp && enabled) Modifier.brutalShadow(s, shadowScale) else Modifier)
            .clip(s).background(fill).border(brutalOutline(), s)
            .clickable(enabled = enabled, interactionSource = source, indication = null, role = Role.Button, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        CompositionLocalProvider(LocalContentColor provides if (!enabled) p.textMuted else if (filled) p.onAccent else p.text) { content() }
    }
}

/** A player icon button: Material's on a Classic theme, the square Neobrut one on a Brutal theme. */
@Composable
fun PlayerIconButton(
    onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true, selected: Boolean = false, content: @Composable () -> Unit,
) {
    if (!LocalPalette.current.brutal) {
        androidx.compose.material3.IconButton(onClick, modifier, enabled, content = content)
        return
    }
    BrutalIconButton(onClick, modifier, enabled, selected, content = content)
}


// ---------------------------------------------------------------- Flow (docs/ANDROID_ART_THEMES_PROPOSAL.md section 4)

private enum class FlowKind { Primary, Tonal }

/** Flow's capsule button, 44dp high: primary is the accent with a white label, secondary is `raised` with an accent label. Inter 600 15. */
@Composable
private fun FlowButton(
    kind: FlowKind, onClick: () -> Unit, modifier: Modifier, enabled: Boolean, shape: Shape?, colors: ButtonColors?,
    contentPadding: PaddingValues, interactionSource: MutableInteractionSource?, content: @Composable RowScope.() -> Unit,
) {
    val p = LocalPalette.current
    val defaults = if (kind == FlowKind.Primary) ButtonDefaults.buttonColors(containerColor = p.accent, contentColor = p.onAccent)
    else ButtonDefaults.buttonColors(containerColor = p.raised, contentColor = p.accentText)
    androidx.compose.material3.Button(
        onClick = onClick, modifier = modifier.heightIn(min = 44.dp), enabled = enabled, shape = shape ?: RoundedCornerShape(22.dp),
        colors = colors ?: defaults, elevation = null,
        contentPadding = if (contentPadding == ButtonDefaults.ContentPadding) PaddingValues(horizontal = 18.dp) else contentPadding,
        interactionSource = interactionSource,
        content = { androidx.compose.material3.ProvideTextStyle(LocalTextStyle.current.copy(fontWeight = FontWeight.SemiBold, fontSize = 15.sp)) { content() } },
    )
}

/** A 4dp rounded bar: `raised` track, accent fill. */
@Composable
private fun FlowProgress(fraction: Float, modifier: Modifier) {
    val p = LocalPalette.current
    val s = RoundedCornerShape(2.dp)
    Box(modifier.height(4.dp).clip(s).background(p.raised)) {
        Box(Modifier.fillMaxWidth(fraction.coerceIn(0f, 1f)).fillMaxHeight().clip(s).background(p.accent))
    }
}

/** Flow's toast: the text colour with page-coloured text, radius 14, level 2 depth and an underlined-free Undo in a light accent. */
@Composable
private fun FlowSnackbar(data: SnackbarData) {
    val p = LocalPalette.current
    val s = RoundedCornerShape(14.dp)
    Box(Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
        Row(
            Modifier.fillMaxWidth().flowDepth(2, s, p).clip(s).background(p.text).padding(start = 14.dp, end = 4.dp),
            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(data.visuals.message, Modifier.weight(1f).padding(vertical = 12.dp), color = p.ink, style = MaterialTheme.typography.bodyMedium)
            data.visuals.actionLabel?.let { label ->
                Box(Modifier.heightIn(min = 48.dp).clickable(role = Role.Button, onClick = { data.performAction() }).padding(horizontal = 12.dp), contentAlignment = Alignment.Center) {
                    Text(label, color = FLOW_SNACK_ACTION, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.labelLarge)
                }
            }
        }
    }
}

/** The Undo colour on the dark toast (flow.css `.snack .lk`). */
private val FLOW_SNACK_ACTION = Color(0xFFFFB48A)
