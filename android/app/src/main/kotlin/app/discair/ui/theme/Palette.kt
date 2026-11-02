package app.discair.ui.theme

import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

/**
 * One colour theme. The names are the `Ink` roles from static/app.css; [Ink] reads whichever palette is
 * current. Values are fixed by the owner's choice of 2026-11-02 (android/DESIGN.md, "Themes and fonts").
 */
class Palette(
    val id: String,
    val label: String,
    val light: Boolean,
    val rail: Color,
    val ink: Color,
    val surface: Color,
    val raised: Color,
    val edge: Color,
    val edgeStrong: Color,
    val text: Color,
    val textMuted: Color,
    val accent: Color,
    val accentDim: Color,
    val onAccent: Color,
    val chartRed: Color,
    val chartRedText: Color,
    val ok: Color,
    val caution: Color,
    /** The smallest text contrast this theme is held to by the unit test (WCAG: 4.5 normal text, 7 for AAA). */
    val minTextContrast: Double = 4.5,
) {
    /** A copy that keeps this theme's accent but uses [dark]'s surfaces and text. For screens drawn over artwork. */
    fun overArtwork(dark: Palette) = Palette(
        id, label, false, dark.rail, dark.ink, dark.surface, dark.raised, dark.edge, dark.edgeStrong, dark.text, dark.textMuted,
        accent = if (light) dark.accent else accent, accentDim = if (light) dark.accentDim else accentDim,
        onAccent = if (light) dark.onAccent else onAccent,
        chartRed = dark.chartRed, chartRedText = dark.chartRedText, ok = dark.ok, caution = dark.caution,
    )
}

private fun c(hex: Long) = Color(0xFF000000 or hex)

object Palettes {
    /** The original theme, unchanged from the first release. Always the dark fallback. */
    val Night = Palette(
        "night", "Night", false,
        rail = c(0x0F0E0D), ink = c(0x141211), surface = c(0x1C1A18), raised = c(0x252220), edge = c(0x34302C), edgeStrong = c(0x787168),
        text = c(0xF4EFE6), textMuted = c(0xB4AC9F), accent = c(0xF5D33F), accentDim = c(0x554B26), onAccent = c(0x141211),
        chartRed = c(0xFF5A3C), chartRedText = c(0xFF7B62), ok = c(0x86D39B), caution = c(0xF0A640),
    )

    /** The day theme used when the phone is in light mode and the owner has not chosen another. */
    val Sand = Palette(
        "sand", "Day · Sand", true,
        rail = c(0xE6DCC8), ink = c(0xEFE6D3), surface = c(0xF8F1E1), raised = c(0xE3D8C0), edge = c(0xCFC2A6), edgeStrong = c(0x857758),
        text = c(0x26201A), textMuted = c(0x62563F), accent = c(0xC04A1A), accentDim = c(0xEFC9B0), onAccent = c(0xFFF8EE),
        chartRed = c(0xA8300E), chartRedText = c(0xA8300E), ok = c(0x25693A), caution = c(0x7F4A00),
    )
    val Paper = Palette(
        "paper", "Day · Paper", true,
        rail = c(0xEDE6D8), ink = c(0xF7F2E8), surface = c(0xFFFDF8), raised = c(0xEFE8DA), edge = c(0xDCD2BE), edgeStrong = c(0x8A8070),
        text = c(0x1E1B17), textMuted = c(0x5E564A), accent = c(0x946F00), accentDim = c(0xF3E3A0), onAccent = c(0xFFFFFF),
        chartRed = c(0xC42F14), chartRedText = c(0xC42F14), ok = c(0x25693A), caution = c(0x7F4A00),
    )
    val Mist = Palette(
        "mist", "Day · Mist", true,
        rail = c(0xE4EAF0), ink = c(0xF1F4F8), surface = c(0xFFFFFF), raised = c(0xE7EDF3), edge = c(0xD2DBE5), edgeStrong = c(0x76869A),
        text = c(0x14202E), textMuted = c(0x506174), accent = c(0x1F5FD0), accentDim = c(0xCFE0FA), onAccent = c(0xFFFFFF),
        chartRed = c(0xC03019), chartRedText = c(0xC03019), ok = c(0x1F6A40), caution = c(0x7F4A00),
    )
    val Sage = Palette(
        "sage", "Day · Sage", true,
        rail = c(0xDCE3D6), ink = c(0xEAF0E4), surface = c(0xF7FAF3), raised = c(0xDFE8D8), edge = c(0xC5D2BC), edgeStrong = c(0x6F8566),
        text = c(0x18231A), textMuted = c(0x4F6050), accent = c(0x2F7A43), accentDim = c(0xC6E1C9), onAccent = c(0xFFFFFF),
        chartRed = c(0xB8381C), chartRedText = c(0xB8381C), ok = c(0x1F6A38), caution = c(0x7F4A00),
    )
    val Blush = Palette(
        "blush", "Day · Blush", true,
        rail = c(0xEFE1E3), ink = c(0xF8EEEF), surface = c(0xFFFAFA), raised = c(0xF1E1E4), edge = c(0xE0C9CE), edgeStrong = c(0x92707A),
        text = c(0x2A1A20), textMuted = c(0x6B4F59), accent = c(0xC42A62), accentDim = c(0xF4C9D8), onAccent = c(0xFFFFFF),
        chartRed = c(0xB8301A), chartRedText = c(0xB8301A), ok = c(0x25693A), caution = c(0x7F4A00),
    )

