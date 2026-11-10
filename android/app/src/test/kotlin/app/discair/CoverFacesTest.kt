package app.discair

import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndex
import app.discair.model.ArtworkIndexResult
import app.discair.model.ArtworkReleaseCounts
import app.discair.model.ArtworkSlot
import app.discair.model.coverBackFaces
import app.discair.model.faceAfter
import app.discair.model.parseArtworkIndex
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Which faces an album's cover can flip to (docs/artwork.md, idea 1). */
class CoverFacesTest {
    private fun image(id: Long, type: String) = ArtworkImage(id, "r", listOf("r"), "1999 JP CD", listOf(type), "", true, 500, 500, "jpg")
    private fun index(vararg types: String): ArtworkIndex {
        val images = types.mapIndexed { i, t -> image(10L + i, t) }
        return ArtworkIndex("rg", null, ArtworkReleaseCounts(1, 1, 0, 0), null, images.associate { it.types.first() to ArtworkSlot(it.imageId, "r", "", true) }, null, images)
    }

    @Test fun noIndexOrNoBackMeansNoFlip() {
        assertTrue(coverBackFaces(null).isEmpty())
        assertTrue(coverBackFaces(index("Front")).isEmpty())
        assertTrue("a spine alone is not a reason to flip", coverBackFaces(index("Front", "Spine", "Tray")).isEmpty())
    }

    @Test fun backThenTrayThenSpine() {
        assertEquals(listOf(10L), coverBackFaces(index("Back", "Front")).map { it.imageId })
        assertEquals(listOf(10L, 12L, 11L), coverBackFaces(index("Back", "Spine", "Tray")).map { it.imageId })
    }

    @Test fun flipsWrapInBothDirections() {
        assertEquals(0, faceAfter(5, 0))
        assertEquals(1, faceAfter(1, 1)); assertEquals(0, faceAfter(2, 1)); assertEquals(1, faceAfter(-1, 1))
        assertEquals(3, faceAfter(-1, 3)); assertEquals(0, faceAfter(4, 3))
    }

    @Test fun recordedFixtureFlipsToItsBack() {
        val body = Json.parseToJsonElement(javaClass.classLoader!!.getResource("librarian/artwork_index.json")!!.readText())
            .jsonObject["response"]!!.jsonObject["body"].toString()
        val index = (parseArtworkIndex(body) as ArtworkIndexResult.Ready).index
        assertEquals(index.slotImage("Back") != null, coverBackFaces(index).isNotEmpty())
    }
}
