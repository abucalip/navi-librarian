package app.discair.ui.library

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import app.discair.data.AlbumSort
import app.discair.data.ArtistSort
import app.discair.data.LibraryRepository
import app.discair.model.LibraryAlbum
import app.discair.model.LibraryArtist
import app.discair.net.ConnectionFailure
import app.discair.net.classifyException
import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

enum class LibraryTab { Artists, Albums }

data class LibraryState(
    val tab: LibraryTab = LibraryTab.Artists,
    val query: String = "",
    val artistSort: ArtistSort = ArtistSort.Name,
    val albumSort: AlbumSort = AlbumSort.Name,
    /** Null means the server's own starting direction for the sort. */
    val descending: Boolean? = null,
    val artists: List<LibraryArtist> = emptyList(),
    val albums: List<LibraryAlbum> = emptyList(),
    val nextCursor: String? = null,
    val total: Int? = null,
    /** `fresh`, `stale`, `building` or `unavailable`, as the server reports its owned index. */
    val indexState: String = "",
    val loading: Boolean = true,
    val failure: ConnectionFailure? = null,
) {
    val effectiveDescending: Boolean
        get() = descending ?: if (tab == LibraryTab.Artists) artistSort.startsDescending else albumSort.startsDescending
}

/** Browses the owned library in the server's order. Sorting and filtering happen on the server. */
class LibraryViewModel(
    private val repo: LibraryRepository,
    private val io: CoroutineDispatcher = Dispatchers.IO,
    private val searchDelayMs: Long = 300,
) : ViewModel() {
    private val _state = MutableStateFlow(LibraryState())
    val state: StateFlow<LibraryState> = _state.asStateFlow()
    private var job: Job? = null

    init { reload() }

    fun selectTab(tab: LibraryTab) {
        if (tab == _state.value.tab) return
        _state.update { it.copy(tab = tab, descending = null) }
        reload()
    }

    fun search(text: String) {
        _state.update { it.copy(query = text) }
        reload(debounce = true)
    }

    fun sortArtists(sort: ArtistSort) { _state.update { it.copy(artistSort = sort, descending = null) }; reload() }
    fun sortAlbums(sort: AlbumSort) { _state.update { it.copy(albumSort = sort, descending = null) }; reload() }

    fun flipDirection() {
        _state.update { it.copy(descending = !it.effectiveDescending) }
        reload()
    }

    fun retry() = reload()

    fun loadMore() {
        val s = _state.value
        if (s.loading || s.nextCursor == null) return
        fetch(s, s.nextCursor, append = true)
    }

    private fun reload(debounce: Boolean = false) {
        job?.cancel()
        _state.update { it.copy(loading = true, failure = null, nextCursor = null) }
        job = viewModelScope.launch {
            if (debounce) delay(searchDelayMs)
            fetch(_state.value, null, append = false)
        }
    }

    private fun fetch(s: LibraryState, cursor: String?, append: Boolean) {
        val request = viewModelScope.launch {
            _state.update { it.copy(loading = true, failure = null) }
            try {
                withContext(io) {
                    // An explicit direction is sent only when the user flipped it.
                    if (s.tab == LibraryTab.Artists) {
                        val page = repo.artists(s.query, s.artistSort, s.descending, cursor)
                        _state.update {
                            it.copy(
                                artists = if (append) it.artists + page.items else page.items,
                                nextCursor = page.nextCursor, total = page.total,
                                indexState = page.indexState, loading = false,
                            )
                        }
                    } else {
                        val page = repo.albums(s.query, s.albumSort, s.descending, cursor)
                        _state.update {
                            it.copy(
                                albums = if (append) it.albums + page.items else page.items,
                                nextCursor = page.nextCursor, total = page.total,
                                indexState = page.indexState, loading = false,
                            )
                        }
                    }
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                _state.update { it.copy(loading = false, failure = classifyException(e, networkAvailable = true)) }
            }
        }
        if (!append) job = request
    }
}

class LibraryViewModelFactory(private val repo: LibraryRepository) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T = LibraryViewModel(repo) as T
}
