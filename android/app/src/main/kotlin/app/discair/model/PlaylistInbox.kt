package app.discair.model

import app.discair.player.QueueItem
import app.discair.player.isValidSongId
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class PlaylistInbox(
    val state: String,
    val items: List<InboxEdition>,
)

@Serializable
data class InboxEdition(
    @SerialName("edition_id") val id: Long,
    val title: String?,
    @SerialName("source_kind") val source: String,
    @SerialName("generated_at") val generatedAt: String?,
    @SerialName("total_count") val totalCount: Int,
    @SerialName("owned_count") val ownedCount: Int?,
    val tracks: List<InboxTrack> = emptyList(),
) {
    val displayTitle: String get() = title?.takeIf(String::isNotBlank) ?: "Untitled playlist"

    fun playbackItems(): List<QueueItem> = tracks.mapNotNull { track ->
        val songId = track.songId?.takeIf(::isValidSongId)
        if (track.matchState != "owned" || songId == null) return@mapNotNull null
        QueueItem(
            songId = songId,
            title = track.displayTitle,
            artist = track.artist.orEmpty(),
            album = track.album.orEmpty(),
            durationSec = ((track.durationMs ?: 0L) / 1000).coerceIn(0L, Int.MAX_VALUE.toLong()).toInt(),
        )
    }
}

@Serializable
data class InboxTrack(
    val position: Int,
    val title: String?,
    val artist: String?,
    val album: String?,
    @SerialName("duration_ms") val durationMs: Long?,
    @SerialName("match_state") val matchState: String?,
    @SerialName("song_id") val songId: String?,
) {
    val displayTitle: String get() = title?.takeIf(String::isNotBlank) ?: "Untitled track"
}
