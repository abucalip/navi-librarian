package app.discair.player

import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import androidx.compose.ui.graphics.toArgb
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.datasource.DefaultDataSource
import androidx.media3.exoplayer.DefaultLoadControl
import androidx.media3.datasource.okhttp.OkHttpDataSource
import androidx.media3.exoplayer.DefaultRenderersFactory
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.audio.AudioSink
import androidx.media3.exoplayer.audio.DefaultAudioSink
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import androidx.media3.session.DefaultMediaNotificationProvider
import androidx.media3.session.MediaNotification
import androidx.media3.session.MediaSession
import androidx.media3.session.MediaSessionService
import app.discair.DiscairApplication
import app.discair.player.crossfade.Cancelable
import app.discair.player.crossfade.CrossfadeEngine
import app.discair.player.crossfade.ExoFadePlayer
import app.discair.player.crossfade.ExoTwins
import app.discair.player.crossfade.Scheduler
import app.discair.player.eq.EqAudioProcessor
import app.discair.player.eq.EqBinding
import app.discair.player.eq.EqRuntimeStatus
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture
import java.util.concurrent.TimeUnit
import okhttp3.OkHttpClient

/**
 * Plays owned songs straight from Navidrome. The service is the only place that sees the Navidrome
 * credentials for playback: a controller adds items by song id only, and the stream URL (with a fresh
 * salt and token) is built here, so no credential crosses the session or lands in a media item's tag.
 *
 * Lifecycle (ANDROID_PLAYER_CONTRACT 3.2): the player and session are released exactly once when the
 * service is destroyed; removing the task pauses and stops the service; audio focus and headphone
 * unplugging are handled by ExoPlayer.
 */
@androidx.annotation.OptIn(UnstableApi::class)
class PlaybackService : MediaSessionService() {
    private var session: MediaSession? = null
    private var player: ExoPlayer? = null
    private var guard: ReleaseGuard? = null

