package app.discair.ui.theme

import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.R

/** Tokens from static/app.css. Dark only; dynamic colour is off (android/DESIGN.md). */
object Ink {
    val Rail = Color(0xFF0F0E0D)
    val Ink = Color(0xFF141211)
    val Surface = Color(0xFF1C1A18)
    val Raised = Color(0xFF252220)
    val Edge = Color(0xFF34302C)
    val EdgeStrong = Color(0xFF787168)
    val Text = Color(0xFFF4EFE6)
    val TextMuted = Color(0xFFB4AC9F)
    val Accent = Color(0xFFF5D33F)
    val AccentDim = Color(0xFF554B26)
    val OnAccent = Color(0xFF141211)
    val ChartRed = Color(0xFFFF5A3C)
    val ChartRedText = Color(0xFFFF7B62)
    val Ok = Color(0xFF86D39B)
    val Caution = Color(0xFFF0A640)
}

val Display = FontFamily(
    Font(R.font.big_shoulders_display_700, FontWeight.Bold),
    Font(R.font.big_shoulders_display_800, FontWeight.ExtraBold),
)
val Body = FontFamily(
    Font(R.font.open_sans_400, FontWeight.Normal),
    Font(R.font.open_sans_500, FontWeight.Medium),
    Font(R.font.open_sans_600, FontWeight.SemiBold),
)
/** Page and section titles, matching the wordmark (web: Peace Sans, -0.085em tracking, 1.05 line height). Single weight. */
val Title = FontFamily(Font(R.font.peace_sans_400, FontWeight.Normal))
private val TitleTracking = (-0.085).em
val Mono = FontFamily(
    Font(R.font.jetbrains_mono_400, FontWeight.Normal),
    Font(R.font.jetbrains_mono_500, FontWeight.Medium),
)

private val colors: ColorScheme = darkColorScheme(
    primary = Ink.Accent,
    onPrimary = Ink.OnAccent,
    primaryContainer = Ink.AccentDim,
    onPrimaryContainer = Ink.Text,
    secondary = Ink.ChartRedText,
    secondaryContainer = Ink.AccentDim,
    onSecondaryContainer = Ink.Text,
    onSecondary = Ink.OnAccent,
    background = Ink.Ink,
    onBackground = Ink.Text,
    surface = Ink.Surface,
    onSurface = Ink.Text,
    surfaceVariant = Ink.Raised,
    onSurfaceVariant = Ink.TextMuted,
    surfaceContainer = Ink.Surface,
    surfaceContainerHigh = Ink.Raised,
    outline = Ink.EdgeStrong,
    outlineVariant = Ink.Edge,
    error = Ink.ChartRedText,
    onError = Ink.OnAccent,
)

private fun style(family: FontFamily, weight: FontWeight, size: Int, line: Int) =
    TextStyle(fontFamily = family, fontWeight = weight, fontSize = size.sp, lineHeight = line.sp)

private fun titleStyle(size: Int) = TextStyle(
    fontFamily = Title, fontWeight = FontWeight.Normal, fontSize = size.sp,
    lineHeight = (size * 1.05f).sp, letterSpacing = TitleTracking,
)

private val type = Typography(
    headlineLarge = titleStyle(32),
    headlineMedium = titleStyle(28),
    titleLarge = titleStyle(22),
    titleMedium = style(Body, FontWeight.SemiBold, 16, 24),
    titleSmall = style(Body, FontWeight.Medium, 14, 20),
    bodyLarge = style(Body, FontWeight.Normal, 16, 24),
    bodyMedium = style(Body, FontWeight.Normal, 14, 20),
    bodySmall = style(Body, FontWeight.Normal, 12, 16),
    labelLarge = style(Body, FontWeight.SemiBold, 14, 20),
    labelMedium = style(Mono, FontWeight.Medium, 12, 16),
    labelSmall = style(Mono, FontWeight.Normal, 11, 16),
)

@Composable
fun DiscairTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = colors, typography = type, content = content)
}
