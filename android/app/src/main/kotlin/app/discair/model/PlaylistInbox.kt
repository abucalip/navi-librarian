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
    @SerialName("acquisition_status") val acquisitionStatus: String? = null,
    @SerialName("acquisition_key") val acquisitionKey: InboxAcquisitionKey? = null,
) {
    val displayTitle: String get() = title?.takeIf(String::isNotBlank) ?: "Untitled track"
}

@Serializable
data class InboxAcquisitionKey(val artist: String, @SerialName("job_album") val jobAlbum: String) {
    fun matches(job: AcquisitionJob): Boolean =
        job.isSong && artist == job.artist && jobAlbum == job.album
}

@Serializable
data class InboxDownload(
    val ok: Boolean,
    val status: String,
    val message: String? = null,
    val artist: String? = null,
    @SerialName("job_album") val jobAlbum: String? = null,
) {
    val acquisitionKey: InboxAcquisitionKey?
        get() = if (status != "identity_conflict" && artist != null && jobAlbum != null) InboxAcquisitionKey(artist, jobAlbum) else null
}

private val ACTIVE_INBOX_DOWNLOADS = setOf(
    "searching", "requested", "queued", "queued_unconfirmed", "already_in_progress",
    "downloading", "download_complete_waiting_for_folder", "importing", "monitoring",
    "recovery_started", "queue_uncertain", "source_switching", "skip_requested", "retry_requested",
)

private val RETRYABLE_INBOX_DOWNLOADS = setOf(
    "no_matches", "queue_failed", "settings_required", "slskd_error", "download_failed", "dismissed",
)

internal fun inboxDownloadActive(status: String?): Boolean = status in ACTIVE_INBOX_DOWNLOADS

internal fun inboxDownloadRetryable(status: String?): Boolean = status in RETRYABLE_INBOX_DOWNLOADS
