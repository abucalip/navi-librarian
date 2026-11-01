package app.discair

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import app.discair.data.CredentialStore
import app.discair.data.EncryptedPrefs
import app.discair.data.ServerSettings
import app.discair.data.SettingsStore
import app.discair.net.ConnectionFailure
import app.discair.net.LibrarianClient
import app.discair.net.NavidromeClient
import app.discair.net.PersistentCookieJar
import app.discair.net.classifyException
import app.discair.net.httpClient

/** Outcome of checking one server. */
sealed interface Check {
    data object Idle : Check
    data object Pending : Check
    data object Ok : Check
    data class Failed(val failure: ConnectionFailure) : Check
}

/** Checks the two servers. Kept free of Android types so the view model can be tested. */
interface Connector {
    fun networkAvailable(): Boolean
    fun checkLibrarian(url: String, user: String, password: String): Check
    fun checkNavidrome(url: String, user: String, password: String): Check
    fun signOut(librarianUrl: String, user: String, password: String)

    /** Saved copies of earlier reads exist, so the app can open without a connection. */
    fun hasOfflineData(): Boolean = false
}

class AppConnector(context: Context, private val cache: app.discair.data.ResponseCache = app.discair.data.NoCache) : Connector {
    private val appContext = context.applicationContext
    // Opening encrypted preferences can take hundreds of milliseconds, so it happens on first use,
    // which is always on the IO dispatcher.
    private val cookies by lazy { PersistentCookieJar(EncryptedPrefs.open(appContext, "discair_session")) }
    private val http by lazy { httpClient(cookies) }
    val client: okhttp3.OkHttpClient get() = http

    /** Set by the container once the player exists, so sign-out also empties the in-memory queue. */
    @Volatile var onSignedOut: () -> Unit = {}

    override fun networkAvailable(): Boolean {
        val manager = appContext.getSystemService(ConnectivityManager::class.java)
        val caps = manager.getNetworkCapabilities(manager.activeNetwork ?: return false)
        return caps?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) == true
    }

    override fun checkLibrarian(url: String, user: String, password: String): Check = run {
        LibrarianClient(http, url, user, password).signIn()
    }

    override fun checkNavidrome(url: String, user: String, password: String): Check = run {
        NavidromeClient(http, url, user, password).ping()
    }

    override fun signOut(librarianUrl: String, user: String, password: String) {
        LibrarianClient(http, librarianUrl, user, password).signOut()
        cookies.clear()
        onSignedOut() // clears the queue and stops audio first, then the service is stopped
        app.discair.player.PlaybackService.stop(appContext) // contract 3.2: sign-out releases the player
        app.discair.player.FileQueueStorage(java.io.File(appContext.filesDir, "player_queue.json")).clear()
        cache.clear() // saved copies belong to the signed-in account
    }

    override fun hasOfflineData() = cache.hasContent()

    private inline fun run(block: () -> Unit): Check = try {
        block()
        Check.Ok
    } catch (e: Exception) {
        Check.Failed(classifyException(e, networkAvailable()))
    }
}

/** Opens the encrypted settings on first use rather than when the view model is created. */
class LazySettingsStore(context: Context) : SettingsStore {
    private val delegate by lazy {
        CredentialStore(EncryptedPrefs.open(context.applicationContext, "discair_settings"))
    }

    override fun load() = delegate.load()
    override fun save(settings: ServerSettings) = delegate.save(settings)
    override fun clear() = delegate.clear()
}
