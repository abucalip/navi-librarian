package app.discair.player

import androidx.media3.common.MediaItem
import app.discair.AppContainer
import app.discair.data.CredentialStore
import app.discair.data.EncryptedPrefs

/**
 * Turns media items that carry only a song id into items with a signed stream URL.
 * Items with an invalid id, or with no saved Navidrome login, are dropped, so nothing is ever requested for them.
 */
class StreamResolver(
    private val settings: () -> app.discair.data.ServerSettings,
    private val quality: () -> StreamQuality = { StreamQuality.Original },
    private val format: () -> TranscodeFormat? = { null },
) {
    constructor(container: AppContainer) : this(
        settings = { CredentialStore(EncryptedPrefs.open(container.app, "discair_settings")).load() },
    )

    fun resolve(items: List<MediaItem>): List<MediaItem> {
        val saved = settings()
        if (saved.navidromeUrl.isBlank() || saved.navidromeUser.isBlank() || saved.navidromePassword.isBlank()) return emptyList()
        val builder = StreamUrlBuilder(saved.navidromeUrl, saved.navidromeUser, saved.navidromePassword)
        return items.mapNotNull { item ->
            if (!isValidSongId(item.mediaId)) return@mapNotNull null
            val url = builder.build(item.mediaId, quality(), format())
            item.buildUpon().setUri(url.toString()).build()
        }
    }
}
