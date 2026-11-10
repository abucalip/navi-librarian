package app.discair

import app.discair.model.ArtworkBooklet
import app.discair.model.ArtworkImage
import app.discair.model.ArtworkIndex
import app.discair.model.ArtworkReleaseCounts
import app.discair.model.ArtworkSlot
import app.discair.model.DiscoveryList
import app.discair.model.discoverPeekFaces
import app.discair.model.peekReleaseGroup
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** The Discover row peek (idea 9): which release group a row asks for, and which three pictures it shows. */
class DiscoverPeekTest {
    private val rg = "1edd139d-4779-4057-8e12-13c783674f0d"

    private fun raw(json: String): JsonObject = Json.parseToJsonElement(json) as JsonObject

    private fun image(id: Long, types: List<String> = emptyList(), format: String = "jpg") = ArtworkImage(
        imageId = id, release = "r", releases = listOf("r"), edition = "1999 JP CD", types = types, comment = "",
        approved = false, width = 1000, height = 1000, format = format,
    )

    private fun index(
        images: List<ArtworkImage>,
        slots: Map<String, Long> = emptyMap(),
        booklet: List<Long>? = null,
    ) = ArtworkIndex(
        rgid = rg, truncatedReason = null, releases = ArtworkReleaseCounts(1, 1, 0, 0), bestFront = null,
        slots = slots.mapValues { (_, id) -> ArtworkSlot(id, "r", "1999 JP CD", true) },
        booklet = booklet?.let { ArtworkBooklet("r", "1999 JP CD", it) }, images = images,
    )

    @Test fun newReleasesUseTheMbidField() {
        assertEquals(rg, peekReleaseGroup(DiscoveryList.NewReleases, raw("""{"mbid": "$rg"}""")))
    }

    @Test fun otherListsUseOnlyReleaseGroupMbid() {
        assertNull(peekReleaseGroup(DiscoveryList.Classics, raw("""{"mbid": "$rg"}""")))
        assertEquals(rg.uppercase().lowercase(), peekReleaseGroup(DiscoveryList.Personal, raw("""{"release_group_mbid": "${rg.uppercase()}"}""")))
    }

    @Test fun badIdsAreIgnored() {
        assertNull(peekReleaseGroup(DiscoveryList.NewReleases, raw("""{"mbid": "not-an-id"}""")))
        assertNull(peekReleaseGroup(DiscoveryList.Daily, raw("""{"release_group_mbid": 42}""")))
        assertNull(peekReleaseGroup(DiscoveryList.Daily, raw("""{}""")))
    }

    @Test fun peekIsBackThenFirstPageThenMedium() {
        val idx = index(
            images = listOf(image(1), image(2, listOf("Back")), image(3, listOf("Booklet")), image(4, listOf("Medium"))),
            slots = mapOf("Back" to 2, "Medium" to 4),
            booklet = listOf(3),
        )
        assertEquals(listOf(2L, 3L, 4L), discoverPeekFaces(idx).map { it.imageId })
    }

    @Test fun pdfPagesAreNotPeeked() {
        val idx = index(
            images = listOf(image(5, listOf("Booklet"), format = "pdf"), image(6, listOf("Medium"))),
            slots = mapOf("Medium" to 6),
            booklet = listOf(5),
        )
        assertEquals(listOf(6L), discoverPeekFaces(idx).map { it.imageId })
    }

    @Test fun missingPicturesGiveNothing() {
        assertEquals(emptyList<ArtworkImage>(), discoverPeekFaces(null))
        assertEquals(emptyList<ArtworkImage>(), discoverPeekFaces(index(images = listOf(image(1)))))
    }
}
