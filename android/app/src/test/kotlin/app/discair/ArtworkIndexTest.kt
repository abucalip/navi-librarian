package app.discair

import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndexResult
import app.discair.model.loadArtworkIndex
import app.discair.model.parseArtworkIndex
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** The artwork index (`GET /api/artwork/index`): the recorded fixtures decode into what the screens will show. */
class ArtworkIndexTest {
    private fun body(name: String): String = Json.parseToJsonElement(
        javaClass.classLoader!!.getResource("librarian/$name.json")!!.readText(),
    ).jsonObject["response"]!!.jsonObject["body"].toString()

    private fun ready(name: String) = (parseArtworkIndex(body(name)) as ArtworkIndexResult.Ready).index

    @Test fun okFixtureReadsSlotsBookletAndImages() {
        val index = ready("artwork_index")
        assertEquals(2001L, index.bestFront)
        assertNull(index.truncatedReason)
        assertTrue(index.images.isNotEmpty())
        assertEquals(index.images.map { it.imageId }.toSet().size, index.images.size)
        for ((type, slot) in index.slots) assertTrue("$type slot resolves", index.slotImage(type) != null && slot.imageId > 0)
        val booklet = index.booklet!!
        assertEquals(booklet.imageIds, index.bookletImages().map { it.imageId })
        assertTrue(index.images.all { it.format in setOf("jpg", "png", "gif", "webp", "pdf") })
    }

    @Test fun editionsAreLabelledAndOwnedFlagIsRead() {
        val index = ready("artwork_index")
        assertTrue(index.slots.values.any { it.fromOwned })
        assertTrue(index.images.all { it.edition.isNotBlank() })
        val back = index.slotImage("Back")!!
        assertEquals("Back cover, ${back.edition}" + (if (back.comment.isBlank()) "" else ": ${back.comment.trim()}"), back.label())
    }

    @Test fun emptyFixtureShowsNothing() {
        assertEquals(ArtworkIndexResult.Empty, parseArtworkIndex(body("artwork_index_empty")))
    }

    @Test fun unavailableIsNeverEmpty() {
        assertEquals(ArtworkIndexResult.Unavailable, parseArtworkIndex(body("artwork_index_unavailable")))
        assertEquals(ArtworkIndexResult.Unavailable, parseArtworkIndex("not json"))
        assertEquals(ArtworkIndexResult.Unavailable, parseArtworkIndex("""{"status":"something_new"}"""))
    }

    @Test fun notLoadedCarriesTheRetryDelay() {
        val r = parseArtworkIndex(body("artwork_index_not_loaded")) as ArtworkIndexResult.NotLoaded
        assertTrue(r.retryAfterSeconds in 1..60)
    }

    @Test fun truncatedFixturesStillShowWhatWasServedAndSayWhy() {
        assertEquals("partial", ready("artwork_index_truncated").truncatedReason)
        assertEquals("release_cap", ready("artwork_index_truncated_release_cap").truncatedReason)
        assertEquals("served_cap", ready("artwork_index_truncated_served_cap").truncatedReason)
    }

    @Test fun badRequestBodyIsNotAnIndex() {
        assertEquals(ArtworkIndexResult.Unavailable, parseArtworkIndex(body("artwork_index_error_bad_rgid")))
    }

    @Test fun oneBadImageEntryDoesNotDropTheRest() {
        val r = parseArtworkIndex(
            """{"status":"ok","rgid":"x","images":[{"types":["Front"]},{"image_id":7,"types":["Front"],"comment":"<b>hi</b>","format":"PDF"},{"image_id":0}]}""",
        ) as ArtworkIndexResult.Ready
        assertEquals(listOf(7L), r.index.images.map { it.imageId })
        val image = r.index.images.single()
        assertTrue(image.isPdf)
        assertEquals("<b>hi</b>", image.comment) // plain text, kept as given
    }

    @Test fun untypedImagesAreInNoSlotAndLabelledImage() {
        val image = ArtworkImage(1, "r", listOf("r"), "", emptyList(), "", true, null, null, "jpg")
        assertTrue(image.isUntyped)
        assertEquals("Image", image.label())
        assertFalse(image.isPdf)
    }

    @Test fun loadAsksAgainOnNotLoadedThenGivesUp() = runBlocking {
        val waits = mutableListOf<Long>()
        var calls = 0
        val done = loadArtworkIndex(wait = { waits += it }) {
            if (++calls < 3) ArtworkIndexResult.NotLoaded(2) else parseArtworkIndex(body("artwork_index_empty"))
        }
        assertEquals(ArtworkIndexResult.Empty, done)
        assertEquals(listOf(2000L, 2000L), waits)

        val never = loadArtworkIndex(tries = 3, wait = {}) { ArtworkIndexResult.NotLoaded(1) }
        assertEquals(ArtworkIndexResult.Unavailable, never) // still building is not a statement about the album
        val failed = loadArtworkIndex(wait = {}) { throw IllegalStateException("offline") }
        assertEquals(ArtworkIndexResult.Unavailable, failed)
    }
}
