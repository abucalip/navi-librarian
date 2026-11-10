package app.discair

import app.discair.model.ArtworkBooklet
import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndex
import app.discair.model.ArtworkReleaseCounts
import app.discair.model.ArtworkSlot
import app.discair.model.SLIDESHOW_LIMIT
import app.discair.model.discImage
import app.discair.model.namedDisc
import app.discair.model.slideshowFrame
import app.discair.model.slideshowImages
import app.discair.player.MemoryPlayerSettings
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** The disc and the slideshow (docs/artwork.md, ideas 3 and 4): what is picked and the timing rules. Same rules as the Mac. */
class NowPlayingArtworkTest {
    private fun pic(id: Long, vararg types: String, comment: String = "", edition: String = "", format: String = "jpg", size: Int? = 1200) =
        ArtworkImage(id, "r", listOf("r"), edition, types.toList(), comment, true, size, size, format)

    private fun index(images: List<ArtworkImage>, slots: Map<String, Long> = emptyMap(), booklet: List<Long> = emptyList()) = ArtworkIndex(
        rgid = "g", truncatedReason = null, releases = ArtworkReleaseCounts(1, 1, 0, 0), bestFront = null,
        slots = slots.mapValues { ArtworkSlot(it.value, "r", "e", true) },
        booklet = if (booklet.isEmpty()) null else ArtworkBooklet("r", "1999 JP CD", booklet),
        images = images,
    )

    private fun frame(f: app.discair.model.SlideshowFrame?): app.discair.model.SlideshowFrame { assertNotNull(f); return f!! }

    @Test fun discNumbersAreReadFromText() {
        assertEquals(2, namedDisc("Disc 2")); assertEquals(2, namedDisc("CD2 label")); assertEquals(2, namedDisc("disk 02, side B"))
        assertEquals(1, namedDisc("Disc No. 1"))
        assertNull(namedDisc("Side A label")); assertNull(namedDisc("")); assertNull(namedDisc("1999 JP CD")); assertNull(namedDisc("Discovery"))
    }

    @Test fun theDiscNamedByTheSongsDiscWins() {
        val i = index(listOf(pic(1, "Medium", comment = "Disc 1"), pic(2, "Medium", comment = "Disc 2")), slots = mapOf("Medium" to 1L))
        assertEquals(2L, discImage(i, 2)?.imageId); assertEquals(1L, discImage(i, 1)?.imageId)
    }

    @Test fun withoutANamedMatchTheMediumSlotThenTheFirstMediumIsUsed() {
        val slotted = index(listOf(pic(1, "Medium"), pic(2, "Medium")), slots = mapOf("Medium" to 2L))
        assertEquals(2L, discImage(slotted, null)?.imageId); assertEquals(2L, discImage(slotted, 3)?.imageId)
        assertEquals(5L, discImage(index(listOf(pic(5, "Medium"), pic(6, "Medium"))), 1)?.imageId)
    }

    @Test fun aLabelThatNamesAnotherDiscIsNotShown() {
        val i = index(listOf(pic(1, "Medium", comment = "Disc 1")), slots = mapOf("Medium" to 1L))
        assertNull(discImage(i, 2)); assertEquals(1L, discImage(i, null)?.imageId)
    }

    @Test fun noMediumImageMeansNoDisc() {
        assertNull(discImage(index(listOf(pic(1, "Front"), pic(2, "Booklet"))), 1))
        assertNull(discImage(index(listOf(pic(3, "Medium", format = "pdf"))), null))
        assertNull(discImage(null, 1))
    }

    @Test fun theSlideshowTakesBookletPagesThenOtherLinerAndPosterOnce() {
        val i = index(
            listOf(pic(1, "Front"), pic(2, "Booklet"), pic(3, "Booklet"), pic(4, "Other"), pic(5, "Liner"), pic(6, "Poster", "Other"),
                pic(7, "Back"), pic(8, "Medium"), pic(9, "Raw/Unedited")),
            booklet = listOf(2L, 3L),
        )
        assertEquals(listOf(2L, 3L, 4L, 5L, 6L), slideshowImages(i).map { it.imageId })
    }

    @Test fun pdfsAndSmallImagesAreLeftOut() {
        val i = index(
            listOf(pic(1, "Booklet", format = "pdf"), pic(2, "Booklet"), pic(3, "Other", size = 250), pic(4, "Other", size = null), pic(5, "Other")),
            booklet = listOf(1L, 2L),
        )
        assertEquals(listOf(2L, 4L, 5L), slideshowImages(i).map { it.imageId })
    }

    @Test fun fewerThanTwoImagesIsNotASlideshowAndItIsCapped() {
        assertTrue(slideshowImages(index(listOf(pic(1, "Other")))).isEmpty())
        assertTrue(slideshowImages(null).isEmpty())
        assertEquals(SLIDESHOW_LIMIT, slideshowImages(index((1L..30L).map { pic(it, "Other") })).size)
    }

    @Test fun slideshowTimingHoldsThenFadesIntoTheNextSlide() {
        val start = frame(slideshowFrame(0.0, 3))
        assertEquals(0, start.index); assertEquals(1, start.next); assertEquals(0f, start.mix, 0f); assertEquals(0f, start.progress, 0f)
        assertEquals(0f, frame(slideshowFrame(10.0, 3)).mix, 0f)
        val fading = frame(slideshowFrame(12.5, 3))
        assertEquals(0, fading.index); assertEquals(1, fading.next); assertEquals(0.5f, fading.mix, 0.0001f)
        assertEquals(1, frame(slideshowFrame(14.0, 3)).index)
        assertEquals(0, frame(slideshowFrame(14.0 * 3 + 1, 3)).index)
        val last = frame(slideshowFrame(14.0 * 2 + 13, 3))
        assertEquals(2, last.index); assertEquals(0, last.next)
        assertNull(slideshowFrame(5.0, 0)); assertEquals(0, frame(slideshowFrame(-3.0, 2)).index)
    }

    @Test fun theSlideshowSwitchIsOnByDefaultAndChangesNotifyListeners() {
        val s = MemoryPlayerSettings()
        assertTrue(s.showSlideshow)
        var calls = 0
        s.onChange { calls++ }
        s.showSlideshow = false
        assertEquals(false, s.showSlideshow); assertEquals(1, calls)
    }
}
