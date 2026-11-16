package app.discair.ui.theme

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Test

/** docs/GALLERY_THEME.md section 8: Gallery's motion values match tokens.json, and the page's blocks rise in turn. */
class GalleryMotionTest {
    /** tokens.json → motion, read without a JSON library: each entry is `"name": { ... }` holding numbers and a curve array. */
    private fun motion(): Map<String, String> {
        val file = listOf("../../docs/design/gallery/tokens.json", "docs/design/gallery/tokens.json").map(::File).first { it.exists() }
        val text = file.readText()
        val block = text.substring(text.indexOf("\"motion\""))
        return Regex("\"(\\w+)\":\\s*(\\{[^{}]*\\}|\\d+)").findAll(block).associate { it.groupValues[1] to it.groupValues[2] }
    }

    private fun num(entry: String, key: String): Int = Regex("\"$key\":\\s*(\\d+)").find(entry)!!.groupValues[1].toInt()

    private fun curve(entry: String): Bezier {
        val v = Regex("\"curve\":\\s*\\[([^\\]]*)\\]").find(entry)!!.groupValues[1].split(",").map { it.trim().toFloat() }
        return Bezier(v[0], v[1], v[2], v[3])
    }

    @Test fun everyValueMatchesTokensJson() {
        val m = motion()
        assertEquals(GalleryMotion.SHARED_COVER_MS, num(m.getValue("sharedCover"), "ms"))
        assertEquals(GalleryMotion.TRAVEL, curve(m.getValue("sharedCover")))
        val rise = m.getValue("placardRise")
        assertEquals(GalleryMotion.RISE_MS, num(rise, "ms"))
        assertEquals(GalleryMotion.RISE_DP, num(rise, "dp"))
        assertEquals(GalleryMotion.RISE_STAGGER_MS, num(rise, "staggerMs"))
        assertEquals(GalleryMotion.RISE_MAX_ITEMS, num(rise, "maxItems"))
        assertEquals(GalleryMotion.SETTLE, curve(rise))
        assertEquals(GalleryMotion.PAGE_FADE_OUT_MS, num(m.getValue("pageFadeOut"), "ms"))
        assertEquals(GalleryMotion.PAGE_FADE_IN_MS, num(m.getValue("pageFadeIn"), "ms"))
        assertEquals(GalleryMotion.PAGE_FADE_IN_DELAY_MS, num(m.getValue("pageFadeIn"), "delayMs"))
        assertEquals(GalleryMotion.NAV_MARKER_MS, num(m.getValue("navMarker"), "ms"))
        assertEquals(GalleryMotion.PLAYER_RISE_MS, num(m.getValue("playerRise"), "ms"))
        assertEquals(GalleryMotion.TRAVEL, curve(m.getValue("playerRise")))
        assertEquals(GalleryMotion.PLAYER_FALL_MS, num(m.getValue("playerFall"), "ms"))
        assertEquals(GalleryMotion.SNACK_IN_MS, num(m.getValue("snackIn"), "ms"))
        assertEquals(GalleryMotion.SNACK_DP, num(m.getValue("snackIn"), "dp"))
        assertEquals(GalleryMotion.SETTLE, curve(m.getValue("snackIn")))
        assertEquals(GalleryMotion.SNACK_HOLD_MS, m.getValue("snackHoldMs").toLong())
    }

    @Test fun theSharedPrintTravelsOnItsOwnCurveAndStopsWhenAnimationsAreOff() {
        assertEquals(Timing(420, Curve.Curved(GalleryMotion.TRAVEL)), GalleryMotion.sharedCover(reduced = false))
        assertEquals(0, GalleryMotion.sharedCover(reduced = true).durationMs)
        assertEquals(MotionFamily.Standard, MotionRules.familyFor(Layout.Gallery))
    }

    @Test fun theFirstSixBlocksRiseFortyMillisecondsApart() {
        // Nothing has moved before the first block's start (120ms); the first block is done 420ms later.
        assertEquals(0f, GalleryMotion.riseFraction(0, 120f), 0f)
        assertEquals(0.5f, GalleryMotion.riseFraction(0, 330f), 1e-4f)
        assertEquals(1f, GalleryMotion.riseFraction(0, 540f), 0f)
        // Each later block starts 40ms after the one before it.
        assertEquals(0f, GalleryMotion.riseFraction(1, 160f), 0f)
        assertEquals(0.5f, GalleryMotion.riseFraction(5, 120f + 200f + 210f), 1e-4f)
        // The seventh block on does not rise; it arrives with the page's fade.
        assertEquals(1f, GalleryMotion.riseFraction(6, 0f), 0f)
        assertEquals(1f, GalleryMotion.riseFraction(-1, 0f), 0f)
        // The clock runs until the sixth block has landed, and not at all when animations are off.
        assertEquals(120 + 200 + 420, GalleryMotion.arrivalMs(reduced = false))
        assertEquals(1f, GalleryMotion.riseFraction(5, GalleryMotion.arrivalMs(false).toFloat()), 0f)
        assertEquals(0, GalleryMotion.arrivalMs(reduced = true))
    }

    @Test fun theHeroSlidesOnTheTravelCurve() {
        assertEquals(380, GalleryMotion.heroSlide(reduced = false).durationMs)
        assertEquals(Curve.Curved(GalleryMotion.TRAVEL), GalleryMotion.heroSlide(reduced = false).curve)
        // With animations removed the album changes in place.
        assertEquals(0, GalleryMotion.heroSlide(reduced = true).durationMs)
    }
}
