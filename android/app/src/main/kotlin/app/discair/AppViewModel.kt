package app.discair

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import app.discair.data.ServerSettings
import app.discair.data.SettingsStore
import app.discair.net.ConnectionFailure
import app.discair.net.UrlProblem
import app.discair.net.UrlResult
import app.discair.net.normalizeBaseUrl
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Checking: a saved setup is being verified. Unavailable: it was verified and failed. */
enum class Screen { Checking, Setup, Unavailable, Home }

data class UiState(
    val screen: Screen = Screen.Checking,
    /** What the setup form shows; may differ from [saved] while the user edits. */
    val form: ServerSettings = ServerSettings(),
    /** What is stored on the device and was last known to work. */
    val saved: ServerSettings = ServerSettings(),
    val showMissing: Boolean = false,
    val librarianUrlProblem: UrlProblem? = null,
    val navidromeUrlProblem: UrlProblem? = null,
    val librarian: Check = Check.Idle,
    val navidrome: Check = Check.Idle,
    /** Why the app returned to setup on its own (for example the saved password was rejected). */
    val notice: String? = null,
) {
    /** Editing existing settings, so Cancel and system back have somewhere to return to. */
    val canCancelEdit: Boolean get() = saved.isComplete
}

class AppViewModel(
    private val store: SettingsStore,
    private val connector: Connector,
    private val io: CoroutineDispatcher = Dispatchers.IO,
) : ViewModel() {
    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    init {
        // The encrypted store is opened off the main thread; the Checking screen shows meanwhile.
        viewModelScope.launch {
            val saved = withContext(io) { store.load() }
            _state.update { it.copy(form = saved, saved = saved) }
            if (saved.isComplete) verify(saved, save = false)
            else _state.update { it.copy(screen = Screen.Setup) }
        }
    }

    fun edit(change: (ServerSettings) -> ServerSettings) = _state.update {
        it.copy(form = change(it.form), librarianUrlProblem = null, navidromeUrlProblem = null)
    }

    /** Validates the form, checks both servers, and stores the settings only if both pass. */
    fun connect() {
        val form = _state.value.form
        if (!form.isComplete) {
            _state.update { it.copy(showMissing = true) }
            return
        }
        val librarian = normalizeBaseUrl(form.librarianUrl)
        val navidrome = normalizeBaseUrl(form.navidromeUrl)
        val problemL = (librarian as? UrlResult.Bad)?.problem
        val problemN = (navidrome as? UrlResult.Bad)?.problem
        if (problemL != null || problemN != null) {
            _state.update { it.copy(librarianUrlProblem = problemL, navidromeUrlProblem = problemN) }
            return
        }
        verify(
            form.copy(
                librarianUrl = (librarian as UrlResult.Ok).url,
                navidromeUrl = (navidrome as UrlResult.Ok).url,
            ),
            save = true,
        )
    }

    /** Re-checks the saved servers, for example after Tailscale was switched on. */
    fun recheck() = verify(_state.value.saved, save = false)

    /**
     * The server rejected the saved credentials during a session. Silent recovery is impossible, so
     * return to setup with the saved values and say why (contract 4.1). Safe to call repeatedly.
     */
    fun sessionExpired() {
        _state.update {
            if (it.screen != Screen.Home) it else it.copy(
                screen = Screen.Setup, form = it.saved, showMissing = false,
                librarian = Check.Idle, navidrome = Check.Idle,
                notice = "You were signed out: Librarian no longer accepts the saved user name and password. " +
                    "Check them, then connect again.",
            )
        }
    }

    fun editServers() = _state.update {
        it.copy(screen = Screen.Setup, form = it.saved, showMissing = false,
            librarianUrlProblem = null, navidromeUrlProblem = null)
    }

    /** Leaves the editor without keeping changes and checks the saved servers again. */
    fun cancelEdit() {
        if (!_state.value.canCancelEdit) return
        _state.update { it.copy(form = it.saved, showMissing = false) }
        recheck()
    }

    fun signOut() {
        viewModelScope.launch {
            withContext(io) {
                val saved = store.load()
                if (saved.isComplete) connector.signOut(saved.librarianUrl, saved.librarianUser, saved.librarianPassword)
                store.clear()
            }
            _state.value = UiState(screen = Screen.Setup)
        }
    }

    private fun verify(settings: ServerSettings, save: Boolean) {
        _state.update {
            it.copy(
                screen = if (save) Screen.Setup else Screen.Checking,
                librarian = Check.Pending,
                navidrome = Check.Pending,
            )
        }
        viewModelScope.launch {
            val librarian = async(io) {
                connector.checkLibrarian(settings.librarianUrl, settings.librarianUser, settings.librarianPassword)
            }
            val navidrome = async(io) {
                connector.checkNavidrome(settings.navidromeUrl, settings.navidromeUser, settings.navidromePassword)
            }
            val l = librarian.await()
            val n = navidrome.await()
            val ok = l is Check.Ok && n is Check.Ok
            // No connection but earlier reads were saved: open on those instead of a dead end. A server
            // that answered with a refusal is not "offline", so that case still stops here.
            val offline = !save && !ok && withContext(io) { connector.hasOfflineData() } &&
                (l as? Check.Failed)?.failure.let { it == ConnectionFailure.NoNetwork || it == ConnectionFailure.Unreachable }
            if (ok && save) withContext(io) { store.save(settings) }
            _state.update {
                it.copy(
                    librarian = l,
                    navidrome = n,
                    form = if (ok && save) settings else it.form,
                    saved = if (ok && save) settings else it.saved,
                    showMissing = false,
                    notice = null,
                    screen = when {
                        ok || offline -> Screen.Home
                        save -> Screen.Setup
                        else -> Screen.Unavailable
                    },
                )
            }
        }
    }
}

class AppViewModelFactory(private val container: AppContainer) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        AppViewModel(LazySettingsStore(container.app), container.connector) as T
}
