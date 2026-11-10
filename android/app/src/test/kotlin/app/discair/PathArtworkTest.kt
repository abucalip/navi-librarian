package app.discair

import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndex
import app.discair.model.ArtworkReleaseCounts
import app.discair.model.ROOM_PHOTO_LIMIT
import app.discair.model.hasRoomPhotos
import app.discair.model.nextPathCover
import app.discair.model.pathCoverFaces
import app.discair.model.roomPhotos
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Paths covers and Same Room (idea 10): which pictures a path row cycles through and which photos Same Room puts side by side. */
class PathArtworkTest {
    private fun image(id: Long, types: List<String> = emptyList(), comment: String = "", format: String = "jpg") = ArtworkImage(
        imageId = id, release = "r", releases = listOf("r"), edition = "1999 JP CD", types = types, comment = comment,
        approved = false, width = 1000, height = 1000, format = format,
    )

    private fun index(vararg images: ArtworkImage) = ArtworkIndex(
        rgid = "rg", truncatedReason = null, releases = ArtworkReleaseCounts(1, 1, 0, 0), bestFront = null,
        slots = emptyMap(), booklet = null, images = images.toList(),
    )

    @Test fun coversAreFrontImagesInOrderWithoutPdfs() {
        val faces = pathCoverFaces(index(image(1, listOf("Front")), image(2, listOf("Back")), image(3, listOf("Front")), image(4, listOf("Front"), format = "pdf")))
        assertEquals(listOf(1L, 3L), faces.map { it.imageId })
    }

    @Test fun oneCoverOrNoIndexMeansNothingToCycle() {
        assertTrue(pathCoverFaces(index(image(1, listOf("Front")), image(2, listOf("Back")))).isEmpty())
        assertTrue(pathCoverFaces(null).isEmpty())
    }

    @Test fun cyclingWraps() {
        assertEquals(1, nextPathCover(0, 3))
        assertEquals(0, nextPathCover(2, 3))
        assertEquals(0, nextPathCover(5, 0))
    }

    @Test fun roomPhotosAreSessionPicturesOnlyAndCapped() {
        val photos = roomPhotos(
            index(
                image(1, listOf("Front")), image(2, listOf("Other")), image(3, comment = "studio session"), image(4, listOf("Liner")),
                image(5, listOf("Poster")), image(6, listOf("Poster"), format = "pdf"),
            ),
        )
        assertEquals(listOf(2L, 3L, 4L), photos.map { it.imageId })
        assertEquals(ROOM_PHOTO_LIMIT, photos.size)
        assertTrue(roomPhotos(null).isEmpty())
    }

    @Test fun sameRoomNeedsAPhotoOnEitherSide() {
        val one = listOf(image(1, listOf("Other")))
        assertTrue(hasRoomPhotos(one, emptyList()))
        assertTrue(hasRoomPhotos(emptyList(), one))
        assertFalse(hasRoomPhotos(emptyList(), emptyList()))
    }
}
