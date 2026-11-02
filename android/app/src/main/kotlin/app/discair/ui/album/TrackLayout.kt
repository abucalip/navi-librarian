package app.discair.ui.album

import app.discair.model.Track

/** True when the tracklist is shown disc by disc: every track names its disc and there is more than one. */
fun showsDiscs(tracks: List<Track>): Boolean =
    tracks.isNotEmpty() && tracks.all { it.disc != null } && tracks.map { it.disc }.toSet().size > 1

/** True when [index] is the first track of a disc that has a heading above it. */
fun startsDisc(tracks: List<Track>, index: Int): Boolean =
    showsDiscs(tracks) && (index == 0 || tracks[index].disc != tracks[index - 1].disc)

/** The number shown for a track: the server's number, else its place in its disc (or in the list). */
fun trackNumberShown(tracks: List<Track>, index: Int): Int =
    tracks[index].number ?: if (showsDiscs(tracks)) {
        tracks.subList(0, index + 1).count { it.disc == tracks[index].disc }
    } else {
        index + 1
    }
