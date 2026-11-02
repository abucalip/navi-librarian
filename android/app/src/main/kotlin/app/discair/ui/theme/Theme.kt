package app.discair.ui.theme

import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.remember
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import app.discair.R

/**
 * Tokens from static/app.css, read from the current [Palette]. Call sites keep their `Ink.Accent` spelling;
 * the value follows the theme the owner chose (Settings, Appearance). Dynamic colour is off (android/DESIGN.md).
 */
object Ink {
    val Rail: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.rail
    val Ink: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.ink
    val Surface: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.surface
    val Raised: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.raised
    val Edge: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.edge
    val EdgeStrong: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.edgeStrong
    val Text: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.text
    val TextMuted: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.textMuted
    val Accent: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.accent
    val AccentDim: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.accentDim
    val OnAccent: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.onAccent
    val ChartRed: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.chartRed
    val ChartRedText: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.chartRedText
    val Ok: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.ok
    val Caution: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.caution
}

/**
 * Artwork tints are dark (value at most 0.4). On a light theme they would sit under dark text, so a light theme
 * gets a pastel of the same hue ([pastelOf]); dark themes use the tint as it is.
 */
@Composable
@ReadOnlyComposable
fun Color.forTheme(): Color = if (LocalPalette.current.light) pastelOf(this) else this

/**
 * The cover's hue as a light wash: low saturation, high value, then lightened further only until its luminance
 * is at least [MIN_PASTEL_LUMINANCE], which keeps the light themes' muted text above 4.5:1 on any hue (blues and
 * purples need the most lightening).
 */
fun pastelOf(tint: Color): Color {
    val max = maxOf(tint.red, tint.green, tint.blue)
    val min = minOf(tint.red, tint.green, tint.blue)
    val delta = max - min
    val saturation = if (max == 0f) 0f else delta / max
    val hue = when {
        delta == 0f -> 0f
        max == tint.red -> 60f * (((tint.green - tint.blue) / delta).mod(6f))
        max == tint.green -> 60f * ((tint.blue - tint.red) / delta + 2f)
        else -> 60f * ((tint.red - tint.green) / delta + 4f)
    }
    var out = Color.hsv(hue, (saturation * 0.6f).coerceAtMost(0.5f), 0.95f)
    var steps = 0
    while (out.luminance() < MIN_PASTEL_LUMINANCE && steps++ < 20) out = androidx.compose.ui.graphics.lerp(out, Color.White, 0.12f)
    return out
}

const val MIN_PASTEL_LUMINANCE = 0.72f

/**
 * Runs [content] with dark surfaces and light text whatever the theme is. For screens that sit on a tint taken
 * from the playing artwork (the player sheet, the navigation island): artwork tints are dark, so light themes
 * must not put dark text on them.
 */
@Composable
fun OnArtwork(content: @Composable () -> Unit) {
    val current = LocalPalette.current
    val palette = remember(current) { if (current.light) current.overArtwork(Palettes.Night) else current }
    if (palette === current) { content(); return }
    // Material components and plain Text read the colour scheme, not Ink, so swap that too.
    val scheme = remember(palette) { colorScheme(palette) }
    CompositionLocalProvider(LocalPalette provides palette, LocalThemePalette provides current) {
        MaterialTheme(colorScheme = scheme, typography = MaterialTheme.typography, shapes = MaterialTheme.shapes, content = content)
    }
}

/** Runs [content] in the theme the owner chose, undoing [OnArtwork]'s dark override. For sheets that do not sit on artwork. */
@Composable
fun InChosenTheme(content: @Composable () -> Unit) {
    val chosen = LocalThemePalette.current ?: run { content(); return }
    val scheme = remember(chosen) { colorScheme(chosen) }
    CompositionLocalProvider(LocalPalette provides chosen, LocalThemePalette provides null) {
        MaterialTheme(colorScheme = scheme, typography = MaterialTheme.typography, shapes = MaterialTheme.shapes, content = content)
    }
}

