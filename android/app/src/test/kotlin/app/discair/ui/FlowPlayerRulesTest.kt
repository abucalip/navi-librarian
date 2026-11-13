package app.discair.ui

import androidx.compose.ui.graphics.compositeOver
import app.discair.ui.player.FlowPlayerRules
import app.discair.ui.theme.Contrast
import app.discair.ui.theme.Palettes
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Step F4 part 1 of docs/ANDROID_ART_THEMES_PROPOSAL.md: the numbers of flow/player (flow.css `.npc`, `.cb`, `.lyr`) and the lyric contrast. */
class FlowPlayerRulesTest {
    @Test fun buttonsAndCoverFollowTheMockup() {
        assertEquals("Now playing", FlowPlayerRules.TITLE)
        assertEquals(48, FlowPlayerRules.SIDE_BUTTON)
        assertEquals(72, FlowPlayerRules.PLAY_BUTTON)
        assertEquals(30, FlowPlayerRules.SIDE_GLYPH)
        assertEquals(32, FlowPlayerRules.PLAY_GLYPH)
        assertEquals(22, FlowPlayerRules.FLAT_GLYPH)
        assertEquals(312, FlowPlayerRules.COVER)
        assertEquals(18, FlowPlayerRules.COVER_RADIUS)
        assertEquals(22, FlowPlayerRules.LYRIC_SIZE)
        assertEquals(30, FlowPlayerRules.LYRIC_LINE)
    }

    @Test fun quietLyricsStayReadableOnTheWashAndThePage() {
        val p = Palettes.Flow
        val quiet = p.text.copy(alpha = FlowPlayerRules.LYRIC_QUIET_ALPHA)
        // Large bold text needs 3:1. The page is the lightest ground; a mid wash is the other end.
        for (ground in listOf(p.ink, p.raised, androidx.compose.ui.graphics.Color(0xFFDFE6EA))) {
            assertTrue(Contrast.ratio(quiet.compositeOver(ground), ground) >= 3.0)
        }
    }
}
