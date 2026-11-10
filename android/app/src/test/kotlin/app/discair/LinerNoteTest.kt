package app.discair

import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndex
import app.discair.model.ArtworkReleaseCounts
import app.discair.model.linerNoteDay
import app.discair.model.linerNoteOrder
import app.discair.model.linerNotePicture
import app.discair.model.linerNoteSeed
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate

/** The liner note of the day (docs/artwork.md, idea 12): a stable day key and album order, and a picture chosen by type only. */
class LinerNoteTest {
    private val a = "1edd139d-4779-4057-8e12-13c783674f0d"
    private val b = "9b7e1f2c-3d4a-4b5c-8d6e-7f8091a2b3c4"
    private val c = "2c3d4e5f-6a7b-4c8d-9e0f-1a2b3c4d5e6f"

    private fun image(id: Long, types: List<String> = emptyList(), comment: String = "", format: String = "jpg") = ArtworkImage(
        imageId = id, release = "r", releases = listOf("r"), edition = "1999 JP CD", types = types, comment = comment,
        approved = false, width = 1000, height = 1000, format = format,
    )

    private fun index(vararg images: ArtworkImage) = ArtworkIndex(
        rgid = "rg", truncatedReason = null, releases = ArtworkReleaseCounts(1, 1, 0, 0), bestFront = null,
        slots = emptyMap(), booklet = null, images = images.toList(),
    )

    @Test fun seedIsStableAndDependsOnTheKey() {
        assertEquals(linerNoteSeed("2026-11-10"), linerNoteSeed("2026-11-10"))
        assertTrue(linerNoteSeed("2026-11-10") != linerNoteSeed("2026-11-11"))
        assertTrue(linerNoteSeed("2026-11-10") >= 0)
    }

    @Test fun dayIsTheIsoDate() {
        assertEquals("2026-03-07", linerNoteDay(LocalDate.of(2026, 3, 7)))
    }

    @Test fun orderIgnoresArrivalOrderAndDropsBadAndRepeatedIds() {
        val one = linerNoteOrder(listOf(a, b, c), "2026-11-10")
        assertEquals(setOf(a, b, c), one.toSet())
        assertEquals(3, one.size)
        assertEquals(one, linerNoteOrder(listOf(c, a, b), "2026-11-10"))
        assertEquals(listOf(a), linerNoteOrder(listOf("not-an-id", a, a.uppercase()), "2026-11-10"))
        assertTrue(linerNoteOrder(emptyList(), "2026-11-10").isEmpty())
    }

    @Test fun pictureIsBookletSessionOrLabelNeverACoverOrPdf() {
        val idx = index(
            image(1, listOf("Front")), image(2, listOf("Back")), image(3, listOf("Booklet"), format = "pdf"),
            image(4, listOf("Booklet")), image(5, listOf("Other")), image(6, listOf("Medium")),
        )
        for (day in listOf("2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13")) {
            val picked = linerNotePicture(idx, day)?.imageId
            assertTrue("$day picked $picked", picked in setOf(4L, 5L, 6L))
        }
        assertEquals(linerNotePicture(idx, "2026-11-10"), linerNotePicture(idx, "2026-11-10"))
    }

    @Test fun noQualifyingPictureMeansNoNote() {
        assertNull(linerNotePicture(index(image(1, listOf("Front")), image(2, listOf("Back")), image(3)), "2026-11-10"))
        assertNull(linerNotePicture(null, "2026-11-10"))
    }
}