    val Amoled = Palette(
        "amoled", "Midnight · AMOLED", false,
        rail = c(0x000000), ink = c(0x000000), surface = c(0x0D0F14), raised = c(0x171A22), edge = c(0x262B36), edgeStrong = c(0x6C7686),
        text = c(0xEEF2F8), textMuted = c(0x9AA4B5), accent = c(0x6FA8FF), accentDim = c(0x1E3358), onAccent = c(0x04101F),
        chartRed = c(0xFF5A3C), chartRedText = c(0xFF8470), ok = c(0x6FD39A), caution = c(0xF0A640),
    )
    val Forest = Palette(
        "forest", "Forest", false,
        rail = c(0x0B100D), ink = c(0x0F1511), surface = c(0x162019), raised = c(0x1E2B22), edge = c(0x2C3C31), edgeStrong = c(0x6E8574),
        text = c(0xEAF2E7), textMuted = c(0xA3B5A6), accent = c(0xBDE35A), accentDim = c(0x3C4C1F), onAccent = c(0x0F1511),
        chartRed = c(0xFF5A3C), chartRedText = c(0xFF8A6E), ok = c(0x8EE0A6), caution = c(0xF0A640),
    )
    val Ocean = Palette(
        "ocean", "Ocean", false,
        rail = c(0x060E10), ink = c(0x0A1417), surface = c(0x102024), raised = c(0x17302F), edge = c(0x244244), edgeStrong = c(0x5F8A8A),
        text = c(0xE6F4F2), textMuted = c(0x9DBDBA), accent = c(0x4FE0C8), accentDim = c(0x17504A), onAccent = c(0x03201C),
        chartRed = c(0xFF5A3C), chartRedText = c(0xFF8A70), ok = c(0x7FE0A0), caution = c(0xF0A640),
    )
    val Ember = Palette(
        "ember", "Ember", false,
        rail = c(0x0E0907), ink = c(0x150E0B), surface = c(0x1F1511), raised = c(0x2B1D17), edge = c(0x42302A), edgeStrong = c(0x8C7066),
        text = c(0xF7EBE4), textMuted = c(0xBFA89C), accent = c(0xFF8A3D), accentDim = c(0x5A3016), onAccent = c(0x1A0C04),
        chartRed = c(0xFF5A3C), chartRedText = c(0xFF8F78), ok = c(0x8ED7A0), caution = c(0xF0A640),
    )
    val Graphite = Palette(
        "graphite", "Graphite", false,
        rail = c(0x0D0D0E), ink = c(0x131314), surface = c(0x1B1B1D), raised = c(0x252527), edge = c(0x35353A), edgeStrong = c(0x7A7A82),
        text = c(0xF2F2F4), textMuted = c(0xA9A9B2), accent = c(0xE8E8EE), accentDim = c(0x46464E), onAccent = c(0x131314),
        chartRed = c(0xFF5A3C), chartRedText = c(0xFF7E6A), ok = c(0x86D39B), caution = c(0xF0A640),
    )
    val HighContrast = Palette(
        "contrast", "High contrast", false,
        rail = c(0x000000), ink = c(0x000000), surface = c(0x0A0A0A), raised = c(0x161616), edge = c(0x8A8A8A), edgeStrong = c(0xCFCFCF),
        text = c(0xFFFFFF), textMuted = c(0xDADADA), accent = c(0xFFE24A), accentDim = c(0x5C5200), onAccent = c(0x000000),
        chartRed = c(0xFF9C86), chartRedText = c(0xFF9C86), ok = c(0x9BF0B0), caution = c(0xFFC266),
        minTextContrast = 7.0,
    )

    /** Light themes in the order the picker shows them; the first is the default day theme. */
    val Light: List<Palette> = listOf(Sand, Paper, Mist, Sage, Blush)

    /** Dark themes in the order the picker shows them; the first is the default night theme. */
    val Dark: List<Palette> = listOf(Night, Amoled, Forest, Ocean, Ember, Graphite, HighContrast)

    val All: List<Palette> = Light + Dark

    fun byId(id: String?): Palette? = All.firstOrNull { it.id == id }
}

val LocalPalette = staticCompositionLocalOf { Palettes.Night }
