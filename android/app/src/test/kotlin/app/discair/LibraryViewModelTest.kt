package app.discair

import app.discair.data.AlbumSort
import app.discair.data.ArtistSort
import app.discair.data.LibraryRepository
import app.discair.model.AlbumPage
import app.discair.model.ArtistPage
import app.discair.model.GenrePage
import app.discair.model.GenreTiles
import app.discair.model.LibraryAlbum
import app.discair.model.LibraryArtist
import app.discair.model.Page
import app.discair.model.Picks
import app.discair.model.Shelf
import app.discair.data.Shelves
import app.discair.net.ConnectionException
import app.discair.net.ConnectionFailure
import app.discair.ui.library.LibraryTab
import app.discair.ui.library.LibraryViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class LibraryViewModelTest {
    private val dispatcher = UnconfinedTestDispatcher()

    private class FakeRepo : LibraryRepository {
        data class Call(val query: String, val sort: String, val descending: Boolean?, val cursor: String?)
        val calls = mutableListOf<Call>()
        var fail: Exception? = null

        override fun absolute(path: String) = path
        override fun artists(query: String, sort: ArtistSort, descending: Boolean?, cursor: String?): Page<LibraryArtist> {
            fail?.let { throw it }
            calls += Call(query, sort.param, descending, cursor)
            val first = cursor == null
            return Page(
                items = listOf(LibraryArtist(id = if (first) "a1" else "a2", name = if (first) "A" else "B")),
                nextCursor = if (first) "next" else null, total = 2, indexState = "ready",
            )
        }
        override fun albums(query: String, sort: AlbumSort, descending: Boolean?, cursor: String?): Page<LibraryAlbum> {
            calls += Call(query, sort.param, descending, cursor)
            return Page(items = listOf(LibraryAlbum(id = "x", name = "X")), total = 1, indexState = "ready")
        }
        override fun picks(count: Int) = Picks()
        override fun genres() = GenreTiles()
        override fun shelf(shelf: Shelves, count: Int) = Shelf()
        override fun artistPage(key: String, id: String?, name: String?, mbid: String?) = ArtistPage()
        override fun albumPage(key: String, id: String?, artist: String?, name: String?, year: Int?) = AlbumPage()
        override fun genrePage(tag: String) = GenrePage()
        override fun discovery(list: String, count: Int) = app.discair.model.DiscoveryResult(emptyList(), false, null)
        override fun feedback(action: app.discair.model.FeedbackAction, artist: String, album: String, metadata: kotlinx.serialization.json.JsonObject) = Unit
        override fun refreshList(list: String) = Unit
        override fun artistBio(artist: String): String? = null
        override fun search(query: String, onEvent: (app.discair.model.SearchEvent) -> Unit) = Unit
        override fun albumLinks(artist: String, album: String, mbid: String?) = app.discair.model.AlbumLinks()
        override fun albumImage(artist: String, album: String): String? = null
        override fun artistImage(name: String): String? = null
    }

    @Before fun setUp() = Dispatchers.setMain(dispatcher)
    @After fun tearDown() = Dispatchers.resetMain()

    private fun model(repo: FakeRepo) = LibraryViewModel(repo, dispatcher, searchDelayMs = 0)

    @Test fun loadsTheFirstPageInServerOrder() {
        val vm = model(FakeRepo())
        assertEquals(listOf("A"), vm.state.value.artists.map { it.name })
        assertEquals(2, vm.state.value.total)
    }

    @Test fun loadMoreAppendsUsingTheServersCursor() {
        val repo = FakeRepo()
        val vm = model(repo)
        vm.loadMore()
        assertEquals(listOf("A", "B"), vm.state.value.artists.map { it.name })
        assertEquals("next", repo.calls.last().cursor)
        assertNull(vm.state.value.nextCursor)
        vm.loadMore() // nothing further to fetch
        assertEquals(2, repo.calls.size)
    }

    @Test fun sortAndDirectionAreSentToTheServerNotAppliedLocally() {
        val repo = FakeRepo()
        val vm = model(repo)
        assertNull(repo.calls.last().descending) // the server's own starting direction
        vm.sortArtists(ArtistSort.Albums)
        assertEquals("album_count", repo.calls.last().sort)
        assertTrue(vm.state.value.effectiveDescending)
        vm.flipDirection()
        assertEquals(false, repo.calls.last().descending)
    }

    @Test fun searchGoesToTheServerAndSwitchingTabResetsTheDirection() {
        val repo = FakeRepo()
        val vm = model(repo)
        vm.flipDirection()
        vm.search("sab")
        assertEquals("sab", repo.calls.last().query)
        vm.selectTab(LibraryTab.Albums)
        assertNull(repo.calls.last().descending)
        assertEquals(listOf("X"), vm.state.value.albums.map { it.name })
    }

    @Test fun failureIsClassifiedAndRetryRecovers() {
        val repo = FakeRepo().apply { fail = ConnectionException(ConnectionFailure.Unreachable) }
        val vm = model(repo)
        assertEquals(ConnectionFailure.Unreachable, vm.state.value.failure)
        repo.fail = null
        vm.retry()
        assertNull(vm.state.value.failure)
        assertEquals(1, vm.state.value.artists.size)
    }
}
