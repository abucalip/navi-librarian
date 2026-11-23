package app.discair.model

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AlbumReviewsDtoTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun decodesCritiqueBrainzAndPressReviews() {
        val raw = """
            {
              "critiquebrainz": [
                {
                  "id": "c807d0b4-0dd0-43fe-a7c4-d29bb61f389e",
                  "source": "CritiqueBrainz",
                  "origin": "BBC",
                  "full_text": "Paragraph one.\n\nParagraph two.",
                  "paragraphs": ["Paragraph one.", "Paragraph two."],
                  "quote": "Paragraph one.",
                  "url": "https://critiquebrainz.org/review/c807d0b4-0dd0-43fe-a7c4-d29bb61f389e",
                  "language": "ar",
                  "author": "Reviewer",
                  "rating": 5,
                  "license": "CC BY-SA 3.0",
                  "license_url": "https://creativecommons.org/licenses/by-sa/3.0/",
                  "published_on": "2022-10-17"
                }
              ],
              "reviews": [
                {"source": "Pitchfork", "quote": "Great album.", "url": "https://pitchfork.com/example"}
              ],
              "retryable": false
            }
        """.trimIndent()

        val decoded = json.decodeFromString(AlbumReviews.serializer(), raw)
        assertEquals(1, decoded.critiquebrainz.size)
        val cb = decoded.critiquebrainz[0]
        assertEquals("BBC", cb.origin)
        assertEquals(listOf("Paragraph one.", "Paragraph two."), cb.paragraphs)
        assertEquals("ar", cb.language)
        assertEquals(5, cb.rating)
        assertEquals("CC BY-SA 3.0", cb.license)
        assertEquals("https://creativecommons.org/licenses/by-sa/3.0/", cb.licenseUrl)
        assertEquals("2022-10-17", cb.publishedOn)
        assertEquals(1, decoded.reviews.size)
        assertEquals("Pitchfork", decoded.reviews[0].source)
    }

    @Test
    fun decodesLegacyResponseWithoutCritiqueBrainz() {
        val raw = """{"reviews": [{"source": "The Guardian", "quote": "Classic.", "url": "https://theguardian.com/x"}]}"""
        val decoded = json.decodeFromString(AlbumReviews.serializer(), raw)
        assertTrue(decoded.critiquebrainz.isEmpty())
        assertEquals(1, decoded.reviews.size)
        assertNull(CritiqueBrainzReview().origin)
    }
}
