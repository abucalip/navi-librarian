package app.discair

import app.discair.model.AlbumPage
import app.discair.model.ApiJson
import app.discair.model.ArtistPage
import app.discair.model.GenrePage
import app.discair.model.GenreTiles
import app.discair.model.ImageLookup
import app.discair.model.LibraryAlbum
import app.discair.model.LibraryArtist
import app.discair.model.Page
import app.discair.model.Picks
import app.discair.model.Shelf
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.serializer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Every Phase 2 DTO must decode the recorded response for its route. */
class DtoFixtureTest {
    private fun body(path: String): String {
        val text = javaClass.classLoader!!.getResource("librarian/$path.json")!!.readText()
        return Json.parseToJsonElement(text).jsonObject["response"]!!.jsonObject["body"].toString()
    }

    private inline fun <reified T> decode(path: String): T = ApiJson.decodeFromString(serializer<T>(), body(path))

    @Test fun libraryArtists() {
        val page = decode<Page<LibraryArtist>>("library_artists")
        assertTrue(page.items.isNotEmpty())
        assertTrue(page.items.all { it.id.isNotBlank() && it.key.isNotBlank() && it.name.isNotBlank() })
        assertNotNull(page.nextCursor)
        assertEquals("fresh", page.indexState)
    }

    @Test fun libraryAlbums() {
        val page = decode<Page<LibraryAlbum>>("library_albums")
        assertTrue(page.items.all { it.key.contains('/') && it.artistKey.isNotBlank() })
    }

    @Test fun dashboard() {
        assertTrue(decode<GenreTiles>("dashboard_genres").items.all { it.tag.isNotBlank() })
        val picks = decode<Picks>("dashboard_picks")
        assertTrue(picks.items.all { it.artist.isNotBlank() && it.album.isNotBlank() })
        for (shelf in listOf("newest", "recent", "frequent")) {
            assertTrue(decode<Shelf>("dashboard_albums_$shelf").items.all { it.id.isNotBlank() && it.owned })
        }
    }

    @Test fun artistPage() {
        val s = decode<ArtistPage>("artist_page").sections
        assertEquals("Abd Al Malik", s.artist.artist!!.name)
        assertTrue(s.artist.artist!!.owned)
        assertTrue(s.ownedAlbums.items.all { it.key.contains('/') })
        assertTrue(s.topSongs.items.isNotEmpty())
        assertTrue(s.missingAlbums.items.isNotEmpty())
        assertTrue(s.similar.items.isNotEmpty())
        assertTrue(s.bio.bio!!.text.isNotBlank())
    }

    @Test fun albumPage() {
        val s = decode<AlbumPage>("album_page").sections
        val album = s.album.album!!
        assertEquals("beatles/1", album.key)
        assertTrue(album.owned)
        assertTrue(s.tracks.items.isNotEmpty())
        assertTrue(s.tracks.items.all { it.title.isNotBlank() })
        assertTrue(s.similarAlbums.items.isNotEmpty())
        assertFalse(s.similarAlbums.items.first().owned)
    }

    @Test fun genrePage() {
        val s = decode<GenrePage>("genre_page").sections
        assertTrue(s.artists.items.isNotEmpty())
        assertTrue(s.albums.items.all { it.key.contains('/') })
    }

    @Test fun imageLookups() {
        assertNotNull(decode<ImageLookup>("artwork").artworkUrl)
        assertNotNull(decode<ImageLookup>("artist_image").artworkUrl)
    }

    @Test fun missingOptionalFieldsDoNotBreakDecoding() {
        val page = ApiJson.decodeFromString(serializer<AlbumPage>(), """{"sections":{"album":{"available":true,"album":{"name":"X"}}}}""")
        assertEquals("X", page.sections.album.album!!.name)
        assertTrue(page.sections.tracks.items.isEmpty())
    }
}

/** The genre tile colour must match the web's `genreTileHue`, so both clients colour a genre alike. */
class GenreHueTest {
    @org.junit.Test fun matchesTheWebHash() {
        org.junit.Assert.assertEquals(341, app.discair.ui.common.genreHue("rock"))
        org.junit.Assert.assertEquals(82, app.discair.ui.common.genreHue("progressive rock"))
        org.junit.Assert.assertEquals(0, app.discair.ui.common.genreHue(""))
    }
}
