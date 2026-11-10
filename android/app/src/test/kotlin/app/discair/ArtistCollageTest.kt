package app.discair

import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndex
import app.discair.model.ArtworkReleaseCounts
import app.discair.model.COLLAGE_LIMIT
import app.discair.model.OwnedAlbum
import app.discair.model.artistCollage
import app.discair.model.qualifiesForCollage
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** The artist photo strip (idea 8): the picture rules and the round-robin mirror the macOS collage. */
class ArtistCollageTest {
    private fun image(id: Long, types: List<String> = emptyList(), comment: String = "", format: String = "jpg") = ArtworkImage(
        imageId = id, release = "r", releases = listOf("r"), edition = "1999 JP CD", types = types, comment = comment,
        approved = false, width = 1000, height = 1000, format = format,
    )

    private fun album(name: String) = OwnedAlbum(name = name, key = name.lowercase(), id = "id-$name", releaseGroupMbid = "rg-$name")

    private fun index(vararg images: ArtworkImage) = ArtworkIndex(
        rgid = "rg", truncatedReason = null, releases = ArtworkReleaseCounts(1, 1, 0, 0), bestFront = null,
        slots = emptyMap(), booklet = null, images = images.toList(),
    )

    @Test fun otherLinerPosterAndRawQualify() {
        assertTrue(image(1, listOf("Other")).qualifiesForCollage())
        assertTrue(image(2, listOf("Liner")).qualifiesForCollage())
        assertTrue(image(3, listOf("Poster")).qualifiesForCollage())
        assertTrue(image(4, listOf("Raw/Unedited")).qualifiesForCollage())
    }

    @Test fun commentWordsQualifyOnlyWithoutPackaging() {
        assertTrue(image(5, comment = "Studio session, 1972").qualifiesForCollage())
        assertTrue(image(6, comment = "The BAND in the garden").qualifiesForCollage())
        assertFalse(image(7, listOf("Front"), comment = "studio version").qualifiesForCollage())
        assertFalse(image(8, listOf("Booklet"), comment = "band photo").qualifiesForCollage())
        assertFalse(image(9, comment = "rear of the jacket").qualifiesForCollage())
    }

    @Test fun pdfsNeverQualify() {
        assertFalse(image(10, listOf("Poster"), format = "pdf").qualifiesForCollage())
    }

    @Test fun roundRobinShowsEveryAlbumBeforeAnyTwice() {
        val a = album("A")
        val b = album("B")
        val ia = index(image(1, listOf("Other")), image(2, listOf("Other")), image(3, listOf("Other")), image(4, listOf("Other")))
        val ib = index(image(11, listOf("Liner")), image(12, listOf("Liner")))
        val out = artistCollage(listOf(a to ia, b to ib))
        assertEquals(listOf(1L, 11L, 2L, 12L, 3L), out.map { it.image.imageId })
        assertEquals(listOf("A", "B", "A", "B", "A"), out.map { it.album.name })
    }

    @Test fun perAlbumCapAndDuplicatesCountOnce() {
        val a = album("A")
        val b = album("B")
        val shared = image(1, listOf("Other"))
        val ia = index(shared, image(2, listOf("Other")), image(3, listOf("Other")), image(4, listOf("Other")), image(5, listOf("Other")))
        val ib = index(shared, image(6, listOf("Other")))
        val out = artistCollage(listOf(a to ia, b to ib))
        assertEquals(3, out.count { it.album.name == "A" })
        assertEquals(1, out.count { it.image.imageId == 1L })
    }

    @Test fun totalIsCappedAtTwelve() {
        val albums = (1..6).map { n ->
            album("A$n") to index(*(1..3).map { image((n * 100 + it).toLong(), listOf("Other")) }.toTypedArray())
        }
        assertEquals(COLLAGE_LIMIT, artistCollage(albums).size)
    }

    @Test fun fewerThanFourPicturesMeansNoStrip() {
        val out = artistCollage(listOf(album("A") to index(image(1, listOf("Other")), image(2, listOf("Other")), image(3, listOf("Other")))))
        assertTrue(out.isEmpty())
    }

    @Test fun nothingQualifyingMeansNoStrip() {
        val out = artistCollage(listOf(album("A") to index(image(1, listOf("Front")), image(2, listOf("Medium")))))
        assertTrue(out.isEmpty())
    }
}
