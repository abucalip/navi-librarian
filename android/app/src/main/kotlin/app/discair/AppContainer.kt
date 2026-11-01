package app.discair

import android.app.Application
import app.discair.data.FileResponseCache
import app.discair.data.LibrarianRepository
import app.discair.data.LibraryRepository
import app.discair.data.ServerSettings
import app.discair.lyrics.LyricsCache
import app.discair.lyrics.LyricsController
import app.discair.lyrics.SubsonicLyricsSource
import app.discair.net.LibrarianClient
import coil3.ImageLoader
import coil3.request.allowHardware
import coil3.network.okhttp.OkHttpNetworkFetcherFactory
import okhttp3.OkHttpClient
import app.discair.player.FileQueueStorage
import app.discair.player.Media3Port
import app.discair.player.NavidromeScrobbler
import app.discair.player.PlayerController
import app.discair.player.PlayerSettings
import app.discair.player.PrefsPlayerSettings
import app.discair.player.eq.EqRuntimeStatus
import app.discair.player.eq.EqSettingsStore
import kotlinx.coroutines.flow.MutableStateFlow
import app.discair.player.eq.PrefsEqSettingsStore
import app.discair.player.ScrobbleApi
import app.discair.player.ScrobbleCoordinator
import app.discair.player.SendOutcome
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

/** Process-wide wiring: one HTTP client, so the session cookie is shared by the API and by images. */
class AppContainer(val app: Application) {
    private val cache = FileResponseCache(java.io.File(app.cacheDir, "responses"))
    val connector = AppConnector(app, cache)
    private val http: OkHttpClient get() = connector.client

    /** The saved servers, set by the signed-in shell, so playback never opens the encrypted store on the main thread. */
    @Volatile var servers: ServerSettings = ServerSettings()

    /** Sends scrobbles with the Navidrome login that is current when the scrobble goes out. */
    private val scrobbleApi = object : ScrobbleApi {
        override suspend fun send(songId: String, submission: Boolean, timeMs: Long): SendOutcome {
            val s = servers
            val api = NavidromeScrobbler.create(OkHttpClient(), s.navidromeUrl, s.navidromeUser, s.navidromePassword)
                ?: return SendOutcome.Ambiguous
            return api.send(songId, submission, timeMs)
        }
    }

    /** Per-device playback choices (streaming quality, scrobbling). */
    val playerSettings: PlayerSettings by lazy {
        PrefsPlayerSettings(app.getSharedPreferences("discair_player", android.content.Context.MODE_PRIVATE))
    }

    /** Per-device equalizer setting; kept at sign-out on purpose (ANDROID_EQ_CONTRACT.md 6). */
    val eqSettings: EqSettingsStore by lazy {
        PrefsEqSettingsStore(app.getSharedPreferences("discair_eq", android.content.Context.MODE_PRIVATE))
    }

    /** What the playback service says about the equalizer for the song now playing; read by the Equalizer screen. */
    val eqStatus = MutableStateFlow(EqRuntimeStatus())

    private val playerLazy = lazy {
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
        val controller = PlayerController(
            port = Media3Port(app),
            storage = FileQueueStorage(java.io.File(app.filesDir, "player_queue.json")),
            scrobbler = ScrobbleCoordinator(scrobbleApi, CoroutineScope(SupervisorJob() + Dispatchers.Default), enabled = playerSettings.scrobbling),
            scope = scope,
        )
        controller.restore()
        val manager = app.getSystemService(android.net.ConnectivityManager::class.java)
        manager.registerDefaultNetworkCallback(object : android.net.ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: android.net.Network) {
                android.os.Handler(android.os.Looper.getMainLooper()).post { controller.networkAvailable() }
            }
        })
        connector.onSignedOut = { android.os.Handler(android.os.Looper.getMainLooper()).post { controller.signOut() } }
        controller
    }

    /** The one player controller. It binds to the playback service on first use and restores the saved queue, paused. */
    val player: PlayerController get() = playerLazy.value

    /** Saves the choice and applies it to a player that is already running. */
    fun setScrobbling(on: Boolean) {
        playerSettings.scrobbling = on
        if (playerLazy.isInitialized()) playerLazy.value.setScrobbling(on)
    }

    private val lyricsCache = LyricsCache(
        java.io.File(app.cacheDir, "lyrics"),
        scope = { "${servers.navidromeUrl}|${servers.navidromeUser}" },
    ).also { connector.lyricsCache = it }

    /** Lyrics for the song that is playing; fetches only while the Now Playing sheet shows the Lyrics view. */
    val lyrics: LyricsController by lazy {
        val source = SubsonicLyricsSource(
            OkHttpClient(),
            login = { servers.let { Triple(it.navidromeUrl, it.navidromeUser, it.navidromePassword) } },
        )
        LyricsController(
            CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate), source, lyricsCache, Dispatchers.IO,
        )
    }

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
