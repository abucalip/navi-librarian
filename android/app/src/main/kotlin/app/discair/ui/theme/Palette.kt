package app.discair.ui.theme

import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.Dp

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
    /** Classic themes keep the original soft look; Brutal themes draw hard outlines and offset shadows (android/DESIGN.md). */
    val family: Family = Family.Classic,
    /** Corner radius, outline and hard-shadow offset of a Brutal theme; null on Classic themes, which keep each component's own. */
    val shape: BrutalShape? = null,
    /** Three extra colours for badges, bar fills and rank chips on Brutal themes. */
    val accent2: Color = accent, val accent3: Color = accent, val accent4: Color = accent,
    /** The colour of the hard shadow (Brutal only). */
    val shadowColor: Color = Color.Transparent,
    /** The smallest contrast of the accent against the page. Brutal accents are pastel and rely on the outline (held to 3:1). */
    val minAccentContrast: Double = 3.0,
    /** How the screens are composed (D-023). Every theme but the Round 2 ones keeps [Layout.Standard], today's composition. */
    val layout: Layout = Layout.Standard,
) {
    val brutal: Boolean get() = shape != null

    /**
     * A copy that keeps this theme's accent but uses [dark]'s surfaces and text. For screens drawn over artwork.
     * The accent stays the theme's own, so the player sheet's Play button and the island's ring match the album page's Play.
     */
    fun overArtwork(dark: Palette) = Palette(
        id, label, false, dark.rail, dark.ink, dark.surface, dark.raised, dark.edge, dark.edgeStrong, dark.text, dark.textMuted,
        accent = accent, accentDim = if (light) dark.accentDim else accentDim,
        onAccent = onAccent,
        chartRed = dark.chartRed, chartRedText = dark.chartRedText, ok = dark.ok, caution = dark.caution,
        minTextContrast = minTextContrast, family = family, shape = shape,
        accent2 = accent2, accent3 = accent3, accent4 = accent4, shadowColor = shadowColor, minAccentContrast = minAccentContrast,
        layout = layout,
    )
}

enum class Family(val label: String) { Classic("Classic"), Brutal("Brutal") }

/**
 * The composition a theme asks for (docs/BRUT_LAYOUTS_PLAN.md, D-023). A layout changes how Home, Now Playing and the
 * navigation are arranged, never what they do. [Standard] is the composition every earlier theme has.
 */
enum class Layout(val label: String) {
    Standard("Standard"), TapeDeck("Cassette Deck"), SheetStack("Sheet Stack"), StickerWall("Sticker Wall"),
}

