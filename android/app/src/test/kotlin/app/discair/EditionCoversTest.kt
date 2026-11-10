package app.discair

import app.discair.model.AcquisitionJob
import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndex
import app.discair.model.ArtworkReleaseCounts
import app.discair.model.EDITION_COVER_LIMIT
import app.discair.model.editionCovers
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** The Downloads row's covers (docs/artwork.md, idea 13): Front images only, never a PDF, at most three; and the release group a Get carries. */
class EditionCoversTest {
    private fun image(id: Long, types: List<String> = emptyList(), format: String = "jpg") = ArtworkImage(
        imageId = id, release = "r", releases = listOf("r"), edition = "1999 JP CD", types = types, comment = "",
        approved = false, width = 1000, height = 1000, format = format,
    )

    private fun index(vararg images: ArtworkImage) = ArtworkIndex(
        rgid = "rg", truncatedReason = null, releases = ArtworkReleaseCounts(1, 1, 0, 0), bestFront = null,
        slots = emptyMap(), booklet = null, images = images.toList(),
    )

    @Test fun onlyFrontImagesInServerOrder() {
        val got = editionCovers(index(image(1, listOf("Back")), image(5, listOf("Front")), image(2, listOf("Front", "Back")), image(7, listOf("Booklet"))))
        assertEquals(listOf(5L, 2L), got.map { it.imageId })
    }

    @Test fun noFrontOrNoIndexMeansNoCovers() {
        assertEquals(emptyList<ArtworkImage>(), editionCovers(index(image(1, listOf("Back")), image(2))))
        assertEquals(emptyList<ArtworkImage>(), editionCovers(null))
    }

    @Test fun leavesOutPdfsAndCapsTheCount() {
        assertEquals(listOf(4L), editionCovers(index(image(9, listOf("Front"), format = "pdf"), image(4, listOf("Front")))).map { it.imageId })
        val many = editionCovers(index(*(1L..10L).map { image(it, listOf("Front")) }.toTypedArray()))
        assertEquals(EDITION_COVER_LIMIT, many.size)
    }

    private fun job(metadata: JsonObject) = AcquisitionJob(
        artist = "A", album = "B", status = "queued", createdAt = 1.0, updatedAt = null,
        details = JsonObject(mapOf("metadata" to metadata)),
    )

    @Test fun jobReadsTheReleaseGroupFromItsMetadata() {
        val rgid = "1EDD139D-4779-4057-8E12-13C783674F0D"
        assertEquals(rgid.lowercase(), job(JsonObject(mapOf("release_group_mbid" to JsonPrimitive(rgid)))).releaseGroup)
        assertNull(job(JsonObject(mapOf("release_group_mbid" to JsonPrimitive("not-an-id")))).releaseGroup)
        assertNull(job(JsonObject(mapOf("year" to JsonPrimitive(1999)))).releaseGroup)
        assertNull(AcquisitionJob("A", "B", "queued", 1.0, null, JsonObject(emptyMap())).releaseGroup)
    }
}
