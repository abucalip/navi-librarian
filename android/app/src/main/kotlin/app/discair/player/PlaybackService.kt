package app.discair.player

import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.datasource.DefaultDataSource
import androidx.media3.datasource.okhttp.OkHttpDataSource
import androidx.media3.exoplayer.DefaultRenderersFactory
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.audio.AudioSink
import androidx.media3.exoplayer.audio.DefaultAudioSink
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
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
        private const val TAG = "Crossfade"

        /** Stops playback and releases the player, for example on sign-out. */
        fun stop(context: Context) {
            context.applicationContext.stopService(Intent(context.applicationContext, PlaybackService::class.java))
        }
    }
}
