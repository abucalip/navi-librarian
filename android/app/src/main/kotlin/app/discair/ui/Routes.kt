package app.discair.ui

import kotlinx.serialization.Serializable

@Serializable data object HomeRoute
@Serializable data object LibraryRoute
@Serializable data object DiscoverRoute
@Serializable data object SearchRoute
@Serializable data object SettingsRoute

@Serializable
data class ArtistRoute(val key: String, val name: String, val id: String? = null, val mbid: String? = null)

@Serializable
data class AlbumRoute(
    val key: String,
    val artist: String,
    val name: String,
    val id: String? = null,
    val year: Int? = null,
)

@Serializable
data class GenreRoute(val tag: String, val name: String)

/** Every name in the app opens its page (LIB-01); screens call these instead of knowing routes. */
class Opener(
    val artist: (name: String, key: String?, id: String?, mbid: String?) -> Unit,
    val album: (key: String, artist: String, name: String, id: String?, year: Int?) -> Unit,
    val genre: (tag: String, name: String) -> Unit,
    val back: () -> Unit,
)
