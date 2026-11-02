package app.discair.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/** DTOs mirror the recorded fixtures in android/contract-fixtures. Unknown fields are ignored; optional ones default. */
val ApiJson = Json {
    ignoreUnknownKeys = true
    coerceInputValues = true
    explicitNulls = false
    isLenient = true
}

// ---- Library (GET /api/library/artists, /api/library/albums)

@Serializable
data class LibraryArtist(
    val id: String = "",
    val key: String = "",
    val name: String = "",
    @SerialName("album_count") val albumCount: Int = 0,
    val added: String? = null,
    @SerialName("artwork_url") val artworkUrl: String? = null,
)

@Serializable
data class LibraryAlbum(
    val id: String = "",
    val key: String = "",
    val name: String = "",
    val artist: String = "",
    @SerialName("artist_key") val artistKey: String = "",
    val year: Int? = null,
    val added: String? = null,
    @SerialName("song_count") val songCount: Int = 0,
    @SerialName("artwork_url") val artworkUrl: String? = null,
)

@Serializable
data class Page<T>(
    val items: List<T> = emptyList(),
    @SerialName("next_cursor") val nextCursor: String? = null,
    val total: Int? = null,
    @SerialName("index_state") val indexState: String = "",
)

// ---- Dashboard

@Serializable
data class GenreTile(val name: String = "", val tag: String = "", @SerialName("album_count") val albumCount: Int = 0)

@Serializable
data class GenreTiles(val items: List<GenreTile> = emptyList())

/** Album card for the Navidrome shelves (newest, recent, frequent). */
@Serializable
data class ShelfAlbum(
    val id: String = "",
    val name: String = "",
    val artist: String = "",
    @SerialName("artist_id") val artistId: String = "",
    val year: Int? = null,
    @SerialName("artwork_url") val artworkUrl: String? = null,
    val owned: Boolean = true,
)

@Serializable
data class Shelf(val items: List<ShelfAlbum> = emptyList())

/** A recommended album: Librarian decides the order and the reason; the app only shows them. */
@Serializable
data class Pick(
    val artist: String = "",
    val album: String = "",
    @SerialName("discovery_category") val category: String = "",
    @SerialName("dashboard_category") val dashboardCategory: String = "",
    val year: Int? = null,
    @SerialName("lastfm_listeners") val listeners: Long? = null,
    val genres: List<String> = emptyList(),
    val reason: String = "",
    @SerialName("similar_to") val similarTo: List<String> = emptyList(),
    @SerialName("suggested_tracks") val suggestedTracks: List<String> = emptyList(),
)

@Serializable
data class Picks(val items: List<Pick> = emptyList(), val count: Int = 0)

// ---- Page envelope shared by artist, album and genre pages

@Serializable
data class Section<T>(
    val available: Boolean = false,
    val complete: Boolean = false,
    val reason: String? = null,
    val items: List<T> = emptyList(),
)

@Serializable
data class SimilarArtist(
    val name: String = "",
    val key: String = "",
    val mbid: String? = null,
    val owned: Boolean = false,
    val id: String? = null,
    @SerialName("artwork_url") val artworkUrl: String? = null,
    val score: Double = 0.0,
    val reasons: List<String> = emptyList(),
)

@Serializable
data class Done(
    @SerialName("elapsed_ms") val elapsedMs: Int = 0,
    @SerialName("deadline_hit") val deadlineHit: Boolean = false,
    val partial: Boolean = false,
)

// ---- Artist page (GET /api/artists/{key})

@Serializable
data class ArtistInfo(
    val id: String? = null,
    val name: String = "",
    val mbid: String? = null,
    val owned: Boolean = false,
    @SerialName("album_count") val albumCount: Int = 0,
    val genre: String? = null,
)

@Serializable
data class ArtistSection(val available: Boolean = false, val artist: ArtistInfo? = null)

@Serializable
data class Bio(val text: String = "", val source: String? = null)

@Serializable
data class BioSection(val available: Boolean = false, val bio: Bio? = null)

@Serializable
data class OwnedAlbum(
    val name: String = "",
    val year: Int? = null,
    @SerialName("song_count") val songCount: Int = 0,
    val key: String = "",
    val id: String = "",
    @SerialName("artwork_url") val artworkUrl: String? = null,
)

@Serializable
data class TopSong(
    val rank: Int = 0,
    val name: String = "",
    @SerialName("listen_count") val listenCount: Long = 0,
    val source: String? = null,
    val owned: Boolean = false,
    val album: String? = null,
)

@Serializable
data class MissingAlbum(
    val name: String = "",
    val year: Int? = null,
    val key: String = "",
    val popularity: Long = 0,
)

