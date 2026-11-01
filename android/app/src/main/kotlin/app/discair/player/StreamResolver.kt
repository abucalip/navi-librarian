package app.discair.player

import androidx.media3.common.MediaItem
import app.discair.AppContainer
import app.discair.data.CredentialStore
import app.discair.data.EncryptedPrefs
import app.discair.data.ServerSettings
import okhttp3.HttpUrl

/**
 * Turns media items that carry only a song id into items with a signed stream URL.
 * Items with an invalid id, or with no saved Navidrome login, are dropped, so nothing is ever requested for them.
 * The streaming quality is read each time, so a change in Settings applies to songs started afterwards.
 */
class StreamResolver(
    private val settings: () -> ServerSettings,
    private val quality: () -> StreamQuality = { StreamQuality.Original },
    private val format: () -> TranscodeFormat? = { null },
) {
    /** The signed address for one song, or null when the id is invalid or the login is incomplete. */
    fun urlFor(songId: String, itemFormatWire: String? = null): HttpUrl? {
        val saved = settings()
        if (saved.navidromeUrl.isBlank() || saved.navidromeUser.isBlank() || saved.navidromePassword.isBlank()) return null
        if (!isValidSongId(songId)) return null
        // A per-item request (the MP3 fallback after an unsupported-format error) wins over the global setting.
        val itemFormat = itemFormatWire?.let { wire -> TranscodeFormat.entries.firstOrNull { it.wire == wire } }
        return StreamUrlBuilder(saved.navidromeUrl, saved.navidromeUser, saved.navidromePassword)
            .build(songId, quality(), itemFormat ?: format())
    }

    fun resolve(items: List<MediaItem>): List<MediaItem> = items.mapNotNull { item ->
        val url = urlFor(item.mediaId, item.requestMetadata.extras?.getString(EXTRA_FORMAT)) ?: return@mapNotNull null
        item.buildUpon().setUri(url.toString()).build()
    }

    companion object {
        /**
         * Uses the servers the signed-in screens already hold, so the encrypted store is not opened on the
         * service's main thread; it is read once, as a fallback, when the service starts without the app open.
         */
        fun forContainer(container: AppContainer): StreamResolver {
            val fallback = lazy { CredentialStore(EncryptedPrefs.open(container.app, "discair_settings")).load() }
            return StreamResolver(
                settings = { container.servers.takeIf { it.navidromeUrl.isNotBlank() } ?: fallback.value },
                quality = { StreamQuality(container.playerSettings.maxBitRate) },
            )
        }
    }
}
