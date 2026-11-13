package app.discair

import app.discair.model.ArtworkChoices
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Test

/** A pick reaches every screen: owned-cover addresses carry it, nothing else is touched. */
class ArtworkChoicesTest {
    @After fun reset() = ArtworkChoices.replace(emptyMap())

    @Test fun anOwnedCoverCarriesItsPick() {
        ArtworkChoices.replace(mapOf("al-1" to 42L))
        assertEquals("/api/owned/artwork/al-1?c=42", ArtworkChoices.versioned("/api/owned/artwork/al-1"))
        assertEquals("http://h/api/owned/artwork/al-1?size=1000&c=42", ArtworkChoices.versioned("http://h/api/owned/artwork/al-1?size=1000"))
        assertEquals("/api/owned/artwork/al-2?c=0", ArtworkChoices.versioned("/api/owned/artwork/al-2"))
    }

    @Test fun anAddressThatAlreadyCarriesAPickIsLeftAlone() {
        ArtworkChoices.replace(mapOf("al-1" to 42L))
        assertEquals("/api/owned/artwork/al-1?c=7", ArtworkChoices.versioned("/api/owned/artwork/al-1?c=7"))
    }

    @Test fun otherAddressesAreUntouched() {
        assertEquals("https://x/y.jpg", ArtworkChoices.versioned("https://x/y.jpg"))
    }

    @Test fun aNewPickAndItsRemovalChangeTheAddress() {
        ArtworkChoices.set("al-1", 5)
        assertEquals("/api/owned/artwork/al-1?c=5", ArtworkChoices.versioned("/api/owned/artwork/al-1"))
        ArtworkChoices.clear("al-1")
        assertEquals("/api/owned/artwork/al-1?c=0", ArtworkChoices.versioned("/api/owned/artwork/al-1"))
    }

    @Test fun theServerAnswerIsRead() {
        assertEquals(mapOf("a" to 3L, "b" to 9L), ArtworkChoices.parse("""{"choices":{"a":3,"b":9}}"""))
        assertEquals(emptyMap<String, Long>(), ArtworkChoices.parse("nope"))
    }
}