@OptIn(androidx.compose.ui.text.ExperimentalTextApi::class)
private fun variable(res: Int, weight: Int) =
    Font(res, FontWeight(weight), variationSettings = FontVariation.Settings(FontVariation.weight(weight)))

/**
 * A title face with a body face. Titles are page and section headings and the rank numerals; everything else
 * is body. Numbers (durations, counts) stay in JetBrains Mono for every pair.
 */
class FontPair(
    val id: String,
    val label: String,
    val titleName: String,
    val bodyName: String,
    val title: FontFamily,
    val titleWeight: FontWeight,
    val titleTracking: TextUnit,
    val titleLineHeight: Float,
    val body: FontFamily,
    val numeral: FontFamily,
    val numeralWeight: FontWeight,
)

object FontPairs {
    /** The original identity (web wordmark and headings). */
    val Discair = FontPair(
        "discair", "Discair", "Peace Sans", "Open Sans",
        title = FontFamily(Font(R.font.peace_sans_400, FontWeight.Normal)), titleWeight = FontWeight.Normal,
        titleTracking = (-0.085).em, titleLineHeight = 1.05f,
        body = FontFamily(
            Font(R.font.open_sans_400, FontWeight.Normal),
            Font(R.font.open_sans_500, FontWeight.Medium),
            Font(R.font.open_sans_600, FontWeight.SemiBold),
        ),
        numeral = FontFamily(
            Font(R.font.big_shoulders_display_700, FontWeight.Bold),
            Font(R.font.big_shoulders_display_800, FontWeight.ExtraBold),
        ),
        numeralWeight = FontWeight.Bold,
    )
    val Editorial = run {
        val title = FontFamily(variable(R.font.fraunces_variable, 800))
        FontPair(
            "editorial", "Editorial", "Fraunces", "Inter",
            title = title, titleWeight = FontWeight.ExtraBold, titleTracking = (-0.02).em, titleLineHeight = 1.15f,
            body = FontFamily(
                variable(R.font.inter_variable, 400), variable(R.font.inter_variable, 500), variable(R.font.inter_variable, 600),
            ),
            numeral = title, numeralWeight = FontWeight.ExtraBold,
        )
    }
    val Bricolage = run {
        val title = FontFamily(variable(R.font.bricolage_grotesque_variable, 800))
        FontPair(
            "bricolage", "Bricolage", "Bricolage Grotesque", "Source Sans 3",
            title = title, titleWeight = FontWeight.ExtraBold, titleTracking = (-0.03).em, titleLineHeight = 1.1f,
            body = FontFamily(
                variable(R.font.source_sans_3_variable, 400), variable(R.font.source_sans_3_variable, 500),
                variable(R.font.source_sans_3_variable, 600),
            ),
            numeral = title, numeralWeight = FontWeight.ExtraBold,
        )
    }
    val Geometric = run {
        val title = FontFamily(variable(R.font.outfit_variable, 800))
        FontPair(
            "geometric", "Geometric", "Outfit", "Manrope",
            title = title, titleWeight = FontWeight.ExtraBold, titleTracking = (-0.03).em, titleLineHeight = 1.1f,
            body = FontFamily(
                variable(R.font.manrope_variable, 400), variable(R.font.manrope_variable, 500), variable(R.font.manrope_variable, 600),
            ),
            numeral = title, numeralWeight = FontWeight.ExtraBold,
        )
    }
    val Transit = run {
        val title = FontFamily(Font(R.font.barlow_condensed_bold, FontWeight.Bold))
        FontPair(
            "transit", "Transit", "Barlow Condensed", "Barlow",
            title = title, titleWeight = FontWeight.Bold, titleTracking = 0.em, titleLineHeight = 1.1f,
            body = FontFamily(
                Font(R.font.barlow_regular, FontWeight.Normal),
                Font(R.font.barlow_medium, FontWeight.Medium),
                Font(R.font.barlow_semibold, FontWeight.SemiBold),
            ),
            numeral = title, numeralWeight = FontWeight.Bold,
        )
    }

    val All: List<FontPair> = listOf(Discair, Editorial, Bricolage, Geometric, Transit)

