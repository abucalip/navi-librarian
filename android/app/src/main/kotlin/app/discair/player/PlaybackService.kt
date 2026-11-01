package app.discair.player

import android.content.Context
import android.content.Intent
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.util.UnstableApi
import androidx.media3.datasource.DefaultDataSource
import androidx.media3.datasource.okhttp.OkHttpDataSource
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import androidx.media3.session.MediaSession
import androidx.media3.session.MediaSessionService
import app.discair.DiscairApplication
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
        val exo = ExoPlayer.Builder(this)
            .setMediaSourceFactory(DefaultMediaSourceFactory(dataSource))
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(C.USAGE_MEDIA)
                    .setContentType(C.AUDIO_CONTENT_TYPE_MUSIC)
                    .build(),
                /* handleAudioFocus = */ true,
            )
            .setHandleAudioBecomingNoisy(true)
            .build()
        val resolver = StreamResolver(container)
        val mediaSession = MediaSession.Builder(this, exo)
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
        player = exo
        session = mediaSession
        guard = ReleaseGuard {
            mediaSession.release()
            exo.release()
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
        /** Stops playback and releases the player, for example on sign-out. */
        fun stop(context: Context) {
            context.applicationContext.stopService(Intent(context.applicationContext, PlaybackService::class.java))
        }
    }
}
