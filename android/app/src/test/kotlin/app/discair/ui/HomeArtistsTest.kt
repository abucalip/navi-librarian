package app.discair.ui

import app.discair.model.ShelfAlbum
import app.discair.ui.home.HomeArtists
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HomeArtistsTest {
    private fun al(artist: String, id: String = "", name: String = "x") = ShelfAlbum(name = name, artist = artist, artistId = id)

    @Test fun recentComesFirstThenFrequentInOrderOfFirstAppearance() {
        val r = HomeArtists.from(listOf(al("B"), al("A")), listOf(al("C"), al("A"), al("D")))
        assertEquals(listOf("B", "A", "C", "D"), r.map { it.name })
    }

    @Test fun anArtistAppearsOnceWhateverTheCaseOrTheAlbum() {
        val r = HomeArtists.from(listOf(al("Bjork", "1", "a"), al("bjork", "", "b")), listOf(al(" Bjork ", "1", "c")))
        assertEquals(1, r.size)
        assertEquals("1", r[0].id)
    }

    @Test fun stopsAtEight() {
        val many = (1..20).map { al("Artist $it") }
        val r = HomeArtists.from(many, emptyList())
        assertEquals(HomeArtists.LIMIT, r.size)
        assertEquals("Artist 8", r.last().name)
    }

    @Test fun blankNamesAreSkipped() {
        assertEquals(listOf("A"), HomeArtists.from(listOf(al(""), al("  "), al("A")), emptyList()).map { it.name })
    }

    @Test fun emptyShelvesGiveNothing() {
        assertTrue(HomeArtists.from(emptyList(), emptyList()).isEmpty())
    }

    @Test fun fewerThanThreeIsNotEnough() {
        assertFalse(HomeArtists.enough(HomeArtists.from(listOf(al("A"), al("B")), emptyList())))
        assertTrue(HomeArtists.enough(HomeArtists.from(listOf(al("A"), al("B")), listOf(al("C")))))
    }
}