    fun byId(id: String?): FontPair? = All.firstOrNull { it.id == id }
}

val LocalFontPair = staticCompositionLocalOf { FontPairs.Discair }

val Mono = FontFamily(
    Font(R.font.jetbrains_mono_400, FontWeight.Normal),
    Font(R.font.jetbrains_mono_500, FontWeight.Medium),
)

private fun colorScheme(p: Palette): ColorScheme {
    // The dark themes set exactly the roles the first release set, so Night is unchanged. The light base
    // scheme has lavender-tinted defaults for every other role, so the light themes set those too.
    val dark = darkColorScheme(
        primary = p.accent,
        onPrimary = p.onAccent,
        primaryContainer = p.accentDim,
        onPrimaryContainer = p.text,
        secondary = p.chartRedText,
        secondaryContainer = p.accentDim,
        onSecondaryContainer = p.text,
        onSecondary = p.onAccent,
        background = p.ink,
        onBackground = p.text,
        surface = p.surface,
        onSurface = p.text,
        surfaceVariant = p.raised,
        onSurfaceVariant = p.textMuted,
        surfaceContainer = p.surface,
        surfaceContainerHigh = p.raised,
        outline = p.edgeStrong,
        outlineVariant = p.edge,
        error = p.chartRedText,
        onError = p.onAccent,
    )
    if (!p.light) return dark
    return lightColorScheme(
        primary = p.accent, onPrimary = p.onAccent, primaryContainer = p.accentDim, onPrimaryContainer = p.text,
        secondary = p.chartRedText, onSecondary = Color.White, secondaryContainer = p.accentDim, onSecondaryContainer = p.text,
        tertiary = p.accent, onTertiary = p.onAccent,
        background = p.ink, onBackground = p.text,
        surface = p.surface, onSurface = p.text, surfaceVariant = p.raised, onSurfaceVariant = p.textMuted,
        surfaceTint = p.surface, surfaceDim = p.rail, surfaceBright = p.raised,
        surfaceContainerLowest = p.rail, surfaceContainerLow = p.surface, surfaceContainer = p.surface,
        surfaceContainerHigh = p.raised, surfaceContainerHighest = p.raised,
        inverseSurface = p.text, inverseOnSurface = p.ink, inversePrimary = p.accentDim,
        outline = p.edgeStrong, outlineVariant = p.edge, error = p.chartRedText, onError = Color.White,
    )
}

private fun style(family: FontFamily, weight: FontWeight, size: Int, line: Int) =
    TextStyle(fontFamily = family, fontWeight = weight, fontSize = size.sp, lineHeight = line.sp)

private fun typography(f: FontPair): Typography {
    fun title(size: Int) = TextStyle(
        fontFamily = f.title, fontWeight = f.titleWeight, fontSize = size.sp,
        lineHeight = (size * f.titleLineHeight).sp, letterSpacing = f.titleTracking,
    )
    return Typography(
        headlineLarge = title(32),
        headlineMedium = title(28),
        titleLarge = title(22),
        titleMedium = style(f.body, FontWeight.SemiBold, 16, 24),
        titleSmall = style(f.body, FontWeight.Medium, 14, 20),
        bodyLarge = style(f.body, FontWeight.Normal, 16, 24),
        bodyMedium = style(f.body, FontWeight.Normal, 14, 20),
        bodySmall = style(f.body, FontWeight.Normal, 12, 16),
        labelLarge = style(f.body, FontWeight.SemiBold, 14, 20),
        labelMedium = style(Mono, FontWeight.Medium, 12, 16),
        labelSmall = style(Mono, FontWeight.Normal, 11, 16),
    )
}

@Composable
fun DiscairTheme(palette: Palette = Palettes.Night, fonts: FontPair = FontPairs.Discair, content: @Composable () -> Unit) {
    val scheme = remember(palette) { colorScheme(palette) }
    val type = remember(fonts) { typography(fonts) }
    CompositionLocalProvider(LocalPalette provides palette, LocalFontPair provides fonts) {
        MaterialTheme(colorScheme = scheme, typography = type, content = content)
    }
}
