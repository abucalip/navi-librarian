package app.discair.ui

import app.discair.ui.common.FlowPagesRules
import org.junit.Assert.assertEquals
import org.junit.Test

/** The numbers of Flow's Album, Artist and Genre pages (flow/album-artist-genre) and the wash's scroll rule. */
class FlowPagesRulesTest {
    @Test fun theNumbersAreTheMockups() {
        assertEquals(420f, FlowPagesRules.WASH_HEIGHT, 0f)
        assertEquals(232, FlowPagesRules.ALBUM_COVER)
        assertEquals(0.92f, FlowPagesRules.ARTIST_PHOTO_RATIO, 0f)
        assertEquals(112, FlowPagesRules.SIMILAR_COVER)
        assertEquals(104, FlowPagesRules.LIBRARY_COVER)
        assertEquals(80, FlowPagesRules.WHO_PHOTO)
        assertEquals(84, FlowPagesRules.WHO_CELL)
        assertEquals(14, FlowPagesRules.GRID_GAP)
    }

    @Test fun theWashScrollsAwayWithTheFirstItemAndIsGoneOnceItHasLeft() {
        assertEquals(0f, FlowPagesRules.washScroll(0, 0, 1000f), 0f)
        assertEquals(300f, FlowPagesRules.washScroll(0, 300, 1000f), 0f)
        assertEquals(1000f, FlowPagesRules.washScroll(0, 5000, 1000f), 0f)
        assertEquals(1000f, FlowPagesRules.washScroll(1, 0, 1000f), 0f)
    }
}