@Serializable
data class Tag(val name: String = "")

@Serializable
data class ArtistSections(
    val artist: ArtistSection = ArtistSection(),
    @SerialName("owned_albums") val ownedAlbums: Section<OwnedAlbum> = Section(),
    val bio: BioSection = BioSection(),
    val tags: Section<Tag> = Section(),
    @SerialName("top_songs") val topSongs: Section<TopSong> = Section(),
    @SerialName("missing_albums") val missingAlbums: Section<MissingAlbum> = Section(),
    val similar: Section<SimilarArtist> = Section(),
)

@Serializable
data class ArtistPage(val sections: ArtistSections = ArtistSections(), val done: Done = Done())

// ---- Album page (GET /api/albums/{artist_key}/{album_key})

@Serializable
data class AlbumInfo(
    val name: String = "",
    val artist: String = "",
    @SerialName("artist_key") val artistKey: String = "",
    @SerialName("artist_id") val artistId: String? = null,
    val key: String = "",
    val year: Int? = null,
    val owned: Boolean = false,
    val id: String? = null,
    @SerialName("artwork_url") val artworkUrl: String? = null,
    @SerialName("song_count") val songCount: Int = 0,
    @SerialName("release_group_mbid") val releaseGroupMbid: String? = null,
)

@Serializable
data class AlbumSection(val available: Boolean = false, val album: AlbumInfo? = null)

@Serializable
data class GenreValue(val available: Boolean = false, val genre: String? = null)

@Serializable
data class Description(
    val paragraphs: List<String> = emptyList(),
    val source: String? = null,
    val url: String? = null,
    /** Set when the text is Wikipedia's (CC BY-SA 4.0). */
    val license: String? = null,
)

@Serializable
data class DescriptionSection(val available: Boolean = false, val description: Description? = null)

@Serializable
data class Track(
    @SerialName("track_number") val number: Int? = null,
    val title: String = "",
    @SerialName("duration_seconds") val durationSeconds: Int? = null,
    val owned: Boolean = false,
    /** The disc, sent only for an album whose library songs span several discs; [number] counts within it. */
    @SerialName("disc_number") val disc: Int? = null,
    /** The file's quality tag for an owned song ("FLAC 16/44", "MP3 320k"); absent when unknown. */
    val quality: String? = null,
)

@Serializable
data class SimilarAlbum(
    val name: String = "",
    val artist: String = "",
    @SerialName("artist_key") val artistKey: String = "",
    val key: String = "",
    val year: Int? = null,
    val owned: Boolean = false,
)

@Serializable
data class AlbumSections(
    val album: AlbumSection = AlbumSection(),
    val genre: GenreValue = GenreValue(),
    val description: DescriptionSection = DescriptionSection(),
    val tracks: Section<Track> = Section(),
    @SerialName("similar_artists") val similarArtists: Section<SimilarArtist> = Section(),
    @SerialName("similar_albums") val similarAlbums: Section<SimilarAlbum> = Section(),
)

@Serializable
data class AlbumPage(val sections: AlbumSections = AlbumSections(), val done: Done = Done())

// ---- Genre page (GET /api/genres/{tag})

@Serializable
data class GenreArtist(val owned: Boolean = false, val id: String? = null, val key: String = "", val name: String = "")

@Serializable
data class GenreAlbum(
    val owned: Boolean = false,
    val id: String? = null,
    val key: String = "",
    val name: String = "",
    val artist: String = "",
    @SerialName("artist_key") val artistKey: String = "",
    val year: Int? = null,
)

@Serializable
data class GenreSections(
    val artists: Section<GenreArtist> = Section(),
    val albums: Section<GenreAlbum> = Section(),
)

@Serializable
data class GenrePage(val sections: GenreSections = GenreSections(), val done: Done = Done())

// ---- Image lookup (GET /api/artwork, /api/artist-image)

@Serializable
data class ImageLookup(@SerialName("artwork_url") val artworkUrl: String? = null)

// ---- Album service links (GET /api/album-links): only services with an exact match are present

@Serializable
data class AlbumLinks(
    @SerialName("apple_music") val appleMusic: String? = null,
    val deezer: String? = null,
    val musicbrainz: String? = null,
    val listenbrainz: String? = null,
)

// ---- Album reviews (GET /api/album-reviews): up to three outlet summary lines; `retryable` when some outlets did not answer

@Serializable
data class AlbumReview(val source: String = "", val quote: String = "", val url: String = "")

@Serializable
data class AlbumReviews(val reviews: List<AlbumReview> = emptyList(), val retryable: Boolean = false)
