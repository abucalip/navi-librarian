package app.discair

import app.discair.model.ArtworkBooklet
import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndex
import app.discair.model.ArtworkReleaseCounts
import app.discair.model.ArtworkSlot
import app.discair.model.MAX_ZOOM
import app.discair.model.bitmapItems
import app.discair.model.bookletView
import app.discair.model.BookletView
import app.discair.model.anotherBooklet
import app.discair.model.BookletStep
import app.discair.model.maxPan
import app.discair.model.nextZoom
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** What the Booklet tab shows and how zoom is kept in bounds (docs/artwork.md, idea 2). */
class BookletTest {
    private fun image(id: Long, type: String, format: String = "jpg") =
        ArtworkImage(id, "r", listOf("r"), "1999 JP CD", listOf(type), "", true, 800, 800, format)

    private fun index(pages: List<ArtworkImage>, extras: List<ArtworkImage> = emptyList(), booklet: Boolean = true): ArtworkIndex {
        val all = pages + extras
        return ArtworkIndex(
            "rg", null, ArtworkReleaseCounts(1, 1, 0, 0), null,
            extras.associate { it.types.first() to ArtworkSlot(it.imageId, "r", "", true) },
            if (booklet) ArtworkBooklet("r", "1999 JP CD", pages.map { it.imageId }) else null, all,
        )
    }

    @Test fun noIndexOrNoBookletMeansNoTab() {
        assertNull(bookletView(null))
        assertNull(bookletView(index(emptyList(), listOf(image(5, "Poster")), booklet = false)))
    }

    @Test fun pagesKeepServerOrderThenStickerObiPoster() {
        val pages = listOf(image(3, "Booklet"), image(1, "Booklet"), image(2, "Booklet"))
        val view = bookletView(index(pages, listOf(image(9, "Poster"), image(8, "Obi"), image(7, "Sticker"))))!!
        assertEquals(listOf(3L, 1L, 2L, 7L, 8L, 9L), view.items.map { it.imageId })
        assertEquals(3, view.pageCount)
        assertEquals("1999 JP CD", view.edition)
    }

    @Test fun anImageIsListedOnce() {
        val page = image(3, "Booklet")
        val view = bookletView(index(listOf(page), listOf(ArtworkImage(3, "r", listOf("r"), "", listOf("Poster"), "", true, 1, 1, "jpg"))))!!
        assertEquals(1, view.items.size)
    }

    @Test fun aPdfBookletOpensInTheViewerByItself() {
        val view = bookletView(index(listOf(image(4, "Booklet", "pdf")), listOf(image(9, "Poster"))))!!
        assertTrue(view.hasPdf)
        assertEquals(listOf(9L), view.bitmapItems().map { it.imageId })
    }

    @Test fun zoomStaysBetweenOneAndTheMaximum() {
        assertEquals(1f, nextZoom(1f, 0.2f), 0f)
        assertEquals(MAX_ZOOM, nextZoom(5f, 3f), 0f)
        assertEquals(2f, nextZoom(1f, 2f), 0f)
    }

    @Test fun panIsLimitedToWhatTheZoomAdds() {
        assertEquals(0f, maxPan(1000f, 1f), 0f)
        assertEquals(500f, maxPan(1000f, 2f), 0f)
    }

    @Test fun otherBookletsFollowTheFirstAndTheButtonCyclesThem() {
        val a = listOf(image(1, "Booklet"), image(2, "Booklet")); val b = listOf(image(3, "Booklet"))
        val base = index(a + b)
        val idx = base.copy(booklets = listOf(
            ArtworkBooklet("a", "1999 JP CD", listOf(1, 2)), ArtworkBooklet("b", "2004 DE CD", listOf(3)), ArtworkBooklet("c", "gone", listOf(99)),
        ))
        val view = bookletView(idx)!!
        assertEquals(listOf(1L, 2L), view.items.map { it.imageId })
        assertEquals(listOf("2004 DE CD"), view.others.map { it.edition })
        val all = listOf(view.copy(others = emptyList())) + view.others
        assertEquals(BookletStep(1, "Booklet 2 of 2 · 2004 DE CD."), anotherBooklet(0, all))
        assertEquals(0, anotherBooklet(1, all).next)
    }

    @Test fun oneBookletMeansNoOtherFound() {
        val view = bookletView(index(listOf(image(1, "Booklet"))))!!
        assertEquals(emptyList<BookletView>(), view.others)
        assertEquals(BookletStep(0, "No other booklet found."), anotherBooklet(0, listOf(view)))
    }
}
