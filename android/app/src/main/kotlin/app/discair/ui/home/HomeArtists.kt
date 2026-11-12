package app.discair.ui.home

import app.discair.model.ShelfAlbum

/** One artist in Home's "In rotation" (Soft Brut) or "Artists" (Flow) module. The photo comes from `GET /api/artist-image` by [name]. */
data class HomeArtist(val name: String, val id: String)

/**
 * The artists the owner has been playing (docs/ANDROID_ART_THEMES_PROPOSAL.md, section 7). No endpoint is needed: take the
 * Recent and Frequent shelves already loaded for Home, keep the distinct artists in order of first appearance (Recent first),
 * up to [LIMIT].
 */
object HomeArtists {
    const val LIMIT = 8

    /** Fewer artists than this and the module shows its sentence instead of a row. */
    const val MIN_SHOWN = 3

    const val EMPTY_SENTENCE = "Play a few albums and the artists you return to appear here."

    fun from(recent: List<ShelfAlbum>, frequent: List<ShelfAlbum>): List<HomeArtist> {
        val seen = HashSet<String>()
        val out = ArrayList<HomeArtist>()
        for (a in recent.asSequence() + frequent.asSequence()) {
            val name = a.artist.trim()
            if (name.isEmpty()) continue
            // The same artist can arrive with and without an id, so the name is the identity.
            if (!seen.add(name.lowercase())) continue
            out += HomeArtist(name, a.artistId)
            if (out.size == LIMIT) break
        }
        return out
    }

    fun enough(artists: List<HomeArtist>) = artists.size >= MIN_SHOWN
}