    override fun onCreate() {
        super.onCreate()
        val container = (application as DiscairApplication).container
        // A client of its own: no Librarian cookies, no redirects, and refused bodies become failures.
        val http = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .followRedirects(false)
            .followSslRedirects(false)
            .addInterceptor(RefusedBodyInterceptor())
            .build()
        val dataSource = DefaultDataSource.Factory(this, OkHttpDataSource.Factory(http))
        val attrs = AudioAttributes.Builder().setUsage(C.USAGE_MEDIA).setContentType(C.AUDIO_CONTENT_TYPE_MUSIC).build()
        val handler = Handler(Looper.getMainLooper())
        // One player, built the same way every time. The equalizer sits in the audio sink only (ANDROID_EQ_CONTRACT.md 4);
        // with it off it copies bytes unchanged. A second player is built only while crossfade is on (contract 5.4).
        var engineRef: CrossfadeEngine? = null
        // Every player reports; only the one the engine calls active is passed on.
        fun listenerFor(p: ExoPlayer) = object : Player.Listener {
            private fun mine() = engineRef?.active.let { it is ExoFadePlayer && it.exo === p }
            override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) { if (mine()) engineRef?.onActiveChanged() }
            override fun onPlaybackStateChanged(state: Int) { if (mine() && state == Player.STATE_READY) engineRef?.onActiveReady() }
            override fun onPlayWhenReadyChanged(playWhenReady: Boolean, reason: Int) { if (mine()) engineRef?.onActivePlayWhenReady(playWhenReady) }
            override fun onPositionDiscontinuity(oldPosition: Player.PositionInfo, newPosition: Player.PositionInfo, reason: Int) {
                if (mine() && reason == Player.DISCONTINUITY_REASON_SEEK) engineRef?.onActiveInterrupted("seek")
            }
            override fun onPlayerError(error: PlaybackException) { if (mine()) engineRef?.onActiveInterrupted("error ${error.errorCodeName}") }
        }
        // ExoPlayer's stock settings resume after only 2 s of audio once a stall happens, so on a slow or jittery link
        // (Tailscale relay, mobile data) a lossless file, which needs several times the bytes per second of an MP3,
        // drains again at once and stalls over and over. Resume with a real cushion, read further ahead, and count the
        // buffer in seconds, not bytes, so hi-res FLAC is not capped at a few seconds by the byte limit.
        val loadControl = DefaultLoadControl.Builder()
            .setBufferDurationsMs(MIN_BUFFER_MS, MAX_BUFFER_MS, START_BUFFER_MS, REBUFFER_MS)
            .setPrioritizeTimeOverSizeThresholds(true)
            .build()
        fun buildPlayer(focus: Boolean, primary: Boolean): Pair<ExoPlayer, () -> Unit> {
            val eq = EqAudioProcessor()
            val renderers = object : DefaultRenderersFactory(this@PlaybackService) {
                override fun buildAudioSink(
                    context: Context,
                    enableFloatOutput: Boolean,
                    enableAudioTrackPlaybackParams: Boolean,
                ): AudioSink = DefaultAudioSink.Builder(context)
                    .setEnableFloatOutput(enableFloatOutput)
                    .setEnableAudioTrackPlaybackParams(enableAudioTrackPlaybackParams)
                    .setAudioProcessors(arrayOf(eq))
                    .build()
            }
            eq.statusListener = { container.eqStatus.value = it } // whichever player is sounding publishes
            val binding = EqBinding(container.eqSettings, eq)
            val player = ExoPlayer.Builder(this@PlaybackService, renderers)
                .setMediaSourceFactory(DefaultMediaSourceFactory(dataSource))
                .setLoadControl(loadControl)
                .setAudioAttributes(attrs, /* handleAudioFocus = */ focus)
                .setHandleAudioBecomingNoisy(true)
                .build()
            // Gapless: the first ten seconds of the next song load before the current one ends, so a slow link
            // (Tailscale, mobile data) does not leave a pause. ExoPlayer trims encoder padding itself when the file
            // carries gapless data (MP3 with a LAME or Xing header, M4A, FLAC, Opus).
            player.preloadConfiguration = ExoPlayer.PreloadConfiguration(PRELOAD_NEXT_US)
            player.addListener(listenerFor(player))
            return player to { binding.close(); eq.statusListener = null }
        }
        val twins = ExoTwins(attrs, handler, build = { buildPlayer(focus = false, primary = false) }, log = { Log.i(TAG, it) })
        val (exo, closeFirst) = buildPlayer(focus = true, primary = true)
        val first = twins.adopt(exo, closeFirst)
        val resolver = StreamResolver.forContainer(container)
        val mediaSession = MediaSession.Builder(this, twins.mirrorOf(first))
            .setCallback(object : MediaSession.Callback {
                // Only this app and the system (notification, lock screen, Bluetooth) may control playback.
                override fun onConnect(
                    mediaSession: MediaSession,
                    controller: MediaSession.ControllerInfo,
                ): MediaSession.ConnectionResult =
                    if (controller.packageName == packageName || controller.isTrusted) {
                        MediaSession.ConnectionResult.accept(
                            MediaSession.ConnectionResult.DEFAULT_SESSION_COMMANDS,
                            MediaSession.ConnectionResult.DEFAULT_PLAYER_COMMANDS,
                        )
                    } else {
                        MediaSession.ConnectionResult.reject()
                    }

                override fun onAddMediaItems(
                    mediaSession: MediaSession,
                    controller: MediaSession.ControllerInfo,
                    mediaItems: MutableList<MediaItem>,
                ): ListenableFuture<MutableList<MediaItem>> =
                    Futures.immediateFuture(resolver.resolve(mediaItems).toMutableList())
            })
            .build()
        // The notification is drawn by the system, so the theme reaches it only as its accent colour: a Neobrut theme tints it.
        setMediaNotificationProvider(ThemedNotificationProvider(DefaultMediaNotificationProvider(this)) { notificationAccent(container) })
        // Crossfade (ANDROID_CROSSFADE_CONTRACT.md): off by default, so the engine does nothing and no second player exists.
        val scheduler = object : Scheduler {
            override fun nowMs() = SystemClock.elapsedRealtime()
            override fun postDelayed(delayMs: Long, block: () -> Unit): Cancelable {
                val r = Runnable { block() }
                handler.postDelayed(r, delayMs)
                return Cancelable { handler.removeCallbacks(r) }
            }
        }
        val engine = CrossfadeEngine(
            primary = first,
            settings = { container.playerSettings.crossfade },
            twin = twins,
            swapSession = { fp -> mediaSession.player = twins.mirrorOf(fp) },
            scheduler = scheduler,
            log = { Log.i(TAG, it) },
        )
        engineRef = engine
        val settingsWatch = container.playerSettings.onChange { handler.post { engine.onSettingsChanged() } }
        player = exo
        session = mediaSession
        guard = ReleaseGuard {
            settingsWatch.close()
            engine.close()
            container.eqStatus.value = EqRuntimeStatus()
            mediaSession.release()
            twins.releaseAll()
        }
    }

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaSession? = session

    /** Swiping the app away stops playback; nothing keeps running in the background after that. */
    override fun onTaskRemoved(rootIntent: Intent?) {
        pauseAllPlayersAndStopSelf()
    }

    override fun onDestroy() {
        guard?.release()
        session = null
        player = null
        super.onDestroy()
    }

    companion object {
        private const val PRELOAD_NEXT_US = 10_000_000L
        private const val MIN_BUFFER_MS = 30_000
        private const val MAX_BUFFER_MS = 60_000
        private const val START_BUFFER_MS = 1_500
        private const val REBUFFER_MS = 8_000
        private const val TAG = "Crossfade"

        /** Stops playback and releases the player, for example on sign-out. */
        fun stop(context: Context) {
            context.applicationContext.stopService(Intent(context.applicationContext, PlaybackService::class.java))
        }
    }
}

/** The accent of the Neobrut theme in use (the day or the night one, as the phone is set), or null for a Classic theme. */
private fun PlaybackService.notificationAccent(container: app.discair.AppContainer): Int? {
    val dark = (resources.configuration.uiMode and android.content.res.Configuration.UI_MODE_NIGHT_MASK) == android.content.res.Configuration.UI_MODE_NIGHT_YES
    val palette = container.appearance.palette(dark)
    return if (palette.brutal) palette.accent.toArgb() else null
}

/** Media3's stock notification, with the notification colour set to a Neobrut theme's accent. A Classic theme is left as it was. */
@UnstableApi
private class ThemedNotificationProvider(
    private val base: MediaNotification.Provider,
    private val accent: () -> Int?,
) : MediaNotification.Provider by base {
    override fun createNotification(
        mediaSession: MediaSession,
        mediaButtonPreferences: com.google.common.collect.ImmutableList<androidx.media3.session.CommandButton>,
        actionFactory: MediaNotification.ActionFactory,
        onNotificationChangedCallback: MediaNotification.Provider.Callback,
    ): MediaNotification {
        val made = base.createNotification(mediaSession, mediaButtonPreferences, actionFactory, onNotificationChangedCallback)
        accent()?.let { made.notification.color = it }
        return made
    }
}
