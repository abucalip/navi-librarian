package app.discair

import android.app.Application
import app.discair.data.FileResponseCache
import app.discair.data.LibrarianRepository
import app.discair.data.LibraryRepository
import app.discair.data.ServerSettings
import app.discair.net.LibrarianClient
import coil3.ImageLoader
import coil3.request.allowHardware
import coil3.network.okhttp.OkHttpNetworkFetcherFactory
import okhttp3.OkHttpClient

/** Process-wide wiring: one HTTP client, so the session cookie is shared by the API and by images. */
class AppContainer(val app: Application) {
    private val cache = FileResponseCache(java.io.File(app.cacheDir, "responses"))
    val connector = AppConnector(app, cache)
    private val http: OkHttpClient get() = connector.client

    val imageLoader: ImageLoader by lazy {
        ImageLoader.Builder(app)
            .allowHardware(false)
            .components { add(OkHttpNetworkFetcherFactory(callFactory = { http.newBuilder().dispatcher(okhttp3.Dispatcher().apply { maxRequestsPerHost = 6 }).build() })) }
            .build()
    }

    /** A repository for the saved servers; the session was established by the connection check. */
    fun repository(settings: ServerSettings, onSessionLost: () -> Unit = {}): LibraryRepository = LibrarianRepository(
        LibrarianClient(http, settings.librarianUrl, settings.librarianUser, settings.librarianPassword, onSessionLost),
        settings.librarianUrl,
        cache,
    )
}
