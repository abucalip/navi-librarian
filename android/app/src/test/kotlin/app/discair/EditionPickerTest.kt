package app.discair

import app.discair.model.AlbumSection
import app.discair.model.ApiJson
import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndex
import app.discair.model.ArtworkReleaseCounts
import app.discair.model.coverEditions
import app.discair.model.coverUrlFor
import app.discair.model.hasEditionChoice
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Which covers the picker offers, and how a pick changes the cover address (docs/artwork.md, idea 7). */
class EditionPickerTest {
    private fun image(id: Long, type: String, format: String = "jpg") =
        ArtworkImage(id, "r", listOf("r"), "199$id JP CD", listOf(type), "", true, 500, 500, format)
    private fun index(vararg images: ArtworkImage) =
        ArtworkIndex("rg", null, ArtworkReleaseCounts(1, 1, 0, 0), null, emptyMap(), null, images.toList())

    @Test fun onlyFrontImagesAreOffered_neverAPdf() {
        val editions = coverEditions(index(image(1, "Front"), image(2, "Back"), image(3, "Front", "pdf"), image(4, "Front")))
        assertEquals(listOf(1L, 4L), editions.map { it.imageId })
        assertTrue(coverEditions(null).isEmpty())
    }

    @Test fun aChoiceNeedsAtLeastTwoCovers() {
        assertFalse(hasEditionChoice(emptyList()))
        assertFalse(hasEditionChoice(coverEditions(index(image(1, "Front")))))
        assertTrue(hasEditionChoice(coverEditions(index(image(1, "Front"), image(2, "Front")))))
    }

    @Test fun aNewPickIsANewAddress() {
        assertEquals("/api/owned/artwork/al-1?c=0", coverUrlFor("/api/owned/artwork/al-1", null))
        assertEquals("/api/owned/artwork/al-1?c=42", coverUrlFor("/api/owned/artwork/al-1", 42))
        assertEquals("/a?size=300&c=7", coverUrlFor("/a?size=300", 7))
        assertNull(coverUrlFor(null, 7))
    }

    @Test fun theAlbumPageCarriesThePickAndStillDecodesWithout() {
        val with = ApiJson.decodeFromString<AlbumSection>("""{"available":true,"album":{"name":"A","artwork_choice":42}}""")
        val without = ApiJson.decodeFromString<AlbumSection>("""{"available":true,"album":{"name":"A"}}""")
        assertEquals(42L, with.album?.artworkChoice)
        assertNull(without.album?.artworkChoice)
    }
}