/** Corner radius, outline width and hard-shadow offset, all in dp. A radius of 0 is square; pills are drawn at 50%. */
class BrutalShape(val radius: Int, val outline: Int, val shadow: Int)

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


    // Brutal family (owner-approved 2026-11-02): pastel fills, hard outlines and offset shadows, varied corner radius.
    val BrutLavender = Palette(
        "brutlavender", "Brut · Lavender", true,
        rail = c(0xF0EEFC), ink = c(0xF0EEFC), surface = c(0xFFFFFF), raised = c(0xDDD7F5), edge = c(0x000000), edgeStrong = c(0x000000),
        text = c(0x000000), textMuted = c(0x4A4570), accent = c(0xB6ACE4), accentDim = c(0xDDD7F5), onAccent = c(0x000000),
        chartRed = c(0xB3261E), chartRedText = c(0xB3261E), ok = c(0x1B6B33), caution = c(0x7F4A00),
        family = Family.Brutal, shape = BrutalShape(6, 2, 4), shadowColor = c(0x000000),
        accent2 = c(0xF28E8E), accent3 = c(0x8FD6CC), accent4 = c(0xFBE27A), minAccentContrast = 1.3,
    )

    val BrutMint = Palette(
        "brutmint", "Brut · Mint", true,
        rail = c(0xEEFBEC), ink = c(0xEEFBEC), surface = c(0xFFFFFF), raised = c(0xCFF3C8), edge = c(0x000000), edgeStrong = c(0x000000),
        text = c(0x000000), textMuted = c(0x2F5A2A), accent = c(0x97EE88), accentDim = c(0xCFF3C8), onAccent = c(0x000000),
        chartRed = c(0xB3261E), chartRedText = c(0xB3261E), ok = c(0x1B6B33), caution = c(0x7F4A00),
        family = Family.Brutal, shape = BrutalShape(6, 2, 4), shadowColor = c(0x000000),
        accent2 = c(0xFED170), accent3 = c(0x9CC9F0), accent4 = c(0xF4A6B8), minAccentContrast = 1.3,
    )

    val BrutLemon = Palette(
        "brutlemon", "Brut · Lemon", true,
        rail = c(0xFFFBF0), ink = c(0xFFFBF0), surface = c(0xFFFFFF), raised = c(0xFFEBC2), edge = c(0x000000), edgeStrong = c(0x000000),
        text = c(0x000000), textMuted = c(0x6B4E12), accent = c(0xFED170), accentDim = c(0xFFEBC2), onAccent = c(0x000000),
        chartRed = c(0xB3261E), chartRedText = c(0xB3261E), ok = c(0x1B6B33), caution = c(0x7F4A00),
        family = Family.Brutal, shape = BrutalShape(6, 2, 4), shadowColor = c(0x000000),
        accent2 = c(0xB6ACE4), accent3 = c(0x97EE88), accent4 = c(0xF29B8B), minAccentContrast = 1.3,
    )

    val BrutCream = Palette(
        "brutcream", "Brut · Cream Pop", true,
        rail = c(0xFBF0E6), ink = c(0xFBF0E6), surface = c(0xFFFFFF), raised = c(0xF6DFCF), edge = c(0x000000), edgeStrong = c(0x000000),
        text = c(0x000000), textMuted = c(0x5A4636), accent = c(0xEE6F6A), accentDim = c(0xF6DFCF), onAccent = c(0x000000),
        chartRed = c(0xB3261E), chartRedText = c(0xB3261E), ok = c(0x1B6B33), caution = c(0x7F4A00),
        family = Family.Brutal, shape = BrutalShape(16, 3, 5), shadowColor = c(0x000000),
        accent2 = c(0xA48FE8), accent3 = c(0x6FCBBF), accent4 = c(0xF8DF72), minAccentContrast = 1.3,
    )

    val BrutSky = Palette(
        "brutsky", "Brut · Sky Pill", true,
        rail = c(0xE8F2FB), ink = c(0xE8F2FB), surface = c(0xFFFFFF), raised = c(0xC8E1F7), edge = c(0x000000), edgeStrong = c(0x000000),
        text = c(0x000000), textMuted = c(0x2B4C6B), accent = c(0x8CC4F0), accentDim = c(0xC8E1F7), onAccent = c(0x000000),
        chartRed = c(0xB3261E), chartRedText = c(0xB3261E), ok = c(0x1B6B33), caution = c(0x7F4A00),
        family = Family.Brutal, shape = BrutalShape(18, 2, 3), shadowColor = c(0x000000),
        accent2 = c(0xF7B267), accent3 = c(0xF4A6C8), accent4 = c(0xA8E6A1), minAccentContrast = 1.3,
    )

    val BrutPoster = Palette(
        "brutposter", "Brut · Poster", true,
        rail = c(0xF3F1EA), ink = c(0xF3F1EA), surface = c(0xFFFFFF), raised = c(0xE2DFD2), edge = c(0x000000), edgeStrong = c(0x000000),
        text = c(0x000000), textMuted = c(0x3F3D36), accent = c(0xFF5A47), accentDim = c(0xE2DFD2), onAccent = c(0x000000),
        chartRed = c(0xB3261E), chartRedText = c(0xB3261E), ok = c(0x1B6B33), caution = c(0x7F4A00),
        family = Family.Brutal, shape = BrutalShape(0, 4, 8), shadowColor = c(0x000000),
        accent2 = c(0xFFD21F), accent3 = c(0x2DD4A8), accent4 = c(0x6C8CFF), minAccentContrast = 1.3,
    )

    val BrutInk = Palette(
        "brutink", "Brut · Ink Lavender", false,
        rail = c(0x15121D), ink = c(0x15121D), surface = c(0x1F1B2B), raised = c(0x2B2640), edge = c(0xF3EEFF), edgeStrong = c(0xF3EEFF),
        text = c(0xF8F5FF), textMuted = c(0xC9C1E6), accent = c(0xB6ACE4), accentDim = c(0x2B2640), onAccent = c(0x000000),
        chartRed = c(0xFF8A80), chartRedText = c(0xFF8A80), ok = c(0x86D39B), caution = c(0xF0A640),
        family = Family.Brutal, shape = BrutalShape(6, 2, 4), shadowColor = c(0xB6ACE4),
        accent2 = c(0xF28E8E), accent3 = c(0x8FD6CC), accent4 = c(0xFBE27A), minAccentContrast = 1.3,
    )

    val BrutMidnight = Palette(
        "brutmidnight", "Brut · Midnight Mint", false,
        rail = c(0x0E1512), ink = c(0x0E1512), surface = c(0x16211C), raised = c(0x1F3029), edge = c(0x97EE88), edgeStrong = c(0x97EE88),
        text = c(0xEEFBEC), textMuted = c(0xB5CFC0), accent = c(0x97EE88), accentDim = c(0x1F3029), onAccent = c(0x000000),
        chartRed = c(0xFF8A80), chartRedText = c(0xFF8A80), ok = c(0x86D39B), caution = c(0xF0A640),
        family = Family.Brutal, shape = BrutalShape(12, 2, 4), shadowColor = c(0x97EE88),
        accent2 = c(0xFED170), accent3 = c(0x9CC9F0), accent4 = c(0xF4A6B8), minAccentContrast = 1.3,
    )

    // Round 2, Cassette Deck (owner-approved 2026-11-03): ruled lists, a ruled navigation bar and a live meter. The same three
    // palettes as the web's Tape Deck; Cobalt's accent is the web's darkened #3D68F0 so white text on it passes.
    val TapeLime = Palette(
        "tapelime", "Tape · Lime", true,
        rail = c(0xF1EEE3), ink = c(0xF1EEE3), surface = c(0xFFFDF6), raised = c(0xF1ECDC), edge = c(0x111111), edgeStrong = c(0x111111),
        text = c(0x111111), textMuted = c(0x4F4D44), accent = c(0xC6F432), accentDim = c(0xE9F8B4), onAccent = c(0x111111),
        chartRed = c(0xB3261E), chartRedText = c(0xB3261E), ok = c(0x1B6B33), caution = c(0x7F4A00),
        family = Family.Brutal, shape = BrutalShape(2, 2, 5), shadowColor = c(0x111111),
        accent2 = c(0xFF5D8F), accent3 = c(0x3D7BFF), accent4 = c(0xFFC93C), minAccentContrast = 1.1,
        layout = Layout.TapeDeck,
    )

    val TapeCobalt = Palette(
        "tapecobalt", "Tape · Cobalt", true,
        rail = c(0xE6EDFB), ink = c(0xE6EDFB), surface = c(0xFBFCFF), raised = c(0xDBE5FA), edge = c(0x0E1B3D), edgeStrong = c(0x0E1B3D),
        text = c(0x0E1B3D), textMuted = c(0x43527A), accent = c(0x3D68F0), accentDim = c(0xD3DFFF), onAccent = c(0xFFFFFF),
        chartRed = c(0xB3261E), chartRedText = c(0xB3261E), ok = c(0x1B6B33), caution = c(0x7F4A00),
        family = Family.Brutal, shape = BrutalShape(2, 2, 5), shadowColor = c(0x0E1B3D),
        accent2 = c(0xFF6B4A), accent3 = c(0xFFD23F), accent4 = c(0x9DB5FF), minAccentContrast = 3.0,
        layout = Layout.TapeDeck,
    )

    val TapeTangerine = Palette(
        "tapetangerine", "Tape · Tangerine", true,
        rail = c(0xFFF0DC), ink = c(0xFFF0DC), surface = c(0xFFFAF2), raised = c(0xFBE6C8), edge = c(0x1B120A), edgeStrong = c(0x1B120A),
        text = c(0x1B120A), textMuted = c(0x5E4A35), accent = c(0xFF8A1F), accentDim = c(0xFFE0B8), onAccent = c(0x1B120A),
        chartRed = c(0xB3261E), chartRedText = c(0xB3261E), ok = c(0x1B6B33), caution = c(0x7F4A00),
        family = Family.Brutal, shape = BrutalShape(2, 2, 5), shadowColor = c(0x1B120A),
        accent2 = c(0x1F8A70), accent3 = c(0xFFD23F), accent4 = c(0xFF5D8F), minAccentContrast = 1.3,
        layout = Layout.TapeDeck,
    )

    // Round 2, Sheet Stack (owner-approved 2026-11-03): soft-cornered sheets, a joined navigation group, a bottom-sheet player with a
    // volume slider. Values from docs/BRUT_LAYOUTS_PLAN.md section 3 ("ink" is the text and the edge; "cy" is the second tone).
    val SheetViolet = Palette(
        "sheetviolet", "Sheet · Violet-orange", false,
        rail = c(0x15131F), ink = c(0x15131F), surface = c(0x221F31), raised = c(0x2E2A43), edge = c(0xF4F1FF), edgeStrong = c(0xF4F1FF),
        text = c(0xF4F1FF), textMuted = c(0xA8A2C4), accent = c(0xFF6A3D), accentDim = c(0x2E2A43), onAccent = c(0x15131F),
        chartRed = c(0xFF8A80), chartRedText = c(0xFF8A80), ok = c(0x86D39B), caution = c(0xF0A640),
        family = Family.Brutal, shape = BrutalShape(14, 2, 4), shadowColor = c(0xFF6A3D),
        accent2 = c(0x35E0D0), accent3 = c(0xFFD166), accent4 = c(0xB6A4FF), minAccentContrast = 3.0,
        layout = Layout.SheetStack,
    )

    val SheetAcid = Palette(
        "sheetacid", "Sheet · Acid Night", false,
        rail = c(0x0D1210), ink = c(0x0D1210), surface = c(0x17201B), raised = c(0x22302A), edge = c(0xEEFAF0), edgeStrong = c(0xEEFAF0),
        text = c(0xEEFAF0), textMuted = c(0x93AD9B), accent = c(0xC6F432), accentDim = c(0x22302A), onAccent = c(0x0D1210),
        chartRed = c(0xFF8A80), chartRedText = c(0xFF8A80), ok = c(0x86D39B), caution = c(0xF0A640),
        family = Family.Brutal, shape = BrutalShape(14, 2, 4), shadowColor = c(0xC6F432),
        accent2 = c(0xFF5DC8), accent3 = c(0x35E0D0), accent4 = c(0xFFD166), minAccentContrast = 3.0,
        layout = Layout.SheetStack,
    )

    val SheetDaylight = Palette(
        "sheetdaylight", "Sheet · Daylight", true,
        rail = c(0xF4EFE6), ink = c(0xF4EFE6), surface = c(0xFFFDF7), raised = c(0xECE4D4), edge = c(0x14121C), edgeStrong = c(0x14121C),
        text = c(0x14121C), textMuted = c(0x5A546A), accent = c(0xFF6A3D), accentDim = c(0xFFD9CB), onAccent = c(0x14121C),
        chartRed = c(0xB3261E), chartRedText = c(0xB3261E), ok = c(0x1B6B33), caution = c(0x7F4A00),
        family = Family.Brutal, shape = BrutalShape(14, 2, 4), shadowColor = c(0x14121C),
        accent2 = c(0x2BB3A6), accent3 = c(0xFFC93C), accent4 = c(0xB6A4FF), minAccentContrast = 1.8,
        layout = Layout.SheetStack,
    )

    /** Light themes in the order the picker shows them; the first is the default day theme. */
    val Light: List<Palette> = listOf(Sand, Paper, Mist, Sage, Blush, BrutLavender, BrutMint, BrutLemon, BrutCream, BrutSky, BrutPoster, TapeLime, TapeCobalt, TapeTangerine, SheetDaylight)

    /** Dark themes in the order the picker shows them; the first is the default night theme. */
    val Dark: List<Palette> = listOf(Night, Amoled, Forest, Ocean, Ember, Graphite, HighContrast, BrutInk, BrutMidnight, SheetViolet, SheetAcid)

    val All: List<Palette> = Light + Dark

    fun byId(id: String?): Palette? = All.firstOrNull { it.id == id }
}

val LocalPalette = staticCompositionLocalOf { Palettes.Night }

/** The owner's chosen palette while [app.discair.ui.theme.OnArtwork] has swapped in a dark one; null otherwise. */
val LocalThemePalette = staticCompositionLocalOf<Palette?> { null }

/** The layout of the theme the owner chose, also while [app.discair.ui.theme.OnArtwork] has swapped in a dark copy of it. */
@androidx.compose.runtime.Composable
@androidx.compose.runtime.ReadOnlyComposable
fun currentLayout(): Layout = LocalPalette.current.layout
