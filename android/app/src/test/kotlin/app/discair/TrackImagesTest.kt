package app.discair

import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndex
import app.discair.model.ArtworkReleaseCounts
import app.discair.model.TRACK_LIMIT
import app.discair.model.trackImages
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** The queue's Track cards (docs/artwork.md, idea 6): only Track images, never a PDF, at most three, none when there are none. */
class TrackImagesTest {
    private fun image(id: Long, vararg types: String, format: String = "jpg") =
        ArtworkImage(id, "r", listOf("r"), "1999 JP CD", types.toList(), "", true, 500, 500, format)

    private fun index(vararg images: ArtworkImage) =
        ArtworkIndex("rg", null, ArtworkReleaseCounts(1, 1, 0, 0), null, emptyMap(), null, images.toList())

    @Test fun noIndexOrNoTrackMeansNoCard() {
        assertTrue(trackImages(null).isEmpty())
        assertTrue(trackImages(index(image(1, "Front"), image(2, "Back"))).isEmpty())
        assertTrue("an untyped image is not a track sheet", trackImages(index(image(3))).isEmpty())
    }

    @Test fun keepsTrackImagesInServerOrder() {
        val got = trackImages(index(image(1, "Front"), image(5, "Track"), image(2, "Track", "Medium"), image(7, "Booklet")))
        assertEquals(listOf(5L, 2L), got.map { it.imageId })
    }

    @Test fun leavesOutPdfsAndCapsTheCount() {
        assertEquals(listOf(4L), trackImages(index(image(9, "Track", format = "pdf"), image(4, "Track"))).map { it.imageId })
        val many = (1L..10L).map { image(it, "Track") }
        assertEquals(TRACK_LIMIT, trackImages(index(*many.toTypedArray())).size)
    }
}
