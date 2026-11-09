package app.discair.player

import app.discair.model.PlayerFact

/** What the one-line field of the player shows. */
sealed interface PlayerLine {
    data class Lyric(val text: String) : PlayerLine
    data class Fact(val fact: PlayerFact) : PlayerLine
    /** Nothing: between lyric lines, switches off, or no facts yet. The slot keeps its height. */
    data object Empty : PlayerLine
}

/**
 * The rule carried over from the Mac player bar. A synced lyric line shows only for time-stamped lyrics. A song without
 * synced lyrics shows a fact instead. Between lines of timed lyrics the field stays empty (no fact fills the gap), so the
 * lyric does not flicker into a fact. With the quote switch off, facts take the field if their switch is on.
 */
object PlayerLineRules {
    fun choose(
        showLyrics: Boolean, showFacts: Boolean, lyricsTimed: Boolean, currentLyric: String?, fact: PlayerFact?,
    ): PlayerLine {
        if (showLyrics && lyricsTimed) {
            val text = currentLyric?.trim().orEmpty()
            return if (text.isNotEmpty()) PlayerLine.Lyric(text) else PlayerLine.Empty
        }
        return if (showFacts && fact != null) PlayerLine.Fact(fact) else PlayerLine.Empty
    }

    /** Facts rotate every 14 s while the song plays. */
    const val FACT_SECONDS = 14L
}

/** Facts the phone already knows from the queue item (no request). Every line is a statement about data the item has. */
object LibraryFacts {
    const val SOURCE = "Your library"

    fun make(item: QueueItem, thisYear: Int): List<PlayerFact> {
        val out = mutableListOf<PlayerFact>()
        fun add(kind: String, text: String) { out += PlayerFact(kind, text, SOURCE, fromServer = false) }
        val year = item.year
        if (year != null && year > 1000 && item.album.isNotBlank()) {
            val age = thisYear - year
            add("album_year", if (age > 0) "${item.album} came out in $year, $age year${if (age == 1) "" else "s"} ago" else "${item.album} came out in $year")
        }
        qualityLabel(item)?.let { add("file", "This file is $it") }
        return out
    }
}
